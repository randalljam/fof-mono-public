file: skills/repo-ops/reword-branch-commits/README.md
title: Reword branch commit messages (history rewrite)
source-github-url: original
source-guide-url: original
history:
  - 2026-07-30 · Randy · Codex [Codex Workspace Setup](019faf02-bddf-76c1-bbfc-6e43cc8b0adf) — fail closed when a rewrite would recreate a durable lineage record
  - 2026-07-03 · Randy · Cursor [Commit reword plan](214cc159) — dragon apply: stash untracked plan/map files before run; 27 commits reworded, tree verified empty diff
  - 2026-07-03 · Randy · Cursor [Commit reword plan](214cc159) — initial skill; commit-tree reword with backup and date preservation


**Use when commit messages on a published feature branch need correction (scope renames, typos) without changing file content or graph order.**

This generic script refuses a rewrite range that contains any branch-lineage record. Recreating
one changes its Git SHA and can invalidate its stable audit chain. For an approved rewrite that
must include a lineage record, follow `skills/repo-ops/branch-lineage-record/README.md` and use
an end-to-end workflow that creates the tracked rewrite map and a superseding v2
`recorded-late` record; do not bypass this guard.


## When to use
- Rename scopes in commit subjects (e.g. `(math-quiz)` → `(dragon-baby)`) before a PR.
- Fix sloppy subjects while keeping stepwise commits and original author/committer dates.
- Branch is **not** `main`, **not merged**, and you are the primary owner.


## Assumptions checked (git)
The script verifies:
- Current branch matches `--branch`.
- Working tree clean (stash or move untracked artifacts such as plan files and message maps if needed: `git stash push -u`).
- `git fetch origin --prune` and local tip equals `origin/<branch>`.
- Branch is not checked out in **more than one** worktree.
- No commit in `<base>..<branch>` is a branch-lineage record.

Run from the worktree that has the branch checked out, or pass `--repo` to that worktree path.


## Assumptions reminded (human)
- No open PR depends on old SHAs for review threads (GitHub updates the PR on force-push, but inline comments on old SHAs look orphaned).
- No collaborator has unpushed commits on this branch.
- If someone has a stale local checkout after your force-push, they run:
  `git fetch origin && git reset --hard origin/<branch>`


## Backup
Before rewrite, create mirror + bundle per [docs/git/git-history-deletion-RUNBOOK.md](../../../docs/git/git-history-deletion-RUNBOOK.md) §2:
```bash
.venv/bin/python3 skills/repo-ops/reword-branch-commits/scripts/git_history_backup.py
```
Artifacts: `/Users/randytrue/Documents/Code/_BACKUP/fof-mono_git-history/fof-mono-backup-<STAMP>.{git,bundle}`


## Message map format
TSV file: `old-sha<TAB>new subject line` (full or 7-char SHA). Lines starting with `#` ignored. Commits omitted from the map keep their existing message.


## Run
```bash
.venv/bin/python3 skills/repo-ops/reword-branch-commits/scripts/reword_commits.py \
  --repo /path/to/worktree \
  --branch feature/my-branch \
  --base "$(git merge-base origin/main HEAD)" \
  --map docs/git/reword-my-branch.map \
  --backup \
  --push
```
Dry-run (preconditions + map load only): add `--dry-run`.


## Verification (built-in)
- `git diff <old-tip> <new-tip>` is empty (trees unchanged).
- Commit count unchanged.
- Mapped subjects match the map.
- The rewritten range contains no durable branch-lineage record.
- On `--push`: requires `forced update` output from `--force-with-lease`.


## Rollback
```bash
git reset --hard <old-tip>
git push --force-with-lease origin <branch>
```
Old tip is printed as `OLD_TIP=…` and remains in reflog and the backup bundle.


## Related
- `skills/repo-ops/branch-lineage-record/README.md` — required superseding records and tracked rewrite-map contract.
- [docs/git/git-history-deletion-RUNBOOK.md](../../../docs/git/git-history-deletion-RUNBOOK.md) — backup §2, re-sync §8 after rewrite.
- `skills/repo-ops/extract-commits-to-subbranch/` — pull a subset of commits to a sub-branch.
