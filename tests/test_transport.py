import json

import pytest

from tests.conftest import Reply, cf, client_for, cloud, local, ollama


def test_cloudflare_contract(upstream, auth):
    upstream.replies.append(cf("actual response"))
    with client_for([cloud()]) as client:
        result = client.post(
            "/v1/inference", headers=auth, json={"prompt": "input", "system_prompt": "system"}
        )
        assert result.status_code == 200
        data = result.json()
        assert (data["provider"], data["model"], data["response"]) == (
            "cf-1",
            "@cf/test/model",
            "actual response",
        )
        assert data["usage"]["output_tokens"] == 2
        stats = client.app.state.router.stats()["providers"][0]
        assert stats["successes"] == 1 and stats["cancellations"] == 0
    call = upstream.calls[0]
    assert (
        call["path"] == "/client/v4/accounts/00000000000000000000000000000001/ai/run/@cf/test/model"
    )
    assert call["headers"]["Authorization"].startswith("Bearer offline-")
    assert call["body"]["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "input"},
    ]


def test_ollama_contract(upstream, auth):
    upstream.replies.append(ollama())
    with client_for([local(upstream.url)]) as client:
        response = client.post(
            "/ask",
            headers=auth,
            json={"prompt": "input", "system_prompt": "system", "max_tokens": 17},
        )
    assert response.status_code == 200
    assert response.json()["provider"] == "local"
    payload = upstream.calls[0]["body"]
    assert payload["system"] == "system" and payload["options"]["num_predict"] == 17
    assert "Authorization" not in upstream.calls[0]["headers"]


@pytest.mark.parametrize("status", [401, 403, 400, 402, 404, 422, 429])
def test_terminal_http_never_fallback(upstream, auth, status):
    upstream.replies.extend([Reply(status=status, body=b'{"error":"secret failure"}'), cf()])
    with client_for([cloud(), cloud(2)]) as client:
        response = client.post(
            "/v1/inference",
            headers=auth,
            json={"prompt": "x", "allow_fallback": True, "max_attempts": 3},
        )
    assert response.status_code in (502, 503)
    assert "secret failure" not in response.text
    assert len(upstream.calls) == 1


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_available_fallback_explicit(upstream, auth, status):
    upstream.replies.extend([Reply(status=status), cf("second")])
    with client_for([cloud(), cloud(2)]) as client:
        response = client.post(
            "/v1/inference",
            headers=auth,
            json={"prompt": "x", "allow_fallback": True, "max_attempts": 2},
        )
    assert response.status_code == 200
    assert response.json()["provider"] == "cf-2"
    assert response.json()["attempts"] == 2 and len(upstream.calls) == 2


@pytest.mark.parametrize(
    "payload",
    [
        b"not json",
        b"[]",
        b"{}",
        b'{"success":false,"errors":[{"code":1}]}',
        b'{"result":{"response":42}}',
        b'{"result":{"response":"x","usage":{"completion_tokens":true}}}',
        b'{"result":{"response":"x","refusal":"policy"}}',
    ],
)
def test_bad_schema_terminal(upstream, auth, payload):
    upstream.replies.extend([Reply(body=payload), cf()])
    with client_for([cloud(), cloud(2)]) as client:
        result = client.post(
            "/v1/inference",
            headers=auth,
            json={"prompt": "x", "allow_fallback": True, "max_attempts": 2},
        )
    assert result.status_code == 502 and len(upstream.calls) == 1


@pytest.mark.parametrize("reason", ["billing", "policy", "invalid model", "auth", "quota"])
def test_application_error_on_5xx_terminal(upstream, auth, reason):
    upstream.replies.extend([Reply(status=503, body=json.dumps({"error": reason}).encode()), cf()])
    with client_for([cloud(), cloud(2)]) as client:
        result = client.post(
            "/v1/inference",
            headers=auth,
            json={"prompt": "x", "allow_fallback": True, "max_attempts": 2},
        )
    assert result.status_code == 502 and len(upstream.calls) == 1


def test_no_silent_fallback(upstream, auth):
    upstream.replies.extend([Reply(status=503), cf()])
    with client_for([cloud(), cloud(2)]) as client:
        result = client.post("/v1/inference", headers=auth, json={"prompt": "x", "max_attempts": 3})
    assert result.status_code == 503 and len(upstream.calls) == 1


def test_policy_boundary(upstream, auth):
    upstream.replies.extend([Reply(status=503), ollama()])
    with client_for([cloud(), local(upstream.url)]) as client:
        result = client.post(
            "/v1/inference",
            headers=auth,
            json={"prompt": "x", "allow_fallback": True, "max_attempts": 3},
        )
    assert result.status_code == 503 and len(upstream.calls) == 1


def test_attempt_and_reservation_caps(upstream, auth, admin):
    upstream.replies.extend([Reply(status=503) for _ in range(4)])
    with client_for([cloud(), cloud(2)], request_token_budget=512) as client:
        result = client.post(
            "/v1/inference",
            headers=auth,
            json={"prompt": "x", "allow_fallback": True, "max_attempts": 3},
        )
        assert result.status_code == 503 and len(upstream.calls) == 1
        node = client.app.state.router.nodes[0]
        assert node.calls == 1 and node.reserved_tokens == 512
        client.post("/v1/providers/reset", headers=admin, json={"confirm": True})
        assert node.calls == 1 and node.reserved_tokens == 512


def test_exhausted_provider_never_reset_in_request(upstream, auth):
    upstream.replies.extend([Reply(status=503), cf()])
    with client_for([cloud(call_limit=1)]) as client:
        for _ in range(2):
            result = client.post(
                "/v1/inference",
                headers=auth,
                json={"prompt": "x", "allow_fallback": True, "max_attempts": 3},
            )
            assert result.status_code == 503
        assert client.app.state.router.nodes[0].calls == 1
    assert len(upstream.calls) == 1


def test_deadline_no_extra_attempt(upstream, auth):
    upstream.replies.extend([Reply(delay=0.3, body=cf().body), cf()])
    with client_for([cloud(), cloud(2)], deadline_seconds=0.05, attempt_seconds=0.2) as client:
        result = client.post(
            "/v1/inference",
            headers=auth,
            json={"prompt": "x", "allow_fallback": True, "max_attempts": 3},
        )
        assert result.status_code == 504
        assert client.app.state.router.active == 0
    assert len(upstream.calls) == 1


def test_attempt_timeout_can_fallback(upstream, auth):
    upstream.replies.extend([Reply(delay=0.3, body=cf().body), cf()])
    with client_for([cloud(), cloud(2)], deadline_seconds=1.0, attempt_seconds=0.05) as client:
        result = client.post(
            "/v1/inference",
            headers=auth,
            json={"prompt": "x", "allow_fallback": True, "max_attempts": 2},
        )
    assert result.status_code == 200 and len(upstream.calls) == 2


def test_429_retry_after_honored(upstream, auth):
    upstream.replies.append(Reply(status=429, headers={"Retry-After": "60"}))
    with client_for([cloud()]) as client:
        result = client.post("/v1/inference", headers=auth, json={"prompt": "x"})
        assert result.status_code == 503
        assert client.app.state.router.stats()["providers"][0]["cooldown_seconds"] > 59


def test_two_nodes_and_strategies(upstream, auth, admin):
    upstream.replies.extend([cf() for _ in range(6)])
    with client_for([cloud(), cloud(2)]) as client:
        results = [
            client.post("/v1/inference", headers=auth, json={"prompt": "x"}).json()["provider"]
            for _ in range(2)
        ]
        assert results == ["cf-1", "cf-2"]
        assert client.post("/v1/providers/strategy/least_used", headers=admin).status_code == 200
        assert client.post("/v1/providers/strategy/random", headers=admin).status_code == 200
        assert client.post("/v1/providers/strategy/unknown", headers=admin).status_code == 422


def test_output_limit_and_usage_unknown(upstream, auth):
    upstream.replies.append(cf("x" * 200))
    with client_for([cloud()]) as client:
        result = client.post("/v1/inference", headers=auth, json={"prompt": "x", "max_tokens": 2})
        assert result.status_code == 502


def test_missing_usage_is_not_zero_estimate(upstream, auth):
    upstream.replies.append(Reply(body=b'{"result":{"response":"x"}}'))
    with client_for([cloud()]) as client:
        result = client.post("/v1/inference", headers=auth, json={"prompt": "x"})
        assert result.json()["usage"] == {
            "input_tokens": None,
            "output_tokens": None,
            "source": "unavailable",
        }
        assert client.app.state.router.nodes[0].unknown_usage_calls == 1


def test_max_three_distinct_attempts_even_when_four_nodes_registered(upstream, auth):
    upstream.replies.extend([Reply(status=503) for _ in range(4)])
    with client_for([cloud(i) for i in range(1, 5)]) as client:
        result = client.post(
            "/v1/inference",
            headers=auth,
            json={"prompt": "x", "max_tokens": 16, "allow_fallback": True, "max_attempts": 3},
        )
        assert result.status_code == 503
        assert sum(n.calls for n in client.app.state.router.nodes) == 3
    assert len(upstream.calls) == 3
    assert len({call["path"] for call in upstream.calls}) == 3


def test_node_token_limit_stops_before_transport(upstream, auth):
    with client_for([cloud(token_limit=128)]) as client:
        result = client.post("/v1/inference", headers=auth, json={"prompt": "x", "max_tokens": 129})
        assert result.status_code == 503
    assert not upstream.calls


def test_ollama_model_mismatch_not_success(upstream, auth):
    upstream.replies.append(ollama(model="different-model"))
    with client_for([local(upstream.url)]) as client:
        result = client.post("/v1/inference", headers=auth, json={"prompt": "x"})
    assert result.status_code == 502


@pytest.mark.parametrize(
    "operator_consent,request_consent,expected",
    [(False, True, 503), (True, False, 503), (True, True, 200)],
)
@pytest.mark.parametrize("stream", [False, True])
def test_cross_provider_fallback_requires_operator_and_request_consent(
    upstream, auth, operator_consent, request_consent, expected, stream
):
    first = cloud(fallback_to=["local"] if operator_consent else [])
    upstream.replies.extend([Reply(status=503), ollama("local fallback")])
    with client_for([first, local(upstream.url)]) as client:
        result = client.post(
            "/v1/inference",
            headers=auth,
            json={
                "prompt": "x",
                "provider": "cf-1",
                "max_tokens": 16,
                "allow_fallback": True,
                "allow_policy_fallback": request_consent,
                "stream": stream,
                "max_attempts": 2,
            },
        )
    assert result.status_code == expected
    assert len(upstream.calls) == (2 if expected == 200 else 1)
    if expected == 200:
        if stream:
            assert "event: end" in result.text and '"provider": "local"' in result.text
        else:
            assert result.json()["provider"] == "local" and result.json()["model"] == "test-model"
