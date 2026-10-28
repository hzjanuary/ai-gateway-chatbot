"""Single event-loop reservations, explicit fallback and bounded circuit state."""

import asyncio
import random
import time
from collections import deque
from collections.abc import AsyncGenerator
from contextlib import aclosing
from dataclasses import dataclass
from typing import Any

import httpx

from gateway.adapters import HTTPAdapter
from gateway.config import Provider, Settings
from gateway.enrichment import enrich
from gateway.models import Chunk, GatewayError, InferenceRequest, Usage


@dataclass
class Node:
    config: Provider
    calls: int = 0
    reserved_tokens: int = 0
    successes: int = 0
    failures: int = 0
    cancellations: int = 0
    unknown_usage_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    in_flight: int = 0
    open_until: float = 0
    disabled: bool = False
    last_error: str | None = None

    def available(self, now: float, tokens: int = 1) -> bool:
        return (
            self.config.authorized
            and not self.disabled
            and self.open_until <= now
            and self.in_flight < (1 if self.open_until else self.config.max_concurrent)
            and self.calls < self.config.call_limit
            and self.reserved_tokens + tokens <= self.config.token_limit
        )


class Router:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client
        self.nodes = [Node(p) for p in settings.providers]
        self.active = 0
        self.cursor = 0
        self.strategy = settings.strategy
        self.logs: deque[dict[str, Any]] = deque(maxlen=100)
        self.web_queries = 0

    def audit(self, request_id: str, code: str, provider: str | None = None) -> None:
        # Values come only from generated IDs, enums, validated registry IDs.
        self.logs.append({"request_id": request_id, "code": code, "provider": provider})

    def ready(self) -> bool:
        return bool(self.settings.inference_hash) and any(
            n.available(time.monotonic()) for n in self.nodes
        )

    def stats(self) -> dict[str, Any]:
        now = time.monotonic()
        return {
            "strategy": self.strategy,
            "active_requests": self.active,
            "state_persistence": "ephemeral_single_process",
            "web_queries": self.web_queries,
            "providers": [
                {
                    "id": n.config.id,
                    "type": n.config.type,
                    "model": n.config.model,
                    "authorized": n.config.authorized,
                    "available": n.available(now),
                    "circuit": (
                        "disabled"
                        if n.disabled
                        else (
                            "open"
                            if n.open_until > now
                            else "half_open" if n.open_until else "closed"
                        )
                    ),
                    "cooldown_seconds": max(0, round(n.open_until - now, 2)),
                    "calls": n.calls,
                    "reserved_tokens": n.reserved_tokens,
                    "successes": n.successes,
                    "failures": n.failures,
                    "cancellations": n.cancellations,
                    "in_flight": n.in_flight,
                    "input_tokens": n.input_tokens,
                    "output_tokens": n.output_tokens,
                    "unknown_usage_calls": n.unknown_usage_calls,
                    "last_error": n.last_error,
                }
                for n in self.nodes
            ],
        }

    def reset_circuits(self) -> None:
        if self.active:
            raise GatewayError("requests_active", 409)
        for node in self.nodes:
            node.open_until = 0
            node.disabled = False
            node.last_error = None

    def candidates(self, request: InferenceRequest) -> list[Node]:
        pool = [n for n in self.nodes if n.config.authorized]
        if request.provider:
            matching = [n for n in pool if n.config.id == request.provider]
            if not matching:
                raise GatewayError("provider_not_registered", 422)
            first = matching[0]
        else:
            if not pool:
                raise GatewayError("no_provider", 503)
            available = [n for n in pool if n.available(time.monotonic(), request.max_tokens)]
            if not available:
                raise GatewayError("providers_exhausted", 503)
            if self.strategy == "least_used":
                first = min(available, key=lambda n: n.calls)
            elif self.strategy == "random":
                first = random.choice(available)
            else:
                first = available[self.cursor % len(available)]
                self.cursor += 1
        same_policy = [
            n
            for n in pool
            if n is not first
            and n.config.policy_group == first.config.policy_group
            and n.config.billing == first.config.billing
        ]
        return [first, *same_policy] if request.allow_fallback else [first]

    async def generate(
        self,
        request: InferenceRequest,
        request_id: str,
        sources: list[dict[str, str]] | None = None,
    ) -> AsyncGenerator[tuple[Node, Chunk, int], None]:
        if self.active >= self.settings.max_concurrent:
            raise GatewayError("concurrency_limit", 429)
        nodes = self.candidates(request)
        self.active += 1
        deadline = time.monotonic() + self.settings.deadline_seconds
        attempts = 0
        reserved = 0
        last_error = GatewayError("providers_exhausted", 503)
        try:
            if request.web_enrichment:
                if not self.settings.web_enrichment_enabled:
                    raise GatewayError("web_enrichment_disabled", 422)
                self.web_queries += 1
                try:
                    prompt, found = await asyncio.wait_for(
                        enrich(self.client, request.prompt), min(5, self.settings.deadline_seconds)
                    )
                except TimeoutError as exc:
                    raise GatewayError("deadline", 504) from exc
                if sources is not None:
                    sources.extend(found)
                request = request.model_copy(update={"prompt": prompt})
            for node in nodes:
                if attempts >= min(request.max_attempts, self.settings.max_attempts):
                    break
                if not node.available(time.monotonic(), request.max_tokens):
                    continue
                if reserved + request.max_tokens > self.settings.request_token_budget:
                    raise GatewayError("request_token_budget", 503)
                if time.monotonic() >= deadline:
                    raise GatewayError("deadline", 504)
                attempts += 1
                reserved += request.max_tokens
                node.calls += 1
                node.reserved_tokens += request.max_tokens
                node.in_flight += 1
                emitted = False
                accounted = False
                finished = False
                output_bytes = 0
                attempt_deadline = min(deadline, time.monotonic() + self.settings.attempt_seconds)
                try:
                    async with aclosing(
                        HTTPAdapter(node.config, self.client).generate(request)
                    ) as stream:
                        while True:
                            remaining = attempt_deadline - time.monotonic()
                            if remaining <= 0:
                                raise GatewayError(
                                    (
                                        "deadline"
                                        if deadline <= attempt_deadline
                                        else "upstream_timeout"
                                    ),
                                    504,
                                    retryable=deadline > attempt_deadline,
                                )
                            try:
                                chunk = await asyncio.wait_for(anext(stream), remaining)
                            except TimeoutError as exc:
                                raise GatewayError(
                                    (
                                        "deadline"
                                        if deadline <= attempt_deadline
                                        else "upstream_timeout"
                                    ),
                                    504,
                                    retryable=deadline > attempt_deadline,
                                ) from exc
                            except StopAsyncIteration as exc:
                                raise GatewayError("upstream_truncated") from exc
                            output_bytes += len(chunk.response.encode())
                            if output_bytes > min(1048576, request.max_tokens * 64):
                                raise GatewayError("output_limit")
                            if chunk.usage:
                                self.record_usage(node, chunk.usage)
                                accounted = True
                                if (
                                    chunk.usage.output_tokens is not None
                                    and chunk.usage.output_tokens > request.max_tokens
                                ):
                                    raise GatewayError("upstream_token_limit")
                            emitted = True
                            if chunk.done:
                                finished = True
                                node.successes += 1
                                node.open_until = 0
                                node.last_error = None
                                self.audit(request_id, "completed", node.config.id)
                            yield node, chunk, attempts
                            if chunk.done:
                                return
                except GatewayError as exc:
                    node.failures += 1
                    node.last_error = exc.code
                    self.audit(request_id, exc.code, node.config.id)
                    if exc.retryable or exc.code == "upstream_rate_limit":
                        node.open_until = time.monotonic() + max(
                            self.settings.cooldown_seconds, exc.retry_after
                        )
                    else:
                        node.disabled = True
                    last_error = exc
                    if emitted or not exc.retryable or not request.allow_fallback:
                        raise
                except (asyncio.CancelledError, GeneratorExit):
                    if not finished:
                        node.cancellations += 1
                        self.audit(request_id, "cancelled", node.config.id)
                    raise
                finally:
                    if not accounted:
                        node.unknown_usage_calls += 1
                    node.in_flight -= 1
            raise last_error
        finally:
            self.active -= 1

    @staticmethod
    def record_usage(node: Node, measured: Usage) -> None:
        node.input_tokens += measured.input_tokens or 0
        node.output_tokens += measured.output_tokens or 0
        if measured.source == "unavailable":
            node.unknown_usage_calls += 1
