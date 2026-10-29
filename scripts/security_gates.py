"""Run non-suppressing Python/source/image scans and preserve raw reports.

Network here is package/advisory infrastructure only; never provider inference.
Exit nonzero on scanner errors, ANY Python advisory, HIGH/CRITICAL image issue,
image secrets, missing Python license evidence, or unknown/forbidden Python license.
OS license inventory is retained for operator redistribution review.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path

TRIVY = "aquasec/trivy@sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c"
DB_REPOSITORY = "ghcr.io/aquasecurity/trivy-db:2"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", type=Path, default=Path(".local/verification"))
    parser.add_argument(
        "--scanner-network",
        choices=("bridge", "host"),
        default="bridge",
        help="Per-container scanner network; host is an explicit Linux DNS workaround only",
    )
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    status: dict[str, object] = {"image": args.image, "scanner": TRIVY}
    status["db_repository"] = DB_REPOSITORY
    status["scanner_network"] = args.scanner_network

    def run(
        name: str, command: list[str], stdin: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        result = subprocess.run(command, input=stdin, capture_output=True, check=False)
        (out / f"{name}.json").write_bytes(result.stdout)
        (out / f"{name}.stderr.txt").write_bytes(result.stderr)
        status[name] = {"command": command, "exit_code": result.returncode}
        return result

    failures = []
    dev_export = run(
        "dev-lock-export",
        [
            "uv",
            "export",
            "--quiet",
            "--locked",
            "--all-extras",
            "--no-emit-project",
            "--format",
            "requirements-txt",
            "--output-file",
            str(out / "requirements-dev.txt"),
        ],
    )
    if dev_export.returncode:
        failures.append("dev-lock-export")
    for label, requirements in (
        ("python-headless", "requirements.txt"),
        ("python-ui", "requirements-ui.txt"),
        ("python-development", str(out / "requirements-dev.txt")),
    ):
        result = run(
            label,
            [
                sys.executable,
                "-m",
                "pip_audit",
                "--require-hashes",
                "--no-deps",
                "--disable-pip",
                "--progress-spinner",
                "off",
                "--format",
                "json",
                "-r",
                requirements,
            ],
        )
        if result.returncode:
            failures.append(label)
    for label, extra in (("source", []), ("history", ["--history"])):
        if run(label, [sys.executable, "scripts/source_gate.py", *extra]).returncode:
            failures.append(label)
    if run("gitleaks", [sys.executable, "scripts/secret_gate.py", "--output", str(out)]).returncode:
        failures.append("gitleaks-unreviewed")
    archive = out / "image.tar"
    saved = subprocess.run(
        ["docker", "image", "save", args.image, "--output", str(archive)],
        capture_output=True,
        check=False,
    )
    (out / "image-save.stderr.txt").write_bytes(saved.stderr)
    if saved.returncode:
        failures.append("image-save")
    else:
        with tarfile.open(archive) as tar:
            docker_manifest = json.load(tar.extractfile("manifest.json"))[0]
            config_data = tar.extractfile(docker_manifest["Config"]).read()
            config_digest = "sha256:" + hashlib.sha256(config_data).hexdigest()
            descriptor = json.load(tar.extractfile("index.json"))["manifests"][0]
            index_digest = descriptor["digest"]
            while True:
                data = tar.extractfile("blobs/sha256/" + descriptor["digest"].split(":")[1]).read()
                assert "sha256:" + hashlib.sha256(data).hexdigest() == descriptor["digest"]
                manifest = json.loads(data)
                if "config" in manifest:
                    assert manifest["config"]["digest"] == config_digest
                    break
                descriptor = next(
                    d
                    for d in manifest["manifests"]
                    if d.get("platform", {}).get("architecture") == "amd64"
                    and d.get("platform", {}).get("os") == "linux"
                )
            provenance = {
                "oci_index_digest": index_digest,
                "platform_manifest_digest": descriptor["digest"],
                "image_config_digest": config_digest,
            }
            (out / "image-digests.json").write_text(json.dumps(provenance, indent=2) + "\n")
            status["digests"] = provenance
        cache = out / "trivy-cache"
        cache.mkdir(exist_ok=True)
        result = run(
            "image-scan",
            [
                "docker",
                "run",
                "--rm",
                "--network",
                args.scanner_network,
                "--mount",
                f"type=bind,source={archive},target=/image.tar,readonly",
                "--mount",
                f"type=bind,source={cache},target=/root/.cache/trivy",
                TRIVY,
                "image",
                "--db-repository",
                DB_REPOSITORY,
                "--input",
                "/image.tar",
                "--format",
                "json",
                "--scanners",
                "vuln,secret,license",
                "--license-full",
                "--exit-code",
                "0",
            ],
        )
        if result.returncode:
            failures.append("image-scanner")
        else:
            report = json.loads(result.stdout)
            vulnerabilities = [
                v for item in report.get("Results", []) for v in item.get("Vulnerabilities", [])
            ]
            secrets = [v for item in report.get("Results", []) for v in item.get("Secrets", [])]
            high = [v for v in vulnerabilities if v["Severity"] in ("HIGH", "CRITICAL")]
            status["image_findings"] = {
                "all_severities": len(vulnerabilities),
                "high_critical": len(high),
                "secrets": len(secrets),
            }
            if high or secrets:
                failures.append("image-security")
        metadata_path = cache / "db" / "metadata.json"
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text())
            (out / "trivy-db-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
            status["db_metadata"] = metadata
            database = cache / "db" / "trivy.db"
            if database.exists():
                with database.open("rb") as stream:
                    status["db_digest"] = hashlib.file_digest(stream, "sha256").hexdigest()
            if (
                metadata.get("Version") != 2
                or datetime.fromisoformat(metadata["NextUpdate"]) <= datetime.now(UTC)
                or not database.exists()
            ):
                failures.append("database-freshness")
        else:
            failures.append("database-metadata")
        sbom = run(
            "image-sbom",
            [
                "docker",
                "run",
                "--rm",
                "--network",
                args.scanner_network,
                "--mount",
                f"type=bind,source={archive},target=/image.tar,readonly",
                "--mount",
                f"type=bind,source={cache},target=/root/.cache/trivy",
                TRIVY,
                "image",
                "--db-repository",
                DB_REPOSITORY,
                "--input",
                "/image.tar",
                "--format",
                "cyclonedx",
            ],
        )
        if sbom.returncode:
            failures.append("image-sbom")
    result = run(
        "image-licenses",
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--entrypoint",
            "python",
            "-i",
            args.image,
            "-",
        ],
        Path("scripts/image_inventory.py").read_bytes(),
    )
    if result.returncode:
        failures.append("license-inventory")
    else:
        for package in json.loads(result.stdout):
            evidence = str(
                [package["license_expression"], package["license"], package["classifiers"]]
            )
            if not package["license_files"] or not any(
                word in evidence.lower()
                for word in (
                    "mit",
                    "apache",
                    "bsd",
                    "isc",
                    "mpl",
                    "mozilla",
                    "python software foundation",
                    "psf-2.0",
                )
            ):
                failures.append("license-review:" + package["name"])
    run("image-provenance", ["docker", "image", "inspect", args.image])
    run("scanner-version", ["docker", "run", "--rm", TRIVY, "--version"])
    run(
        "os-packages",
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--entrypoint",
            "dpkg-query",
            args.image,
            "-W",
            "-f=${Package}\t${Version}\t${source:Package}\t${source:Version}\n",
        ],
    )
    status["failures"] = failures
    status["image_security_gate_passed"] = not failures
    (out / "security-summary.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps({"failures": failures, "reports": str(args.output)}, indent=2))
    raise SystemExit(bool(failures))


if __name__ == "__main__":
    main()
