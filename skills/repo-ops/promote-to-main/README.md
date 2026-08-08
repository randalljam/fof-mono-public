file: skills/repo-ops/promote-to-main/README.md
title: Promote core work off a feature branch into its own main PR
source-github-url: original
source-guide-url: original
history:
  - 2026-06-17 · Randy · Claude Code [math-quiz compare report](https://claude.ai/code/session_01Q4qQCJebkNKDxSC8Nq8WAC) — initial procedure, distilled from extracting core/grant_cloud_s3_access.py out of a feature branch into its own main PR


**You're deep in a feature/app branch and realize some of the work is general/core/infra that
belongs on `main`, not buried in this feature. This is how to lift it out cleanly: its own
`main`-based branch + PR, removed from the feature branch, with the human's local clone kept in
sync so a stray "Sync" doesn't undo it.**


## When to use
- Mid-feature, you wrote something that isn't tied to the feature — a `core/` module, an
  `infra`/ops script, a cross-cutting doc — and it should land on `main` on its own merits.
- You want that work reviewed and merged independently of the (still-unfinished) feature branch.

Do **not** use this for work that depends on the feature branch's own unmerged changes — see the
principle below.


## Principle: only *independent* work can be promoted
A branch's commits can be lifted to `main` only if they don't depend on anything that isn't
already on `main`. Think in terms of the stack:
```
main
 └─ feature/<app>-goal            (unmerged feature work)
     └─ feature/<app>-subtask     (you are here)
```
- **Independent commits** (e.g. a brand-new `core/foo.py` that imports nothing from the feature)
  can be re-based onto `main` and PR'd immediately. ✅ this skill.
- **Dependent commits** (a doc that references files only on `feature/<app>-goal`, code that
  imports the feature's modules) cannot — they must ride with the parent and merge bottom-up
  (`feature/<app>-goal` → `main` first, then the subtask). Don't try to promote those.

Confirm separability before doing anything: the commits you want to promote should touch **only**
the files going to `main`, and those files should not import/reference the feature's unmerged work.


## Procedure (cloud agent)
Run each numbered step, verify its output, and stop if anything doesn't match. The cleanup in
step 2 rewrites a pushed branch, so it needs **explicit user approval** (see Git safety rules in
`AGENTS.md`).


### 0. Identify the commit range and confirm it's separable
```
git log --oneline <feature-base>..HEAD          # see the branch's commits
git diff --stat <last-kept-commit>..HEAD         # the commits to promote should touch ONLY
                                                 #   the file(s) destined for main
```
`<last-kept-commit>` is the newest commit you're keeping on the feature branch; everything above
it is what you'll promote. Verify the promoted range is contiguous and path-isolated.


### 1. Extract to a `main`-based branch + open a PR (additive — safe)
```
git fetch origin --prune
git checkout -b <new-branch> origin/main         # type-first name; omit app token for cross-cutting
git cherry-pick <last-kept-commit>..<tip>        # replay the promoted commits onto main
git diff --stat origin/main..HEAD                # confirm the diff is exactly the intended file(s)
# compile/test the promoted code here if applicable
git push -u origin <new-branch>
```
Open a PR into `main` (GitHub MCP `create_pull_request`, or the printed compare URL). **Do not
merge it** — the human reviews/merges. Branch name follows `AGENTS.md` → Branch naming (type-first
prefix; cross-cutting core work usually needs no app token, e.g. `feature/cloud-agent-s3-access`).


### 2. Clean the source feature branch (force-push — REQUIRES explicit user approval)
First prove the promoted work is safe elsewhere, *then* remove it here. Verify before and after:
```
# --- pre-flight (make NO change if any check is wrong) ---
git checkout <feature-branch>
git status --porcelain                            # MUST be empty (no uncommitted work to lose)
git rev-parse --short origin/<new-branch>         # promoted work exists on its own remote branch
git ls-tree --name-only origin/<new-branch> <promoted-path>   # MUST print the path
test "$(git rev-parse origin/<feature-branch>)" = "$(git rev-parse HEAD)"  # remote == local (lease-safe)

# --- rewrite + push ---
git reset --hard <last-kept-commit>
git log --oneline <feature-base>..HEAD            # expect ONLY the kept commits; promoted ones gone
ls <promoted-path>                                # expect "No such file" here now (it's on the PR branch)
git push --force-with-lease origin <feature-branch>

# --- post-push verification ---
git fetch origin --prune
test "$(git rev-parse origin/<feature-branch>)" = "$(git rev-parse HEAD)"  # in sync
git rev-parse --short origin/<new-branch>         # promoted branch UNTOUCHED
```
`--force-with-lease` (never bare `--force`) only succeeds if the remote is still where you expect.
If it's rejected, STOP and inspect — someone else pushed; do not retry with `--force`.


### 3. Hand the user the local-clone coordination instructions
The force-push in step 2 leaves the human's **local** checkout stale and *ahead* of the remote (it
still has the promoted commits). If they hit their editor's **Sync / pull+push** button, the push
half will shove those commits **back** onto the remote and undo the cleanup. So you must give them
a paste-in block for their **local coding agent** (they run it locally; they should not be hand-
running terminal git). Fill in the placeholders from this run and hand them the template below.


## Local-agent coordination instructions (fill in, then give to the user)
Give the user this block to paste into their **local** coding agent (Cursor, etc.). Replace
`<FEATURE_BRANCH>`, `<PROMOTED_PATH>`, `<N>`, `<K>`, and the PR/merge note:
```
Context: a cloud session moved <N> commit(s) off `<FEATURE_BRANCH>` into its own PR (the work now
lives on `main` / a separate PR branch). It force-pushed `<FEATURE_BRANCH>`, so my local clone is
stale and *ahead* of the remote. Do NOT use the editor's "Sync Changes" — its push would put the
moved commits back on the remote and undo the cleanup. Align my local branch to the cleaned remote
instead, with verification, and STOP and report if anything doesn't match.

git branch --show-current            # must be <FEATURE_BRANCH>; if not, git checkout it
git fetch origin --prune
git status --short --branch          # expect clean; the branch line may say "ahead <N>" (expected).
                                     #   If there are uncommitted FILE changes, STOP and tell me.
git ls-tree --name-only origin/main <PROMOTED_PATH>
                                     # MUST print the path -> proves the moved work is safe on main,
                                     #   so dropping the local copies loses nothing. If empty, STOP.
git reset --hard origin/<FEATURE_BRANCH>
git status --short --branch          # expect "up to date with origin/...", clean
git log --oneline -<K>               # expect the kept commits only; no moved ones
ls <PROMOTED_PATH>                   # expect "No such file" locally — correct; it lives on main now
ls -la .env                          # (if relevant) untouched — reset --hard never touches
                                     #   gitignored/untracked files, so local .env / .venv are safe
# Do not push.
```
After the user runs it, their local matches the cleaned remote and the Sync indicator clears.


## Why "don't hit Sync"
After the force-push, `remote = <last-kept-commit>` but the human's `local = <tip>`, which is
`<last-kept-commit>` **plus** the promoted commits — i.e. local is strictly *ahead*. A Sync /
pull-then-push fast-forwards the **remote** back up to `<tip>`, re-adding the promoted commits and
re-introducing the very duplication you just removed (and a likely future conflict with `main`).
`git reset --hard origin/<feature-branch>` moves local *back* to the remote, after which there is
nothing to sync. (Identical-content files often merge cleanly anyway, but don't rely on it —
align the branch.)


## Notes
- **Approval gates:** step 1 is additive and safe; **step 2 is a force-push and needs the user's
  explicit OK each time** (`AGENTS.md` → Git safety rules). Never bare `--force`.
- **Direct-to-`main` variant:** for tiny operational/markdown changes the user may authorize a
  direct commit to `main` instead of a PR (`git push origin HEAD:main`); if `main` is protected the
  push is rejected — fall back to the branch+PR flow above.
- **This very skill** was added via this flow (the `core/grant_cloud_s3_access.py` extraction →
  PR #25), so it's a faithful record of a real run.
