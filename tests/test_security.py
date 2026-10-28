import json
import stat
import subprocess
import sys

import pytest
from pydantic import ValidationError

from gateway.config import ConfigError, Provider, Settings, initialize, load_settings, token_hash
from tests.conftest import ADMIN, INFERENCE, UPSTREAM, Reply, client_for, cloud, local


def test_private_explicit_idempotent_init(tmp_path):
    directory = tmp_path / "private"
    assert initialize(directory, True)
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    assert not initialize(directory, True)
    assert before == {p.name: p.read_bytes() for p in directory.iterdir()}
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in directory.iterdir())
    settings = load_settings(directory)
    assert settings.inference_hash == token_hash(
        (directory / "inference.token").read_text().strip()
    )
    assert settings.admin_hash != settings.inference_hash
    assert "token_urlsafe" not in (directory / "settings.json").read_text()


@pytest.mark.parametrize("token", ["", "your_secure_access_token_here", "a" * 64, "change_me_" * 8])
def test_missing_or_placeholder_token_fails_closed(monkeypatch, tmp_path, token):
    monkeypatch.setenv("GATEWAY_INFERENCE_TOKEN", token)
    with pytest.raises(ConfigError):
        load_settings(tmp_path)


def test_missing_config_zero_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("GATEWAY_CONFIG_DIR", str(tmp_path))
    settings = load_settings()
    assert (
        settings.providers == [] and settings.inference_hash is None and settings.admin_hash is None
    )
    from fastapi.testclient import TestClient

    from gateway.api import create_app

    with TestClient(create_app(settings)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503
        assert client.post("/v1/inference", json={"prompt": "x"}).status_code == 503
        assert (
            client.get("/v1/monitoring/stats", headers={"Authorization": "Bearer x"}).status_code
            == 503
        )


def test_reject_private_file_permissions_and_symlink(tmp_path):
    initialize(tmp_path / "private", True)
    path = tmp_path / "private/settings.json"
    path.chmod(0o644)
    with pytest.raises(ConfigError):
        load_settings(path.parent)
    target = tmp_path / "other"
    target.mkdir(mode=0o700)
    (target / "settings.json").symlink_to(path)
    with pytest.raises(ConfigError):
        load_settings(target)


def test_bad_configuration_never_prints_raw_input(tmp_path, capsys):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"inference_hash": UPSTREAM}))
    path.chmod(0o600)
    with pytest.raises(ConfigError) as result:
        load_settings(tmp_path)
    assert UPSTREAM not in str(result.value)
    assert result.value.__suppress_context__


@pytest.mark.parametrize(
    "route,method",
    [
        ("/v1/monitoring/stats", "get"),
        ("/v1/monitoring/logs", "get"),
        ("/v1/monitoring/health", "get"),
        ("/v1/providers", "get"),
        ("/v1/status", "get"),
        ("/v1/providers/reset", "post"),
        ("/v1/providers/strategy/random", "post"),
    ],
)
def test_admin_boundary(auth, admin, route, method):
    with client_for() as client:
        function = getattr(client, method)
        assert function(route).status_code == 401
        assert function(route, headers=auth).status_code == 403
        response = function(route, headers=admin)
        assert response.status_code in (200, 422)
        assert client.delete("/v1/monitoring/logs", headers=admin).status_code == 405


def test_inference_boundary_and_legacy(auth, admin):
    with client_for() as client:
        for endpoint in ("/v1/inference", "/ask"):
            assert client.post(endpoint, json={"prompt": "x"}).status_code == 401
            assert client.post(endpoint, headers=admin, json={"prompt": "x"}).status_code == 403
            assert client.post(endpoint, headers=auth, json={"prompt": "x"}).status_code == 503
        assert client.get("/v1/models", headers=admin).status_code == 403
        assert client.get("/v1/models", headers=auth).status_code == 200
        assert set(client.get("/health").json()) == {"status", "version"}


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://169.254.169.254",
        "http://metadata.google.internal",
        "http://localhost:11434",
        "http://user:pass@127.0.0.1",
        "http://127.0.0.1/path",
        "http://127.0.0.1?x=y",
        "http://127.0.0.1#x",
        "ftp://127.0.0.1",
        "http://0.0.0.0",
        "http://224.0.0.1",
        "http://8.8.8.8",
        "http://[::ffff:169.254.169.254]",
    ],
)
def test_ssrf_rejected(endpoint):
    with pytest.raises((ValidationError, ValueError)):
        local(endpoint)


def test_private_zone_is_explicit():
    with pytest.raises(ValidationError):
        Provider(
            id="x",
            type="ollama",
            endpoint="http://127.0.0.1:11434",
            model="llama3",
            billing="local",
        )
    assert local("http://127.0.0.1:11434").allow_private


def test_cloudflare_not_operator_redirectable():
    with pytest.raises(ValidationError):
        cloud(endpoint="https://evil.example")
    with pytest.raises(ValidationError):
        Settings(
            providers=[cloud(), cloud(2).model_copy(update={"account_id": cloud().account_id})]
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("endpoint", "http://127.0.0.1:9"),
        ("headers", {"Authorization": "stolen"}),
        ("max_tokens", 4097),
        ("temperature", "nan"),
        ("max_attempts", 4),
        ("prompt", ""),
        ("research_mode", True),
    ],
)
def test_request_validation_no_echo(upstream, auth, field, value):
    with client_for([cloud()]) as client:
        data = {"prompt": "SENSITIVE-PROMPT-CANARY", field: value}
        result = client.post("/v1/inference", headers=auth, json=data)
        assert result.status_code == 422
        assert "SENSITIVE" not in result.text and "stolen" not in result.text
    assert not upstream.calls


def test_body_limit_streamed_and_content_length(auth):
    with client_for() as client:
        result = client.post("/v1/inference", headers=auth, content=b"x" * 65537)
        assert result.status_code == 413
        result = client.post(
            "/v1/inference", headers=auth, content=iter([b"x" * 32000, b"x" * 34000])
        )
        assert result.status_code == 413


def test_sanitized_logs_and_errors(upstream, auth, admin, caplog):
    canary = "PRIVATE-PROMPT-COMPLETION-NEVER-LOG"
    upstream.replies.append(
        Reply(status=403, body=json.dumps({"error": canary + UPSTREAM}).encode())
    )
    with client_for([cloud()]) as client:
        response = client.post("/v1/inference", headers=auth, json={"prompt": canary})
        logs = client.get("/v1/monitoring/logs", headers=admin).text
        stats = client.get("/v1/monitoring/stats", headers=admin).text
        for text in (logs, stats, response.text, caplog.text):
            assert all(secret not in text for secret in (canary, INFERENCE, ADMIN, UPSTREAM))


def test_doctor_and_metadata_never_generate(tmp_path):
    path = tmp_path / "private"
    initialize(path, True)
    for command in (["doctor"], ["provider", "list"], ["provider", "test-metadata"]):
        result = subprocess.run(
            [sys.executable, "-m", "gateway.cli", "--config-dir", str(path), *command],
            capture_output=True,
            text=True,
            check=True,
        )
        assert json.loads(result.stdout)["network_calls"] == 0
        for token_file in path.glob("*.token"):
            assert token_file.read_text().strip() not in result.stdout + result.stderr


def test_unapproved_provider_no_traffic(upstream, auth):
    provider = cloud().model_copy(update={"authorized": False})
    with client_for([provider]) as client:
        assert client.post("/v1/inference", headers=auth, json={"prompt": "x"}).status_code == 503
    assert not upstream.calls


def test_handwritten_hash_cannot_enable_placeholder_token():
    from fastapi.testclient import TestClient

    from gateway.api import create_app

    with TestClient(create_app(Settings(inference_hash=token_hash("placeholder")))) as client:
        assert (
            client.get("/v1/models", headers={"Authorization": "Bearer placeholder"}).status_code
            == 401
        )


def test_openapi_and_settings_schema_match_checked_in_contract():
    from pathlib import Path

    from gateway.api import create_app

    assert create_app().openapi() == json.loads(Path("docs/api/openapi.json").read_text())
    assert Settings.model_json_schema() == json.loads(
        Path("docs/api/settings.schema.json").read_text()
    )
