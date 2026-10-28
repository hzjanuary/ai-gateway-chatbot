# Security policy

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
