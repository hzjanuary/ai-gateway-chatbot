# AI Gateway Multi-Node rebranding verification

Local verification date: 2026-10-29. Base main:
`cd9ce1ebfcfdfedc05fd56b0a95f01ee8f4f2508`.
Branch: `chore/rebrand-ai-gateway-multi-node`.

## Coverage correction and preservation

The reproduced old gate expected 24 commits and reported 23 with zero new secret
findings. Missing SHA is the base commit above: a real deletion-only change of
30 lines, not an empty tree change. See [full coverage rationale](gitleaks-history-coverage.md).

Commit `66bf9cd` independently accounts for every selected SHA, verifies truly
patchless trees against all parents, and requires singleton forward/reverse
scanner receipts for content-bearing commits. The pinned scanner/default rules
and three historical fingerprints are unchanged. Tests detect side-branch,
merge-resolution and deleted synthetic secrets; incomplete selection fails even
when its primary statistic matches a complete scan. No SHA exception/subtraction.

All 14 original staged rebranding files were SHA-256 snapshotted before this fix.
Their contents were verified byte-for-byte unchanged, then committed separately
as `f6ae796527150197a89c1d0b6e14c834f3463263`. At that commit the real history gate
passes **26/26 content-bearing SHAs**: primary raw count 25 plus one confirmed
reverse receipt for the deletion-only commit, zero patchless commits. Primary raw
findings remain three; independent receipts repeat those same three. Six raw
findings, three distinct fingerprints, zero unreviewed. All raw reports retained.

## Executed local checks

- Complete `scripts/quality.sh` on Python **3.12.9** and isolated **3.13.2**:
  **123/123 tests each**, zero failures/errors/skips. All original 117 cases remain;
  the history regression suite now has eight cases. Lock/hash exports, Ruff, Black,
  strict MyPy, source/private-path/all-blob scans, full-history Gitleaks and pinned
  wheel/sdist builds pass. No lockfile or dependency version change.
- OpenAPI matches the checked-in schema on both versions. Compared with base,
  **only info.title changes**; paths, operation IDs, schemas, auth and responses
  are identical. Settings schema equality remains enabled.
- Wheel metadata keeps distribution `oss-inference-gateway` version 0.1.0 and
  entrypoint `gateway`; description and five project URLs use canonical branding.
  Wheel installed/imported and CLI help verified outside the source checkout.
- 63 relative Markdown links checked with no missing targets. Canonical repository,
  issues/security, README and existing release return HTTP 200; old repository and
  release URLs redirect to the new canonical location.
- Headless and optional UI images rebuilt from clean committed source f6ae796:
  **11/11 and 12/12 smoke checks PASS**. Clean headless archive also passes all
  123 tests, lint/type/package checks. Actual image OCI title/source/revision and
  headless CLI branding are verified. No application inference logic changed.

| Local image | Docker OCI image ID |
| --- | --- |
| Headless | `sha256:37efc97812d5d4ce1b029ce81102181359e65ab1866d4e547773e66edcc66967` |
| UI | `sha256:5a86fa0335e12c832ca759218ecd76aa5f4bdfcd573ccca1c47a57a2c3a32934` |

These identities refer to f6ae796, not a later documentation/pushed commit. New
remote builds have their own provenance. Local smoke does not constitute a fresh
Trivy approval. Existing OS findings/image-security **FAIL** remain preserved;
remote CI must run all original scans and retain their actual failed results.

## Repository identity and immutable release

Origin changed from the historical repository URL to
`https://github.com/hzjanuary/ai-gateway-multi-node.git`; local directory unchanged.
GitHub About already exactly matched the requested description, so was not changed.
Topics now exactly match all 15 requested topics, including `ai-inference`.

The original spec, release notes and all historical JSON evidence are byte-identical
to base. Published release ID 427468446, its body/title/date/prerelease state, and
tag `v0.1.0` at `0f2afa3fd08ab9d7d6aa0de35c36b869d7e1c163` remain unchanged.
Historical original URLs/hashes/provenance remain as classified in
[the reference inventory](repository-rebranding.md). No CODEX-GOAL.md recreation,
credential/config migration, gate suppression, merge, new tag/release, deployment,
image publication or external provider generation is performed.

SPEC-001 historical acceptance stays **23 PASS / 0 FAIL / 1 BLOCKED**; GW-20 is
still BLOCKED, and image approval still FAILS. This maintenance verification does
not fabricate live inference or a new release/security approval. Full raw local
checks remain in ignored `.local/verification/rebrand/`. Final pushed-SHA workflow
URLs/outcomes and PR diff review are recorded in the PR after genuine CI completes.
