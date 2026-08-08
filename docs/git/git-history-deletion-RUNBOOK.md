file: fof-mono_git-history-deletion-RUNBOOK.md
title: Git History Deletion RUNBOOK
last-updated: 2026-07-28_1136
ai: Cursor - GPT-5.5
session: `local data continuity`

__Git History Deletion RUNBOOK__

Use this runbook when a committed path should be removed from all reachable Git history, not merely deleted from the current checkout. This is destructive history surgery: create a standalone backup first, validate locally, and coordinate before any rewritten branch is pushed.

Commands in **General Procedure** use `fof-mono`, `/Users/randytrue/Documents/Code`, and `[PRIVATE-GIT-REMOTE]` as the working repo, parent directory, and remote. Substitute those names when applying this runbook to a different clone.


## General Procedure

### 1. Confirm Scope
Identify the exact path to remove and verify that similarly named paths should remain. Prefer exact path filters over globs.
Useful checks:
```bash
git status --short
git ls-files -- <path>
git log --all --name-status -- <path>
git rev-list --objects --all -- <path> | git cat-file --batch-check='%(objecttype) %(objectsize) %(rest)'
```
If a current local copy must survive the rewrite, copy or archive it outside the repo before filtering. History backups protect Git state, but a rewrite can also change the working tree.

### 2. Create a Mirror and Bundle Backup
Create backup artifacts outside all checkouts under `_BACKUP`. Set `BACKUP_STAMP` once so the mirror and bundle share the same date-time label (local time, `YYYY-MM-DD_HHMM`). Each run creates new files; delete old backups manually when no longer needed.
```bash
BACKUP_DIR=/Users/randytrue/Documents/Code/_BACKUP/fof-mono_git-history
BACKUP_STAMP=$(date +%Y-%m-%d_%H%M)
mkdir -p "${BACKUP_DIR}"
echo "Backup stamp: ${BACKUP_STAMP}"
git clone --mirror /Users/randytrue/Documents/Code/fof-mono "${BACKUP_DIR}/fof-mono-backup-${BACKUP_STAMP}.git"
cd "${BACKUP_DIR}/fof-mono-backup-${BACKUP_STAMP}.git"
git bundle create "${BACKUP_DIR}/fof-mono-backup-${BACKUP_STAMP}.bundle" --all
git bundle verify "${BACKUP_DIR}/fof-mono-backup-${BACKUP_STAMP}.bundle"
git show-ref | wc -l
```
Example artifacts: `/Users/randytrue/Documents/Code/_BACKUP/fof-mono_git-history/fof-mono-backup-2026-06-18_1618.git`, `/Users/randytrue/Documents/Code/_BACKUP/fof-mono_git-history/fof-mono-backup-2026-06-18_1618.bundle`.
Keep both backup artifacts outside the working repo. Do not continue if the mirror clone, bundle creation, or bundle verification fails. Record `BACKUP_STAMP` because rollback (§9) needs the same value.

### 3. Install or Verify `git-filter-repo`
Use `git-filter-repo` for targeted path deletion.
```bash
python3 -m pip install git-filter-repo
git filter-repo --help
```
In fof-mono, use the project virtual environment:
```bash
cd /Users/randytrue/Documents/Code/fof-mono
.venv/bin/python3 -m pip install git-filter-repo
.venv/bin/git-filter-repo --help
```

### 4. Rewrite One Target at a Time
Run one filter, validate it, then move to the next target.
```bash
cd /Users/randytrue/Documents/Code/fof-mono
git filter-repo --path <exact/path/> --invert-paths
git log --all -- <exact/path/>
git ls-files -- <exact/path/>
```
The expected result is no history and no tracked files for the removed path.

For linked-worktree setups, prefer running history rewrite in a **fresh throwaway clone** (recommended) instead of a clone that currently has multiple linked worktrees attached.

Optional: limit rewrite to one branch when blobs exist on that branch only:
```bash
git filter-repo --path <exact/path/> --invert-paths --refs refs/heads/<branch>
```

### 5. Add Ignore Rules for Local-Only Paths
If the path should remain on disk but not in Git, add an anchored ignore rule:
```gitignore
/<path>/
```
Then validate:
```bash
git status --short -- <path> .gitignore
git status --ignored --short -- <path>
```

### 6. Cleanup and Validate Repository Health
After all filters succeed:
```bash
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git count-objects -vH
git fsck --full
git status --short
git log --oneline --decorate --max-count=10
```
Commit any intentional current-tree changes, such as `.gitignore` updates.

### 7. Remote Coordination
Do not push automatically. Rewriting a shared branch requires coordination because other clones will have the old commit graph.
`git-filter-repo` removes the `origin` remote as a safety precaution so the rewritten history cannot be pushed accidentally. This does not delete the GitHub repo. It only removes the local nickname that points to GitHub.
After explicit approval, re-add the remote, fetch first, verify the remote branch is the expected old state, then use `--force-with-lease`.
```bash
git remote -v
```
Expected immediately after `git-filter-repo`: no output, because `origin` was removed.
```bash
git remote add origin [PRIVATE-GIT-REMOTE]
git remote -v
git fetch origin
git log --oneline origin/<branch> -3
```
Then push the rewritten branch and set upstream tracking:
```bash
git push --force-with-lease -u origin <branch>
```
Expected push output includes:
```text
+ <old-sha>...<new-sha> <branch> -> <branch> (forced update)
branch '<branch>' set up to track 'origin/<branch>'.
```
Verify:
```bash
git status --short --branch
git log --oneline --decorate -5
```
Before pushing, ensure no other clone/session will push to that same branch between backup and force-push.

### 8. After the Rewrite — Re-sync Every Dependent Branch (MANDATORY)
A history rewrite gives every rewritten commit a **new SHA**. Any branch, worktree, or
clone still pointing at the **old** commits is now on a parallel, dead copy of history.
If it is not reset it diverges silently and forever: a later merge/PR to `main` finds only
the **pre-rewrite** commit as a common ancestor and reports dozens of **spurious conflicts**
(the same files, rewritten on both sides, look independently changed).

> **This is exactly what the 2026-06-05 `main` rewrite (§ "Real run") caused.** The
> `feature/math-quiz-compare-report` / `-further-dev` line was forked from pre-rewrite `main`
> and never reset, so it stayed on the old copy. Its merge-base with `main` was stranded at
> the cutover boundary; a later PR hit ~30 spurious conflicts and was fixable only by
> re-forking onto current `main` (PR #28, 2026-06-24).

Do all of the following immediately after the force-push, before any further work.

**8a. Enumerate every dependent ref BEFORE you rewrite.** A rewrite affects *every* ref that
contains the rewritten commits, not just the branch you filtered.
```bash
git branch -a --contains <first-rewritten-commit>   # branches (local+remote) on the old line
git worktree list
git for-each-ref --format='%(refname:short)' refs/heads refs/remotes
```
List them. Decide per branch: **reset**, **re-fork/re-root**, or **abandon**. Leave none on
the old copy.

**8b. Hard-reset every clone, worktree, and `main` to the rewritten refs** — including the
human's primary local `main`, so future branches fork from the right place.
```bash
git fetch origin --prune
git checkout main && git reset --hard origin/main
# repeat for each additional worktree/clone that had the old history
```

**8c. Re-create dependent feature branches off the rewritten `main`.** A branch already built
on the old copy cannot be repaired by merging — **re-fork** it: branch from the new `main` and
re-apply its unique work (`git checkout <old-branch> -- <paths>` for an additive feature, or
cherry-pick its genuinely-unique commits), verify/tests, PR, then delete the diseased branch.

**8d. A squash-merge does NOT reconcile divergence.** Integrating a rewritten branch into
`main` via **squash** copies its *content* into one new commit but puts **none of its commits
into `main`'s ancestry** — so any *sibling* branch built on the old copy still shares only the
pre-rewrite ancestor with `main` and will still conflict. If siblings depend on it, use a real
merge, or re-fork the siblings (8c) after the squash lands.

**8e. Audit each active branch for stranded history.** For every branch, confirm its merge-base
with `main` is recent and it carries no rewritten "twin" commits:
```bash
git merge-base origin/main <branch>                 # should be RECENT, not an old rewrite boundary
git rev-list --left-right --count origin/main...<branch>
git log origin/main --format='%at|%s' > /tmp/main_set.txt
git log <branch> --not origin/main --format='%at|%s' | grep -Fxf /tmp/main_set.txt | wc -l   # "twins"
```
**Healthy:** recent merge-base, **0 twins**. **Stranded:** merge-base pinned at an old rewrite
boundary **plus** many twins (ahead-commits that duplicate a `main` commit by author-date+subject)
→ re-fork it (8c) before its next PR. Verify the repaired relationship in Holodeck and put the
branch purpose/parent in the re-forked branch's first commit per `AGENTS.md`.

### 9. Rollback
If validation fails before pushing, use the same `BACKUP_STAMP` from §2:
```bash
BACKUP_DIR=/Users/randytrue/Documents/Code/_BACKUP/fof-mono_git-history
BACKUP_STAMP=2026-06-18_1618   # replace with your stamp
git clone "${BACKUP_DIR}/fof-mono-backup-${BACKUP_STAMP}.git" "/Users/randytrue/Documents/Code/fof-mono-restored-${BACKUP_STAMP}"
```
Or restore from the bundle:
```bash
BACKUP_DIR=/Users/randytrue/Documents/Code/_BACKUP/fof-mono_git-history
BACKUP_STAMP=2026-06-18_1618   # replace with your stamp
mkdir "/Users/randytrue/Documents/Code/fof-mono-restored-${BACKUP_STAMP}"
cd "/Users/randytrue/Documents/Code/fof-mono-restored-${BACKUP_STAMP}"
git clone "${BACKUP_DIR}/fof-mono-backup-${BACKUP_STAMP}.bundle" .
```


## Real run: fof-mono - remove `exchanges/` and `apps/math_quiz/` from history (2026-06-05)
This section documents an executed cleanup on `main` in fof-mono on 2026-06-05 (commit `9ad3f35` - "Document targeted git history cleanup"). It is a worked example and audit trail, not steps to re-run unless those paths reappear in history.

### Targets
Remove these paths from history in this order:
1. Root `exchanges/`
2. Historical `apps/math_quiz/`
Preserve the active app at `apps/math-quiz/`.

### Backup Commands
Predates the dated-backup convention in General Procedure §2:
```bash
BACKUP_DIR=/Users/randytrue/Documents/Code/_BACKUP/fof-mono_git-history
mkdir -p "${BACKUP_DIR}"
git clone --mirror /Users/randytrue/Documents/Code/fof-mono "${BACKUP_DIR}/fof-mono-backup.git"
cd "${BACKUP_DIR}/fof-mono-backup.git"
git bundle create "${BACKUP_DIR}/fof-mono-backup.bundle" --all
git bundle verify "${BACKUP_DIR}/fof-mono-backup.bundle"
git show-ref | wc -l
```

### Filters used in that run
```bash
cd /Users/randytrue/Documents/Code/fof-mono
git filter-repo --path exchanges/ --invert-paths
git filter-repo --path apps/math_quiz/ --invert-paths
```

### Remote update used in that run
```bash
git remote add origin [PRIVATE-GIT-REMOTE]
git fetch origin
git push --force-with-lease -u origin main
```

### Aftermath note (added 2026-06-24)
This force-push rewrote every commit after the cutover, giving them new SHAs. Branches forked
from **pre-rewrite** `main` — the `math-quiz-compare-report` / `-further-dev` line — were never
reset and stayed on the old copy. That stranded their merge-base with `main` at the cutover
boundary and produced ~30 spurious conflicts at PR time (fixed only by re-forking onto current
`main`). The §8 re-sync/audit steps exist to prevent exactly this; they were not part of the
runbook when this run executed.
