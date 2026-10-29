# SPEC-001 verification — source PASS; workflows and image security FAIL

Observed **2026-10-29**. Branch `feat/spec-001-oss-inference-gateway`.
**23 PASS / 0 FAIL / 1 BLOCKED / 0 NOT_RUN** against the original GW definitions.
This acceptance score does **not** mean the workflows or images pass: both real
workflows conclude **FAIL**, solely because the unchanged OS vulnerability gate
correctly rejects 44 HIGH findings. GW-20 remains BLOCKED; zero real inference.

Tested feature commit: **`4bde8290262f3d6e1bf304dd8e51a8d57154f907`**.
PR checkout: **`47809f39eb357d4265d721052f2cb241df0805e8`**, GitHub's synthetic
merge of that head with unchanged main `d2d859a8b59a5a396c62478a315f533d27007934`.
This is not a merge into main. [Draft PR #2](https://github.com/hzjanuary/ai-gateway-chatbot/pull/2)
remains open/unmerged. The three formerly unpushed commits b576c76, bbe76d0 and
fa3dde6 are preserved and included in the normal, non-force feature push.

The final result documentation is local-only after reviewing the authorized new
runs, to honor the stop boundary without starting another CI cycle. It changes no
runtime, scanner, tests, dependency or workflow inputs. The exact remotely tested
candidate above must not be confused with a later local reporting HEAD. The public
PR description records the final outcomes. No merge, tag/release, image publication,
deployment, paid billing, history rewrite or retained-data deletion occurred.

## Confirmed corrections and infrastructure diagnosis

FastAPI's locked OpenAPI generator falls back to `http.client.responses`; Python
3.13 changed phrases for 413/422. Eight explicit error descriptions now preserve
the unchanged golden document on Python 3.12/3.13. HTTP codes, ErrorEnvelope,
response schemas, validation/auth/roles/streaming and dependency lock are unchanged.
The new phrase-mutation regression still requires exact full-document equality.

Pinned Gitleaks ordinary `git log -p -U0 --all` omitted the patch of synthetic PR
merge `ffab9b6edd364259a588aa1b94f4a9df348f396a`. Its exact 17-commit graph reproduced
16 scanned, then 17 with `--all --full-history --diff-merges=separate`. Every merge
is diffed against every parent; all reachable branch history and all scanner rules
remain included. Strict nonzero/count equality and the three exact historical span
reviews remain enforced; SHA/parent inventories and shallow-history rejection are
recorded. There is no merge subtraction or first-parent traversal. Two temporary
five-commit merge tests prove clean 5/5 coverage, detection at the transient side
commit and merge resolution, ordinary 4/5 FAIL, and omitted 2/5 FAIL even with no
findings. Raw duplicate rule/parent findings are retained. Synthetic credentials
are generated only in temporary test repositories, not published as source.

The Trivy failure was **Docker bridge DNS reachability**, not an established TLS,
proxy or registry credential defect. Host DNS/direct verified HTTPS succeeds for
both mirror.gcr.io and ghcr.io; bridge containers time out resolving both; explicit
host-network containers resolve both and receive the normal registry HTTP 401
challenge. No private resolver/proxy/credential values are in sanitized evidence.
No host DNS, Docker daemon, firewall or VPN settings were modified.

The pinned 0.76.1 CLI confirms official defaults and `--db-repository` support.
Both scan/SBOM invocations explicitly select `ghcr.io/aquasecurity/trivy-db:2`.
Opt-in `--scanner-network host` restores only the local scanner connection; default
and CI remain bridge. **GHCR selection alone does not solve local bridge DNS.**
Both official downloads complete with valid current DBs under these choices.
Metadata/digest are retained; absent/expired/schema-mismatched DB evidence fails.
No skip-update, empty/stale DB, TLS bypass, ignore-unfixed or suppression was used.
Source matrix `fail-fast: false` preserves complete evidence without changing gates.

## Actual new GitHub Actions outcomes

| Event / real run | Checkout | Python 3.12 source | Python 3.13 source | Headless image job | UI image job | Overall |
| --- | --- | --- | --- | --- | --- | --- |
| [Push 40808326213](https://github.com/hzjanuary/ai-gateway-chatbot/actions/runs/40808326213) | exact feature HEAD 4bde829 | PASS | PASS | FAIL: known OS gate; build/smoke PASS | FAIL: known OS gate; build/smoke PASS | **FAIL** |
| [PR 40808329433](https://github.com/hzjanuary/ai-gateway-chatbot/actions/runs/40808329433) | synthetic merge 47809f3 | PASS | PASS | FAIL: known OS gate; build/smoke PASS | FAIL: known OS gate; build/smoke PASS | **FAIL** |

All eight jobs completed; **0 CANCELLED / 0 SKIPPED**. Actual source runtimes are
Python **3.12.15** and **3.13.17**. Every source job passes **117/117 tests**,
lock/hash exports, Ruff, Black, strict MyPy, source/private/history scans, wheel/
sdist build and Python advisory gates. Gitleaks covers **20/20** pushed commits
and **21/21** PR commits, three raw/reviewed historical findings, zero unreviewed.
The inventories in [remote evidence](evidence/remote-ci-4bde829.json) list every
examined SHA and parent, including the new PR merge. No coverage check was relaxed.

Every image job passes its clean committed archive install, full 117-test source
suite, package/build and actual runtime smoke. Headless has 11 named smoke checks;
UI has 12, including authenticated optional UI startup. Provider output comes only
from isolated HTTP loopback/internal-network fixtures; no live provider is claimed.
All image security subcommands complete, SBOMs succeed, artifacts upload even on
failure. Security summary failures are exactly `["image-security"]` in all four.

Eight artifact ZIPs were downloaded and individually SHA-256 verified against the
GitHub artifact digests. Source tar contents/hashes and image manifest/config chains
were verified; no .env, provider/admin credentials, sessions, logs or private raw
local evidence appears in source archives. LICENSE/NOTICE and the exact Streamlit
supplement hash pass. Raw reports and all severities remain preserved, not replaced.

## Local verification and provenance

After the minimal scanner change, `./scripts/quality.sh` passes on Python 3.12.9;
full isolated Python 3.13.2 pytest passes. Both have **117/117** (114 original plus
three new cases), zero failures/errors/skips. The earlier full 3.13 quality result
is retained. Test files: security 45, transport 44, streams 17, enrichment/UI 6,
packaging 3, real Git history 2. These are 117 distinct cases, not a sum of reruns.

Controlled security invocations (exit **1**, only known image-security failure):

```sh
.venv/bin/python scripts/security_gates.py --image inference-gateway:spec001-bbe76d0 --scanner-network host --output .local/verification/trivy-restore/headless-security
.venv/bin/python scripts/security_gates.py --image inference-gateway:spec001-ui-bbe76d0 --scanner-network host --output .local/verification/trivy-restore/ui-security
```

Those existing images were not rebuilt for a scanner endpoint change. Their exact
OCI index/platform/config digests remain unchanged, with runtime source
`bbe76d06cfb8707df0a4ecbba28da52fe14672b7` and Python 3.13.18. Both actual image
smokes rerun successfully from that exact archived source (11/12 checks). Runtime,
Dockerfile and locked build inputs are unchanged between bbe76d0 and 4bde829.
The new remote images are separately built/labeled from their actual checkout;
local identities are not relabeled as the new remote source commit.

Pre-push source archive at 4bde829: SHA-256
`77ab1966642b4a819bdcbea5f50f29479407862d60e7dbe20892b87c10f56a6c`.
PR merge archive: `5214ece30c2af808c7697312da0d41d1f5030bd7bcce5b792d0c461682fb4484`.
Both remote variants verify their event's identical source archive. Clean archive,
tracked-file Gitleaks, all-Git-blob/private-path checks and license checks pass.

| Event / variant | Root image manifest digest | Image config digest |
| --- | --- | --- |
| Push headless | `sha256:e7c69ef9c554e261d4efdf7cbf4600797bb07c64ffd87d8319c1aa18fac5f8ff` | `sha256:9d8d706db6f3a8e7e7ed14a40ea6f8a42330c973f759cddb9b0f86ce897e2072` |
| Push UI | `sha256:83b7b32982c87026b7f9d5a08d10f965934727fd3a13c0576178cb7d043ec90a` | `sha256:ec91315818d427d7be697e2e0444960087f475168afc930bead3c048d1a6b72b` |
| PR headless | `sha256:b775f7bb42796208f36c0bde885a4b942f2fc85ed91a347ff13666b3c05e987b` | `sha256:aacf4e9b57041d34fce04c08ef0e997e01257b0f0a5871be9f3b9c5e87b2fc65` |
| PR UI | `sha256:b34720ec17022be77d2c692e8e578d17435851017127c639c697f72c81406929` | `sha256:df6123dd78be8e548211b6d8f22dcd7220b0476eb9723631b46d4eaf602b2848` |

Remote saved-image roots are single-platform manifests; the helper's historical
`oci_index_digest` field equals that platform manifest in these artifacts. The
table uses its actual meaning. No registry push, signing or bit-identical rebuild
claim is made. All use pinned linux/amd64 Python base
`sha256:aaf08c5490d52cd92bc27142a5215b1e47355a5eaf9adfad2a0fbc022d0b5490`.

## Security and DB evidence — independent FAIL retained

Trivy **0.76.1**, immutable scanner
`aquasec/trivy@sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c`.
Official DB repository: `ghcr.io/aquasecurity/trivy-db:2`, schema **2**,
UpdatedAt **2026-10-29T01:22:22.544155871Z**,
NextUpdate **2026-10-30T01:22:22.544155326Z**. DB file SHA-256
`ad47d4d7f64fb08225e3d0c9f59118e724ecf82a14d5502fff71c742d6cb24b4`.
Per-scan download times and metadata are in the evidence. Local and all four remote
scans use valid current DBs; scanner completes exit 0, aggregate gate exits 1.

Every scan: **164 OS findings = 0 CRITICAL / 44 HIGH / 58 MEDIUM / 61 LOW /
1 UNKNOWN**; zero image secrets and zero Python-package vulnerabilities. Exact
CVE/package/installed/severity/fixed-version tuples match the preserved baseline;
newer DB and separate image build identities introduce no findings delta. HIGH
entries cover CVE-2025-69720, CVE-2026-16742, CVE-2026-54369, CVE-2026-76642,
CVE-2026-78408, CVE-2026-78409, CVE-2026-78410 and CVE-2026-9538. Their scanned
stable fixed-version fields remain absent/null. Full rows and available vendor fixes
are retained in [security findings](security-findings.md) and machine/raw evidence.
No finding or severity was suppressed, downgraded or erased.

Python audits: zero advisories for **17 headless / 44 UI / 99 dev-build** packages.
Actual Python license/text inventory checks pass 17/44 distributions; SBOMs contain
105/132 components. Raw Trivy license matches remain exactly baseline: 684/1718,
including the known UI CRITICAL license-category WTFPL match inside PyArrow's
bundled LICENSE.txt. This is not a CRITICAL CVE; it remains unsuppressed for image
redistribution review. Neither license inventory success nor functional CI grants
Docker image approval. All vulnerability/secret/license scanners remain enabled.

## GW-01…GW-24 acceptance matrix

Current statuses use the new exact push/PR evidence; detailed original offline
proof remains in retained historical reports. All 117 source cases revalidate the
supported offline behaviors. GW-21 measures complete CI execution/provenance under
its original definition, not a successful OS gate or overall green workflow.

| ID | Status | Current evidence and limits |
| --- | --- | --- |
| GW-01 | PASS | Four clean committed archive installs/builds, 117 tests each, package builds and no operator state. |
| GW-02 | PASS | Security tests plus actual image private init: explicit/idempotent setup, file permissions, missing/weak/placeholder tokens denied. |
| GW-03 | PASS | Admin/UI authentication tests and actual optional UI startup; no server token prefill. |
| GW-04 | PASS | Full inference/admin role endpoint matrix and legacy alias tests. |
| GW-05 | PASS | Protected admin families, minimal public health/readiness/schema, safe validation errors; no retained-log deletion API. |
| GW-06 | PASS | Compose loopback, optional profiles, non-root/read-only/cap-drop and actual image checks. |
| GW-07 | PASS | 44 transport cases plus streams: real loopback HTTP Cloudflare/Ollama formats, no external provider calls. |
| GW-08 | PASS | Routing strategy, provider/model truthfulness and explicitly consented policy fallback tests. |
| GW-09 | PASS | Auth/quota/billing/model/schema/policy errors never fallback; exact upstream counts asserted. |
| GW-10 | PASS | Bounded distinct attempts/deadlines/reservations, permitted failures and operator/caller policy consent tests. |
| GW-11 | PASS | Exhaustion/reset invariants, no duplicate/reset during a request. |
| GW-12 | PASS | 17 stream cases: fragmented UTF-8/SSE/NDJSON, malformed/truncated frames, disconnect cancellation and no post-output switch. |
| GW-13 | PASS | Nonstream error statuses, valid JSON/SSE, real provider identification fields in offline transport fixtures. |
| GW-14 | PASS | Body/prompt/output/concurrency/call/token/deadline limits and cancellation release tests. |
| GW-15 | PASS | Fixed Cloudflare origin, explicit IP-only approved Ollama trust zone, injection/metadata/redirect rejection. |
| GW-16 | PASS | Six enrichment/UI cases include opt-in bounded mock search and untrusted context; no external search. |
| GW-17 | PASS | Canary/privacy tests, actual image logs without synthetic prompts/tokens, zero image secrets. |
| GW-18 | PASS | Cooldown/half-open/accounting tests and truthful ephemeral restart behavior. |
| GW-19 | PASS | Actual image init/doctor/provider metadata/CLI tests; Ollama-format HTTP fixture, no real generation. |
| GW-20 | BLOCKED | Zero live requests. Prior authorized smoke stopped at non-generative preflight with no eligible configured real provider. No inference authorized in this task. |
| GW-21 | PASS | Both genuine event workflows execute source/ops/secret/history/archive/license/dependency/image/OS/SBOM scans with exact provenance and verified artifacts. Raw OS FAIL and overall workflow FAIL are preserved. |
| GW-22 | PASS | Required interface/privacy/cost/security/license docs exist; exact OpenAPI/settings schema tests pass on both remote Python versions, golden JSON unchanged. |
| GW-23 | PASS | Four actual clean-source image builds and runtime/CLI/health/restart/UI smoke passes; no seeded operator/session data. |
| GW-24 | PASS | Source functional/history/dependency readiness separated from OS/license/image approval and live acceptance; no fake green claim. |

## Retained evidence and remaining release work

Authoritative new [remote evidence](evidence/remote-ci-4bde829.json) contains job
conclusions/steps, each SHA/parent graph, eight artifact digests, DB/image/source
identities, full common CVE rows and raw report hashes. [Local remediation evidence](evidence/trivy-restore-local.json)
records bounded connectivity checks and existing-image scans. Full ZIPs/logs/scans
are retained in ignored `.local/verification/remote-ci-4bde829/` and
`.local/verification/trivy-restore/`. No temporary signed artifact URL or private
network/credential configuration is included in committed evidence.

Earlier [remote failures](evidence/remote-ci-4761d6a.json), [local corrections and
DNS failures](evidence/ci-regressions-local-bbe76d0.json), [zero-call live preflight](evidence/live-smoke-preflight.json),
R=`46744d5aed5a797701c0bea00705664f0f229a13` archives/images/raw hashes, and all
original failed scans remain preserved. The previous verification text is also
retained locally and in Git history. New successes do not rewrite old FAIL records.

Source functional/history/dependency verification at 4bde829 is **PASS** for a
source-only candidate. Source-only v0.1.0 publication still needs owner/reviewer
acceptance of the documented live-validation limitation, disclosure/release notes,
review/synchronization of the final sanitized report, and separate authorization
for merge/tag/release. No such publication is performed here. Docker security approval
remains **FAIL** until actual supported OS remediation or separately approved
security disposition, plus redistribution/license review; then rebuild/rescan.
GW-20 remains **BLOCKED** until a separately authorized genuine provider smoke.
The authorized remote verification is finished; work stops at this boundary.
