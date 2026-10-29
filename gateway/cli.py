"""Operator CLI: metadata/doctor are offline; only request can generate content."""

import argparse
import json
import logging
import sys
from pathlib import Path

import httpx

from gateway.config import ConfigError, config_dir, initialize, load_settings, private_read


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="gateway",
        description="AI Gateway Multi-Node — Route smarter. Fail over safely. Run anywhere.",
    )
    root.add_argument("--config-dir", type=Path)
    sub = root.add_subparsers(dest="command", required=True)
    config = sub.add_parser("config").add_subparsers(dest="config_command", required=True)
    init = config.add_parser("init")
    init.add_argument("--admin", action="store_true")
    sub.add_parser("doctor")
    provider = sub.add_parser("provider").add_subparsers(dest="provider_command", required=True)
    provider.add_parser("list")
    provider.add_parser("test-metadata")
    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    ui = sub.add_parser("ui")
    ui.add_argument("role", choices=["chat", "admin"])
    ui.add_argument("--host", default="127.0.0.1")
    ui.add_argument("--port", type=int)
    for command in ("request", "metrics", "reset"):
        action = sub.add_parser(command)
        action.add_argument("--url", default="http://127.0.0.1:8000")
        action.add_argument("--token-file", type=Path)
        if command == "request":
            action.add_argument("--prompt-file", type=Path, help="Otherwise read prompt from stdin")
            action.add_argument("--provider")
            action.add_argument("--max-tokens", type=int, default=512)
            action.add_argument("--stream", action="store_true")
            action.add_argument("--allow-fallback", action="store_true")
            action.add_argument("--allow-policy-fallback", action="store_true")
            action.add_argument("--max-attempts", type=int, default=1)
            action.add_argument("--web-enrichment", action="store_true")
        elif command == "reset":
            action.add_argument("--confirm", action="store_true", required=True)
    return root


def run(args: argparse.Namespace) -> int:
    directory = args.config_dir or config_dir()
    if args.command == "config":
        created = initialize(directory, args.admin)
        print(
            json.dumps(
                {"created": created, "secrets": "operator-only .token files; no token output"}
            )
        )
        return 0
    settings = load_settings(directory)
    if args.command in ("doctor", "provider"):
        result: dict[str, object] = {
            "network_calls": 0,
            "metadata_validation": "local_configuration_only",
            "inference_auth_configured": bool(settings.inference_hash),
            "admin_enabled": bool(settings.admin_hash),
            "providers": [
                {"id": p.id, "type": p.type, "model": p.model, "authorized": p.authorized}
                for p in settings.providers
            ],
            "inference_ready": bool(settings.inference_hash)
            and any(p.authorized for p in settings.providers),
        }
        print(json.dumps(result, indent=2))
        return 0 if settings.inference_hash else 1
    if args.command == "serve":
        import uvicorn

        from gateway.api import create_app

        uvicorn.run(
            create_app(settings),
            host=args.host,
            port=args.port,
            access_log=False,
            proxy_headers=False,
            workers=1,
        )
        return 0
    if args.command == "ui":
        if args.role == "admin" and not settings.admin_hash:
            raise ConfigError("Admin UI disabled: no private admin hash")
        try:
            from streamlit.web import cli as streamlit_cli
        except ImportError as exc:
            raise ConfigError("Install the locked ui extra first") from exc
        entry = Path(__file__).with_name("ui.py")
        import os

        os.environ["GATEWAY_UI_ROLE"] = args.role
        os.environ["GATEWAY_CONFIG_DIR"] = str(directory)
        sys.argv = [
            "streamlit",
            "run",
            str(entry),
            "--server.address",
            args.host,
            "--server.port",
            str(args.port or (8502 if args.role == "admin" else 8501)),
            "--server.headless",
            "true",
            "--global.developmentMode",
            "false",
            "--server.fileWatcherType",
            "none",
            "--browser.gatherUsageStats",
            "false",
        ]
        streamlit_cli.main()
        return 0
    role = "inference" if args.command == "request" else "admin"
    token = private_read(args.token_file or directory / f"{role}.token").strip()
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(trust_env=False, timeout=310, follow_redirects=False) as client:
        if args.command == "metrics":
            response = client.get(args.url + "/v1/monitoring/stats", headers=headers)
        elif args.command == "reset":
            response = client.post(
                args.url + "/v1/providers/reset", headers=headers, json={"confirm": True}
            )
        else:
            prompt = args.prompt_file.read_text() if args.prompt_file else sys.stdin.read(32001)
            payload = {
                "prompt": prompt,
                "provider": args.provider,
                "max_tokens": args.max_tokens,
                "stream": args.stream,
                "allow_fallback": args.allow_fallback,
                "allow_policy_fallback": args.allow_policy_fallback,
                "max_attempts": args.max_attempts,
                "web_enrichment": args.web_enrichment,
            }
            if args.stream:
                with client.stream(
                    "POST", args.url + "/v1/inference", headers=headers, json=payload
                ) as stream:
                    if stream.status_code != 200:
                        print(
                            json.dumps(
                                {"error": "gateway_request_failed", "status": stream.status_code}
                            )
                        )
                        return 1
                    ended = False
                    for line in stream.iter_lines():
                        print(line, flush=True)
                        if line == "event: error":
                            return 1
                        if line == "event: end":
                            ended = True
                    return 0 if ended else 1
            response = client.post(args.url + "/v1/inference", headers=headers, json=payload)
        if response.status_code != 200:
            print(json.dumps({"error": "gateway_request_failed", "status": response.status_code}))
            return 1
        print(json.dumps(response.json(), ensure_ascii=False))
        return 0


def main(argv: list[str] | None = None) -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    try:
        status = run(parser().parse_args(argv))
    except (ConfigError, OSError, httpx.HTTPError, ValueError, RuntimeError):
        # Never echo an exception: it may contain credential/config/provider text.
        print(
            "Gateway command failed; check private configuration and local connectivity.",
            file=sys.stderr,
        )
        status = 2
    raise SystemExit(status)


if __name__ == "__main__":
    main()
