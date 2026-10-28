# SPEC-001 verification — remote CI FAIL; stopped for owner review

Observed **2026-10-28**, branch `feat/spec-001-oss-inference-gateway`.
**21 PASS / 1 BLOCKED / 2 FAIL / 0 NOT_RUN** in the acceptance matrix after remote CI.
The earlier 22-PASS offline snapshot remains preserved in its raw evidence. This is an
engineering score, not production approval: the independent **Docker image security
gate is FAIL** (44 HIGH OS findings). The owner has now authorized normal push of
this feature branch, a PR to main and genuine remote Actions verification. No
release/tag, image publication, merge or deployment is authorized. No real provider generation or external search was executed.

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

Offline evidence refers to source R and local image digests above. Remote findings
refer to pushed HEAD `4761d6a0e18277d8632927e35a9219ca61ede56e` and the distinct
PR merge ref recorded below; no local success overrides a failed remote gate. Suite counts are full-file
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
| GW-21 | FAIL | Genuine push run 40703768224 and PR run 40703883376 completed on the authorized branch. Python 3.13 OpenAPI contract test failed (113/114 PASS), PR scan coverage failed (17 expected / 16 scanned), and OS image gates retain FAIL. No rerun or gate change. [Remote evidence](evidence/remote-ci-4761d6a.json). |
| GW-22 | FAIL | Required documentation/license/privacy/security artifacts exist, but remote Python 3.13 generates different OpenAPI HTTP 413/422 descriptions from the committed contract. The exact schema gate is not green. Local Python 3.12 snapshot remains historical evidence only. |
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

Current source publication readiness: **FAIL pending contract/CI coverage review**.
The source branch is public for review, not approved for release. Earlier offline
Python 3.12 gates passed, but remote failures supersede readiness claims. Docker
image security approval: **FAIL**. Production/live provider acceptance: **BLOCKED**.
Remote CI: **EXECUTED, FAIL**. Public release/deployment remains
**NOT AUTHORIZED** for release artifacts, image publication, tags, merging and deployment.
Feature-branch push/PR and Actions verification are now authorized. The active plan
stays open for the actual remote results and live-provider availability.

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
one-request smoke after preflight; inspect the now-authorized remote CI evidence; wait for a reviewed stable base fixing the OS
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
This preflight still provides no live PASS; subsequent remote CI findings below
supersede the earlier acceptance/readiness score.

## Feature-branch publication and remote CI authorization

Owner authorization permits a normal non-force push of only
`feat/spec-001-oss-inference-gateway` to origin, opening a PR targeting main, and
executing/inspecting genuine Actions checks on the exact pushed commit. It does
not permit merge, release/tag, registry image publication, deployment, history
rewrite, weakened gates or additional inference.

Pre-push audited HEAD: `9158a36a5aee7596c5ca5464bb750f773c4e8674` (clean worktree).
Origin is the intended hzjanuary/ai-gateway-chatbot repository; main remains the
observed baseline and no matching remote feature branch/PR existed at preflight.
Tracked-file Gitleaks, all-history Gitleaks review, private-path checks, committed
source archive and license checks are rerun before push. Raw reports remain
local under `.local/verification/remote-ci-prepush/`; no operator state or private
evidence is staged or uploaded. Remote run URLs/outcomes will be added only after
GitHub supplies actual run/job records. Known OS findings retain raw reports and
FAIL status. Any unexpected new functional/security/secret/integrity defect stops
this run without changing gates or silently repairing it.

## Genuine remote Actions results — STOP condition reached

Authorized normal, non-force push published only feature branch
`feat/spec-001-oss-inference-gateway` at
`4761d6a0e18277d8632927e35a9219ca61ede56e`. Main remains
`d2d859a8b59a5a396c62478a315f533d27007934`.
[Draft PR #2](https://github.com/hzjanuary/ai-gateway-chatbot/pull/2) targets main
and remains unmerged. No tags, registry images, deployments or inference were added.

Pre-push checks at the original reviewed HEAD and final pushed HEAD confirmed
zero current tracked secrets/private paths, clean worktree, archive exclusion of
operator state/private evidence and valid license hashes/texts. Final source tar
SHA-256: `119d569b703d4c07f62e13e453068a0622244fab93e50509f3ce17a3a3a05b31`.
Gitleaks history at pushed HEAD: 16/16 commits, raw three historical reviewed
findings, zero new findings. No .env, real provider/admin token, session, logs or
private raw evidence was pushed; only intentionally sanitized verification records.

| Workflow | Checkout tested | Overall outcome | Actual source test evidence | Other gates |
| --- | --- | --- | --- | --- |
| [Push 40703768224](https://github.com/hzjanuary/ai-gateway-chatbot/actions/runs/40703768224) | Exact pushed HEAD `4761d6a0e18277d8632927e35a9219ca61ede56e` | FAIL | Python 3.12 JUnit 114 PASS, quality/advisory steps succeeded but job concluded CANCELLED by matrix fail-fast; Python 3.13 JUnit 113 PASS / 1 FAIL and job FAIL | Both clean image smoke/build checks PASS; OS image gates FAIL; artifact upload succeeded |
| [PR 40703883376](https://github.com/hzjanuary/ai-gateway-chatbot/actions/runs/40703883376) | GitHub synthetic merge ref `ffab9b6edd364259a588aa1b94f4a9df348f396a`, **not** direct HEAD | FAIL | Python 3.12 JUnit 114 PASS, job FAIL at scan coverage; Python 3.13 JUnit 113 PASS / 1 FAIL retained although job concluded CANCELLED | Both clean image smoke/build checks PASS; scan coverage and OS image gates FAIL; artifact upload succeeded |

The PR merge ref is an ephemeral test commit created by GitHub, not a merge into
main. Both run records identify the PR head, but only the push run directly tests
the exact pushed checkout. The distinction is retained in every image/source record.

**Unexpected defect 1:**
`tests/test_security.py::test_openapi_and_settings_schema_match_checked_in_contract`
fails on Python 3.13. Generated HTTP descriptions are `Content Too Large` (413)
and `Unprocessable Content` (422), while the committed schema says `Request Entity
Too Large` / `Unprocessable Entity`. The logs prove schema wording drift, not a
different HTTP numeric status. The test remains enabled and failed; no normalization,
regeneration, test relaxation or runtime change was made.

**Unexpected defect 2:** PR Gitleaks coverage expected 17 commits but reported 16,
including the additional synthetic merge ref. Raw findings remain the same three
reviewed historical cases, zero unreviewed secrets. Coverage verification correctly
fails; it was not bypassed or relabeled as successful. Push history coverage 16/16
passes. The PR image gate reports `gitleaks-unreviewed` as its aggregate failure
label even though the actual cause is coverage, not a new secret.

The owner's explicit condition requires stop on a new functional/security/secret/
integrity defect. Accordingly **no code/workflow/gate changes, reruns, or further
pushes are performed**. The final report is committed **locally only** after the
stop, and PR metadata is updated with the failures. It is not claimed that this
local reporting commit was remotely tested. All already-started runs were allowed
to finish so raw OS scans and artifacts could be preserved.

### Remote image and scan provenance

| Event / image | Source checkout | Root image manifest digest | Image config digest |
| --- | --- | --- | --- |
| Push / headless | `4761d6a0e18277d8632927e35a9219ca61ede56e` | `sha256:933371e8121aedeb9391965a6ae1fe3fa6a08d08c733ab0575a5cca90e16efc2` | `sha256:362b25ecd4becdc1a18f9a1fc56b1e218b8e23b54a61e130a14deed094557bd9` |
| Push / UI | `4761d6a0e18277d8632927e35a9219ca61ede56e` | `sha256:f0aac22a0479f553f5433f067fd4d51b947ab9556000cc580fa9aff8be89a727` | `sha256:95401cee5bf4655c2d4f05e213cf7ac103862ca502f7fa894d61ea28c0112836` |
| PR / headless | `ffab9b6edd364259a588aa1b94f4a9df348f396a` | `sha256:bf241382e80917f2c4d2905103bf6c58a0da7abb53c1a9149376c3ba928d6a55` | `sha256:56ea25c4e6cb90cbc1a754d726d35d2c7c39eb821c9e91f05cfb4226c0470d14` |
| PR / UI | `ffab9b6edd364259a588aa1b94f4a9df348f396a` | `sha256:a518e97663fd52b17e41625a58106ee5902bdd2c8a911841e9cb50f650fda6c9` | `sha256:31d7dbde84d65289a100b286ff6ec989fb66dfc7b6eb46d7aed4b64d1e7cc8da` |

The remote saved-image root is a single platform manifest, unlike local Docker 29
index-based images. The raw helper field is named oci_index_digest; in these remote
artifacts it equals the platform manifest digest. The table uses the actual manifest
meaning rather than asserting an index or registry publication. PR source archive
SHA-256: `e7ecf087bd7aeae194aca33ee9522c656bc95d3debe29d2f4c09481dea64277f`.

All four remote images retain **164 OS findings / 44 HIGH / 0 CRITICAL** and
**0 image secrets**. All HIGH fixed-version fields are absent/null in the scanned
Debian trixie data. Exact package/CVE/version rows, all severities and scanner
metadata are preserved in raw image-scan.json, with hashes in the sanitized
[remote evidence](evidence/remote-ci-4761d6a.json).

The eight HIGH CVEs are CVE-2025-69720, CVE-2026-16742, CVE-2026-54369,
CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410 and
CVE-2026-9538. [Security findings](security-findings.md) records primary Debian
tracker links and fixed-version availability; no severity was downgraded.

Each image security report also contains zero Python advisories for 17 headless,
44 UI and 99 dev/build dependencies; actual-image license inventories are 17/44
and image secrets are zero. PR security reports additionally fail coverage. These
subgate successes do not make either workflow, source publication or image approval
green. Eight remote artifact ZIPs were downloaded and SHA-256 matched to GitHub's
reported artifact digests. Full ZIPs/logs/scans remain in ignored local directory
`.local/verification/remote-ci-4761d6a/`; sanitized metadata only is in source.

Remaining BLOCKED criterion: **GW-20** (no eligible live provider, zero new inference).
**GW-21 and GW-22 are FAIL**, requiring owner review of the newly discovered defects
before changes or reruns. Image approval independently remains FAIL due to OS
findings. Main, release/tag, Docker publication, deployment and history remain untouched.
