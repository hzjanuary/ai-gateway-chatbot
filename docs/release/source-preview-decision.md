# Owner decision: v0.1.0 source-only preview

Recorded 2026-10-29 from the repository owner's explicit release instruction.

The owner authorizes an early **SOURCE-ONLY v0.1.0 GitHub pre-release**, normal
feature publication and PR #2 merge through the ordinary GitHub mechanism, subject
to required reviews, rules and status checks. The owner acknowledges source
publication despite the documented unresolved Debian OS findings in tested images.
This decision does not approve Docker images or unrestricted production deployment.

SPEC-001 stays **23 PASS / 0 FAIL / 1 BLOCKED**. GW-20 remains BLOCKED with zero
genuine live provider requests. Offline loopback tests do not substitute for model
execution. The original acceptance definitions and their evidence are unchanged.

Docker image-security approval remains **FAIL**. Preserve the raw baseline and
completed current scans: **0 CRITICAL / 44 HIGH / 58 MEDIUM / 61 LOW / 1 UNKNOWN**.
Preserve the failed image-security jobs and overall workflow conclusions. No VEX,
suppression, scanner exception, severity downgrade or security signoff is created.
Third-party/bundled license obligations remain separate from the MIT project license.

The pre-release contains GitHub source archives only. No prebuilt Docker image,
deployment, inference or provider/billing account change is authorized. Do not
bypass branch protection or required checks, rewrite history or delete the feature
branch, retained evidence, credentials, configuration, test data or volumes.

Publication prerequisites are the final diff/documentation review, source secret/
private-path/archive/license checks, genuine CI on the final feature SHA, and a
normal PR merge if GitHub rules allow it. A required failing image-security check
blocks merge; this decision does not permit changing that rule. Tag v0.1.0 only on
the verified new main commit and only if unused. Actual publication state and
commit identities must be read back from GitHub, not inferred from this decision.

See [verification](verification.md), [security findings](security-findings.md),
[release checklist](checklist.md) and [unfinished maintenance](maintenance-backlog.md).
