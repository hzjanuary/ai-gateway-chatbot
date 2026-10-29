# SPEC-001 - Open-Source Self-Hosted Inference Gateway

Status: PROPOSED - not implemented or accepted
Repository: https://github.com/hzjanuary/ai-gateway-chatbot
Observed default-branch baseline: `d2d859a8b59a5a396c62478a315f533d27007934` (2026-10-28 inspection)
Proposed branch: `feat/spec-001-oss-inference-gateway`
Release target: separate early source preview after verification; do not reuse MAOS acceptance evidence.

## 1. Outcome

Turn the current easyResearchAssistant prototype into an independently useful, **self-hosted LLM inference gateway**: a small, secure API that routes explicitly authorized requests across configured, real provider endpoints with bounded health/cooldown, correct streaming, truthful failures and audit-safe observability. Keep the optional chat/admin experiences but remove them from the mandatory runtime and security perimeter.

This is a gateway, **not** a LangGraph multi-agent OS. Multi-provider authorization and reliable response semantics are the product; do not add agents, RAG vectors, Kubernetes or unnecessary databases as an OSS checkbox.

## 2. Observed baseline (static inspection, not executed)

- `api_gateway.py` provides `/v1/inference`, legacy `/ask`, token validation, SSE, `Cloudflare Workers AI`, local `Ollama`, monitoring and strategy/reset endpoints. `GatewayConfig.ACCESS_TOKEN` silently generates a new random token if missing and startup logs an 8-character token prefix.
- `api_gateway.py` currently switches away from a provider after 401/403 as well as 429/5xx; an SSE stream may have already emitted output before a fallback; non-streaming response can report `provider: unknown`.
- `provider_manager.py` manages Cloudflare account nodes in memory and can reset exhausted nodes while the same request is in flight. The code and README describe availability optimistically; there is no shown durable quota or request reservation model.
- `search_tool.py` provides optional DuckDuckGo prompt augmentation described as RAG, but no persistent document retrieval; rename it accurately to optional **web research**, not document RAG.
- `admin_app.py` `verify_admin_password()` returns `True` when `ADMIN_PASSWORD` is unset; Streamlit UI can be publicly exposed by Compose. `docker-compose.yml` exposes API and both Streamlit ports on all host interfaces and bind-mounts repository source into the backend runtime.
- `.env.template` has user-populated token/provider fields; `providers.example.json` includes placeholder credentials. `Dockerfile` uses unpinned `python:3.10-slim` and includes no explicit runtime hardening/licensing verification. MIT LICENSE exists; no test directory or GitHub Actions exists in the reviewed tree despite README `pytest tests/` instructions.

Re-evaluate against actual local HEAD before editing; do not claim these defects persist if code has changed.

## 3. Scope and product decisions

### Preserve
- FastAPI API-first provider routing, Cloudflare Workers AI and Ollama support, selection strategies, bounded cooldown/circuit-breaker ideas, usage/status monitoring and SSE.
- Optional authenticated chat UI and administrative dashboard as separate profiles or distributions.
- Optional web research plugin with actual source URLs and explicit network use.

### Improve
- Vendor-neutral, typed provider adapter boundary with capability contracts for request, streaming, errors and measured usage. Include an OpenAI-compatible adapter only if exercised against a real compatible API contract. Avoid implying compatibility with every provider.
- Explicit allowlisted provider configurations. Never rotate accounts to evade provider rate limits, terms, billing or usage restrictions. Honor provider terms, quotas and ownership.
- Local secure bootstrap, separate inference/admin permissions, predictable restart/health and no ambiguous fallback.

### Exclude from initial release
- Public multi-tenant SaaS, invoicing, auto-paid account creation, arbitrary user-provided endpoint URLs, automatic online research by default, remote provider traffic on health/doctor, production SLA guarantees.

## 4. Architecture and contracts

```text
CLI config/init/doctor  ---> Private settings + credentials (0600)
                                 |
Optional UI (auth) ---> FastAPI REST/SSE gateway ---> Router/Quota/Policy
                                 |                  |          |
                             Request ID       Provider A  Provider B / Ollama
                                 |
                   Sanitized counters/errors/diagnostics
```

A local SQLite store may hold bounded usage/cooldown/audit metadata for one instance; if persistence is unnecessary or unsafe for latency, explain the chosen alternative and document reset semantics. Do not store prompts/completions by default. No Redis/PostgreSQL requirement solely to imitate MAOS.

### Authentication and data handling
- Fail closed on missing, default or placeholder token. `gateway config init` creates an installation token and an optional separate admin token in an operator-only private directory; do not show token prefixes in logs. Prefer hashed token verification at rest where practical and constant-time compare.
- A request token grants inference only; provider management, logs, strategy mutation and reset require separate admin authority. UI sessions must not bypass API authentication. Insecure admin password fallback is forbidden.
- Default host binding loopback; dashboard opt-in, authenticated, and not published on an interface by default. Document TLS/proxy, request limits, reverse proxy headers and network trust assumptions.
- No raw prompts/completions in INFO logs, metrics, health or exception messages. Explicit, narrow opt-in debugging with redaction. Treat web results/provider outputs as untrusted content.
- Provider endpoint URLs are operator-registered, validated against SSRF (scheme, localhost/private-network policy, DNS rebinding where relevant). User requests must never set arbitrary upstream URLs/authorization headers. Local Ollama is an explicit trust-zone exception.

### Provider policy and fallback
- Validate provider type, endpoint, model identifier and compatibility at startup/doctor, without generation or free-plan assumptions. No silent paid default.
- Error classification distinguishes 429/502/503/504/timeouts/connect failures from 401/403, billing, invalid model/request, invalid JSON, policy refusal and bad schema. Never fallback on auth/billing/policy errors. Per-request max distinct attempts and time/token/cost ceilings must be enforced before each attempt.
- Never reset exhausted provider state mid-request to exceed the retry budget. Circuit breaker/open/half-open state and quotas must have bounded, tested semantics. Include cancellation/deadline handling and cleanup.
- **No silent failover after downstream output has been emitted.** For streaming, either choose the provider before first chunk or terminate the stream with an explicit structured error/event on midstream failure. Do not concatenate chunks from different providers into one apparent answer.
- SSE must support multiline/chunk-split frames, correct `data:` framing, usage/end event and client disconnect. Non-streaming returns the real provider ID, model and actual response, never `unknown` or a success object containing an error. Status codes and normalized errors must be documented.
- A model's `:free` suffix is not evidence of free billing. Default service makes no remote call. All additional provider attempts and research/search traffic must be explicit and counted.

### Optional web research and UIs
- Research mode is OFF by default, requires a separate opt-in flag and bounded external web queries. Cite real results with URL and retrieval time; never turn web text into privileged system instructions or claim it proves factual correctness.
- Streamlit UI and admin dashboard are optional profiles. UI shares API auth and hides secrets; compare stored password hashes/secure sessions; disabled/misconfigured admin auth must abort UI startup, not grant access.
- A basic CLI provides `config init`, `doctor`, `provider list/test-metadata`, `request`, `metrics` and `reset --confirm`. `test-metadata` never implies live inference and makes no generation requests.

### Packaging, CI, licenses
- Pinned supported Python dependencies + lock, minimal non-root Docker runtime, no source-code bind mount, no test fixtures or secret files in image, `LICENSE`/`NOTICE` and third-party license inventory, SBOM and vulnerability scans.
- Default Docker Compose exposes only API on loopback; provider remote access is opt-in. Honest health/readiness reflect missing credentials and no providers; docs distinguish API alive vs inference ready.
- Unit and integration tests use recorded/synthetic HTTP server responses that exercise real adapters without calling paid endpoints. Real inference acceptance is separately authorized and capped at 1-2 calls max where practical, with provider's verified plan and privacy.
- GitHub Actions gates: dependency lock, pytest, Ruff/Black/MyPy, source secrets/private paths, Docker/Compose, licenses/image provenance, Python and OS scans. A known OS issue is recorded, not silently ignored or made green.

## 5. Milestones

**G0 - Audit and contract baseline:** inventory actual providers and all endpoints; threat model UI/API/auth/data; isolate baseline failures; save exact source SHA and test matrix.

**G1 - Secure runtime/auth/config:** private config bootstrap, admin/inference role separation, safe bind/network, bounded requests, source/image secrets gates, correct docs.

**G2 - Routing and transport correctness:** typed adapters, provider state and quotas, deterministic fallback policy, safe SSE and nonstream responses, timeout/cancel semantics, route/error tests.

**G3 - Operator experience:** CLI, optional secured UI, optional research, sanitized metrics, controlled provider registry, clean Docker setup and isolated restart.

**G4 - OSS verification and publication prep:** locked tests, dependency license/image inventory and reproducible build, clean-first-run, remote CI evidence when authorized, source release gate separate from image-security signoff.

## 6. Acceptance matrix

| ID | Evidence needed |
| --- | --- |
| GW-01 | Fresh source clone builds from pinned dependencies with no user credential or sample provider. |
| GW-02 | No silent random auth token or usable placeholder; secure initialization is explicit and idempotent. |
| GW-03 | Missing dashboard admin secret denies access; no UI auth bypass. |
| GW-04 | Inference and administration privileges cannot be interchanged. |
| GW-05 | All public/admin endpoints have deliberate auth and information-disclosure boundaries. |
| GW-06 | Default API binds loopback; UI ports/remote providers not exposed by default. |
| GW-07 | Cloudflare and Ollama adapters exercise actual response formats via an HTTP test server. |
| GW-08 | At least two configured nodes route deterministically, with true provider/model reported. |
| GW-09 | 401/403, billing, invalid model/schema and permission failures NEVER trigger fallback. |
| GW-10 | Eligible availability failures fallback only within per-request attempt and budget caps. |
| GW-11 | Provider exhaustion cannot be reset or duplicated inside a single request. |
| GW-12 | SSE parser handles split/multiline events and disconnect; partial output cannot be silently merged across providers. |
| GW-13 | Non-stream failure is a non-2xx truthful error; valid completion never says provider unknown. |
| GW-14 | Request size, output tokens, concurrency, deadline and call budgets are enforced and tested. |
| GW-15 | Malicious caller upstream URL/headers are rejected; operator endpoints validated for SSRF. |
| GW-16 | Opt-in web research has bounded query count, untrusted text handling and real citation URLs. |
| GW-17 | Logs, traces, UI and error reports redact keys, headers, prompts and completion content by default. |
| GW-18 | Provider cooldown/health and observability remain truthful across restart (or documented as ephemeral). |
| GW-19 | `doctor`, token setup, provider discovery and local Ollama path work without paid provider calls. |
| GW-20 | One authorized bounded live provider request proves end-to-end actual inference (LIVE; BLOCKED if no authorization). |
| GW-21 | CI runs backend, ops, secret/artifact, license, image, dependency and OS scans with provenance. |
| GW-22 | README/SECURITY/NOTICE/LICENSE/docs show supported interfaces, privacy/costs and single-instance limitations. |
| GW-23 | Real clean-clone image/CLI startup and local health test pass, with no seeded user/request/log data. |
| GW-24 | Source publication readiness and Docker/production security approval are independently decided; no fake PASS. |

For every criterion track PASS/FAIL/BLOCKED/NOT_RUN, command, test count, exact SHA and image digest. No live call, provider account rotation, billing change or public release without distinct owner authorization.

## 7. Artifacts and documentation

Deliver architecture + API contract, request/stream state diagrams, provider adapter guide, `docs/security-model.md`, local-first install/CLI guide, troubleshooting, `SECURITY.md` with private disclosure process, `CONTRIBUTING.md`, `LICENSE`, `NOTICE`, actual-image license inventory, `docs/release/verification.md` and release checklist. README must not say production-ready without matching exposure/security evidence. Describe research as optional web enrichment rather than vector RAG.

## 8. Boundaries

No real secrets in test code or logs. No fake production provider. No inference without consent. No push/merge/tag/publish/deploy/history rewrite/deletion of operator state without separate permission. Keep historical Git provenance available. If backend readiness passes but OS scan fails, record a source-preview-only candidate explicitly instead of suppressing findings.
