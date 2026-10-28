"""Real Cloudflare REST/SSE and Ollama JSON/NDJSON transports; no production doubles."""

import json
from collections.abc import AsyncGenerator, AsyncIterator
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Protocol
from urllib.parse import quote

import httpx

from gateway.config import Provider
from gateway.models import Chunk, GatewayError, InferenceRequest, Usage

CLOUDFLARE_ORIGIN = "https://api.cloudflare.com"
MAX_FRAME = 65536
MAX_RESPONSE = 1048576


def obj(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GatewayError("upstream_schema")
    return value


def parse_json(value: str | bytes) -> dict[str, Any]:
    try:
        return obj(json.loads(value))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise GatewayError("upstream_schema") from exc


def count(value: Any) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise GatewayError("upstream_schema")
    return value


def usage(data: dict[str, Any], ollama: bool = False) -> Usage:
    u = data if ollama else obj(data.get("usage", {}))
    inp = count(u.get("prompt_eval_count" if ollama else "prompt_tokens"))
    out = count(u.get("eval_count" if ollama else "completion_tokens"))
    return Usage(
        input_tokens=inp,
        output_tokens=out,
        source="provider" if inp is not None or out is not None else "unavailable",
    )


def reject_error(data: dict[str, Any]) -> None:
    if data.get("error") or data.get("errors") or data.get("success") is False:
        # Application errors, including billing/policy/model/auth, are terminal.
        raise GatewayError("upstream_rejected")
    if data.get("refusal") or data.get("finish_reason") in ("content_filter", "refusal"):
        raise GatewayError("upstream_policy")


async def lines(response: httpx.Response) -> AsyncIterator[str]:
    """Bound memory before line decoding; HTTP chunk and UTF-8 boundaries are unrelated."""
    buffer = b""
    async for block in response.aiter_bytes():
        buffer += block
        if len(buffer) > MAX_FRAME and b"\n" not in buffer[: MAX_FRAME + 1]:
            raise GatewayError("upstream_frame_limit")
        while b"\n" in buffer:
            raw, buffer = buffer.split(b"\n", 1)
            if len(raw) > MAX_FRAME:
                raise GatewayError("upstream_frame_limit")
            try:
                yield raw.rstrip(b"\r").decode("utf-8")
            except UnicodeError as exc:
                raise GatewayError("upstream_schema") from exc
    if buffer:
        try:
            yield buffer.rstrip(b"\r").decode("utf-8")
        except UnicodeError as exc:
            raise GatewayError("upstream_schema") from exc


async def sse_data(response: httpx.Response) -> AsyncIterator[str]:
    data: list[str] = []
    size = 0
    async for line in lines(response):
        if not line:
            if data:
                yield "\n".join(data)
            data, size = [], 0
        elif line.startswith("data:"):
            value = line[5:]
            if value.startswith(" "):
                value = value[1:]
            size += len(value.encode())
            if size > MAX_FRAME:
                raise GatewayError("upstream_frame_limit")
            data.append(value)
    if data:
        # A frame must be terminated by a blank line; do not salvage truncated content.
        raise GatewayError("upstream_truncated")


async def bounded_body(response: httpx.Response) -> bytes:
    body = b""
    async for block in response.aiter_bytes():
        body += block
        if len(body) > MAX_RESPONSE:
            raise GatewayError("upstream_response_limit")
    return body


async def check_status(response: httpx.Response) -> None:
    if response.headers.get("content-encoding", "identity") != "identity":
        raise GatewayError("upstream_encoding")
    status = response.status_code
    if status == 200:
        return
    # No body, URL or headers ever escape into logs/errors. JSON errors on a 5xx
    # remain terminal if they indicate application policy/auth/billing rejection.
    body = await bounded_body(response)
    terminal = False
    if body.strip() and "json" in response.headers.get("content-type", ""):
        try:
            parsed = parse_json(body)
            text = json.dumps(parsed).lower()
            terminal = any(
                word in text
                for word in (
                    "billing",
                    "payment",
                    "credit",
                    "quota",
                    "auth",
                    "permission",
                    "policy",
                    "model",
                    "schema",
                )
            )
        except GatewayError:
            terminal = True
    retry_after = 0.0
    value = response.headers.get("retry-after", "")
    try:
        retry_after = max(0.0, float(value))
    except ValueError:
        try:
            retry_after = max(
                0.0, (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds()
            )
        except (ValueError, TypeError, OverflowError):
            pass
    if not 0 <= retry_after <= 604800:
        retry_after = 604800.0
    if status == 429:
        raise GatewayError(
            "upstream_rate_limit", 503, upstream_status=status, retry_after=retry_after
        )
    retryable = 500 <= status <= 599 and not terminal
    raise GatewayError(
        "upstream_unavailable" if retryable else "upstream_rejected",
        503 if retryable else 502,
        retryable=retryable,
        upstream_status=status,
        retry_after=retry_after,
    )


class Adapter(Protocol):
    def generate(self, request: InferenceRequest) -> AsyncGenerator[Chunk, None]: ...


class HTTPAdapter:
    def __init__(self, provider: Provider, client: httpx.AsyncClient) -> None:
        self.provider = provider
        self.client = client

    async def generate(self, request: InferenceRequest) -> AsyncGenerator[Chunk, None]:
        p = self.provider
        if p.type == "cloudflare":
            url = f"{CLOUDFLARE_ORIGIN}/client/v4/accounts/{p.account_id}/ai/run/{quote(p.model, safe='@/:-_.')}"
            headers = (
                {"Authorization": f"Bearer {p.api_token.get_secret_value()}"} if p.api_token else {}
            )
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})
            payload: dict[str, Any] = {
                "messages": messages,
                "stream": request.stream,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
            }
        else:
            url = p.endpoint.rstrip("/") + "/api/generate"
            headers = {}
            payload = {
                "model": p.model,
                "prompt": request.prompt,
                "system": request.system_prompt or "",
                "stream": request.stream,
                "options": {"num_predict": request.max_tokens, "temperature": request.temperature},
            }
        try:
            async with self.client.stream("POST", url, headers=headers, json=payload) as response:
                await check_status(response)
                content_type = response.headers.get("content-type", "").split(";")[0]
                if not request.stream:
                    if content_type != "application/json":
                        raise GatewayError("upstream_schema")
                    data = parse_json(await bounded_body(response))
                    reject_error(data)
                    result = obj(data.get("result")) if p.type == "cloudflare" else data
                    reject_error(result)
                    text = result.get("response")
                    if not isinstance(text, str) or not text:
                        raise GatewayError("upstream_schema")
                    if p.type == "ollama" and (
                        result.get("done") is not True or result.get("model") != p.model
                    ):
                        raise GatewayError("upstream_schema")
                    yield Chunk(response=text, done=True, usage=usage(result, p.type == "ollama"))
                    return
                if p.type == "cloudflare":
                    if content_type != "text/event-stream":
                        raise GatewayError("upstream_schema")
                    measured = Usage()
                    async for raw in sse_data(response):
                        if raw == "[DONE]":
                            yield Chunk(done=True, usage=measured)
                            return
                        data = parse_json(raw)
                        reject_error(data)
                        if "usage" in data:
                            measured = usage(data)
                        text = data.get("response", "")
                        if not isinstance(text, str) or not any(
                            k in data for k in ("response", "usage")
                        ):
                            raise GatewayError("upstream_schema")
                        if text:
                            yield Chunk(response=text)
                else:
                    if content_type not in ("application/x-ndjson", "application/json"):
                        raise GatewayError("upstream_schema")
                    async for raw in lines(response):
                        if not raw:
                            continue
                        data = parse_json(raw)
                        reject_error(data)
                        text = data.get("response")
                        if (
                            not isinstance(text, str)
                            or type(data.get("done")) is not bool
                            or data.get("model") != p.model
                        ):
                            raise GatewayError("upstream_schema")
                        done = data["done"]
                        if text or done:
                            yield Chunk(
                                response=text, done=done, usage=usage(data, True) if done else None
                            )
                        if done:
                            return
                raise GatewayError("upstream_truncated")
        except httpx.TimeoutException as exc:
            raise GatewayError("upstream_timeout", 504, retryable=True) from exc
        except httpx.TransportError as exc:
            raise GatewayError("upstream_connection", 503, retryable=True) from exc
