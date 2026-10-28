"""Read historical code only; do not import prototype or expose secret values."""

import json
import subprocess

BASELINE = "d2d859a8b59a5a396c62478a315f533d27007934"


def source(path: str) -> str:
    return subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], text=True)


api = source("api_gateway.py")
admin = source("admin_app.py")
compose = source("docker-compose.yml")
checks = {
    "missing_token_random": 'os.getenv("ACCESS_TOKEN", secrets.token_urlsafe(32))' in api,
    "token_prefix_logged": "config.ACCESS_TOKEN[:8]" in api,
    "missing_admin_allows": "if not ADMIN_PASSWORD:\n        return True" in admin,
    "inflight_node_reset": "provider_manager.reset_all_nodes()\n            tried_nodes.clear()" in api,
    "auth_failure_fallback": "elif is_auth_error:" in api and "switching node" in api,
    "unknown_provider": 'provider_used = "unknown"' in api,
    "prompt_logging": "request.prompt[:50]" in api,
    "public_bind": '"8000:8000"' in compose,
    "source_mount": ".:/app" in compose,
}
print(json.dumps({"source": BASELINE, "static_defects": checks}, indent=2))
assert all(checks.values()), "Baseline has changed: review expected evidence"
