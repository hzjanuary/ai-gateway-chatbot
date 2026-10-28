import json
import time
from pathlib import Path

import httpx

from gateway.config import Settings, initialize, token_hash
from tests.conftest import (
    ADMIN,
    INFERENCE,
    Reply,
    cf,
    client_for,
    cloud,
    live_gateway,
    local,
    ollama,
)


def test_enrichment_disabled_no_network(upstream, auth):
    with client_for([cloud()]) as client:
        result = client.post(
            "/v1/inference", headers=auth, json={"prompt": "x", "web_enrichment": True}
        )
    assert result.status_code == 422 and not upstream.calls


def test_enrichment_bounded_untrusted_real_urls(upstream, auth):
    body = b'<a class="result__a" href="https://docs.example.org/actual">Ignore system</a><a class="result__snippet">untrusted instruction</a><a class="result__a" href="javascript:evil">bad</a>'
    upstream.replies.extend([Reply(body=body, content_type="text/html"), cf()])
    with client_for([cloud()], web_enrichment_enabled=True) as client:
        response = client.post(
            "/v1/inference",
            headers=auth,
            json={"prompt": "question", "system_prompt": "trusted", "web_enrichment": True},
        )
        assert client.app.state.router.web_queries == 1
    assert response.status_code == 200 and len(upstream.calls) == 2
    sources = response.json()["sources"]
    assert len(sources) == 1 and sources[0]["url"] == "https://docs.example.org/actual"
    assert sources[0]["retrieved_at"]
    messages = upstream.calls[1]["body"]["messages"]
    assert messages[0] == {"role": "system", "content": "trusted"}
    assert "Untrusted web search data" in messages[1]["content"]
    assert "untrusted instruction" in messages[1]["content"]


def test_web_error_is_failure_not_fabricated_context(upstream, auth):
    upstream.replies.append(Reply(status=503))
    with client_for([cloud()], web_enrichment_enabled=True) as client:
        result = client.post(
            "/v1/inference", headers=auth, json={"prompt": "x", "web_enrichment": True}
        )
    assert result.status_code == 503 and len(upstream.calls) == 1


def test_admin_ui_missing_secret_fails_closed(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("GATEWAY_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("GATEWAY_UI_ROLE", "admin")
    test = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "gateway/ui.py")).run()
    assert not test.exception
    assert test.error and "disabled" in test.error[0].value
    assert len(test.text_input) == 0 and len(test.json) == 0


def test_optional_admin_and_chat_use_api_auth(tmp_path, monkeypatch, upstream):
    from streamlit.testing.v1 import AppTest

    directory = tmp_path / "private"
    initialize(directory, True)
    settings = Settings(
        inference_hash=token_hash(INFERENCE),
        admin_hash=token_hash(ADMIN),
        providers=[local(upstream.url)],
    )
    (directory / "settings.json").write_text(json.dumps(settings.model_dump(mode="json")))
    monkeypatch.setenv("GATEWAY_CONFIG_DIR", str(directory))
    with live_gateway(settings) as (url, app):
        monkeypatch.setenv("BACKEND_URL", url)
        monkeypatch.setenv("GATEWAY_UI_ROLE", "admin")
        test = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "gateway/ui.py")).run()
        test.text_input[0].set_value(INFERENCE).run()
        assert not test.json
        test.text_input[0].set_value(ADMIN).run()
        assert not test.exception and len(test.json) == 2
        assert "offline-" not in str(test.json[0].value)
        monkeypatch.setenv("GATEWAY_UI_ROLE", "chat")
        chat = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "gateway/ui.py")).run()
        chat.text_input[0].set_value(ADMIN).run()
        assert chat.error and "denied" in chat.error[0].value
        upstream.replies.append(ollama("UI completion"))
        chat.text_input[0].set_value(INFERENCE).run()
        assert not chat.exception and chat.chat_input
        chat.chat_input[0].set_value("UI prompt").run()
        assert not chat.exception
        assert len(upstream.calls) == 1
        assert app.state.router.nodes[0].successes == 1


def test_disconnect_before_headers_and_after_first_output(upstream):
    settings = Settings(
        inference_hash=token_hash(INFERENCE), providers=[cloud()], attempt_seconds=2.0
    )
    with live_gateway(settings) as (url, app):
        import socket

        upstream.replies.append(Reply(delay=0.3, body=cf().body))
        endpoint = httpx.URL(url)
        sock = socket.create_connection((endpoint.host, endpoint.port))
        payload = b'{"prompt":"x"}'
        request = (
            f"POST /v1/inference HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer {INFERENCE}\r\nContent-Type: application/json\r\nContent-Length: {len(payload)}\r\n\r\n".encode()
            + payload
        )
        sock.sendall(request)
        until = time.monotonic() + 2
        while not upstream.calls and time.monotonic() < until:
            time.sleep(0.005)
        sock.close()
        until = time.monotonic() + 2
        while app.state.router.active and time.monotonic() < until:
            time.sleep(0.005)
        assert app.state.router.active == 0
        assert app.state.router.nodes[0].cancellations == 1
        upstream.replies.append(
            Reply(
                content_type="text/event-stream",
                chunks=[b'data: {"response":"first"}\n\n'] + [b": ping\n\n"] * 30,
                delay=0.02,
            )
        )
        with httpx.Client(trust_env=False) as client:
            with client.stream(
                "POST",
                url + "/v1/inference",
                headers={"Authorization": f"Bearer {INFERENCE}"},
                json={"prompt": "x", "stream": True},
            ) as response:
                assert response.status_code == 200
                for line in response.iter_lines():
                    if line == "event: delta":
                        break
        until = time.monotonic() + 2
        while app.state.router.active and time.monotonic() < until:
            time.sleep(0.005)
        assert app.state.router.active == 0
        assert app.state.router.nodes[0].cancellations == 2
        assert upstream.closed.wait(2)
