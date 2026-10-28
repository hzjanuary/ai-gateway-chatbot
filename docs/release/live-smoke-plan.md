# Separately authorized live acceptance — NOT EXECUTED

GW-20 remains BLOCKED. Installing, doctor, metadata, tests and health do not authorize
live inference. No key belongs in chat, a report or a command argument.

Before authorization the owner must select exactly one already registered provider
ID/model and verify ownership, provider plan/billing/usage/privacy and model license.
No account provisioning, billing change, model download or web search is part of it.

Proposed reviewable smoke: one request, nonstream, prompt `Reply exactly OK.`,
max_tokens 8, max_attempts 1, allow_fallback false, allow_policy_fallback false,
web_enrichment false. Use a small deadline configured by the operator (for example
10 seconds). An upstream timeout/failure still consumes the one-call allowance;
stop on failure and do not retry automatically. There is no approved second call.

After distinct authorization, the owner can execute locally using the existing
private token file (replace only the provider ID, never paste a key):

```sh
printf '%s' 'Reply exactly OK.' | gateway --config-dir /private/operator/path request \
  --provider OPERATOR_SELECTED_ID --max-tokens 8 --max-attempts 1
```

Record only timestamp, source/image identity, provider/model ID, HTTP outcome,
attempt count, request ID, measured usage and whether text passed the expected
check. Do not store prompt/completion content or credentials in public evidence.
A successful request verifies that chosen endpoint/model at that time; it does not
prove high availability, future free usage, fallback safety on all services or SLA.
