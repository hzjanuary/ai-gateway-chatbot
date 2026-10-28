# SPEC-001 verification — active candidate

Status: verification in progress. No publication/deployment authorization. Exact
source SHA/image digests and final test counts will be filled from measured clean
archive/image evidence. No live provider request has been authorized or executed.

| ID | Status | Required evidence |
| --- | --- | --- |
| GW-01 | NOT_RUN | clean archive locked install/build |
| GW-02 | NOT_RUN | private explicit idempotent init tests |
| GW-03 | NOT_RUN | optional UI deny and valid-token tests |
| GW-04 | NOT_RUN | role matrix for every endpoint |
| GW-05 | NOT_RUN | public/admin information boundaries |
| GW-06 | NOT_RUN | actual Compose profiles / bind checks |
| GW-07 | NOT_RUN | Cloudflare and Ollama real HTTP transports |
| GW-08 | NOT_RUN | deterministic two-node routing |
| GW-09 | NOT_RUN | terminal error no-fallback transport counts |
| GW-10 | NOT_RUN | explicit availability fallback and budget caps |
| GW-11 | NOT_RUN | exhausted state not reset within request |
| GW-12 | NOT_RUN | SSE fragmentation/disconnect/post-output failure |
| GW-13 | NOT_RUN | truthful nonstream errors and provider identity |
| GW-14 | NOT_RUN | limits/deadline/concurrency/reservations |
| GW-15 | NOT_RUN | registry SSRF and caller URL/header rejection |
| GW-16 | NOT_RUN | opt-in bounded untrusted web enrichment |
| GW-17 | NOT_RUN | canary/log/UI/error redaction |
| GW-18 | NOT_RUN | actual restart and ephemeral state disclosure |
| GW-19 | NOT_RUN | actual image CLI and local Ollama-format HTTP fixture |
| GW-20 | BLOCKED | separate owner authorization for 1–2 bounded live calls |
| GW-21 | NOT_RUN | local complete gates; remote CI additionally BLOCKED (no push) |
| GW-22 | NOT_RUN | documentation/licenses/privacy/security review |
| GW-23 | NOT_RUN | clean archive actual image/CLI health/restart |
| GW-24 | NOT_RUN | independent source/image security decisions |

The active plan remains open for external blockers. Source preview is not Docker
security approval, live inference acceptance, production readiness or a release.
