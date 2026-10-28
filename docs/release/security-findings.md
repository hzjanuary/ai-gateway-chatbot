# Security findings and independent release decisions

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
