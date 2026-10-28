# Security model

Trust boundary: one operator-owned process, one inference secret, a distinct optional
admin secret and a static private provider registry. No multi-tenant isolation or
SLA. Host administrators, the process owner, container daemon and configured
upstream operators are trusted. An inference caller is not an administrator.

Tokens are created only by explicit init. High-entropy bearer values are stored
0600 for operator clients, SHA-256 digests in server settings (appropriate for
random tokens), verified with constant-time comparison. Raw provider credentials
must remain readable to the process but are never serialized in observability.
Config reads use no-follow open plus actual file owner/type/mode checks. Protect
parent directories against replacement; use a local private directory, never a
shared/network writable mount. An interrupted init will not overwrite anything.
Admin disabled or misconfigured means denied. API authorization is enforced even
when a UI session exists. Tokens are role-specific; admin cannot infer.

Public routes expose only liveness, boolean configuration readiness, version and
static OpenAPI. Admin routes expose sanitized metadata/counters and a bounded
100-entry event buffer. There is no log file reader/deletion endpoint, arbitrary
upstream URL/header/model request field, public registry mutation or debug mode.
Pydantic validation details are replaced with fixed messages to avoid input echo.

Cloudflare uses fixed HTTPS origin and per-account paths. Ollama requires literal
IP addresses, rejects link-local/unspecified/multicast/reserved destinations and
requires explicit private trust-zone approval. Public Ollama uses TLS. No DNS
rebinding path exists for Ollama, redirects and ambient proxies are disabled.
Cloudflare DNS and CA trust remain OS/host responsibilities. Apply egress firewall
rules as defense in depth; private Ollama is an intentional operator-granted SSRF
exception. A compromised local operator can edit the registry: this is not a sandbox
against the host owner.

Requests reserve node calls and max output tokens synchronously before awaiting
transport, preventing concurrent oversubscription in one event loop. Failed and
cancelled attempts spend reservations because the remote provider may have run.
Actual usage is recorded only if explicitly reported by a valid provider response.
This does not bound monetary cost or tokenization exactly: limits in the provider
account remain authoritative. Restart resets all session counters/circuit state;
use one worker and no replicas. Reset admin operation never refunds quotas.

Transient errors open a monotonic cooldown. Once elapsed, one half-open request
can probe; success closes, failure reopens. Auth/model/schema/policy failures disable
the node until operator reset/restart; reset does not test credentials. 429 stops
without fallback; Retry-After is honored up to seven days (larger/unbounded values
use seven days; operators should disable the node if provider restrictions last
longer). There are no automatic background probes or account provisioning.

A shared request deadline includes enrichment and provider attempts. First event
is validated before sending 200. After downstream start, provider is fixed and an
error must close the stream without end. Disconnect cancels in-flight HTTP and
releases slots. Output frames/responses are bounded; no response body is logged.
System prompts and web enrichment are not a prompt-injection security boundary:
untrusted text may still influence generated content. There is no tool execution.

Default logs contain only lifecycle messages. The bounded admin event buffer has
safe codes/IDs, not prompts/completions. No raw debug logging mode is supplied.
Do not enable framework/HTTP wire debugging in a deployment containing private
traffic. CLI/UI show completion only to the requesting user. Protect terminal,
browser session, reverse proxy logs and metrics access accordingly.

Remote deployment requires TLS, authentication-preserving proxy configuration,
body/connection/idle time limits, disabled SSE buffering and restrictive firewall.
Uvicorn proxy-header trust is disabled by CLI. No CORS middleware grants browser
origins; same-origin clients or a deliberately configured trusted proxy are required.
A bearer-token service is not appropriate for an untrusted public multi-user SaaS.
