# AI Gateway Multi-Node: repository identity and compatibility

Canonical repository: https://github.com/hzjanuary/ai-gateway-multi-node.

**Route smarter. Fail over safely. Run anywhere.**

The repository was renamed from `hzjanuary/ai-gateway-chatbot`. Use the canonical
URL for current clone/install, issues, contribution, security and package links.
The local checkout directory does not need to be renamed. GitHub's old URL may
redirect; that redirect is not the canonical installation instruction.

## Updated public surfaces

README, contribution/security documentation, Python distribution description and
project URLs, FastAPI title, CLI help, optional UI headings and OCI title/source/
description now identify **AI Gateway Multi-Node**. CI retains every quality and
security gate and includes the rebranding branch in the push trigger. There were
no old repository references in examples requiring changes; generic technical
terms such as inference gateway remain appropriate.

| Stable identifier | Reason retained |
| --- | --- |
| Python distribution `oss-inference-gateway`, version 0.1.0 | Avoid an unnecessary package/dependency migration; wheel installation remains compatible. |
| Python module `gateway` and command `gateway` | Preserve imports, entrypoint and all command options. Help description alone changes. |
| Config paths/env names, Compose project/service/image aliases | Preserve existing private state, service discovery and local image commands. |
| API paths, schemas, role/security definitions and operation IDs | No API migration. Only OpenAPI `info.title` changes with the new public name. |
| Removed `CODEX-GOAL.md` | Keep the owner's deletion; do not recreate a task file. Its dormant export exclusion remains protective. |

## Historical references preserved

| Reference | Classification and treatment |
| --- | --- |
| `docs/release/evidence/*.json` | Immutable earlier evidence: retain original URLs, SHAs, hashes, image identities, counts and provenance byte-for-byte. |
| `docs/release/verification.md` and `security-findings.md` old CI/PR URLs | Dated verification snapshots. Preserve original run URLs rather than inventing new provenance after a rename. |
| `docs/release/v0.1.0-notes.md` release title | Historical published release wording; not an active product-name recommendation. |
| `docs/specs/SPEC-001-open-source-inference-gateway.md` | Original specification with its old repository and easyResearchAssistant baseline; preserve the original document. |
| SPEC-001 plans and `feat/spec-001-oss-inference-gateway` | Historical planning/branch identities, not the current canonical repository name. |
| Published tag/release and private raw reports | Do not modify, move, recreate or rewrite. Current navigation may use the renamed repository's canonical URL. |

No badges claimed overall green CI before the rename, and no green security badge
is added. [v0.1.0](https://github.com/hzjanuary/ai-gateway-multi-node/releases/tag/v0.1.0)
remains the source-only pre-release at
`0f2afa3fd08ab9d7d6aa0de35c36b869d7e1c163`. Original SPEC-001 acceptance stays
**23 PASS / 0 FAIL / 1 BLOCKED**, with **GW-20 BLOCKED**. Docker security approval
stays **FAIL** for the disclosed OS findings. Rebranding neither proves live
inference nor approves images, availability, enterprise security or production use.
See [security findings](release/security-findings.md), [verification](release/verification.md)
and [maintenance backlog](release/maintenance-backlog.md).
