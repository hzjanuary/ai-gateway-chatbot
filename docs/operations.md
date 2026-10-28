# Operator guide and prototype migration

Do not reuse the old `.env`/providers.json implicitly. Keep them private and retain
operator logs. The new service reads a private settings.json only, plus explicit
GATEWAY_INFERENCE_TOKEN / GATEWAY_ADMIN_TOKEN environment overrides if provided.
Invalid overrides fail startup. Do not pass secrets on command arguments or paste
them into support issues. Env overrides may be visible to the host owner and do
not generate client token files; private file config is preferred.

Initialize in a new 0700 directory; copy only the necessary provider registration
into it using a private editor. Keep raw .token files for CLI users; distribute
inference separately from admin. For a server-only copy, retain settings.json with
its hashes/provider credentials and omit client .token files. Back it up securely.
Rotation is an explicit private edit of the relevant hash plus client token file,
then restart; no automatic rotation endpoint. Never delete operator files as part
of upgrading. Init does not add an admin token to an already initialized directory.
To enable admin later, generate a strong token privately, write its hash and a
0600 admin.token file under operator control, then restart.

For an admin UI Compose directory, export only the existing admin hash, with no
provider credentials or raw tokens (run as the operator owning both directories):

```sh
uv run python - <<'PY'
import json, os
from pathlib import Path
from gateway.config import load_settings
cfg = load_settings(Path('.local/private'))
assert cfg.admin_hash, 'Admin is disabled'
d = Path('.local/admin-ui')
d.mkdir(mode=0o700, parents=True, exist_ok=True)
fd = os.open(d / 'settings.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as f:
    json.dump({'admin_hash': cfg.admin_hash}, f)
PY
```

Compose defaults to container UID/GID 10001. For native initialized config export
GATEWAY_UID/GATEWAY_GID as your non-root numeric IDs. File ownership checks remain
mandatory; do not chmod secrets world-readable to fix permissions. Rootless Docker
user namespace mappings require adjusting ownership with your host administrator.
The private mount is read-only; runtime never modifies operator configuration.

CLI commands: `config init [--admin]`, `doctor`, `provider list`, `provider
 test-metadata`, `serve`, `ui chat|admin`, `request`, `metrics`, `reset --confirm`.
`request` can add `--stream`, `--provider`, `--max-tokens`, `--max-attempts`,
`--allow-fallback`, `--web-enrichment`, `--prompt-file`, `--token-file`, `--url`.
Do not point --url or BACKEND_URL at an untrusted server: it receives the role token.
Use HTTPS for remote URLs. Metadata commands are offline and cannot prove upstream
credentials, billing or model compatibility. Only a separately authorized live
request can verify those. Service `/ready` is not an inference probe.

Before restart, drain active requests at the proxy; graceful Uvicorn shutdown closes
HTTP clients. Ephemeral counters, session quotas and cooldowns reset on process
restart. Restart is not a method to evade quotas: observe the provider's account
limits independently and persist operational budgets outside this process if needed.
No health request sends traffic upstream. Disable a node by setting authorized false
in the private registry and restarting; do not reset repeatedly to bypass 429.

Troubleshooting:

- 503 authentication_not_configured: initialize explicitly; check private file
  owner/mode and chosen directory. Admin may intentionally be disabled.
- 401/403 API: use the correct role token; X-Access-Token is no longer supported.
- 502 upstream_rejected/schema: inspect scoped credentials/model/plan privately;
  sanitized gateway diagnostics do not expose upstream bodies. No auth fallback.
- 503 providers_exhausted/rate_limit: wait for allowed cooldown, inspect session
  budget and provider account restrictions. Reset circuits cannot refund budget.
- 504: total or per-attempt deadline; do not interpret partial output as a completion.
- SSE has no end: request failed/disconnected. Do not concatenate a new request
  with old partial content.
- Docker Ollama connection: register a literal, firewall-protected host/private IP;
  container loopback does not reach host Ollama.
- Old research_mode: use web_enrichment with global opt-in; query will leave host.
- Admin UI disabled: provide only a valid admin hash to UI and type the corresponding
  token. No insecure password fallback exists.

Provider API contracts verified against official documentation:
[Cloudflare REST](https://developers.cloudflare.com/workers-ai/get-started/rest-api/),
[Workers AI streaming](https://developers.cloudflare.com/workers-ai/configuration/streaming/),
[Ollama generate](https://docs.ollama.com/api/generate).
Supported scope is text response + usage. Structured/tool/multimodal output is not
accepted or silently stringified; add a separate adapter contract before supporting it.
