"""Review tracked source/history without printing potentially sensitive matching text."""

import argparse
import json
import re
import subprocess
from pathlib import Path, PurePosixPath

PATTERNS = {
    "provider_key": re.compile(
        rb"(?:sk-[A-Za-z0-9_-]{32,}|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[A-Z0-9]{16})"
    ),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "private_home": re.compile(rb"/(?:home|Users)/[A-Za-z][A-Za-z0-9_-]+/"),
}
FORBIDDEN = {
    "providers.json",
    "settings.json",
    "system.log",
    ".env",
    ".env.local",
    ".env.production",
}


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args])


def inspect(path: str, content: bytes) -> list[str]:
    findings = []
    parts = PurePosixPath(path).parts
    if (
        PurePosixPath(path).name in FORBIDDEN
        or any(p in (".local", ".venv", "__pycache__") for p in parts)
        or path.endswith((".token", ".log", ".key", ".pem"))
    ):
        findings.append("private_artifact_name")
    for label, pattern in PATTERNS.items():
        if pattern.search(content):
            findings.append(label)
    return findings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    findings = []
    checked = 0
    if args.history:
        entries = git("rev-list", "--objects", "--all").decode().splitlines()
        for entry in entries:
            fields = entry.split(" ", 1)
            if len(fields) != 2:
                continue
            oid, path = fields
            if git("cat-file", "-t", oid).strip() != b"blob":
                continue
            checked += 1
            labels = inspect(path, git("cat-file", "blob", oid))
            if labels:
                findings.append({"blob": oid, "path": path, "rules": labels})
    else:
        for path in git("ls-files", "-z").decode().split("\0"):
            if not path or not Path(path).is_file():
                continue
            checked += 1
            labels = inspect(path, Path(path).read_bytes())
            if labels:
                findings.append({"path": path, "rules": labels})
    print(
        json.dumps(
            {
                "scope": "all_git_blobs" if args.history else "tracked_worktree",
                "checked": checked,
                "findings": findings,
                "limitation": "Pattern scan is evidence, not proof that arbitrary secrets cannot exist.",
            },
            indent=2,
        )
    )
    raise SystemExit(bool(findings))


if __name__ == "__main__":
    main()
