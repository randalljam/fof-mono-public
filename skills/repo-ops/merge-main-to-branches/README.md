file: skills/repo-ops/merge-main-to-branches/README.md
title: Merge main or shared commits into active branches
source-github-url: original
source-guide-url: original
history:
  - 2026-07-01 · Randy · Cursor — title-bar-only settings conflicts preserve target branch worktree color
  - 2026-07-01 · Randy · Cursor — differing-overlap aborts now require automatic per-file diff analysis
  - 2026-07-01 · Randy · Cursor — identical-overlap paths now auto-pass preflight without override
  - 2026-06-30 · Randy · Cursor — conservative file-overlap preflight, merge-tree verification, structured abort report for branch owners
  - 2026-06-30 · Randy · Cursor [Repo Size And Hooks](90c8a941-72ad-4b56-b21c-4b7a84b4b89f) — initial procedure for fanning out repo-management updates across active branches

**Use this when a repo-wide change on `main` or a specific shared commit needs to be propagated to multiple active feature branches without rebasing or rewriting history.**


## What this does (for humans)

This skill **fans out shared repo updates to active feature branches** using normal git history — merge commits or cherry-picks, then normal pushes. It never rebases or force-pushes.

In **merge mode**, each target branch receives everything currently on `origin/main` that it was missing, while **keeping its own branch-specific commits**. After a successful merge, comparing the branch to `main` should show mostly work that belongs only on that branch; everything already merged to `main` is shared ancestry.

This skill is **conservative by default**. Before merging `main` into a branch, it checks whether **the same files** were changed on both `main` and the branch since they diverged. Branches with no overlapping files proceed automatically. If overlapping files end up **byte-for-byte identical** between `origin/main` and the branch tip, that overlap is benign and also proceeds automatically. If any overlapping file differs between `origin/main` and the branch tip, the merge for that branch is **not attempted** — the skill reports the differing overlapping paths so the branch owner can decide what to do.

That is stricter than waiting for git to conflict on the same *lines*. Two branches can edit different parts of the same file and merge cleanly; this skill still skips that case so branch owners are not surprised by automatic merges on files they are actively working on. The exception is identical final content: if both histories touched a path but the branch already matches `origin/main` for that path, there is nothing for the branch owner to reconcile. Think of it as the branch-wide equivalent of VS Code Sync stopping when the same file changed locally and on the remote: refresh everything except files this branch is also working on, unless the owner reviews overlap first.

**Cherry-pick mode** replays one specific commit or range onto each branch instead of all of `main`. The same file-overlap preflight applies, but the source file list comes from the cherry-pick commit(s), not all of `main`.


## When to use
- A general repo-management, docs, hooks, bootstrap, CI, or core-code update should be available on active app branches.
- The user asks to "merge main into branches", "fan out this commit", "port this shared update", or "sync active branches with main".
- The operation should be normal additive history: merge commits or cherry-picked commits, then normal pushes. Never force-push for this workflow.
Do **not** use this for extracting work off a feature branch into `main`; use `skills/repo-ops/promote-to-main/README.md` for that.


## Terms
- **Merge main forward / forward-port** — merge `origin/main` into each target branch. Use when the branch should receive all current `main` changes.
- **Cherry-pick / fan-out** — replay one specific commit or range onto each target branch. Use when the user wants only a repo-management patch, not every current `main` change.
- **File overlap** — a path changed on both the source (`main` or cherry-pick commit(s)) and the target branch since their common ancestor. Overlap blocks automatic merge for that branch only when the overlapping file content differs between the source tip and branch tip.
- **Backport** — usually means moving a newer change to an older release/support branch. Avoid that term for ordinary feature branch synchronization unless it is actually a release branch.


## Safety rules
- Get explicit user approval for the target branch list and any branch exclusions before changing branches or pushing.
- Exclude branches the user names, and do not improvise substitutes for branches that are missing.
- Keep a clean working tree. If `git status --porcelain` is not empty before starting a branch, stop and report it.
- Use `git fetch origin --prune` before branch inventory and before any ancestry checks.
- Never use rebase, amend, reset, or force-push in this workflow.
- Push only the branch currently being updated, and verify push output.
- Run the file-overlap preflight before every merge or cherry-pick attempt. If overlap exists, compare final file content; proceed automatically only when every overlapping path is identical between the source tip and branch tip. Do not merge when differing overlap exists unless the user explicitly overrides for a named branch.
- If a merge or cherry-pick conflicts despite a clean overlap check, collect conflict details, abort, and report. Do not resolve conflicts unless the user explicitly asks.


## Choose the mode
Use **merge mode** when:
- The user says "merge main to all active branches" or "bring branches up to date with main".
- It is acceptable for branches to receive every change currently on `origin/main`.
Use **cherry-pick mode** when:
- The user identifies a specific commit, commit range, or "the last repo-management commit".
- The user wants only that update on branches, not unrelated `main` changes.
When unsure, ask. Default recommendation for repo-wide policy updates is cherry-pick mode if the change is isolated in one commit; otherwise merge mode is simpler and more canonical.


## Preflight
Run these checks before touching target branches:
```bash
git fetch origin --prune
git status --short --branch
git branch --show-current
git branch -r
git log --oneline --decorate -20
git config core.hooksPath
git config user.name
git config user.email
whoami
```
Confirm:
- Current working tree is clean.
- Hooks are installed (`scripts/git/hooks`); if not, run `./scripts/git/install-hooks.sh` before any commits.
- The source ref exists (`origin/main` for merge mode, or the commit/range for cherry-pick mode).
- The target branch list is explicit and excludes any user-managed branches.
- Record git identity and machine login (`whoami`) for the final report header.


## Build the target list
List active remote branches, then ask the user to confirm the final set:
```bash
git branch -r --format='%(refname:short)' | sort
```
Do not include:
- `origin/main`
- `origin/HEAD`
- archived, merged, or deleted branches
- any branch the user excludes, such as another person's active branch
For each candidate branch, verify it still exists after prune:
```bash
git rev-parse --verify --quiet origin/<branch>
```


## File overlap preflight (required before merge or cherry-pick)
For each target branch, compute overlapping paths **before** attempting the merge or cherry-pick. Use remote refs so the check matches what will be merged.

### Merge mode — source and branch file lists
```bash
BASE=$(git merge-base origin/main origin/<branch>)

git diff --name-only "$BASE" origin/main | sort -u > /tmp/main-files.txt
git diff --name-only "$BASE" origin/<branch> | sort -u > /tmp/branch-files.txt

comm -12 /tmp/main-files.txt /tmp/branch-files.txt > /tmp/overlap-files.txt
```

### Cherry-pick mode — source and branch file lists
```bash
BASE=$(git merge-base origin/main origin/<branch>)

git diff --name-only <commit-or-range> | sort -u > /tmp/source-files.txt
git diff --name-only "$BASE" origin/<branch> | sort -u > /tmp/branch-files.txt

comm -12 /tmp/source-files.txt /tmp/branch-files.txt > /tmp/overlap-files.txt
```

### Identical-overlap check
If `/tmp/overlap-files.txt` is not empty, compare each overlapping path at the source tip and branch tip before deciding whether to abort. This catches the benign case where both histories touched the same file but ended with identical content.

Merge mode:
```bash
> /tmp/differing-overlap-files.txt
while IFS= read -r path; do
  git diff --quiet origin/main "origin/<branch>" -- "$path" || printf '%s\n' "$path" >> /tmp/differing-overlap-files.txt
done < /tmp/overlap-files.txt
```

Cherry-pick mode:
```bash
SOURCE_TREE=<commit-or-range-end>

> /tmp/differing-overlap-files.txt
while IFS= read -r path; do
  git diff --quiet "$SOURCE_TREE" "origin/<branch>" -- "$path" || printf '%s\n' "$path" >> /tmp/differing-overlap-files.txt
done < /tmp/overlap-files.txt
```

### Interpret overlap
- **`/tmp/overlap-files.txt` is empty** — no shared paths; proceed to the merge-tree check below, then merge or cherry-pick.
- **`/tmp/overlap-files.txt` is not empty** and **`/tmp/differing-overlap-files.txt` is empty** — all overlapping paths are identical at the source tip and branch tip; record them as benign identical overlaps and proceed to the merge-tree check, then merge or cherry-pick.
- **`/tmp/differing-overlap-files.txt` is not empty** — do **not** merge or cherry-pick this branch. Record the differing paths for the abort report (see below) and continue to the next target branch.

### Differing-overlap analysis
When `/tmp/differing-overlap-files.txt` is not empty, automatically analyze the differences before reporting back. Do not merely list paths. For each differing overlapping file, include:
- Name/status and shortstat for source vs branch tip.
- Whether the branch file is older/stale, branch-specific, source-specific, or unclear.
- The commits on the branch that touched the file since the fork base.
- The commits on the source that touched the file since the fork base.
- A concise recommendation: keep source, keep branch, reconcile both, or defer.

Use commands like:
```bash
git diff --name-status <source-tip> "origin/<branch>" -- "$path"
git diff --shortstat <source-tip> "origin/<branch>" -- "$path"
git log --oneline "$BASE..origin/<branch>" -- "$path"
git log --oneline "$BASE..<source-tip>" -- "$path"
git diff --unified=0 <source-tip> "origin/<branch>" -- "$path"
```

For small text files or small diffs, summarize the actual changed lines. For large docs, summarize by section headings, removed/added sections, and commit provenance rather than pasting a huge diff. If the differing path is `.vscode/settings.json`, first distinguish title-bar-only differences from real workspace setting differences; title-bar-only differences should be treated as benign local worktree identity, not as a blocking overlap. During an actual merge, resolve title-bar-only `.vscode/settings.json` conflicts by preserving the **target branch/worktree** title-bar colors and `window.titleBarStyle` while taking source/main for non-title-bar workspace settings. Do not resolve those conflicts with a blanket `git checkout --theirs -- .vscode/settings.json`, because that can copy main's title-bar color into the worktree branch.

### Belt-and-suspenders: dry-run merge (merge mode only)
When overlap is empty or only identical in merge mode, run a no-checkout merge preview before the real merge (Git 2.38+):
```bash
git merge-tree "$BASE" "origin/<branch>" origin/main
```
If the output contains conflict markers or reported conflicts, treat the branch like an overlap abort: do not merge, record that `merge-tree` predicted conflicts, and continue to the next branch. An empty or identical-only overlap list can still fail on renames, deletes, or other edge cases; this step catches those before history is changed.

Cherry-pick mode has no equivalent single-command preview; rely on the file-overlap preflight and abort on cherry-pick conflict if needed.


## Merge mode procedure
For each confirmed target branch:
```bash
git checkout <branch>
git status --porcelain
git pull --ff-only
```
Run the **file overlap preflight** and **merge-tree** check (above). If either blocks the branch, skip the merge and record an abort report entry.

If preflight passes:
```bash
git merge --no-edit origin/main
```
If the merge succeeds:
```bash
# Run focused tests or at least syntax/docs checks when applicable.
git status --short --branch
git push origin <branch>
git status --short --branch
```
Record:
- branch name
- merge commit SHA, if a merge commit was created
- whether the branch was already up to date
- push confirmation output


## Cherry-pick mode procedure
For each confirmed target branch:
```bash
git checkout <branch>
git status --porcelain
git pull --ff-only
```
Run the **file overlap preflight** (above). If differing overlap exists, skip the cherry-pick and record an abort report entry. If overlap exists but all overlapping paths are identical at the source tip and branch tip, proceed automatically.

If preflight passes:
```bash
git cherry-pick <commit-or-range>
```
If the cherry-pick succeeds:
```bash
# Run focused tests or at least syntax/docs checks when applicable.
git status --short --branch
git push origin <branch>
git status --short --branch
```
Record:
- branch name
- new cherry-pick commit SHA(s)
- push confirmation output


## Overlap abort report (per blocked branch)
When preflight finds differing overlapping files (or `merge-tree` predicts conflicts), do not merge that branch. Emit this block for the branch owner — they can paste it to their local coding agent. If overlap existed but every overlapping path was identical, do not emit an abort block; list those paths in the final report as "benign identical overlap" for transparency.

```text
Run by: <git config user.name> (<git config user.email>, login: <whoami>)
Source: origin/main | <commit-or-range>
Mode: merge | cherry-pick
Fork base: <BASE short sha>

Updated (merge succeeded on other branches):
- <branch-a>: pushed <sha or "already up to date">
- <branch-b>: pushed <sha or "already up to date">
(or: none yet — list successful branches from earlier in this run as they accumulate)

Merge aborted on: <branch>

Simultaneous changes were detected on both the source and this branch since the fork base.
The merge was not attempted because final content differs for the following overlapping files:

- <repo-relative/path/one>
- <repo-relative/path/two>

Automatic overlap analysis:
- <path>: <summary of source changes> / <summary of branch changes>; recommendation <keep source | keep branch | reconcile both | defer>
- <path>: <summary>

---

Instructions for your local coding agent:

Review the overlapping files on branch <branch> compared to main (or the cherry-pick
source). For each file listed above:

1. Summarize what changed on main (or in the source commit).
2. Summarize what changed on this branch.
3. Recommend one of:
   - keep the branch version and layer branch work on top of main later;
   - replace with the main version if branch changes were incidental or obsolete;
   - merge or reconcile both sides deliberately;
   - defer — overlap is expected and intentional; no action now.

The branch owner uses this report to decide whether to merge main manually, replace
specific files, stash and reapply, or leave the branch as-is until later.
```

Refresh the "Updated (merge succeeded on other branches)" section as the run progresses so each abort block shows which sibling branches already succeeded.


## Conflict handling
If `git merge` or `git cherry-pick` reports conflicts after a clean preflight (unexpected), collect:
```bash
git status --short
git diff --name-only --diff-filter=U
```
Then abort the in-progress operation:
```bash
git merge --abort
# or, for cherry-pick mode:
git cherry-pick --abort
```
Report using the same shape as an overlap abort, but note that the failure happened during the merge/cherry-pick despite a clean file-overlap preflight. Include conflicted files and a short read of why the conflict likely happened.

After abort, verify the branch is back to its original clean state:
```bash
git status --short --branch
```
Continue to the next target branch unless the user asked to stop the whole run on first failure.


## Final report
Start every final report with runner identity:
```text
Run by: <git config user.name> (<git config user.email>, login: <whoami>)
Source: origin/main or <commit/range>
Mode: merge or cherry-pick
```
Then summarize:
```text
Updated:
- <branch>: pushed <sha or merge sha>; verification <command/result>
- <branch>: pushed <sha or merge sha>; benign identical overlap <path count or "none">

Aborted — differing overlapping changes (merge not attempted):
- <branch>: <count> file(s) — see per-branch abort blocks above

Aborted — merge-tree predicted conflicts:
- <branch>: <brief note>

Conflicts during merge/cherry-pick (after clean preflight):
- <branch>: <files>; recommendation <what to do next>

Skipped / not attempted:
- <branch>: <reason>
```
If every branch succeeded, say that clearly. If any branch was blocked by overlap, `merge-tree`, or conflict, do not describe the overall fan-out as complete; say exactly which branches still need action and include the full per-branch abort blocks from above.


## Limitations (for humans)
File-overlap preflight is conservative and path-based, not a guarantee of zero risk:
- **Renames** — `main` may rename a path while the branch edits the old path; overlap logic may not flag every rename case. The `merge-tree` check helps in merge mode.
- **Deletes on main** — if `main` deletes a file the branch still edits, inspect `git diff --name-status "$BASE" origin/main` when diagnosing odd cases.
- **Semantic coupling** — `main` may change a dependency the branch relies on without touching the branch's files. Overlap preflight does not catch that; run focused tests when applicable.
- **Cherry-pick mode** — no `merge-tree` preview; overlap preflight is the main gate.
