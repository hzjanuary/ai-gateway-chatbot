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
