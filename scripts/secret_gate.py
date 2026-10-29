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
# Scan every reachable commit and each merge against every parent. Ordinary
# `git log -p` has no merge patch, including GitHub's synthetic PR merge.
LOG_OPTS = "--all --full-history --diff-merges=separate"


def scan_history(repo, out, reviews, *, log_opts=LOG_OPTS):
    repo, out = Path(repo).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    report = out / "gitleaks-history.json"
    # Never let a stale report stand in for a failed scan.
    report.unlink(missing_ok=True)
    expected = subprocess.check_output(
        ["git", "-C", str(repo), "rev-list", "--all"], text=True
    ).splitlines()
    graph = subprocess.check_output(
        ["git", "-C", str(repo), "rev-list", "--all", "--parents"], text=True
    ).splitlines()
    shallow = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "--is-shallow-repository"], text=True
    ).strip()
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
        f'type=bind,source={repo / ".git"},target=/repo/.git,readonly',
        "--mount",
        f"type=bind,source={out},target=/reports",
        GITLEAKS,
        "git",
        "/repo",
        f"--log-opts={log_opts}",
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
    unknown = []
    findings = json.loads(report.read_text()) if report.exists() else []
    for finding in findings:
        review = reviews.get(finding["Fingerprint"])
        if review:
            source = subprocess.check_output(
                ["git", "-C", str(repo), "show", review["commit"] + ":" + review["file"]],
                text=True,
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
    expected_commits = len(expected)
    matched = re.search(rb"(\d+) commits scanned", result.stderr)
    scanned = int(matched.group(1)) if matched else 0
    passed = (
        result.returncode in (0, 1)
        and report.exists()
        and not unknown
        and scanned == expected_commits
        and scanned > 0
        and shallow == "false"
        and b"fatal:" not in result.stderr
    )
    summary = {
        "scanner": GITLEAKS,
        "raw_exit_code": result.returncode,
        "log_opts": log_opts,
        "expected_commit_ids": expected,
        "commit_parent_graph": graph,
        "shallow_repository": shallow != "false",
        "expected_commits": expected_commits,
        "scanned_commits": scanned,
        "raw_findings": len(findings),
        "reviewed_findings": len(findings) - len(unknown),
        "unreviewed_findings": unknown,
        "reviewed_gate_passed": passed,
        "rules_suppressed": False,
    }
    (out / "gitleaks-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(".local/verification"))
    args = parser.parse_args()
    reviews = {
        r["fingerprint"]: r for r in json.loads(Path("scripts/history_findings.json").read_text())
    }
    summary = scan_history(Path.cwd(), args.output, reviews)
    print(json.dumps(summary, indent=2))
    raise SystemExit(not summary["reviewed_gate_passed"])


if __name__ == "__main__":
    main()
