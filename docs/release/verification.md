# SPEC-001 verification — offline source preview

Observed **2026-10-28**, branch `feat/spec-001-oss-inference-gateway`.
**22 PASS / 2 BLOCKED / 0 FAIL / 0 NOT_RUN** in the acceptance matrix. This is an
engineering score, not production approval: the independent **Docker image security
gate is FAIL** (44 HIGH OS findings). No publication, push, tag, merge or deployment
has been performed. No real provider generation or external search was executed.

Verified implementation/source commit **R**:
`46744d5aed5a797701c0bea00705664f0f229a13`.
Baseline: `d2d859a8b59a5a396c62478a315f533d27007934`.
Later documentation/evidence commits do not change that verified runtime payload;
images deliberately retain R as OCI revision. Do not relabel them as a later HEAD.

Committed source archive (both image builds):
`source-46744d5aed5a797701c0bea00705664f0f229a13.tar`, SHA-256
`210c8578461542b12b9f71c1fdfefe34484f00d272699cd18eca4e8d4fdc5d13`.
The archive was extracted into a new temporary directory, installed from the lock,
tested and packaged; no workspace credentials/logs, .git, .venv or seeded state.
Raw source/image archives remain local, not published.

| Variant | Local image | OCI index digest | Platform manifest digest | Image config digest |
| --- | --- | --- | --- | --- |
| Headless | `inference-gateway:spec001-46744d5` | `sha256:0167c5222313949bbd66e2b4e993116d74d039f95f673c5890f11352cf2209dc` | `sha256:f015520040be66f1ef8ac076d48852426d88ad1a47403daa2619f6240dd04e43` | `sha256:ed7e7191828e1c3002059f655d6e7ee33fe61cbc0b7054836f9d05a61bf7e8de` |
| Optional UI | `inference-gateway:spec001-ui-46744d5` | `sha256:020ba8a61c58c38074ef046dc8902f2a2fe95cc9035e6cb30c914a23c5c6d4b1` | `sha256:eee583d31ef3ddf7ef79b6bf6578a7d2292f3fd389f8a22231802ddf370189fa` | `sha256:e1825102068e68219a456734aa1dce59a3b83bfd23fc732f616e5dbae4f72e67` |

Both use Linux amd64 `python:3.13-slim-trixie` base manifest
`sha256:aaf08c5490d52cd92bc27142a5215b1e47355a5eaf9adfad2a0fbc022d0b5490`.
Docker 29 reports the OCI index as image ID; config and platform manifest were
independently extracted/hash-checked from the saved image. These are local build
identities, not evidence of registry publication or signing.

## Exact command records

Run at R with a non-root operator and Docker access. Only loopback/internal HTTP
fixtures generate test output. No host ports are published by release smoke.

**Q — complete workspace quality** (exit 0):

```sh
./scripts/quality.sh > .local/verification/quality-accepted.stdout.txt 2> .local/verification/quality-accepted.stderr.txt
```

Q executes uv lock/hash-export checks, Ruff, Black, strict MyPy, `uv run --locked
--extra ui pytest -q --junitxml=.local/verification/pytest.xml`, tracked source/all
Git blob scans, immutable Gitleaks with full coverage verification, and
`uv run --locked python -m build --no-isolation` using locked Hatchling.

**H — clean source + actual headless image** (exit 0):

```sh
.venv/bin/python scripts/release_smoke.py --image inference-gateway:spec001-46744d5 --build --quality --output .local/verification/accepted-headless
```

**U — actual optional UI image** (exit 0):

```sh
.venv/bin/python scripts/release_smoke.py --image inference-gateway:spec001-ui-46744d5 --build --ui --output .local/verification/accepted-ui
```

**SH / SU — full security gates** (both exit **1**, only image-security failed):

```sh
.venv/bin/python scripts/security_gates.py --image inference-gateway:spec001-46744d5 --output .local/verification/accepted-headless-security
.venv/bin/python scripts/security_gates.py --image inference-gateway:spec001-ui-46744d5 --output .local/verification/accepted-ui-security
```

SH/SU run Python advisory scans of headless/UI/development+build locks, source and
history scans, coverage-verified Gitleaks, actual image OS/Python/secret/license
scan, CycloneDX SBOM, package/license texts, source-package inventory and provenance.
All raw stdout/stderr, scanner metadata and failed findings are retained. The
script gathers all reports before returning failure; it never suppresses OS issues.

Baseline evidence command: `python3 scripts/baseline_audit.py` — nine historical
static defects confirmed, no prototype import/credential or provider execution.

## Measured test counts

Q and H each passed the same **114 distinct pytest cases**, zero failures/errors:
Python 3.12.9 locally and in the clean archive. Actual images run Python 3.13.
Do not add the two runs together as 228 distinct tests.

| Suite alias | Test file | Cases |
| --- | --- | ---: |
| S | tests/test_security.py | 44 |
| T | tests/test_transport.py | 44 |
| F | tests/test_streams.py | 17 |
| UIt | tests/test_enrichment_ui.py | 6 |
| P | tests/test_packaging.py | 3 |

H passed **11 named archive/image checks**; U passed **12**, including actual chat
and admin UI startup in a read-only container. These are separate runtime assertions,
not additional pytest cases. One upstream Starlette HTTPX deprecation warning was
observed; it did not fail a test or weaken any gate. Ruff, Black, strict MyPy and
wheel/sdist builds pass. No remote CI result is claimed.

## GW-01…GW-24 acceptance matrix

All rows refer to source R and the image digests above. Suite counts are full-file
coverage counts from JUnit; named tests identify the relevant evidence within them.
Commands Q/H/U/SH/SU are the exact invocations above.

| ID | Status | Commands, measured counts and authoritative evidence |
| --- | --- | --- |
| GW-01 | PASS | H: fresh extracted committed archive, locked install, 114 tests, wheel/sdist build; both images built from that archive, no user config. |
| GW-02 | PASS | Q/H, S=44: explicit private/idempotent init, missing/placeholder/handwritten weak hash denied, file owner/mode/symlink checks; H image init. |
| GW-03 | PASS | Q, UIt=6: missing/wrong admin secret denied, valid admin API validated; U: missing secret abort and actual chat/admin startup. |
| GW-04 | PASS | Q, S=44: endpoint role matrix, admin cannot infer and inference cannot read/mutate admin endpoints; legacy alias covered. |
| GW-05 | PASS | Q, S=44: all admin route families protected, public minimal health/schema/readiness, no raw validation echo, no log-file deletion/reader. |
| GW-06 | PASS | Q, P=3: loopback ports, optional profiles, no source mounts, non-root/read-only/cap-drop; H/U actual Compose config validates all profiles. |
| GW-07 | PASS | Q/H, T=44 and F=17: real loopback HTTP servers exercise Cloudflare REST/SSE and Ollama JSON/NDJSON, actual payloads and auth; external DNS denied. |
| GW-08 | PASS | Q/H, T=44: deterministic two-node round robin, strategy changes, actual provider ID/model; explicit consented Cloudflare→Ollama fallback in JSON and SSE. |
| GW-09 | PASS | Q/H, T=44: 401/403/400/402/404/422/429, billing/policy/model/schema errors never fallback; exact upstream request counts. |
| GW-10 | PASS | Q/H, T=44: explicit 500/502/503/504 and attempt-timeout fallback, max three distinct attempts, reservation/shared deadline; policy change needs operator target plus caller consent. |
| GW-11 | PASS | Q/H, T=44: exhausted node stays exhausted, no duplicate/reset inside request, admin reset preserves spent call/token reservations. |
| GW-12 | PASS | Q/H, F=17: byte-split UTF-8, multiline SSE, LF/CRLF/CR+BOM, NDJSON, malformed/truncated streams, pre-output status and post-output error/no end, real socket disconnect before/after output. |
| GW-13 | PASS | Q/H, T=44: nonstream failure is non-2xx, malformed/error responses cannot become success, provider/model never unknown; actual image JSON and SSE. |
| GW-14 | PASS | Q/H, S=44/T=44/F=17: HTTP/prompt/output limits, attempt/token/call budgets, separate gateway/node concurrency, deadline and cancellation release. |
| GW-15 | PASS | Q/H, S=44: caller endpoint/header injection rejected, fixed Cloudflare origin, explicit IP-only Ollama private trust zone, metadata/link-local/redirect-style URL rejection. |
| GW-16 | PASS | Q/H, UIt=6: enrichment globally/per-request opt-in, one bounded local mock search, actual returned URL/time preserved, untrusted data stays in user context. No external web search performed. |
| GW-17 | PASS | Q/H, S=44/UIt=6: canaries excluded from errors/logs/metrics/UI; H/U actual image logs lack synthetic prompt/completion/tokens; SH/SU image secrets=0. |
| GW-18 | PASS | Q/H, F=17: bounded cooldown/Retry-After and one half-open probe; H/U real restart resets counters truthfully; ephemeral single-instance limits documented. |
| GW-19 | PASS | H/U: actual image init/doctor/provider list/test-metadata prove zero generation; CLI request/stream/metrics/reset exercise isolated real HTTP Ollama-format fixture. No real Ollama model or remote generation claimed. |
| GW-20 | BLOCKED | **0 live calls**. One bounded 8-output-token request is now authorized, but non-generative preflight found no configured real provider or running local Ollama; Cloudflare Free plan/hard quota unconfirmed. Stopped before inference. See [sanitized preflight](evidence/live-smoke-preflight.json) and [one-call plan](live-smoke-plan.md). |
| GW-21 | BLOCKED | Workflow pins actions and runs source/ops/history/license/image/Python/OS/SBOM gates; Q/H/U locally pass, SH/SU correctly fail OS. **0 remote CI runs**: no authorized push. Remote CI execution cannot be inferred from local evidence. |
| GW-22 | PASS | Q plus manual review: README/API/OpenAPI/settings schema, architecture/state diagram, adapter guide, privacy/limits, operations/migration/troubleshooting, SECURITY/CONTRIBUTING/LICENSE/NOTICE/examples and actual-image license inventory. |
| GW-23 | PASS | H/U: clean committed archive, locked install/build, actual non-root image CLI, network-none missing-config health/not-ready, isolated registered HTTP provider, restart, no seeded artifacts, optional UI startup. |
| GW-24 | PASS | Independent decisions recorded below: source offline preview PASS; image security FAIL; live acceptance and remote CI BLOCKED. No fake green release or production/SLA claim. |

## Security, licenses and release decisions

Python advisory counts: **0 / 17** headless, **0 / 44** UI, **0 / 99** all locked
runtime/UI/dev/build packages. Both images: **164 OS findings, 44 HIGH, 0 CRITICAL,
0 Python-package vulnerabilities, 0 secrets**. HIGH entries represent eight CVEs;
raw reports retain all severities. Debian stable versions remain affected as
verified against the primary trackers; see [security findings](security-findings.md).
No advisory gate was lowered and no ignore-unfixed was used.

Actual-image Python licenses: **17 headless / 44 UI** distributions have recognized
license evidence and actual text. Streamlit's missing wheel license is supplemented
from its exact official release tag with SHA-256 verification. See
[license inventory](third-party-licenses.md). CycloneDX: **105 headless / 132 UI**
components. OS package/source versions and licenses remain available for owner
redistribution review before image publication.

Gitleaks: **13/13 commits scanned, raw exit 1 / three findings**, all reviewed against
immutable historical span hashes (two curl placeholders and one retired short
prototype default). No rule/file/commit suppression, no history rewrite. Reviewed
secret gate passes with zero unreviewed findings. Current source/private-path
pattern scans: zero findings; raw results and limitations retained.

Source preview offline engineering readiness: **PASS, owner publication review
still required**. Docker image security approval: **FAIL**. Production/live provider
acceptance: **BLOCKED**. Remote CI: **BLOCKED**. Public release/deployment remains
**NOT AUTHORIZED**. The active plan stays open for these external gates.

## Evidence and reproducibility limits

[Machine summary and raw-report hashes](evidence/summary.json) records immutable
source/archive/image identity. Raw reports are local under `.local/verification/`:
`quality-accepted.*`, `accepted-headless/`, `accepted-ui/`,
`accepted-headless-security/`, `accepted-ui-security/`. They include source/image
archives, JUnit, full advisory/OS/secret/license results, actual license texts,
SBOMs, DB metadata, build output and failed pre-fix attempts in earlier folders.
No credentials or operator logs were deleted or published.

Reproducibility proven: clean source install/build/test/image runtime from exact
pinned source/dependency/base inputs. **Bit-for-bit identical rebuilds are not
claimed**: build timestamps/attestations and advisory database updates may differ.
No signatures, registry publication, live availability or remote CI success implied.

Next owner actions: review the source preview and private disclosure channel;
make an eligible real provider available privately, then resume the already authorized
one-request smoke after preflight; authorize push only if
remote CI/publication is desired; wait for a reviewed stable base fixing the OS
findings and rebuild/rescan both images before Docker security approval. Never
work around quota errors by account rotation or repeated circuit reset.

## Authorized live-smoke preflight update

At `1fbca20fae2c048961340e4751232fefbfca8434`, the owner authorized one real request,
maximum eight output tokens, no retries/fallback/research/hidden calls/billing change.
The environment had no registered provider or gateway configuration. Local Ollama
was absent/inactive and its non-generative version endpoint refused connection.
No qualifying Cloudflare account/Free plan/hard quota was confirmed. Therefore
**0 generation requests**, no generation HTTP status/output/usage, completion
**NOT_EXECUTED**. Provider-side enforcement could not be verified, so the request
was not sent. The allowance remains unused. No eight-total-token guarantee is made.

[Preflight evidence](evidence/live-smoke-preflight.json) preserves sanitized counts,
conditions and commit/Python provenance. This was a native Python preflight, not
an execution of either release image against a live model. GW-20 remains BLOCKED;
22/24 acceptance PASS and the independent image/CI decisions are unchanged.
