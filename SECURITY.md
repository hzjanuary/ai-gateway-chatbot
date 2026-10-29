# Security policy

## v0.1.0 source-preview limitations

This early preview is intended for development, experimentation and self-hosting.
The owner authorizes source-only publication despite the disclosed Debian OS
findings. This is **not Docker image-security approval**: tested images retain
**0 CRITICAL / 44 HIGH / 58 MEDIUM / 61 LOW / 1 UNKNOWN** findings and a **FAIL**
security gate. Raw scans, scanner/DB provenance and third-party license findings
are preserved in the [security findings](docs/release/security-findings.md) and
[verification report](docs/release/verification.md).

GW-20 genuine Cloudflare Workers AI/Ollama inference remains **BLOCKED**. Offline
HTTP loopback tests do not prove model execution, provider availability or cost.
Operators must review provider data policies, credentials, dependency updates,
network exposure and their container environment before deployment. No unrestricted
internet-facing production security approval or availability SLA is provided.
Only explicitly registered Cloudflare Workers AI/Ollama text endpoints are
implemented; no other provider, durable billing/quota system, automatic model
download, managed hosting or remote deployment is supplied.

The [owner publication decision](docs/release/source-preview-decision.md) is
separate from image security signoff. [Maintenance backlog](docs/release/maintenance-backlog.md)
retains unfinished live, OS and license review work. No scan exception, VEX,
suppression or fabricated live evidence is introduced by this release.

0.1 source preview is the only maintained line. It has no production/SLA claim.
Before deployment consult docs/release/verification.md for separate source, image
security and live-provider decisions; an unapproved image must not be published
as a security-approved production release.

Report vulnerabilities privately using the repository's GitHub **Security → Report
 a vulnerability** feature when private reporting is enabled. If unavailable,
request a private contact channel from the maintainer without including exploit,
credentials, prompts, logs or personal data in a public issue. No private reporting
endpoint has been verified by this offline implementation; do not assume an email
address or response SLA. Share affected commit/image digest, minimal synthetic
reproduction and impact through the confirmed private channel.

Do not include real keys in issues or test fixtures. If a key was disclosed, revoke
it through the provider's normal operator workflow and preserve evidence privately.
This repository does not auto-revoke credentials, delete logs or rewrite history.

Dependency/image vulnerability scans fail without suppressions. Preserve raw
scanner output and database/tool versions. A source preview can be assessed
independently of an image with known OS findings; disclose them and retain a failed
image-security gate until fixes are verified. Publishing requires separate owner
authorization and license/privacy review.
