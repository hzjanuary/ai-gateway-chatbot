from pathlib import Path

import yaml


def test_compose_exposure_and_hardening():
    config = yaml.safe_load(Path("docker-compose.yml").read_text())
    services = config["services"]
    assert "profiles" not in services["backend"]
    assert services["chat-ui"]["profiles"] == ["ui"]
    assert services["admin-ui"]["profiles"] == ["admin"]
    for service in services.values():
        assert all(port.startswith("127.0.0.1:") for port in service["ports"])
        assert service["read_only"] and service["cap_drop"] == ["ALL"]
        assert "no-new-privileges:true" in service["security_opt"]
        assert service["user"] == "${GATEWAY_UID:-10001}:${GATEWAY_GID:-10001}"
        for volume in service.get("volumes", []):
            assert volume["read_only"]
            assert volume["target"] == "/var/lib/gateway"
            assert volume["source"] != "."
    assert not services["chat-ui"].get("volumes")


def test_docker_context_is_allowlisted_and_runtime_minimal():
    dockerignore = Path(".dockerignore").read_text().splitlines()
    assert "*" in dockerignore
    assert not any(line in dockerignore for line in ("!tests/", "!.env", "!.git/", "!.local/"))
    dockerfile = Path("Dockerfile").read_text()
    assert "COPY . ." not in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert "--require-hashes" in dockerfile
    assert "@sha256:" in dockerfile


def test_no_placeholder_provider_or_secret_in_examples():
    import json

    assert json.loads(Path("providers.example.json").read_text())["providers"] == []
    assert (
        json.loads(Path("examples/ollama-settings.json").read_text())["providers"][0]["authorized"]
        is False
    )
    assert "TOKEN=" not in Path(".env.template").read_text()
