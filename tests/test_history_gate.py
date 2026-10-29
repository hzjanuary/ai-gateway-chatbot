"""Exercise the exact pinned scanner on real merge patches, never a scanner stub."""

import importlib.util
import json
import secrets
import subprocess

import pytest

spec = importlib.util.spec_from_file_location("secret_gate", "scripts/secret_gate.py")
secret_gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(secret_gate)


@pytest.mark.parametrize("with_secret", [False, True])
def test_real_merge_history_coverage_and_secret_detection(tmp_path, with_secret):
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args, check=True):
        return subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True, check=check
        )

    def commit(message):
        git("add", ".")
        git("commit", "-m", message)
        return git("rev-parse", "HEAD").stdout.strip()

    git("init", "-b", "main")
    git("config", "user.name", "Offline scanner regression")
    git("config", "user.email", "scanner@example.invalid")
    conflict = repo / "conflict.py"
    conflict.write_text('value = "base"\n')
    base = commit("base")
    git("checkout", "-b", "side")
    conflict.write_text('value = "side"\n')
    # Generated only inside this temporary repo; no real credential or tracked canary.
    side_value = "gh" + "p_" + secrets.token_hex(20) if with_secret else "side marker"
    (repo / "side.py").write_text(f'token = "{side_value}"\n')
    side = commit("side content")
    (repo / "side.py").write_text('value = "removed before merge"\n')
    removed = commit("remove transient side value")
    git("checkout", "main")
    conflict.write_text('value = "main"\n')
    main = commit("main content")
    assert git("merge", "--no-ff", "side", check=False).returncode == 1
    merge_value = "gh" + "p_" + secrets.token_hex(20) if with_secret else "merge marker"
    conflict.write_text(f'token = "{merge_value}"\n')
    merge = commit("resolve real merge")
    assert git("rev-list", "--parents", "-n", "1", merge).stdout.split() == [
        merge,
        main,
        removed,
    ]

    old = secret_gate.scan_history(repo, tmp_path / "ordinary", {}, log_opts="--all")
    assert old["expected_commits"] == 5
    assert old["scanned_commits"] == 4
    assert not old["reviewed_gate_passed"]
    old_findings = json.loads((tmp_path / "ordinary/gitleaks-history.json").read_text())
    assert merge not in {f["Commit"] for f in old_findings}

    complete = secret_gate.scan_history(repo, tmp_path / "complete", {})
    assert set(complete["expected_commit_ids"]) == {base, side, removed, main, merge}
    assert complete["expected_commits"] == complete["scanned_commits"] == 5
    assert complete["coverage_passed"]
    assert complete["patchless_commits"] == 0
    assert complete["reviewed_gate_passed"] is (not with_secret)
    findings = json.loads((tmp_path / "complete/gitleaks-history.json").read_text())
    if with_secret:
        assert {f["Commit"] for f in findings} == {side, merge}
        assert {f["File"] for f in findings} == {"side.py", "conflict.py"}
        # Multiple rules and per-parent merge patches can report the same canary.
        # Keep every raw finding; none is reviewed or suppressed in this repository.
        assert complete["raw_findings"] == len(complete["unreviewed_findings"]) >= 2
    else:
        assert complete["raw_findings"] == 0

    # Even with no findings, a successful scanner exit cannot prove truncated coverage.
    omitted = secret_gate.scan_history(
        repo, tmp_path / "omitted", {}, log_opts=f"--full-history --diff-merges=separate {main}"
    )
    assert omitted["scanned_commits"] == 2
    assert omitted["expected_commits"] == 5
    assert omitted["raw_findings"] == 0
    assert not omitted["reviewed_gate_passed"]
    assert not omitted["coverage_passed"]
    assert set(omitted["scope_missing_commit_ids"]) == {side, removed, merge}


def initialize_repo(repo):
    repo.mkdir()

    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

    git("init", "-b", "main")
    git("config", "user.name", "Offline coverage regression")
    git("config", "user.email", "scanner@example.invalid")
    return git


@pytest.mark.parametrize("last_change", ["linear", "empty", "deletion_only"])
def test_linear_empty_and_deletion_only_receipts(tmp_path, last_change):
    repo = tmp_path / "repo"
    git = initialize_repo(repo)
    content = repo / "example.txt"
    content.write_text("initial text\n")
    git("add", ".")
    git("commit", "-m", "initial content")
    base = git("rev-parse", "HEAD")
    content.write_text("updated text\n")
    git("commit", "-am", "linear edit")
    parent = git("rev-parse", "HEAD")
    if last_change == "linear":
        content.write_text("third text\n")
        git("commit", "-am", "second edit")
    elif last_change == "empty":
        git("commit", "--allow-empty", "-m", "empty commit")
    else:
        content.unlink()
        git("commit", "-am", "delete only")
    head = git("rev-parse", "HEAD")
    complete = secret_gate.scan_history(repo, tmp_path / "complete", {})
    assert complete["reviewed_gate_passed"] and complete["coverage_passed"]
    assert complete["expected_commits"] == complete["accounted_commits"] == 3
    assert complete["uncovered_commit_ids"] == []
    receipt = next(r for r in complete["coverage_receipts"] if r["commit"] == head)
    if last_change == "empty":
        assert git("rev-parse", head + "^{tree}") == git("rev-parse", parent + "^{tree}")
        assert complete["patchless_commit_ids"] == [head]
        assert complete["primary_scanned_commits"] == complete["scanned_commits"] == 2
        assert receipt["scans"] == []
    elif last_change == "deletion_only":
        assert git("rev-parse", head + "^{tree}") != git("rev-parse", parent + "^{tree}")
        assert git("diff", "--numstat", parent, head) == "0\t1\texample.txt"
        assert complete["patchless_commit_ids"] == []
        assert complete["primary_scanned_commits"] == 2
        assert complete["scanned_commits"] == 3
        assert receipt["status"] == "SCANNED_REVERSE"
        assert [s["scanned_commits"] for s in receipt["scans"]] == [0, 1]
        # Omitting the deletion produces the SAME primary count; identity proof
        # must still reject it, even though a count-only comparison cannot tell.
        same_count = secret_gate.scan_history(
            repo,
            tmp_path / "same-primary-count",
            {},
            log_opts=f"--full-history --diff-merges=separate {parent}",
        )
        assert same_count["primary_scanned_commits"] == complete["primary_scanned_commits"]
        assert same_count["scope_missing_commit_ids"] == [head]
        assert not same_count["coverage_passed"] and not same_count["reviewed_gate_passed"]
    else:
        assert complete["scanned_commits"] == complete["primary_scanned_commits"] == 3
        assert complete["patchless_commit_ids"] == []

    # No count balancing by empty/deletion-only commits may hide an omitted edit.
    omitted = secret_gate.scan_history(repo, tmp_path / "omitted", {}, log_opts=base)
    assert not omitted["reviewed_gate_passed"] and not omitted["coverage_passed"]
    assert set(omitted["scope_missing_commit_ids"]) == {parent, head}
    assert omitted["raw_findings"] == 0


def test_empty_root_requires_independent_empty_tree_proof(tmp_path):
    repo = tmp_path / "repo"
    git = initialize_repo(repo)
    git("commit", "--allow-empty", "-m", "empty root")
    head = git("rev-parse", "HEAD")
    complete = secret_gate.scan_history(repo, tmp_path / "complete", {})
    assert complete["reviewed_gate_passed"]
    assert complete["scanned_commits"] == complete["primary_scanned_commits"] == 0
    assert complete["expected_commits"] == complete["accounted_commits"] == 1
    assert complete["patchless_commit_ids"] == [head]
    assert complete["coverage_receipts"][0]["parent_trees"] == {}


def test_merge_equal_to_one_parent_still_requires_content_scan(tmp_path):
    repo = tmp_path / "repo"
    git = initialize_repo(repo)
    content = repo / "example.txt"
    content.write_text("base\n")
    git("add", ".")
    git("commit", "-m", "base")
    base = git("rev-parse", "HEAD")
    git("checkout", "-b", "side")
    content.write_text("side content\n")
    git("commit", "-am", "side")
    side = git("rev-parse", "HEAD")
    git("checkout", "main")
    git("merge", "--no-ff", "side", "-m", "synthetic-style merge")
    merge = git("rev-parse", "HEAD")
    assert git("rev-parse", merge + "^{tree}") == git("rev-parse", side + "^{tree}")
    assert git("rev-parse", merge + "^{tree}") != git("rev-parse", base + "^{tree}")
    complete = secret_gate.scan_history(repo, tmp_path / "complete", {})
    assert complete["reviewed_gate_passed"]
    assert complete["expected_commits"] == complete["scanned_commits"] == 3
    assert merge not in complete["patchless_commit_ids"]
    assert next(r for r in complete["coverage_receipts"] if r["commit"] == merge)["status"] == (
        "SCANNED_FORWARD"
    )


def test_deleted_secret_is_scanned_and_never_automatically_reviewed(tmp_path):
    repo = tmp_path / "repo"
    git = initialize_repo(repo)
    (repo / "readme.txt").write_text("clean root\n")
    git("add", ".")
    git("commit", "-m", "clean root")
    generated = "gh" + "p_" + secrets.token_hex(20)
    secret_file = repo / "removed.py"
    secret_file.write_text(f'token = "{generated}"\n')
    git("add", ".")
    git("commit", "-m", "temporary synthetic value")
    introduced = git("rev-parse", "HEAD")
    secret_file.unlink()
    git("commit", "-am", "delete synthetic value")
    deleted = git("rev-parse", "HEAD")
    complete = secret_gate.scan_history(repo, tmp_path / "complete", {})
    assert complete["coverage_passed"]
    assert complete["expected_commits"] == complete["scanned_commits"] == 3
    assert not complete["reviewed_gate_passed"]
    assert complete["reviewed_findings"] == 0
    assert complete["unreviewed_findings"]
    receipt = next(r for r in complete["coverage_receipts"] if r["commit"] == deleted)
    assert receipt["status"] == "SCANNED_REVERSE"
    reverse = json.loads((tmp_path / "complete" / receipt["scans"][-1]["report"]).read_text())
    primary = json.loads((tmp_path / "complete/gitleaks-history.json").read_text())
    assert {r["Commit"] for r in primary} == {introduced}
    assert {r["Commit"] for r in reverse} == {deleted}
