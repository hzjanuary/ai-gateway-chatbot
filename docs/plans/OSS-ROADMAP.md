# AI Gateway - OSS Implementation Roadmap

Planning baseline: main `d2d859a8b59a5a396c62478a315f533d27007934`; SPEC-001 is authoritative. This is a proposed roadmap, not evidence of implementation.

## Release posture

- v0.1 source-preview goal: a genuinely operational, authenticated, local-first inference router with true Cloudflare/Ollama transport semantics, optional UI, CLI, tests and security disclosure.
- Do not build an agent OS, add arbitrary new providers, promise SLA, rotate accounts to dodge quotas or enable billed inference during QA.
- Separate engineering quality (GW-01..GW-24), live provider verification, source publication and Docker-image security decisions.

| Sequence | Work package | Required output | Exit gate |
| --- | --- | --- | --- |
| G0 | Inventory and controlled baseline | API/stream contract, endpoint auth matrix, source SHA, history/secret report, regression test harness | Current 401/403, SSE and UI behavior reproduced using synthetic input |
| G1 | Authentication and configuration | Secure `config init`, two privileges, no token prefix in logs, authenticated optional dashboards, loopback Compose | Anonymous/missing-secret bypass tests fail closed; no source mounts in runtime |
| G2 | Provider transport and routing | Typed Cloudflare/Ollama adapters, explicit provider allowlist, per-request budget, cooldown, valid non-stream provider attribution | 429/5xx eligible; 401/403/billing not eligible; exact request count demonstrated |
| G3 | Streaming and web research | Correct incremental SSE, disconnect handling, no post-stream fallback, opt-in bounded search with true citations | Frame fragmentation and partial-output negative tests pass |
| G4 | Operator and durability | CLI doctor, provider listing, health/readiness, sanitized metrics, optional persisted counters, clean restart | Clean clone on actual image, first login, request through local mock provider and logs redacted |
| G5 | OSS release candidate | Lock, CI, tests, LICENSE/NOTICE, SBOM, secret/image gates, README/SECURITY | GW matrix backed by actual evidence, owner receives source-vs-image readiness recommendation |

## First local actions for Codex

1. Check `git status --porcelain`, `git rev-parse HEAD`, current workflows/tags/branches; do not overwrite a dirty tree.
2. Read `api_gateway.py`, `provider_manager.py`, `admin_app.py`, `streamlit_app.py` and all config files. Note critical concerns: unauthenticated admin UI when password absent; fallback on 401/403; unknown provider in non-stream responses; in-flight reset and SSE switching.
3. Build an offline test HTTP server simulating Cloudflare success/429/403/partial stream and Ollama NDJSON. Save baseline negative results without real keys.
4. Create the branch and active plan. Only then modify runtime.

## Evidence policy

- Every change needs a failing-then-passing test where practical; keep generated fixture credentials synthetic.
- Actual stream and provider behaviors are measured through production parser and real HTTP transports against local deterministic servers.
- Trivy and Python advisory results stay raw; vulnerabilities are not ignored automatically. Even a source-only release needs public risk disclosure.
- A live LLM test cannot run without a separate owner budget/plan and does not use a fallback on auth errors.
- No push/merge/release unless authorized after candidate review.
