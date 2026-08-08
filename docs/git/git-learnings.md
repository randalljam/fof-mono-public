file: plans/git/git-learnings.md
title: Git Learnings
last-updated: 2026-07-28_0504
ai: Cursor - Grok 4.5
session: `git learnings and title bar`


Personal notes on Git concepts as they come up. Runbook snippets for common ops live in [`git-commands.md`](git-commands.md).


## Commands
### `git fetch origin`
Updates your local copy of remote refs (including `origin/main`) from GitHub. Doesn't change your working files or current checkout.

### `git switch --detach origin/main`
Checks out the commit that `origin/main` currently points to, without attaching a branch name. Parks this worktree detached at the tip of `main` (or “detached at `origin/main`”).

Prefer that phrasing — not “detached head on the HEAD of main.” HEAD is the worktree’s “you are here”; the tip of main is just a commit.


## Terminology
### Ref / bookmark / branch
A **branch** is a named ref: a small file like `refs/heads/main` whose content is a commit SHA. “Sticky note on a commit” and “bookmark” are informal ways of saying the same thing.

Why say “bookmark” / “ref” instead of only “branch”? Because branches are only one kind of named SHA:

| kind | example path |
|------|----------------|
| local branch | `refs/heads/main` |
| remote-tracking branch | `refs/remotes/origin/main` |
| tag | `refs/tags/v1.0` |
| notes, replace, etc. | other `refs/...` |

- **Ref** (Git’s real term) = any named pointer to a SHA (usually a commit).
- **Bookmark** = informal synonym for that.
- **Branch** = a ref under `refs/heads/` that is expected to move as you commit.

So: every branch is a ref; not every ref is a branch.

### Remote refs
Local bookmarks that mirror branches on the remote (GitHub). Names like `origin/main` and `origin/feature/foo` live under `refs/remotes/`. `git fetch` updates those bookmarks; it doesn’t move your local `main` or change checked-out files.

### HEAD
Git’s “you are here” pointer. Normally it points at a branch name (`main`), so when you commit, that branch moves forward. In detached HEAD, it points straight at a commit hash instead of a branch.

HEAD either:
- points at a ref (`ref: refs/heads/main`) → you’re on that branch, or
- stores a raw SHA → detached HEAD.

The ref it points at then holds the commit SHA. HEAD itself is not usually called a “bookmark”; it’s “where this checkout is.”


## Worktrees and the detached-main standby
### Why Git blocks the same branch in two worktrees
A branch is one movable sticky note. Commits on that branch move that note forward. If two worktrees were both “on `main`,” both would fight over the same sticky note: commit in A, and B’s idea of `main` jumps; checkout/reset in one would surprise the other. Git forbids it so a branch has a single owner worktree.

### What parking detached at tip of main means
You’re not sharing the `main` branch — you’re only sharing the **same commit snapshot**. Implications:

- **Safe for reading / prepping / starting a new branch** from current main.
- **Don’t commit while detached** (or immediately `git switch -c feature/...` so the commit gets a branch).
- **No conflict with `fof-mono` on `main`** until you create a branch or try to check out `main` itself.
- **Overlapping edits aren’t the special danger** — two worktrees always have separate working trees. The real rule is: don’t both try to own/move the same branch. If both edit the same tracked files and you later merge/cherry-pick, that’s normal multi-checkout discipline, not a detached-HEAD-specific trap.
- **Stale tip:** after others land on `main`, re-fetch and re-detach to refresh the standby.

Parking detached at tip of `main` is the standard hot-standby pattern; the discipline is “don’t treat it as `main`, create a branch before real commits.”

### Start a feature from a dirty detached standby
Create/switch to the branch **first**, then commit. You don’t need a clean tree.

```bash
git switch -c feature/whatever
git add …
git commit
```

`git switch -c` makes a new branch at your current commit (tip of main), keeps your uncommitted changes, and attaches HEAD to that branch. The next commit is then the first commit on `feature/whatever`, with main as its parent.

Avoid committing while still detached; if you did, recover with `git switch -c feature/whatever` right after so that commit gets a branch name.
