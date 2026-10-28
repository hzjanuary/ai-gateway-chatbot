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
- Live request remains BLOCKED until separately authorized with provider/plan/privacy,
  1–2 calls maximum, tiny output cap, no fallback/search, no raw key/content evidence.
- Remote CI evidence remains BLOCKED until an authorized push. No local green run
  can prove a remote GitHub Actions execution.
- Owner must explicitly authorize push, public disclosure, tags, release or deployment.
- Do not delete credentials/logs, rewrite historical Git or auto-change provider billing.
