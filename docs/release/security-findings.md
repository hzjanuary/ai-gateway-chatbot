# Security findings and independent release decisions

Latest 2026-10-29: official GHCR schema-2 DB download and both existing-image scans
succeed with explicit local scanner host networking, without host configuration
changes. DB updated 2026-10-29T01:22:22Z. Exact CVE/package/version/severity/fix rows
are unchanged from the preserved baseline: 164 OS findings, 44 HIGH, 58 MEDIUM,
61 LOW, 1 UNKNOWN, 0 CRITICAL. Zero secrets/Python vulnerabilities; gate still FAIL.
Raw license classifications also match baseline exactly (684/1718), including the
existing UI WTFPL CRITICAL license-category match in PyArrow's bundled LICENSE.txt.
No license match is suppressed or treated as image publication approval. Inventory
text checks pass 17/44 and both SBOMs succeed. See [fresh DB and raw-report hashes](evidence/trivy-restore-local.json).

2026-10-29 correction update: local source bbe76d06 passes both Python quality
suites (117 tests each) and both new image smoke runs. New image scans each exit
1 with `image-scanner`: container DNS times out fetching the Trivy DB mirror.
No new vulnerability/secret scan JSON was produced. The prior raw 164 OS findings
and 44 HIGH remain preserved FAIL, not superseded by an empty report. No scanner
retry/configuration change or suppression was performed; stopped before feature
push and new remote CI. Python advisory scans still report zero for 17/44/99
packages. See [sanitized correction evidence](evidence/ci-regressions-local-bbe76d0.json).

Verified runtime source: `46744d5aed5a797701c0bea00705664f0f229a13`.
Observed 2026-10-28. All full reports remain in `.local/verification` and their
SHA-256 values are recorded in [evidence summary](evidence/summary.json).

Python advisory scans found **0** advisories across 17 headless, 44 UI and 99
runtime/UI/development/build dependencies. Both actual-image Python license gates
pass (17/44 distributions); no image secrets were detected. These are measured
scanner results, not a claim that vulnerabilities cannot exist.

Trivy **0.76.1**, immutable scanner digest recorded by security_gates.py, found
**164 OS package/CVE findings**, **71 unique CVEs**, including **44 HIGH findings
across eight unique CVEs**, **0 CRITICAL**, in each image. Python image-package
vulnerabilities: zero. DB UpdatedAt: `2026-10-28T07:10:42.861393948Z`.
The HIGH/CRITICAL gate returns failure and remains **FAIL**. Full lower-severity
findings are retained. No ignore-unfixed, advisory suppression or package-removal
workaround was used to make it green.

| HIGH CVE | Source packages represented in the image | Authoritative tracker |
| --- | --- | --- |
| CVE-2026-76642 | util-linux | [Debian](https://security-tracker.debian.org/tracker/CVE-2026-76642) |
| CVE-2026-78408 | util-linux | [Debian](https://security-tracker.debian.org/tracker/CVE-2026-78408) |
| CVE-2026-78409 | util-linux | [Debian](https://security-tracker.debian.org/tracker/CVE-2026-78409) |
| CVE-2026-78410 | util-linux | [Debian](https://security-tracker.debian.org/tracker/CVE-2026-78410) |
| CVE-2026-54369 | acl | [Debian](https://security-tracker.debian.org/tracker/CVE-2026-54369) |
| CVE-2025-69720 | ncurses | [Debian](https://security-tracker.debian.org/tracker/CVE-2025-69720) |
| CVE-2026-16742 | systemd | [Debian](https://security-tracker.debian.org/tracker/CVE-2026-16742) |
| CVE-2026-9538 | perl | [Debian](https://security-tracker.debian.org/tracker/CVE-2026-9538) |

The checked stable trixie versions remain marked vulnerable; available fixes shown
for unstable/forky do not prove a safe stable-image update exists. Some Debian
notes use a lower urgency/minor classification; the gateway's HIGH gate is **not**
lowered to match. Non-root, dropped capabilities and read-only runtime limit some
paths, but do not prove non-exploitability or justify an automatic waiver. Rebuild
from a reviewed fixed stable base and repeat the exact gates before image approval.

Gitleaks scanned every one of 13 commits at the verified source point. Raw result:
exit **1**, **3 findings**. Exact review in scripts/history_findings.json identifies
two historical localhost curl placeholders and one public prototype default of
18 characters. That default is removed and cannot satisfy the current minimum-32
high-entropy token policy. If an operator reused the historical default, it must
be replaced privately. No real provider credential was identified in these reviewed
spans; history was not rewritten. Full redacted raw findings remain preserved;
**no scanner rule/file/commit is suppressed**. Any new finding or changed span
fails review. The wrapper also rejects successful exits with zero/incomplete scan
coverage, a real false-green behavior observed during Docker ownership testing.

The Streamlit 1.66.1 wheel omitted License-File/text. The official tagged Apache-2.0
text is now shipped, checksum-pinned and read back from the actual image. Dual
Apache/BSD metadata and PSF-2.0 were correctly recognized; license findings were
fixed with evidence, not waived. OS license/source redistribution obligations and
private-disclosure availability require owner review before any public image.

**Source-preview offline engineering gates: PASS. Docker image security approval:
FAIL. Production/live acceptance: BLOCKED. Public release/push/deploy: NOT AUTHORIZED.**

## Remote CI follow-up and fixed-version availability

Push workflow [40703768224](https://github.com/hzjanuary/ai-gateway-chatbot/actions/runs/40703768224)
and PR workflow [40703883376](https://github.com/hzjanuary/ai-gateway-chatbot/actions/runs/40703883376)
retain the same 164 OS findings / 44 HIGH / zero CRITICAL in all four images.
Every HIGH entry has no FixedVersion value in the scanned trixie report. Primary
Debian tracker review on 2026-10-28 confirms stable trixie remains affected; the
fixed source versions below belong to unstable/forky, not an approved stable fix.

| CVE | Scanned stable source version | Stable FixedVersion in Trivy | Debian unstable fixed source version |
| --- | --- | --- | --- |
| [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) | ncurses 6.5+20250216-2 | none | 6.6+20251231-1 |
| [CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742) | systemd 257.13-1~deb13u1 | none | 261.2-1 |
| [CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369) | acl 2.3.2-2+b1 | none | 2.4.0-1 |
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) | util-linux 2.41.5-0+deb13u1 | none | 2.42.3-1 |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) | util-linux 2.41.5-0+deb13u1 | none | 2.42.4-1 |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) | util-linux 2.41.5-0+deb13u1 | none | 2.42.3-1 |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) | util-linux 2.41.5-0+deb13u1 | none | 2.42.3-1 |
| [CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538) | perl 5.40.1-6+deb13u1 | none | 5.42.3-1 |

Exact binary package versions, repeated package/CVE rows, raw scan hashes and
artifact digests are retained in [remote evidence](evidence/remote-ci-4761d6a.json).
Raw findings and FAIL status are unchanged; no downgrades or suppressions.

Remote evidence also invalidates a broad source-ready conclusion: Python 3.13
fails the exact OpenAPI contract, and PR scan coverage reports 17 expected versus
16 scanned commits. No new secret finding was detected. The owner required stop
on new defects, so code/workflows/gates are unchanged and no rerun is attempted.
Current source publication readiness is FAIL pending owner defect review; image
security approval remains independently FAIL for OS findings.
