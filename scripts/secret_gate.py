"""Immutable Gitleaks history scan; retain raw exit/findings and review only exact spans.

No scanner rules, files or commits are skipped. Any unreviewed finding fails.
Review manifest covers two historical documentation placeholders and one retired
prototype default that cannot pass the current gateway token policy.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

GITLEAKS = (
    "zricethezav/gitleaks@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f"
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(".local/verification"))
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    report = out / "gitleaks-history.json"
    command = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--env",
        "GIT_CONFIG_COUNT=1",
        "--env",
        "GIT_CONFIG_KEY_0=safe.directory",
        "--env",
        "GIT_CONFIG_VALUE_0=/repo",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--mount",
        f'type=bind,source={Path.cwd() / ".git"},target=/repo/.git,readonly',
        "--mount",
        f"type=bind,source={out},target=/reports",
        GITLEAKS,
        "git",
        "/repo",
        "--log-opts=--all",
        "--redact",
        "--no-banner",
        "--report-format",
        "json",
        "--report-path",
        "/reports/gitleaks-history.json",
    ]
    result = subprocess.run(command, capture_output=True, check=False)
    (out / "gitleaks-history.stdout.txt").write_bytes(result.stdout)
    (out / "gitleaks-history.stderr.txt").write_bytes(result.stderr)
    reviews = {
        r["fingerprint"]: r for r in json.loads(Path("scripts/history_findings.json").read_text())
    }
    unknown = []
    findings = json.loads(report.read_text()) if report.exists() else []
    for finding in findings:
        review = reviews.get(finding["Fingerprint"])
        if review:
            source = subprocess.check_output(
                ["git", "show", review["commit"] + ":" + review["file"]], text=True
            )
            span = "\n".join(source.splitlines()[review["start_line"] - 1 : review["end_line"]])
            if hashlib.sha256(span.encode()).hexdigest() == review["source_span_sha256"]:
                continue
        unknown.append(
            {
                "fingerprint": finding["Fingerprint"],
                "rule": finding["RuleID"],
                "file": finding["File"],
            }
        )
    expected_commits = int(subprocess.check_output(["git", "rev-list", "--all", "--count"]))
    matched = re.search(rb"(\d+) commits scanned", result.stderr)
    scanned = int(matched.group(1)) if matched else 0
    passed = (
        result.returncode in (0, 1)
        and report.exists()
        and not unknown
        and scanned == expected_commits
        and scanned > 0
        and b"fatal:" not in result.stderr
    )
    summary = {
        "scanner": GITLEAKS,
        "raw_exit_code": result.returncode,
        "expected_commits": expected_commits,
        "scanned_commits": scanned,
        "raw_findings": len(findings),
        "reviewed_findings": len(findings) - len(unknown),
        "unreviewed_findings": unknown,
        "reviewed_gate_passed": passed,
        "rules_suppressed": False,
    }
    (out / "gitleaks-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    raise SystemExit(not passed)


if __name__ == "__main__":
    main()
