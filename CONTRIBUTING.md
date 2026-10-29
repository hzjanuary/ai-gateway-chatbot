# Contributing to AI Gateway Multi-Node

Use the canonical repository: https://github.com/hzjanuary/ai-gateway-multi-node.
Clone it with `git clone https://github.com/hzjanuary/ai-gateway-multi-node.git`.
Open focused pull requests against main; report ordinary bugs through
[Issues](https://github.com/hzjanuary/ai-gateway-multi-node/issues), and follow
[SECURITY.md](SECURITY.md) for private security reports. See
[repository branding and compatibility](docs/repository-rebranding.md).

Use Python 3.12/3.13 and `uv sync --locked --extra ui`, then scripts/quality.sh.
All provider tests run real HTTP transports against loopback servers, with external
DNS blocked by the test fixture. Never use real provider credentials or inference
in CI. Test doubles belong only in tests; no fixture provider may enter runtime.

Update API contracts/OpenAPI when changing interfaces, and include negative tests
for permissions, terminal errors, framing and budgets. Keep prompts/completions out
of logs; never print raw configuration validation/provider error messages.

Update exact dependencies and uv.lock together, export both requirements files with
hashes and run scripts/security_gates.py on both headless/UI images. Do not weaken
security gates or add blanket advisory ignores. Preserve full scan evidence and
licenses. Source artifact and image approval remain independent.

No push/tag/publish is performed by local release scripts. A separately approved
live smoke must verify plan/privacy, use only one preselected provider, disable
fallback and web enrichment, cap max_tokens and calls, and record only sanitized
metadata. No content/key belongs in public evidence.
