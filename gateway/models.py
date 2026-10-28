"""Strict public and normalized transport contracts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class InferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    prompt: str = Field(min_length=1, max_length=32000)
    system_prompt: str | None = Field(default=None, max_length=4000)
    max_tokens: int = Field(default=512, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0, le=2, allow_inf_nan=False)
    stream: bool = False
    provider: str | None = Field(default=None, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    allow_fallback: bool = False
    allow_policy_fallback: bool = False
    max_attempts: int = Field(default=1, ge=1, le=3)
    web_enrichment: bool = False


class Usage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    source: Literal["provider", "unavailable"] = "unavailable"


class Chunk(BaseModel):
    response: str = ""
    done: bool = False
    usage: Usage | None = None


class GatewayError(Exception):
    def __init__(
        self,
        code: str,
        status: int = 502,
        *,
        retryable: bool = False,
        upstream_status: int | None = None,
        retry_after: float = 0,
    ) -> None:
        self.code = code
        self.status = status
        self.retryable = retryable
        self.upstream_status = upstream_status
        self.retry_after = retry_after
        super().__init__(code)

    def public(self, request_id: str) -> dict[str, object]:
        result: dict[str, object] = {
            "code": self.code,
            "message": "Gateway request failed; consult sanitized operator diagnostics.",
            "request_id": request_id,
        }
        if self.upstream_status is not None:
            result["upstream_status"] = self.upstream_status
        return {"error": result}


class CompletionResponse(BaseModel):
    response: str
    provider: str
    provider_type: Literal["cloudflare", "ollama"]
    model: str
    request_id: str
    attempts: int
    usage: Usage
    sources: list[dict[str, str]]


class ErrorDetails(BaseModel):
    code: str
    message: str
    request_id: str
    upstream_status: int | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetails
