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
- [x] G4: locked dependencies, CI/security/license gates, docs and release artifacts.
- [x] G5: clean archive/image/runtime verification, GW-01..24 evidence and local commits.
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

## Release gate observations

- Local backend gates: 106 tests PASS, Ruff/Black/MyPy PASS; archive first build
  caught uv 0.6.5 lacking `uv build --locked`. Fixed with a locked Hatchling dev
  dependency and no-isolation build; repeat the clean package gate.
- First UI actual-image JSON/SSE/CLI/restart smoke PASS (d986c4c). Python advisory
  scan: 17 headless / 44 UI dependencies, zero findings. Trivy 0.76.1 image scan:
  164 OS findings, 44 HIGH; image-security gate FAIL, no suppressions.
- Gitleaks raw history scan finds three historical public examples/retired defaults.
  Immutable fingerprints and source-span hashes are reviewed explicitly; scanner
  reports and exit 1 are retained. Any new finding fails. Scan coverage must equal
  actual Git commit count (scanner exit 0 with zero commits is rejected).
- Streamlit published wheel lacks license text. Supplement official tag license
  with checksum; inventory must prove the actual image contains it. License
  classifier parsing was corrected for dual BSD/Apache and PSF-2.0 metadata.
- Remaining: final clean source/image evidence, complete security reports, release
  matrix; real provider authorization, remote CI and image OS gate remain open.

- Contract audit added cross-provider Cloudflare→Ollama fallback gated by an
  operator target plus separate request policy consent; default boundaries remain
  closed. SSE now supports CR-only and UTF-8 BOM as well as fragmented LF/CRLF.
- Actual UI startup revealed Streamlit auto-detecting development mode under pip
  --target. CLI now explicitly selects production mode and disables file watching;
  repeat actual-image UI health tests. Failure logs remain preserved.

## Current decision

Verified implementation R=46744d5aed5a797701c0bea00705664f0f229a13: full local gates
and 114 tests PASS both in workspace and clean archive; headless/UI image checks
PASS, including actual UI startup after production-mode fix. 22/24 acceptance
criteria PASS; GW-20 live and GW-21 remote CI BLOCKED. Python 17/44/99 package
scans and image license/secret gates PASS. Both OS gates FAIL: 164 findings,
44 HIGH (eight CVEs), zero CRITICAL. Do not approve images or claim production
readiness. All authorized implementation/evidence work is complete; this plan
remains ACTIVE for live consent, remote CI authorization and a fixed stable base.
See docs/release/verification.md for commands/digests/counts and independent decisions.
