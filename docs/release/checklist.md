# Release checklist

- Audit the complete SPEC-001 GW-01..24 matrix against current authoritative evidence.
- Record exact code SHA, archive SHA-256, base manifest, image config digest and OCI revision.
- Run scripts/quality.sh from the committed source archive, not an operator workspace.
- Run scripts/release_smoke.py with a clean archive build, isolated loopback/internal
  HTTP fixtures, actual image CLI, health/auth, restart and private-file checks.
- Run scripts/security_gates.py for headless and optional UI; retain all raw reports,
  actual-image Python license texts, OS inventory, CycloneDX SBOM and scanner DB dates.
- Inspect every Python/OS finding and license condition. Failed scans remain failures;
  unavailable scans remain BLOCKED. Never turn an OS failure into a source failure
  automatically, or source tests into an image approval automatically.
- Source preview recommendation, Docker security approval and production/live acceptance
  need independent decisions. No production-ready claim without appropriate evidence.
- GW-20 remains BLOCKED for this source preview. No inference may be performed in
  this release workflow; offline tests do not replace genuine model execution.
- Read genuine push/PR checks on the final feature SHA. Python 3.12/3.13 source,
  full history/secret/integrity and license checks must pass. Preserve known OS
  failures honestly; do not claim that overall CI passed. A new unexpected
  functional, secret, integrity or licensing failure stops publication.
- Present the README security warning before installation and record the owner's
  [source-only decision](source-preview-decision.md) separately from image approval.
  Acceptance stays 23 PASS / 0 FAIL / 1 BLOCKED. Preserve raw scans and maintenance backlog.
- Inspect required reviewers/rules/status checks before marking Draft PR #2 ready
  and merging normally. Never bypass protection or reinterpret a required failed
  image check. Do not squash/rebase/rewrite the preserved feature history or delete it.
- After merge, verify main and unused v0.1.0 tag. Publish only a GitHub PRE-RELEASE
  with source archives and explicit live/OS/license limitations; no Docker asset.
- Read back main, README/SECURITY, tag target, release prerelease flag and source
  archive contents/hashes. Preserve raw CI/artifact evidence and all local state.
- Stop after this one source-only preview; do not begin a new implementation,
  inference, deployment or publication campaign.
- Owner must explicitly authorize push, public disclosure, tags, release or deployment.
- Do not delete credentials/logs, rewrite historical Git or auto-change provider billing.
