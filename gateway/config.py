"""Explicit operator configuration; private token files are never printed."""

import hashlib
import ipaddress
import json
import os
import secrets
import stat
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, model_validator


class ConfigError(Exception):
    """Safe message only: never include config values or Pydantic input dumps."""


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def valid_token(value: str) -> bool:
    return (
        len(value) >= 32
        and len(set(value)) >= 12
        and not any(x in value.lower() for x in ("your_", "change", "placeholder", "example"))
        and all(33 <= ord(c) <= 126 for c in value)
    )


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class Provider(StrictModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    type: Literal["cloudflare", "ollama"]
    model: str = Field(min_length=1, max_length=160, pattern=r"^[a-zA-Z0-9_@./:-]+$")
    authorized: bool = False
    policy_group: str = Field(default="local", pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    billing: Literal["local", "unverified", "approved"] = "unverified"
    account_id: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{32}$")
    api_token: SecretStr | None = Field(default=None, repr=False)
    endpoint: str = "https://api.cloudflare.com"
    allow_private: bool = False
    max_concurrent: int = Field(default=1, ge=1, le=32)
    call_limit: int = Field(default=100, ge=1, le=1000000)
    token_limit: int = Field(default=100000, ge=1, le=100000000)

    @model_validator(mode="after")
    def validate_policy(self) -> "Provider":
        if ".." in self.model.split("/") or "//" in self.model:
            raise ValueError("invalid model")
        if self.type == "cloudflare":
            if (
                self.endpoint != "https://api.cloudflare.com"
                or not self.account_id
                or not self.api_token
                or not valid_token(self.api_token.get_secret_value())
                or self.billing != "approved"
                or self.allow_private
                or not self.model.startswith("@cf/")
            ):
                raise ValueError(
                    "Cloudflare requires explicit account, credential and billing approval"
                )
        else:
            parts = urlsplit(self.endpoint)
            if (
                parts.username
                or parts.password
                or parts.query
                or parts.fragment
                or parts.path not in ("", "/")
                or parts.scheme not in ("http", "https")
                or not parts.hostname
                or self.api_token
                or self.account_id
            ):
                raise ValueError("invalid Ollama endpoint")
            # Literal addresses prevent DNS rebinding and proxy/metadata hostname tricks.
            try:
                address = ipaddress.ip_address(parts.hostname)
                port = parts.port
            except ValueError as exc:
                raise ValueError("Ollama requires an IP literal") from exc
            if port is not None and not 1 <= port <= 65535:
                raise ValueError("invalid port")
            if (
                address.is_unspecified
                or address.is_multicast
                or address.is_link_local
                or address.is_reserved
            ):
                raise ValueError("unsafe endpoint address")
            if not address.is_global and not self.allow_private:
                raise ValueError("local/private Ollama requires explicit trust-zone approval")
            if address.is_global and parts.scheme != "https":
                raise ValueError("remote Ollama requires TLS")
            if self.billing != "local":
                raise ValueError("Ollama requires declared local billing")
        return self


class Settings(StrictModel):
    inference_hash: str | None = Field(default=None, repr=False, pattern=r"^[a-f0-9]{64}$")
    admin_hash: str | None = Field(default=None, repr=False, pattern=r"^[a-f0-9]{64}$")
    providers: list[Provider] = Field(default_factory=list, max_length=32)
    strategy: Literal["round_robin", "least_used", "random"] = "round_robin"
    max_concurrent: int = Field(default=4, ge=1, le=128)
    deadline_seconds: float = Field(default=60.0, ge=0.05, le=300)
    attempt_seconds: float = Field(default=20.0, ge=0.02, le=120)
    cooldown_seconds: float = Field(default=30.0, ge=0.01, le=86400)
    max_attempts: int = Field(default=3, ge=1, le=3)
    request_token_budget: int = Field(default=4096, ge=1, le=12288)
    web_enrichment_enabled: bool = False

    @model_validator(mode="after")
    def unique_registry(self) -> "Settings":
        ids = [p.id for p in self.providers]
        identities = [
            (p.type, p.account_id if p.type == "cloudflare" else p.endpoint.rstrip("/"))
            for p in self.providers
        ]
        if len(ids) != len(set(ids)) or len(identities) != len(set(identities)):
            raise ValueError("duplicate providers or upstream quota identity")
        if self.admin_hash and self.admin_hash == self.inference_hash:
            raise ValueError("role tokens must differ")
        if any(h == token_hash("") for h in (self.admin_hash, self.inference_hash)):
            raise ValueError("empty token hash")
        return self


def config_dir() -> Path:
    return Path(
        os.environ.get("GATEWAY_CONFIG_DIR", str(Path.home() / ".config/inference-gateway"))
    )


def private_read(path: Path) -> str:
    # O_NOFOLLOW, owner/mode/type checks apply to the file actually read.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.geteuid():
            raise ConfigError("Configuration must be an owned regular file with mode 0600")
        if info.st_size > 262144:
            raise ConfigError("Configuration file exceeds size limit")
        return handle.read(262145)


def load_settings(directory: Path | None = None) -> Settings:
    path = (directory or config_dir()) / "settings.json"
    try:
        result = Settings.model_validate_json(private_read(path)) if path.exists() else Settings()
        for role in ("inference", "admin"):
            value = os.environ.get(f"GATEWAY_{role.upper()}_TOKEN")
            if value is not None:
                if not valid_token(value):
                    raise ConfigError("Invalid role token; use explicit config init")
                result = result.model_copy(update={f"{role}_hash": token_hash(value)})
        return Settings.model_validate(result.model_dump())
    except (OSError, ValueError, ValidationError):
        raise ConfigError("Invalid or inaccessible private gateway configuration") from None


def initialize(directory: Path, admin: bool = False) -> bool:
    """Explicit bootstrap only. Idempotent; never replace existing files or print tokens."""
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = directory.lstat()
    if directory.is_symlink() or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise ConfigError(
            "Configuration directory must be owned, private (0700), and not a symlink"
        )
    settings_path = directory / "settings.json"
    if settings_path.exists():
        load_settings(directory)
        return False
    tokens = {"inference": secrets.token_urlsafe(48)}
    if admin:
        tokens["admin"] = secrets.token_urlsafe(48)
    for role, token in tokens.items():
        path = directory / f"{role}.token"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(token + "\n")
    settings = Settings.model_validate(
        {f"{role}_hash": token_hash(token) for role, token in tokens.items()}
    )
    fd = os.open(settings_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(json.dumps(settings.model_dump(), indent=2) + "\n")
    return True
