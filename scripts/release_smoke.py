"""Clean committed archive + actual-image offline CLI/health/auth/restart evidence.

Creates and removes only uniquely named test containers/networks and temporary
synthetic configuration. Never loads operator credentials or publishes host ports.
"""

import argparse
import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
import time
import uuid
from pathlib import Path

BASE = "python:3.13-slim-trixie@sha256:aaf08c5490d52cd92bc27142a5215b1e47355a5eaf9adfad2a0fbc022d0b5490"


def run(command, *, stdin=None, cwd=None):
    return subprocess.run(command, input=stdin, cwd=cwd, capture_output=True, check=True).stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--quality", action="store_true")
    parser.add_argument("--ui", action="store_true")
    parser.add_argument("--output", type=Path, default=Path(".local/verification"))
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    sha = run(["git", "rev-parse", "HEAD"]).decode().strip()
    archive = out / f"source-{sha}.tar"
    run(["git", "archive", "--format=tar", f"--output={archive}", sha])
    result = {
        "source_commit": sha,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "image": args.image,
        "checks": {},
        "live_provider": "BLOCKED: no separate authorization",
        "host_ports_published": False,
    }
    checks = result["checks"]
    uid, gid = os.getuid(), os.getgid()
    assert uid != 0, "Run verification as a non-root operator with Docker access"
    prefix = "spec001-" + uuid.uuid4().hex[:10]
    names = []
    network_created = False
    try:
        with tempfile.TemporaryDirectory(prefix="gateway-release-") as temp:
            scratch = Path(temp)
            source = scratch / "source"
            source.mkdir()
            with tarfile.open(archive) as tar:
                names_in_archive = tar.getnames()
                assert not any(
                    part
                    in (".git", ".local", ".venv", "__pycache__", "settings.json", "providers.json")
                    or part.endswith((".token", ".log"))
                    for name in names_in_archive
                    for part in Path(name).parts
                )
                tar.extractall(source, filter="data")
            checks["source_archive_no_operator_state"] = True
            if args.quality:
                synced = subprocess.run(
                    ["uv", "sync", "--locked", "--extra", "ui"],
                    cwd=source,
                    capture_output=True,
                    check=False,
                )
                (out / "clean-sync.stdout.txt").write_bytes(synced.stdout)
                (out / "clean-sync.stderr.txt").write_bytes(synced.stderr)
                assert synced.returncode == 0, "Clean dependency installation failed"
                # Source archive has no .git; source/history gates run at original Git checkout.
                (source / ".local/verification").mkdir(parents=True, exist_ok=True)
                for label, command in [
                    (
                        "ruff",
                        ["uv", "run", "--locked", "ruff", "check", "gateway", "tests", "scripts"],
                    ),
                    (
                        "black",
                        [
                            "uv",
                            "run",
                            "--locked",
                            "black",
                            "--check",
                            "--workers",
                            "1",
                            "gateway",
                            "tests",
                            "scripts",
                        ],
                    ),
                    ("mypy", ["uv", "run", "--locked", "mypy"]),
                    (
                        "pytest",
                        [
                            "uv",
                            "run",
                            "--locked",
                            "pytest",
                            "-q",
                            "--junitxml=.local/verification/pytest.xml",
                        ],
                    ),
                    ("package", ["uv", "build", "--locked"]),
                ]:
                    completed = subprocess.run(
                        command, cwd=source, capture_output=True, check=False
                    )
                    (out / f"clean-{label}.stdout.txt").write_bytes(completed.stdout)
                    (out / f"clean-{label}.stderr.txt").write_bytes(completed.stderr)
                    assert completed.returncode == 0, f"Clean {label} failed"
                (out / "clean-pytest.xml").write_bytes(
                    (source / ".local/verification/pytest.xml").read_bytes()
                )
                checks["clean_locked_install_quality_package"] = True
            if args.build:
                command = [
                    "docker",
                    "build",
                    "--build-arg",
                    f"SOURCE_REVISION={sha}",
                    "--build-arg",
                    f"INSTALL_UI={'true' if args.ui else 'false'}",
                    "-t",
                    args.image,
                    str(source),
                ]
                completed = subprocess.run(command, capture_output=True, check=False)
                (out / "build.stdout.txt").write_bytes(completed.stdout)
                (out / "build.stderr.txt").write_bytes(completed.stderr)
                assert completed.returncode == 0, "Clean archive Docker build failed"
                checks["clean_archive_image_build"] = True
            image = json.loads(run(["docker", "image", "inspect", args.image]))[0]
            assert image["Config"]["User"] == "10001:10001"
            assert image["Config"]["Labels"]["org.opencontainers.image.revision"] == sha
            result["image_config_digest"] = image["Id"]
            result["repo_digests"] = image["RepoDigests"]
            result["base_manifest"] = BASE
            # No registry publish, hence local images need not have a registry RepoDigest.
            run(["docker", "network", "create", "--internal", prefix])
            network_created = True
            mock = prefix + "-mock"
            names.append(mock)
            run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    mock,
                    "--network",
                    prefix,
                    "--mount",
                    f"type=bind,source={source / 'tests/runtime_mock.py'},target=/mock.py,readonly",
                    "--entrypoint",
                    "python",
                    BASE,
                    "/mock.py",
                ]
            )
            mock_info = json.loads(run(["docker", "inspect", mock]))[0]
            address = mock_info["NetworkSettings"]["Networks"][prefix]["IPAddress"]
            private = scratch / "private"
            private.mkdir(mode=0o700)
            bind = ["--mount", f"type=bind,source={private},target=/state"]
            initial = run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "--user",
                    f"{uid}:{gid}",
                    *bind,
                    args.image,
                    "--config-dir",
                    "/state",
                    "config",
                    "init",
                    "--admin",
                ]
            )
            assert json.loads(initial)["created"]
            settings_path = private / "settings.json"
            cfg = json.loads(settings_path.read_text())
            cfg["providers"] = [
                {
                    "id": "offline-ollama",
                    "type": "ollama",
                    "model": "test-model",
                    "endpoint": f"http://{address}:11434",
                    "allow_private": True,
                    "billing": "local",
                    "authorized": True,
                    "policy_group": "test",
                    "call_limit": 10,
                    "token_limit": 1280,
                }
            ]
            settings_path.write_text(json.dumps(cfg))
            checks["image_cli_private_init"] = all(
                (p.stat().st_mode & 0o777) == 0o600 for p in private.iterdir()
            )
            # Actual image startup without config has alive but not ready and no traffic.
            empty = prefix + "-empty"
            names.append(empty)
            run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    empty,
                    "--network",
                    "none",
                    "--read-only",
                    "--cap-drop",
                    "ALL",
                    "--security-opt",
                    "no-new-privileges:true",
                    "--tmpfs",
                    "/tmp",
                    args.image,
                ]
            )

            def wait_health(container):
                for _ in range(60):
                    probe = subprocess.run(
                        [
                            "docker",
                            "exec",
                            container,
                            "python",
                            "-c",
                            "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').status)",
                        ],
                        capture_output=True,
                        check=False,
                    )
                    if probe.returncode == 0:
                        return
                    time.sleep(0.1)
                raise AssertionError("Image did not become alive")

            wait_health(empty)
            run(
                [
                    "docker",
                    "exec",
                    empty,
                    "python",
                    "-c",
                    "import urllib.request,urllib.error\ntry: urllib.request.urlopen('http://127.0.0.1:8000/ready'); raise AssertionError('false ready')\nexcept urllib.error.HTTPError as e: assert e.code==503",
                ]
            )
            checks["default_image_alive_not_ready_network_none"] = True
            backend = prefix + "-gateway"
            names.append(backend)
            run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    backend,
                    "--network",
                    prefix,
                    "--user",
                    f"{uid}:{gid}",
                    "--read-only",
                    "--cap-drop",
                    "ALL",
                    "--security-opt",
                    "no-new-privileges:true",
                    "--tmpfs",
                    "/tmp",
                    "--mount",
                    f"type=bind,source={private},target=/state,readonly",
                    "--env",
                    "GATEWAY_CONFIG_DIR=/state",
                    args.image,
                    "serve",
                    "--host",
                    "0.0.0.0",
                ]
            )
            wait_health(backend)
            for command in (["doctor"], ["provider", "list"], ["provider", "test-metadata"]):
                metadata = json.loads(run(["docker", "exec", backend, "gateway", *command]))
                assert metadata["network_calls"] == 0
            before = json.loads(run(["docker", "exec", backend, "gateway", "metrics"]))
            assert before["providers"][0]["calls"] == 0
            checks["image_cli_metadata_zero_generation"] = True
            completion = json.loads(
                run(
                    [
                        "docker",
                        "exec",
                        "-i",
                        backend,
                        "gateway",
                        "request",
                        "--provider",
                        "offline-ollama",
                        "--max-tokens",
                        "16",
                    ],
                    stdin=b"synthetic image test",
                )
            )
            assert (
                completion["provider"] == "offline-ollama"
                and completion["usage"]["output_tokens"] == 5
            )
            streamed = run(
                [
                    "docker",
                    "exec",
                    "-i",
                    backend,
                    "gateway",
                    "request",
                    "--provider",
                    "offline-ollama",
                    "--max-tokens",
                    "16",
                    "--stream",
                ],
                stdin=b"synthetic stream test",
            )
            assert b"event: end" in streamed and b"event: error" not in streamed
            checks["actual_image_offline_json_and_sse"] = True
            after = json.loads(run(["docker", "exec", backend, "gateway", "metrics"]))
            assert after["providers"][0]["calls"] == 2
            assert after["providers"][0]["reserved_tokens"] == 32
            run(["docker", "exec", backend, "gateway", "reset", "--confirm"])
            same = json.loads(run(["docker", "exec", backend, "gateway", "metrics"]))
            assert same["providers"][0]["calls"] == 2
            run(["docker", "restart", backend])
            wait_health(backend)
            restarted = json.loads(run(["docker", "exec", backend, "gateway", "metrics"]))
            assert restarted["providers"][0]["calls"] == 0
            checks["restart_ephemeral_accounting_truthful"] = True
            for container in (empty, backend):
                logs = run(["docker", "logs", container])
                assert b"synthetic" not in logs and b"offline image transport verified" not in logs
                for token_file in private.glob("*.token"):
                    assert token_file.read_text().strip().encode() not in logs
            checks["actual_image_logs_no_sensitive_content"] = True
            filesystem = run(
                [
                    "docker",
                    "exec",
                    backend,
                    "python",
                    "-c",
                    "from pathlib import Path; assert not Path('/app/tests').exists(); assert not Path('/app/.git').exists(); assert not Path('/app/.env').exists(); print('clean')",
                ]
            )
            assert b"clean" in filesystem
            checks["image_has_no_test_or_operator_artifacts"] = True
            env = {
                **os.environ,
                "GATEWAY_PRIVATE_DIR": str(private),
                "GATEWAY_ADMIN_UI_DIR": str(private),
            }
            compose = subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    str(source / "docker-compose.yml"),
                    "--profile",
                    "ui",
                    "--profile",
                    "admin",
                    "config",
                    "--format",
                    "json",
                ],
                env=env,
                capture_output=True,
                check=True,
            )
            composed = json.loads(compose.stdout)
            for service in composed["services"].values():
                assert all(port["host_ip"] == "127.0.0.1" for port in service["ports"])
            checks["compose_all_profiles_loopback"] = True
            if args.ui:
                disabled = subprocess.run(
                    ["docker", "run", "--rm", "--network", "none", args.image, "ui", "admin"],
                    capture_output=True,
                    check=False,
                )
                assert disabled.returncode != 0
                checks["image_admin_ui_missing_secret_aborts"] = True
            result["status"] = "PASS"
    except Exception as exc:
        result["status"] = "FAIL"
        result["error_type"] = type(exc).__name__
        raise
    finally:
        (out / "release-smoke.json").write_text(json.dumps(result, indent=2) + "\n")
        for container in reversed(names):
            subprocess.run(["docker", "rm", "-f", container], capture_output=True, check=False)
        if network_created:
            subprocess.run(["docker", "network", "rm", prefix], capture_output=True, check=False)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
