/goal

Implement SPEC-001 as a complete headless-first open-source refactor of THIS AI gateway repository.

Repository: hzjanuary/ai-gateway-chatbot
Spec: docs/specs/SPEC-001-open-source-inference-gateway.md
Observed GitHub baseline: d2d859a8b59a5a396c62478a315f533d27007934
Target branch: feat/spec-001-oss-inference-gateway

MISSION
Replace the prototype with a reliable, self-hosted API-first LLM inference gateway. Preserve and verify legitimate Cloudflare Workers AI / Ollama routing, provider selection, explicit fallback, stream and non-stream behavior, admin observability and optional chat/dashboard. Do not turn it into MAOS or bundle a fake provider.

EXECUTION
1. Re-read actual local HEAD, repository instructions, Docker, all provider code and Git history. Protect credentials and operator logs. Create feature branch and active plan, identify baseline tests/risks and document concrete request/stream/error contracts.
2. Implement secure config init with private secrets, no arbitrary generated unknown token and no logged prefixes. Separate inference access from admin mutations/metrics/log access. Admin UI must fail closed without a valid secret; optional UIs cannot bypass API auth. Bind loopback by default and remove production source bind mounts.
3. Implement typed provider adapters, validated operator-registered endpoints, accurate provider/model reporting, and strict response normalization. Classify 429/5xx/timeouts vs 401/403/billing/schema/policy. Never use paid or policy-changing fallback by default. Enforce attempt/timeout/concurrency/token limits; never reset exhausted nodes inside a request to exceed budget.
4. Fix stream correctness, including split/multiline SSE frames, disconnect/cancel, failure after first emitted chunk, provider switch before first output only, truthful HTTP/non-stream errors and token accounting. Never stitch two providers' generated content together silently.
5. Keep optional web research separate and disabled by default. Name it web enrichment, not persistent document RAG. Maintain honest source URLs and treat web text as untrusted.
6. Build real offline HTTP mock-server transport tests for Cloudflare and Ollama, simulated rate limits, malformed payloads, missing auth, exhausted budgets, concurrency, sensitive logging and an optional UI. Test clean restart/health, operator CLI, secure Compose, actual release image and source archive.
7. Introduce locked dependencies, CI, source/image/license/security gates, LICENSE/NOTICE, README/API schemas, examples, disclosure policy and reproducibility evidence. Run complete local gates; inspect OS and Python findings and preserve raw reports.
8. Create docs/release/verification.md with GW-01..GW-24 PASS/FAIL/BLOCKED/NOT_RUN, exact commands, test counts, source commit and image digest. A real provider live request remains BLOCKED until a separately authorized bounded smoke. Distinguish source publication readiness from Docker-image security approval. Commit locally in coherent steps and keep plan active for blockers.

RESTRICTIONS
- Do NOT ask for keys in chat, automatically call inference or paid endpoints, modify provider accounts, bypass limits/terms, enable billing or perform web search on behalf of users during tests.
- Do NOT deploy, push, merge, publish, tag, rewrite history, delete logs/credentials or weaken vulnerability gates without separate authorization.
- No false high-availability claims; failed provider requests must remain failures, not success placeholders. Use test doubles only in tests.
- Fix routine in-scope issues autonomously and keep the worktree clean. Stop for actual external permission or irreversible changes, not ordinary code design decisions.

FINAL REPORT IN VIETNAMESE
Include changed architecture, fixed auth/fallback/SSE behaviors, contract tests, real image/CLI validation, acceptance scores and BLOCKED live requirements, provider privacy/usage limits, security findings, precise SHA/image provenance and explicit next operator actions.
