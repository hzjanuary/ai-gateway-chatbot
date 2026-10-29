# v0.1.0 preview maintenance backlog

These items remain unfinished after the owner's source-only publication decision.
This is a backlog, not authorization to start more work during the release.

| Item | Status | Required evidence before closure |
| --- | --- | --- |
| GW-20 genuine provider inference | BLOCKED | Separately authorized bounded smoke, eligible provider/plan/privacy conditions, enforced token cap, real HTTP/model/output/usage provenance. Offline fixtures are insufficient. No inference in this release workflow. |
| Debian image vulnerabilities | FAIL | Supported remediation or a separately approved security disposition, then rebuilt actual images and complete current scans. Existing 44 HIGH and all other severities remain disclosed. |
| Image redistribution and licenses | OPEN | Review preserved OS/bundled license obligations, including the known PyArrow license-text WTFPL classification; retain raw matches and separate distribution text inventory. No blanket image approval. |
| Provider cost and operations | OPERATOR RESPONSIBILITY | Review provider plan, model licenses, data policies, credentials, network exposure, dependency updates and container environment. No free-plan/currency guarantee, durable billing or SLA. |

Only Cloudflare Workers AI and Ollama text-generation adapters are implemented.
No additional provider, managed deployment, automatic model provisioning,
multi-instance durable quota, production availability or security guarantee is
implied by v0.1.0. The optional enrichment feature remains disabled by default.

See [security findings](security-findings.md), [verification](verification.md) and
[source-only owner decision](source-preview-decision.md). Keep GW-20 BLOCKED and
image-security FAIL until the stated evidence actually changes.
