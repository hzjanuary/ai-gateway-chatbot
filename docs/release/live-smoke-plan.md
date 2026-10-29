# Authorized live acceptance — STOPPED AT PREFLIGHT

The owner explicitly authorized exactly one generation request with at most eight
completion/output tokens, no retry/fallback/research/hidden calls or billing change.
The allowance is **unused**: preflight stopped before inference on 2026-10-28.
No key belongs in chat, a report or a command argument.

Preflight source commit: `1fbca20fae2c048961340e4751232fefbfca8434`.
No gateway provider registry/configuration was present in the default directory or
repository operator locations. No Ollama binary/service was available; the sole
non-generative GET `/api/version` at `127.0.0.1:11434` failed to connect (no HTTP
response). No correctly identified Cloudflare account/Free plan/hard quota was
confirmed. No services were installed/started, no models downloaded, no remote
provider endpoint contacted and no generation request submitted.

Consequently provider/model/output/usage/generation HTTP status are **not available**;
completion is **NOT_EXECUTED**, generation attempts **0**, and runtime enforcement of
the eight-output-token ceiling is **not verified**. Gateway counters were unavailable,
not inferred from a mock or a success placeholder. See [sanitized evidence](evidence/live-smoke-preflight.json).
GW-20 remains BLOCKED by provider availability/conditions, no longer by missing
smoke authorization. This result proves no live inference/fallback/streaming behavior.

Before any generation, exactly one already configured real provider ID/model must
be available with verified ownership, local execution or the required confirmed
Cloudflare Free plan/hard quota, privacy and model license. Configure these privately;
provide only a non-secret provider ID/endpoint/model reference when resuming.
No account provisioning, billing change, model download or web search is part of it.

Proposed reviewable smoke: one request, nonstream, prompt `Reply exactly OK.`,
max_tokens 8, max_attempts 1, allow_fallback false, allow_policy_fallback false,
web_enrichment false. Use a small deadline configured by the operator (for example
10 seconds). An upstream timeout/failure still consumes the one-call allowance;
stop on failure and do not retry automatically. There is no approved second call.

After preflight succeeds under the existing one-request authorization, the operator
can use an existing private token file (replace only the provider ID, never paste a key):

```sh
printf '%s' 'Reply exactly OK.' | gateway --config-dir /private/operator/path request \
  --provider OPERATOR_SELECTED_ID --max-tokens 8 --max-attempts 1
```

Record only timestamp, source/image identity, provider/model ID, HTTP outcome,
attempt count, request ID, measured usage and whether text passed the expected
check. Only the authorized minimal synthetic output may be retained for this smoke;
never retain credentials or unrelated request content in public evidence.
A successful request verifies that chosen endpoint/model at that time; it does not
prove high availability, future free usage, fallback safety on all services or SLA.
