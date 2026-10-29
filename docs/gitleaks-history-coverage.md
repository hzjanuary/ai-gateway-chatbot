# Gitleaks history coverage: commit identities and content receipts

The pinned scanner remains Gitleaks 8.30.1, immutable image
`zricethezav/gitleaks@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f`.
No detection rule, path or historical review is relaxed.

## Reproduced 23/24 mismatch

Baseline `cd9ce1ebfcfdfedc05fd56b0a95f01ee8f4f2508` has 24 reachable commits.
The full-history scanner reports 23. That exact latest commit deletes 30 lines of
CODEX-GOAL.md and adds no lines. Its tree differs from its parent, so it is not an
empty commit and cannot be removed from required content coverage. A singleton
forward scan reports zero commit fragments; the same pinned scanner with Git's
reverse-diff option `-R` reports one. This is a mismatch between the scanner's
added-fragment statistic and reachable commit count, not a new secret finding.

## Evidence required by the gate

1. Enumerate every reachable SHA and parent from `git rev-list --all`. Independently
   audit the actual `git log` revision selection, rejecting missing or extra SHAs.
2. Preserve the original full-history scan, log options and raw statistics. Default
   options remain `--all --full-history --diff-merges=separate`.
3. Compare each commit's tree with **all** parent trees (or the computed empty tree
   for a root). Only identical trees can be recorded as patchless. A merge equal
   to one parent but different from another is content-bearing.
4. For every content-bearing SHA, run a singleton `<sha>^!` scan with the same merge
   diff policy. It must produce exactly one commit receipt. If a successful scan
   has zero fragments, scan its reverse diff so deleted bytes become added
   fragments. That receipt must also report exactly one commit. Tool errors are
   failures; reverse scanning does not turn scanner errors into success.
5. Require the covered and independently patchless SHA sets to account for the exact
   expected set, without overlap; require the primary raw count to match the
   independently confirmed forward receipts. Reject shallow or changing history.
   Unproven content remains FAIL. No particular SHA is hardcoded or subtracted.

The forward/reverse receipts and raw reports are retained individually. The
original primary count is exposed as `primary_scanned_commits`, while
`scanned_commits` counts unique content-bearing SHAs with actual scanner receipts.
`patchless_commits` and `accounted_commits` remain separate. Thus 23 forward plus
one reverse is provable 24-SHA content coverage, not a rewritten scanner statistic.

Every finding from **every** scan is reviewed against the same exact historical
fingerprint and source-span hash. Additional receipts can repeat the three known
findings; `primary_raw_findings`, total `raw_findings` and `distinct_findings`
distinguish those counts. No duplicate raw output is erased, and no new finding
is automatically approved. A secret detected in deleted content still fails.

Regression repositories cover linear history, an empty commit and empty root,
real merges, transient side-branch secrets, merge-resolution secrets, deliberately
omitted history, deletion-only commits and deleted synthetic secrets. All scanner
containers use networking disabled. No realistic credential is stored in source.
