"""Real HTTP upstreams bound only to loopback. Tests never contact external providers."""

import json
import threading
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest
from fastapi.testclient import TestClient

from gateway.api import create_app
from gateway.config import Provider, Settings, token_hash

INFERENCE = "offline-inference-only-Aa0Zx9Kp2Wq8s3Yv7"
ADMIN = "offline-admin-only-Bb1Yw8Lq3Xr9t4Zu6"
UPSTREAM = "offline-upstream-only-Cc2Xv7Mr4Ys0u5At8"


@dataclass
class Reply:
    status: int = 200
    body: bytes = b""
    content_type: str = "application/json"
    chunks: list[bytes] = field(default_factory=list)
    delay: float = 0
    headers: dict[str, str] = field(default_factory=dict)


def cf(text: str = "hello") -> Reply:
    return Reply(
        body=json.dumps(
            {
                "success": True,
                "errors": [],
                "result": {"response": text, "usage": {"prompt_tokens": 5, "completion_tokens": 2}},
            }
        ).encode()
    )


def ollama(text: str = "hello", model: str = "test-model") -> Reply:
    return Reply(
        body=json.dumps(
            {
                "model": model,
                "response": text,
                "done": True,
                "eval_count": 2,
                "prompt_eval_count": 5,
            }
        ).encode()
    )


class MockServer:
    def __init__(self) -> None:
        self.replies: deque[Reply] = deque()
        self.calls: list[dict[str, Any]] = []
        self.closed = threading.Event()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_POST(self) -> None:
                body = self.rfile.read(int(self.headers.get("content-length", 0)))
                owner.calls.append(
                    {"path": self.path, "headers": dict(self.headers), "body": json.loads(body)}
                )
                self.reply()

            def do_GET(self) -> None:
                owner.calls.append({"path": self.path})
                self.reply()

            def reply(self) -> None:
                reply = owner.replies.popleft() if owner.replies else Reply(status=500)
                try:
                    if reply.delay:
                        time.sleep(reply.delay)
                    self.send_response(reply.status)
                    self.send_header("Content-Type", reply.content_type)
                    self.send_header("Connection", "close")
                    for key, value in reply.headers.items():
                        self.send_header(key, value)
                    self.end_headers()
                    for chunk in reply.chunks or [reply.body]:
                        self.wfile.write(chunk)
                        self.wfile.flush()
                        if reply.chunks and reply.delay:
                            time.sleep(reply.delay)
                except (BrokenPipeError, ConnectionResetError):
                    owner.closed.set()
                self.close_connection = True

            def log_message(self, *args: object) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


@pytest.fixture
def upstream(monkeypatch: pytest.MonkeyPatch) -> Any:
    import gateway.adapters
    import gateway.enrichment

    server = MockServer()
    # The only origin override exists in tests. Production config cannot redirect Cloudflare.
    monkeypatch.setattr(gateway.adapters, "CLOUDFLARE_ORIGIN", server.url)
    monkeypatch.setattr(gateway.enrichment, "SEARCH_URL", server.url + "/search")
    yield server
    server.close()


def cloud(index: int = 1, **kwargs: Any) -> Provider:
    return Provider(
        id=f"cf-{index}",
        type="cloudflare",
        account_id=f"{index:032x}",
        api_token=UPSTREAM,
        model="@cf/test/model",
        authorized=True,
        billing="approved",
        policy_group="test",
        **kwargs,
    )


def local(url: str, **kwargs: Any) -> Provider:
    return Provider(
        id="local",
        type="ollama",
        endpoint=url,
        model="test-model",
        authorized=True,
        billing="local",
        allow_private=True,
        **kwargs,
    )


@contextmanager
def client_for(providers: list[Provider] | None = None, **kwargs: Any) -> Any:
    settings = Settings(
        inference_hash=token_hash(INFERENCE),
        admin_hash=token_hash(ADMIN),
        providers=providers or [],
        **kwargs,
    )
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture
def auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {INFERENCE}"}


@pytest.fixture
def admin() -> dict[str, str]:
    return {"Authorization": f"Bearer {ADMIN}"}


@pytest.fixture(autouse=True)
def offline_network(monkeypatch):
    """Fail before DNS for any accidental non-loopback destination in the test process."""
    import ipaddress
    import socket

    original = socket.getaddrinfo

    def guarded(host, *args, **kwargs):
        if host not in ("localhost", None):
            try:
                allowed = ipaddress.ip_address(
                    host.decode() if isinstance(host, bytes) else host
                ).is_loopback
            except ValueError:
                allowed = False
            if not allowed:
                raise AssertionError("Tests cannot resolve or call external hosts")
        return original(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", guarded)


@contextmanager
def live_gateway(settings):
    import socket

    import uvicorn

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(settings), access_log=False, proxy_headers=False, log_level="critical"
        )
    )
    thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
    thread.start()
    until = time.monotonic() + 5
    while not server.started:
        if time.monotonic() > until:
            raise AssertionError("Local gateway did not start")
        time.sleep(0.005)
    try:
        yield f"http://127.0.0.1:{port}", server.config.app
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        listener.close()
        assert not thread.is_alive()
