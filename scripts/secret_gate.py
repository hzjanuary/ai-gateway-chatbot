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
import shlex
import subprocess
from pathlib import Path

GITLEAKS = (
    "zricethezav/gitleaks@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f"
)
# Scan every reachable commit and each merge against every parent. Ordinary
# `git log -p` has no merge patch, including GitHub's synthetic PR merge.
LOG_OPTS = "--all --full-history --diff-merges=separate"


def scan_patch(repo, out, label, log_opts):
    """Retain one unmodified pinned-scanner result, including a zero-fragment result."""
    report = out / f"{label}.json"
    # Never let a stale report stand in for a failed scan.
    report.unlink(missing_ok=True)
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
        f"/reports/{label}.json",
    ]
    result = subprocess.run(command, capture_output=True, check=False)
    (out / f"{label}.stdout.txt").write_bytes(result.stdout)
    (out / f"{label}.stderr.txt").write_bytes(result.stderr)
    findings = json.loads(report.read_text()) if report.exists() else []
    matched = re.search(rb"(\d+) commits scanned", result.stderr)
    return {
        "log_opts": log_opts,
        "report": report.name,
        "raw_exit_code": result.returncode,
        "scanned_commits": int(matched.group(1)) if matched else 0,
        "valid": (
            report.exists()
            and result.returncode == int(bool(findings))
            and b"fatal:" not in result.stderr.lower()
        ),
    }, findings


def scan_history(repo, out, reviews, *, log_opts=LOG_OPTS):
    repo, out = Path(repo).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

    expected = git("rev-list", "--all").splitlines()
    graph = git("rev-list", "--all", "--parents").splitlines()
    shallow = git("rev-parse", "--is-shallow-repository")
    options = shlex.split(log_opts)
    # Audit the actual requested revision scope separately from scanner statistics.
    selected = set(git("log", *options, "--format=%H", "--no-patch").splitlines())
    primary, findings = scan_patch(repo, out, "gitleaks-history", log_opts)
    primary_findings = len(findings)
    empty_tree = (
        subprocess.check_output(
            ["git", "-C", str(repo), "hash-object", "-t", "tree", "--stdin"], input=b""
        )
        .decode()
        .strip()
    )
    parents = {row.split()[0]: row.split()[1:] for row in graph}
    # Selection is audited above; singleton receipts cannot accidentally rescan --all.
    diff_options = [
        option
        for option in options
        if option == "--full-history" or option.startswith("--diff-merges=")
    ]
    receipts = []
    covered, forward, patchless = set(), set(), set()
    scans_valid = primary["valid"]
    for oid in expected:
        tree = git("rev-parse", oid + "^{tree}")
        parent_trees = {parent: git("rev-parse", parent + "^{tree}") for parent in parents[oid]}
        receipt = {"commit": oid, "tree": tree, "parent_trees": parent_trees, "scans": []}
        receipts.append(receipt)
        if oid not in selected:
            receipt["status"] = "OMITTED_FROM_REQUESTED_SCOPE"
            continue
        if (
            all(tree == value for value in parent_trees.values())
            if parent_trees
            else tree == empty_tree
        ):
            # A merge equal to only ONE parent is not patchless.
            patchless.add(oid)
            receipt["status"] = "PATCHLESS_TREE_EQUAL_TO_ALL_PARENTS_OR_EMPTY_ROOT"
            continue
        opts = " ".join([*diff_options, oid + "^!"])
        proof, found = scan_patch(repo, out, f"coverage-{oid}-forward", opts)
        findings.extend(found)
        receipt["scans"].append(proof)
        scans_valid = scans_valid and proof["valid"]
        if proof["valid"] and proof["scanned_commits"] == 1:
            covered.add(oid)
            forward.add(oid)
            receipt["status"] = "SCANNED_FORWARD"
        elif proof["valid"] and proof["scanned_commits"] == 0:
            # A deletion-only patch has content changes but no added fragments.
            # Reverse it in Git so the exact deleted bytes are scanned as additions.
            proof, found = scan_patch(repo, out, f"coverage-{oid}-reverse", opts + " -R")
            findings.extend(found)
            receipt["scans"].append(proof)
            scans_valid = scans_valid and proof["valid"]
            if proof["valid"] and proof["scanned_commits"] == 1:
                covered.add(oid)
                receipt["status"] = "SCANNED_REVERSE"
            else:
                receipt["status"] = "UNPROVEN_CONTENT_COVERAGE"
        else:
            receipt["status"] = "INVALID_SCANNER_RECEIPT"
    unknown = []
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
    coverage_passed = (
        scans_valid
        and selected == set(expected)
        and covered | patchless == set(expected)
        and not covered & patchless
        and primary["scanned_commits"] == len(forward)
        and expected_commits > 0
        and shallow == "false"
        and set(git("rev-list", "--all").splitlines()) == set(expected)
    )
    summary = {
        "scanner": GITLEAKS,
        "raw_exit_code": primary["raw_exit_code"],
        "log_opts": log_opts,
        "expected_commit_ids": expected,
        "commit_parent_graph": graph,
        "shallow_repository": shallow != "false",
        "expected_commits": expected_commits,
        "primary_scanned_commits": primary["scanned_commits"],
        "scanned_commits": len(covered),
        "patchless_commits": len(patchless),
        "accounted_commits": len(covered | patchless),
        "content_covered_commit_ids": sorted(covered),
        "patchless_commit_ids": sorted(patchless),
        "uncovered_commit_ids": sorted(set(expected) - covered - patchless),
        "scope_missing_commit_ids": sorted(set(expected) - selected),
        "scope_unexpected_commit_ids": sorted(selected - set(expected)),
        "coverage_passed": coverage_passed,
        "coverage_receipts": receipts,
        "primary_raw_findings": primary_findings,
        "raw_findings": len(findings),
        "distinct_findings": len({f["Fingerprint"] for f in findings}),
        "distinct_unreviewed_findings": len({f["fingerprint"] for f in unknown}),
        "reviewed_findings": len(findings) - len(unknown),
        "unreviewed_findings": unknown,
        "reviewed_gate_passed": coverage_passed and not unknown,
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
