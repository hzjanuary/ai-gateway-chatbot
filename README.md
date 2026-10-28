# OSS Inference Gateway

A self-hosted, headless-first FastAPI gateway for explicitly registered Cloudflare
Workers AI and Ollama text-generation endpoints. This is a single-process source
preview, with bounded routing and truthful JSON/SSE errors. No provider, model,
credential, paid call, web search or dashboard is enabled by installation.

**Release decisions and measured limitations:** [verification](docs/release/verification.md).
Source readiness and image security approval are independent. No availability SLA.

## Local installation

Python 3.12 or 3.13 recommended; the release image targets Linux amd64/Python 3.13.
Dependencies are version locked with hashes; `uv.lock` is authoritative.

```sh
git clone https://github.com/hzjanuary/ai-gateway-chatbot.git
cd ai-gateway-chatbot
uv sync --locked --no-dev
uv run --no-dev gateway config init --admin
uv run --no-dev gateway doctor
uv run --no-dev gateway provider list
uv run --no-dev gateway provider test-metadata
uv run --no-dev gateway serve
```

`config init` explicitly generates separate inference/admin tokens into private
`inference.token` and `admin.token` files (0600) and hashes into `settings.json`.
The directory is 0700; nothing prints token values or prefixes. Repeating init
preserves every existing file. Missing config permits liveness but denies inference
and administration. `--admin` applies on first initialization only. Interrupted
initialization fails safely; inspect existing files privately rather than deleting
or automatically replacing them.

Default directory: `~/.config/inference-gateway`. Override via
`gateway --config-dir /private/path ...` or `GATEWAY_CONFIG_DIR`. There is no automatic
`.env` loading. Existing prototype secrets/logs are never migrated or removed.
See [migration and operations](docs/operations.md).

`/health` means the process is alive; `/ready` reports configuration/circuit
readiness only. Neither calls a provider or proves credentials/model access.

## Register a provider explicitly

Privately edit the initialized `settings.json`, preserving the two hashes.
The registry is static per process; restart after edits. `authorized: false` is the
default. No public API accepts endpoints, upstream headers, accounts or models.

Ollama example (merge the `providers` array from
[examples/ollama-settings.json](examples/ollama-settings.json), choose an already
installed model and set `authorized: true` only when ready):

```json
{"id":"local-ollama","type":"ollama","model":"llama3.1",
 "endpoint":"http://127.0.0.1:11434","allow_private":true,
 "authorized":true,"billing":"local","policy_group":"on-premise",
 "call_limit":20,"token_limit":10240,"max_concurrent":1}
```

Ollama requires an IP literal and explicit private-network approval. Public IPs
require HTTPS. Link-local, metadata, unspecified and multicast addresses are denied;
DNS names, redirects and ambient proxy variables are disabled. In Docker,
`127.0.0.1` is the container: register the explicitly trusted host/private IP and
firewall Ollama so other hosts cannot reach it. No automatic model pull or GPU tuning.

Cloudflare provider fields: `id`, `type: "cloudflare"`, a real `@cf/...` text model,
32-hex `account_id`, private `api_token`, `authorized: true`, `billing: "approved"`,
and an operator-chosen `policy_group`. Endpoint is fixed to
`https://api.cloudflare.com`; use a scoped Workers AI token and verify the plan,
model license, billing and privacy before authorization. Doctor validates syntax
only. Duplicate Cloudflare accounts/upstream Ollama endpoints are rejected.

## Request and streaming

The CLI reads prompts from stdin or a file and tokens from private files, keeping
credentials out of shell history/process arguments:

```sh
printf '%s' 'Explain inference gateways' | uv run --no-dev gateway request \
  --provider local-ollama --max-tokens 128
printf '%s' 'Explain inference gateways' | uv run --no-dev gateway request \
  --provider local-ollama --max-tokens 128 --stream
uv run --no-dev gateway metrics
uv run --no-dev gateway reset --confirm
```

Only `request` generates content. Doctor, list and test-metadata perform **zero
network calls**. Metrics/reset call the local gateway with the admin token.
`reset` clears circuits only; spent call/token reservations remain spent.

`POST /v1/inference` (or deprecated `/ask`) requires an inference Bearer token.
JSON contains prompt, optional system_prompt/provider, max_tokens, temperature,
stream, allow_fallback, max_attempts and web_enrichment. Unknown fields are rejected.
Nonstream reports actual provider ID/type, model, attempts, nullable measured usage
and request ID. The API is not an OpenAI-compatible endpoint.

SSE uses `start`, `delta`, `usage`, `end` events. A failure before first output is
non-2xx JSON; a failure after `start` emits `error` and closes without `end`.
Consumers **must require end** to accept completion. No provider switching after
start, no content stitching. See [full contract](docs/api/contract.md) and
[OpenAPI schema](docs/api/openapi.json).

Fallback requires `allow_fallback: true` **and** `max_attempts > 1`, stays within
the same explicit billing/privacy policy group and can occur only before output.
401/403, billing, policy, bad model/schema and 429 never cause fallback. 429 enters
cooldown and stops the request. 5xx/network/attempt-timeout may use another distinct
node within a shared deadline and output reservation budget. This is availability
handling for legitimately authorized endpoints, never account rotation to evade
provider limits. An upstream failure can consume provider quota even with no output.

## Limits, privacy and optional features

Default limits: 64 KiB HTTP body, 32000 prompt characters, 4000 system characters,
4096 max output tokens, four active gateway requests, three maximum distinct
attempts, 4096 reserved output tokens per request, 20 seconds per attempt and
60 seconds total. Each node also has session call/token and concurrency caps.
No refund on failed/cancelled attempts. Unknown usage remains null; reservations
are conservative ceilings, not a tokenizer or a currency/billing guarantee.
Provider misbehavior is bounded by response/frame limits and terminated explicitly.

Prompts/completions are not stored or logged by default. Admin-only diagnostics
contain safe codes, generated request IDs and registered IDs; no raw provider
errors, credentials, headers or input-validation values. Counters/circuits/reserved
quotas are **ephemeral**, resetting on restart; run one worker/replica. Provider
account limits remain authoritative. This gateway cannot guarantee a free plan,
cost-free inference, durable quota or high availability.

Cloudflare receives complete request content and follows its own
[data usage policy](https://developers.cloudflare.com/workers-ai/platform/data-usage/)
and [usage limits](https://developers.cloudflare.com/workers-ai/platform/limits/).
Local Ollama keeps inference on the registered machine; an external Ollama IP
sends content there. Model licenses and runtime telemetry remain operator concerns.

Web enrichment is disabled globally and per request. Enable
`web_enrichment_enabled: true` and send `web_enrichment: true` to make at most one
external search request (three snippets, real URLs and retrieval times). The query
is disclosed to DuckDuckGo. Result pages are never fetched. Search data is untrusted
user context, never privileged system instructions or a guarantee of correctness.
This is not persistent document RAG. Offline tests substitute a local HTTP search
response and do not perform internet searches.

Optional Streamlit UI:

```sh
uv sync --locked --extra ui
uv run gateway ui chat
uv run gateway ui admin
```

Both bind loopback. Chat asks for the inference token; admin requires a configured
hash plus the actual admin token and revalidates against the API on every rerun.
No token is prefilled from server configuration. Do not share browser sessions or
expose Streamlit directly to the internet. Disable UI telemetry (CLI does this).

## Docker / Compose

```sh
uv run gateway --config-dir .local/private config init --admin
# Match the private file owner; do not run the services as root.
export GATEWAY_UID="$(id -u)" GATEWAY_GID="$(id -g)"
export SOURCE_REVISION="$(git rev-parse HEAD)"
docker compose build backend
docker compose up -d backend
```

Default exposure is `127.0.0.1:8000`; container listens on its internal interface
for Compose networking. No source code mount, no provider by default. Private
config is a read-only bind mount, runtime filesystem is read-only, capabilities are
dropped, privileges cannot increase, and resources are capped. Missing bind source
aborts rather than silently creating insecure files. Native `gateway serve` and
standalone image default to loopback. Production image is non-root UID 10001.

Optional `--profile ui` starts chat. For `--profile admin`, create a separate 0700
`.local/admin-ui` directory and 0600 settings.json containing **only** the same
admin_hash (no raw tokens/provider credentials). Then start that profile. See
[operations](docs/operations.md) for the safe export command. UI images use a
separate dependency set and need their own scan/approval.

For any remote exposure, terminate TLS at a trusted proxy, cap request/body/idle
limits, preserve streaming with proxy buffering disabled, firewall direct ports
and add network egress policy. Proxy headers and wildcard CORS are disabled.
See [security model](docs/security-model.md).

## Development and release verification

```sh
uv sync --locked --extra ui
mkdir -p .local/verification
./scripts/quality.sh
python scripts/release_smoke.py --image inference-gateway:local
uv run python scripts/security_gates.py --image inference-gateway:local
```

Tests exercise actual HTTP transports with loopback servers; no real provider
calls. Source/history patterns, hash exports, pytest/Ruff/Black/MyPy, clean source
archive, image/CLI restart, actual image licenses/SBOM and Python/OS vulnerability
reports are separate gates. High/critical image findings and any Python advisory
fail; scanner errors also fail. Reports stay raw under `.local/verification`.
No gate suppressions or automatic publication. Follow [release checklist](docs/release/checklist.md).

MIT licensed; see [LICENSE](LICENSE), [NOTICE](NOTICE), [CONTRIBUTING](CONTRIBUTING.md)
and [private security disclosure](SECURITY.md).
