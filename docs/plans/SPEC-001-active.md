# SPEC-001 active implementation plan

Baseline: `d2d859a8b59a5a396c62478a315f533d27007934`. Branch:
`feat/spec-001-oss-inference-gateway`. Original specification remains authoritative.

## Audit (2026-10-28)

Read all six Python modules, Docker/Compose/templates, tracked file inventory and
all seven historical commits. No baseline tests, lock or CI exist. No operator
credentials/logs were opened, copied, removed or executed. No provider was contacted.
Baseline defects were confirmed statically: randomly generated missing token with
prefix logging; admin password missing grants access; admin uses inference token;
public node health; arbitrary body values echoed by validation; 401/403 fallback;
in-flight reset; malformed provider responses ignored/stringified; fallback after
partial output; provider `unknown`; prompts in logs; automatic Ollama; unbounded
web searches; public port bindings and production source mount.

## Work packages

- [x] G0: baseline audit, feature branch, initial contracts and negative evidence.
- [x] G1: private explicit initialization, role separation, safe configuration/network.
- [x] G2: strict typed transports, bounded routing, correct SSE/cancel/accounting.
- [x] G3: CLI, optional UI/web enrichment, truthful observability and restart behavior.
- [ ] G4: locked dependencies, CI/security/license gates, docs and release artifacts.
- [ ] G5: clean archive/image/runtime verification, GW-01..24 evidence and local commits.
- [ ] External: separately authorized bounded live inference (GW-20).
- [ ] External: remote CI/publication only with separate authorization.

## Decisions and risks

Single-process counters, reservations and circuit state are ephemeral and documented;
no durable quota promise. Per-operator session caps are conservative reservations,
never refunded on failed upstream calls. Reset clears circuits only, never quotas.
Default startup has no configured provider and makes zero upstream calls. Explicit
provider IDs, operator authorization, cost/privacy policy group and per-request
fallback consent are all required to send a second request. No account rotation to
work around a shared quota: Cloudflare account IDs must be unique, and 429 stops.
Image security approval is distinct from source preview evidence.

## Validation policy

Use a real loopback HTTP server for both provider formats and failure/cancel tests.
Preserve raw dependency/OS scans and exact image/source identity. Live generation,
web search, push, publish, tag, deploy, credential/log deletion remain unauthorized.
An unavailable external gate remains BLOCKED, never inferred PASS.
