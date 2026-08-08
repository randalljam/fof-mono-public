file: skills/repo-ops/extract-commits-to-subbranch/README.md
title: Extract commits to a sub-branch (squash-merge back)
source-github-url: original
source-guide-url: original
history:
  - 2026-07-03 · Randy · Cursor [Commit reword plan](214cc159) — dragon apply: cherry-pick conflicts on test_dev_server; gh squash blocked → local merge --squash; add/add on clone_user_file.py
  - 2026-07-03 · Randy · Cursor [Commit reword plan](214cc159) — initial skill; cherry-pick extract, drop from parent, optional squash PR


**Use when a feature branch mixes two concerns and you want one chunk on a sub-branch, squashed back into the parent, while preserving detailed commit history in the sub-branch PR on GitHub.**


## When to use
- Parent branch (e.g. `feature/dragon`) contains commits that belong elsewhere (e.g. general math-quiz app tuning).
- You want those commits as **one squash commit** on the parent after review, with full stepwise history visible only in the sub-branch PR.
- Commit messages are already correct (run `reword-branch-commits` first if not).


## Commit selection
Use `list_commits_for_extract.py` to inspect candidates:
```bash
.venv/bin/python3 skills/repo-ops/extract-commits-to-subbranch/scripts/list_commits_for_extract.py \
  --repo /path/to/worktree \
  --branch feature/parent \
  --base "$(git merge-base origin/main HEAD)" \
  --scope-prefix "(math-quiz)" \
  --exclude-path apps/math-quiz/dragon/
```
Criteria (pick one or combine):
1. **Explicit SHA list** — comma-separated or one SHA per line in a file.
2. **Scope prefix** — subject contains `(math-quiz)` etc.
3. **Path-based** — helper flags `MIXED` when `--exclude-path` prefixes appear.

Warn when a kept commit touches the same files as an extracted commit (transient mid-history breakage is OK; final tree is verified).


## Procedure
1. Same preconditions and backup as `reword-branch-commits`.
2. Record parent tip: `PRE_TIP=$(git rev-parse HEAD)`.
3. Create sub-branch at fork-base; cherry-pick selected commits (committer date = author date).
4. Rebuild parent branch **without** those commits (new SHAs, same trees for kept commits). Parent tip tree **will differ** from `PRE_TIP` until step 7 — that is expected.
5. Push sub-branch and force-with-lease push parent.
6. **PAUSE (default)** — inspect graph; proceed only when satisfied.
7. Squash-merge sub-branch → parent (PR or local `git merge --squash`). GitHub may report conflicts when parent already dropped the same paths — resolve locally favoring the sub-branch, then commit. Delete sub-branch after merge.
8. Verify: `git diff $PRE_TIP HEAD` empty on parent (content identical, history reorganized).


## Run (pause before PR)
```bash
.venv/bin/python3 skills/repo-ops/extract-commits-to-subbranch/scripts/extract_commits.py \
  --repo /path/to/worktree \
  --source-branch feature/math-quiz-dragon-baby \
  --sub-branch feature/math-quiz-app-tuning \
  --parent-base 7e39123c0d512b95dd2af8b2a3e00617503014ba \
  --commits c60da8d,3d94481,cde361a,... \
  --pre-tip-file /tmp/pre-extract-tip.txt \
  --backup \
  --push
```


## Run (squash PR after pause)
Add `--auto --squash-pr --pr-title "feat(math-quiz): …"`.


## Provenance
After squash-merge, individual extracted commits and per-commit diffs remain on the **closed GitHub PR** for the sub-branch. They are not ancestors of the parent branch.


## Related
- `skills/repo-ops/reword-branch-commits/` — fix messages before extracting.
- [docs/git/git-history-deletion-RUNBOOK.md](../../../docs/git/git-history-deletion-RUNBOOK.md) — backup and re-sync.
