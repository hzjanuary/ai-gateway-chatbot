import asyncio
import json
import threading
import time

import httpx
import pytest

from gateway.models import InferenceRequest
from gateway.router import Router
from tests.conftest import Reply, cf, client_for, cloud, local


def sse(*chunks, delay=0):
    return Reply(content_type="text/event-stream", chunks=list(chunks), delay=delay)


def events(response):
    return [
        (frame.splitlines()[0][7:], json.loads(frame.splitlines()[1][6:]))
        for frame in response.text.strip().split("\n\n")
    ]


def test_sse_split_utf8_multiline(upstream, auth):
    raw = ': heartbeat\r\ndata: {"response":\r\ndata: "chào"}\r\n\r\ndata: {"usage":{"prompt_tokens":3,"completion_tokens":2}}\n\ndata: [DONE]\n\n'.encode()
    upstream.replies.append(sse(*[raw[i : i + 1] for i in range(len(raw))]))
    with client_for([cloud()]) as client:
        result = client.post("/v1/inference", headers=auth, json={"prompt": "x", "stream": True})
    assert result.status_code == 200
    data = events(result)
    assert [name for name, _ in data] == ["start", "delta", "usage", "end"]
    assert data[1][1]["response"] == "chào"
    assert data[2][1]["output_tokens"] == 2


def test_ollama_ndjson_split(upstream, auth):
    raw = b'{"model":"test-model","response":"a","done":false}\n{"model":"test-model","response":"b","done":true,"eval_count":2,"prompt_eval_count":4}\n'
    upstream.replies.append(
        Reply(
            content_type="application/x-ndjson",
            chunks=[raw[i : i + 3] for i in range(0, len(raw), 3)],
        )
    )
    with client_for([local(upstream.url)]) as client:
        result = client.post("/v1/inference", headers=auth, json={"prompt": "x", "stream": True})
    data = events(result)
    assert [name for name, _ in data] == ["start", "delta", "delta", "usage", "end"]
    assert data[3][1]["output_tokens"] == 2


def test_stream_fallback_before_output(upstream, auth):
    upstream.replies.extend(
        [Reply(status=503), sse(b'data: {"response":"second"}\n\ndata: [DONE]\n\n')]
    )
    with client_for([cloud(), cloud(2)]) as client:
        result = client.post(
            "/v1/inference",
            headers=auth,
            json={"prompt": "x", "stream": True, "allow_fallback": True, "max_attempts": 2},
        )
    assert events(result)[0][1]["provider"] == "cf-2" and len(upstream.calls) == 2


@pytest.mark.parametrize(
    "tail",
    [
        b"garbage\n\n",
        b'data: {"error":"policy"}\n\n',
        b'data: {"response":42}\n\n',
        b'data: {"response":"truncated"}',
    ],
)
def test_midstream_error_no_stitch(upstream, auth, tail):
    upstream.replies.extend([sse(b'data: {"response":"first"}\n\n', tail), cf("second")])
    with client_for([cloud(), cloud(2)]) as client:
        response = client.post(
            "/v1/inference",
            headers=auth,
            json={"prompt": "x", "stream": True, "allow_fallback": True, "max_attempts": 2},
        )
    names = [name for name, _ in events(response)]
    assert names[-1] == "error" and "end" not in names
    assert "second" not in response.text and len(upstream.calls) == 1


@pytest.mark.parametrize(
    "raw",
    [
        b"not-sse",
        b'data: {"response":42}\n\n',
        b'data: {"other":"x"}\n\n',
        b"data: " + b"a" * 70000 + b"\n\n",
    ],
)
def test_stream_invalid_before_headers_truthful(upstream, auth, raw):
    upstream.replies.append(sse(raw))
    with client_for([cloud()]) as client:
        response = client.post("/v1/inference", headers=auth, json={"prompt": "x", "stream": True})
    assert response.status_code == 502 and "event: start" not in response.text


def test_stream_timeout_after_first_has_error(upstream, auth):
    upstream.replies.extend(
        [sse(b'data: {"response":"first"}\n\n', b"data: [DONE]\n\n", delay=0.05), cf()]
    )
    with client_for([cloud(), cloud(2)], deadline_seconds=0.08, attempt_seconds=0.08) as client:
        response = client.post(
            "/v1/inference",
            headers=auth,
            json={"prompt": "x", "stream": True, "allow_fallback": True, "max_attempts": 2},
        )
    assert "event: error" in response.text and "event: end" not in response.text
    assert len(upstream.calls) == 1


async def test_cancel_releases_upstream_and_reservations(upstream):
    from gateway.config import Settings

    upstream.replies.append(
        sse(b'data: {"response":"first"}\n\n', *[b": ping\n\n"] * 20, delay=0.02)
    )
    async with httpx.AsyncClient(trust_env=False) as client:
        router = Router(Settings(providers=[cloud()]), client)
        stream = router.generate(InferenceRequest(prompt="x", stream=True), "cancel")
        first = await anext(stream)
        assert first[1].response == "first"
        assert router.active == 1
        await stream.aclose()
        assert router.active == 0 and router.nodes[0].in_flight == 0
        assert router.nodes[0].cancellations == 1
        assert router.nodes[0].calls == 1 and router.nodes[0].reserved_tokens == 512
    assert upstream.closed.wait(1)


def test_global_and_node_concurrency(upstream, auth, admin):
    upstream.replies.append(Reply(delay=0.3, body=cf().body))
    with client_for([cloud()], max_concurrent=1) as client:
        results = []
        thread = threading.Thread(
            target=lambda: results.append(
                client.post("/v1/inference", headers=auth, json={"prompt": "x"})
            )
        )
        thread.start()
        until = time.monotonic() + 2
        while not upstream.calls and time.monotonic() < until:
            time.sleep(0.005)
        second = client.post("/v1/inference", headers=auth, json={"prompt": "x"})
        reset = client.post("/v1/providers/reset", headers=admin, json={"confirm": True})
        assert second.status_code == 429 and reset.status_code == 409
        thread.join()
        assert results[0].status_code == 200
    assert len(upstream.calls) == 1


async def test_half_open_only_one_probe(upstream):
    from gateway.config import Settings

    upstream.replies.append(Reply(delay=0.1, body=cf().body))
    async with httpx.AsyncClient(trust_env=False) as client:
        router = Router(Settings(providers=[cloud(max_concurrent=5)]), client)
        router.nodes[0].open_until = time.monotonic() - 1
        first = router.generate(InferenceRequest(prompt="x"), "first")
        task = asyncio.create_task(anext(first))
        await asyncio.sleep(0.02)
        second = router.generate(InferenceRequest(prompt="x"), "second")
        from gateway.models import GatewayError

        with pytest.raises(GatewayError):
            await anext(second)
        await task
        await first.aclose()
        assert router.nodes[0].successes == 1


def test_node_concurrency_separate_from_gateway_cap(upstream, auth):
    upstream.replies.append(Reply(delay=0.2, body=cf().body))
    with client_for([cloud()], max_concurrent=4) as client:
        responses = []
        thread = threading.Thread(
            target=lambda: responses.append(
                client.post("/v1/inference", headers=auth, json={"prompt": "x"})
            )
        )
        thread.start()
        until = time.monotonic() + 2
        while not upstream.calls and time.monotonic() < until:
            time.sleep(0.005)
        second = client.post("/v1/inference", headers=auth, json={"prompt": "x"})
        assert second.status_code == 503
        thread.join()
        assert responses[0].status_code == 200
    assert len(upstream.calls) == 1


def test_cr_only_sse_frames_and_utf8_bom(upstream, auth):
    raw = '\ufeffdata: {"response":"first"}\r\rdata: [DONE]\r\r'.encode()
    upstream.replies.append(sse(*[raw[i : i + 1] for i in range(len(raw))]))
    with client_for([cloud()]) as client:
        response = client.post("/v1/inference", headers=auth, json={"prompt": "x", "stream": True})
    assert response.status_code == 200
    assert [name for name, _ in events(response)] == ["start", "delta", "usage", "end"]
