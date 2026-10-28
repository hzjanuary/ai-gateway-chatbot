"""Authenticated headless REST/SSE service with minimal public liveness."""

import asyncio
import json
import secrets
import uuid
from collections.abc import AsyncIterator
from contextlib import aclosing, asynccontextmanager
from typing import Annotated, Any

import httpx
from fastapi import Depends, FastAPI, Query, Request, Security
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from gateway import __version__
from gateway.config import Settings, load_settings, token_hash, valid_token
from gateway.models import CompletionResponse, ErrorEnvelope, GatewayError, InferenceRequest, Usage
from gateway.router import Router


class BodyLimit:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        chunks: list[Message] = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > 65536:
                response = JSONResponse(GatewayError("body_limit", 413).public(request_id), 413)
                await response(scope, receive, send)
                return
            chunks.append(message)
            if not message.get("more_body", False):
                break

        async def replay() -> Message:
            if chunks:
                return chunks.pop(0)
            return await receive()

        async def safe_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).extend(
                    [
                        (b"x-request-id", request_id.encode()),
                        (b"x-content-type-options", b"nosniff"),
                        (b"cache-control", b"no-store"),
                    ]
                )
            await send(message)

        await self.app(scope, replay, safe_send)


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configured = settings or load_settings()
        # No proxy env, redirects, retries or auto network probes.
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(configured.attempt_seconds),
            trust_env=False,
            follow_redirects=False,
            limits=httpx.Limits(max_connections=64),
        ) as client:
            app.state.router = Router(configured, client)
            yield

    app = FastAPI(
        title="OSS Inference Gateway",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        responses={
            status: {"model": ErrorEnvelope} for status in (401, 403, 413, 422, 429, 502, 503, 504)
        },
    )
    app.add_middleware(BodyLimit)

    def router(request: Request) -> Router:
        return request.app.state.router  # type: ignore[no-any-return]

    async def authorize(request: Request, role: str, authorization: str | None) -> None:
        cfg = router(request).settings
        expected = cfg.inference_hash if role == "inference" else cfg.admin_hash
        other = cfg.admin_hash if role == "inference" else cfg.inference_hash
        if not expected:
            raise GatewayError("authentication_not_configured", 503)
        value = (
            authorization.removeprefix("Bearer ")
            if authorization and authorization.startswith("Bearer ")
            else ""
        )
        digest = token_hash(value)
        if valid_token(value) and secrets.compare_digest(digest, expected):
            return
        if value and other and secrets.compare_digest(digest, other):
            raise GatewayError("wrong_role", 403)
        raise GatewayError("unauthorized", 401)

    inference_bearer = HTTPBearer(auto_error=False, scheme_name="InferenceBearer")
    admin_bearer = HTTPBearer(auto_error=False, scheme_name="AdminBearer")

    async def inference_auth(
        request: Request,
        credentials: Annotated[
            HTTPAuthorizationCredentials | None, Security(inference_bearer)
        ] = None,
    ) -> None:
        await authorize(
            request, "inference", "Bearer " + credentials.credentials if credentials else None
        )

    async def admin_auth(
        request: Request,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Security(admin_bearer)] = None,
    ) -> None:
        await authorize(
            request, "admin", "Bearer " + credentials.credentials if credentials else None
        )

    @app.exception_handler(GatewayError)
    async def gateway_error(request: Request, exc: GatewayError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status == 401 else {}
        return JSONResponse(exc.public(request.state.request_id), exc.status, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic errors include raw input. Never return them, even for bad auth headers.
        return JSONResponse(
            GatewayError("invalid_request", 422).public(request.state.request_id), 422
        )

    @app.get("/")
    @app.get("/health")
    async def health() -> dict[str, object]:
        return {"status": "alive", "version": __version__}

    @app.get("/ready")
    async def ready(request: Request) -> JSONResponse:
        is_ready = router(request).ready()
        return JSONResponse(
            {"ready": is_ready, "probe": "configuration_only"}, 200 if is_ready else 503
        )

    @app.get("/v1/models", dependencies=[Depends(inference_auth)])
    async def models(request: Request) -> dict[str, object]:
        return {
            "models": [
                {"provider": n.config.id, "type": n.config.type, "model": n.config.model}
                for n in router(request).nodes
                if n.config.authorized
            ]
        }

    def event(name: str, payload: dict[str, Any]) -> str:
        return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    @app.post(
        "/ask",
        dependencies=[Depends(inference_auth)],
        deprecated=True,
        response_model=CompletionResponse,
    )
    @app.post(
        "/v1/inference",
        dependencies=[Depends(inference_auth)],
        response_model=CompletionResponse,
        responses={200: {"content": {"text/event-stream": {"schema": {"type": "string"}}}}},
    )
    async def inference(body: InferenceRequest, request: Request) -> Any:
        request_id = request.state.request_id
        sources: list[dict[str, str]] = []
        stream = router(request).generate(body, request_id, sources)

        async def disconnected() -> None:
            while True:
                if (await request.receive())["type"] == "http.disconnect":
                    return

        pending = asyncio.ensure_future(anext(stream))
        watcher = asyncio.create_task(disconnected())
        try:
            done, _ = await asyncio.wait([pending, watcher], return_when=asyncio.FIRST_COMPLETED)
            if watcher in done:
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)
                await stream.aclose()
                return Response(status_code=499)
            first = pending.result()
        except BaseException:
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
            await stream.aclose()
            raise
        finally:
            watcher.cancel()
            await asyncio.gather(watcher, return_exceptions=True)
        node, chunk, attempts = first
        identity = {
            "provider": node.config.id,
            "provider_type": node.config.type,
            "model": node.config.model,
            "request_id": request_id,
            "attempts": attempts,
            "sources": sources,
        }
        if not body.stream:
            await stream.aclose()
            return {
                **identity,
                "response": chunk.response,
                "usage": (chunk.usage or Usage()).model_dump(),
            }

        async def output() -> AsyncIterator[str]:
            async with aclosing(stream):
                try:
                    yield event("start", identity)
                    item = chunk
                    while True:
                        if item.response:
                            yield event("delta", {"response": item.response})
                        if item.done:
                            yield event("usage", (item.usage or Usage()).model_dump())
                            yield event("end", {"request_id": request_id})
                            return
                        _, item, _ = await anext(stream)
                except GatewayError as exc:
                    yield event("error", exc.public(request_id))

        return StreamingResponse(
            output(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"}
        )

    admin = [Depends(admin_auth)]

    @app.get("/v1/status", dependencies=admin)
    @app.get("/v1/providers", dependencies=admin)
    @app.get("/v1/monitoring/stats", dependencies=admin)
    @app.get("/v1/monitoring/health", dependencies=admin)
    async def stats(request: Request) -> dict[str, Any]:
        return router(request).stats()

    @app.get("/v1/monitoring/logs", dependencies=admin)
    async def logs(
        request: Request, count: int = Query(default=10, ge=1, le=100)
    ) -> dict[str, object]:
        return {"logs": list(router(request).logs)[-count:]}

    class Confirmation(BaseModel):
        model_config = ConfigDict(extra="forbid", strict=True)
        confirm: bool

    @app.post("/v1/providers/reset", dependencies=admin)
    async def reset(body: Confirmation, request: Request) -> dict[str, bool]:
        if not body.confirm:
            raise GatewayError("confirmation_required", 422)
        router(request).reset_circuits()
        return {"circuits_reset": True, "quota_reset": False}

    @app.post("/v1/providers/strategy/{strategy}", dependencies=admin)
    async def strategy(strategy: str, request: Request) -> dict[str, str]:
        if strategy not in ("round_robin", "random", "least_used"):
            raise GatewayError("invalid_strategy", 422)
        router(request).strategy = strategy  # type: ignore[assignment]
        return {"strategy": strategy}

    return app


app = create_app()
