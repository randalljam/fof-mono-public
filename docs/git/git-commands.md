file: git-commands.md
title: Git Commands Reference
last-updated: 2026-06-06_1500
ai: Cursor - Composer 2.5 Fast
session: `delete branch after PR merge`

__Git Commands Reference__

Short runbook snippets for common Git operations in this repo. Destructive or history-rewriting procedures live in [`git-history-deletion-RUNBOOK.md`](git-history-deletion-RUNBOOK.md).

## Delete a branch after merging a PR

When a pull request is merged and you click **Delete branch** on GitHub, only the **remote** branch is removed. Your machine may still have:

- a **local branch** (e.g. `feature/hermes-agent`)
- a **stale remote-tracking ref** (e.g. `remotes/origin/feature/hermes-agent`) until you fetch and prune

GitGraph and similar views read **local** refs — so the branch can still appear until you clean up locally.

| Target | Where it lives | Delete with |
|--------|--------------|-------------|
| Remote branch | GitHub | **Delete branch** on the merged PR (or `git push origin --delete <branch>`) |
| Remote-tracking ref | Local pointer to old remote | `git fetch origin` + `git remote prune origin` |
| Local branch | Your machine | `git branch -d <branch>` |

There is no single command that removes all three; run the local steps below after deleting on GitHub.

### Procedure
Check out a branch other than the one you are deleting (usually `main`):

```bash
git checkout main
git pull origin main
```

Refresh remote state and drop stale `origin/…` pointers:

```bash
git fetch origin
git remote prune origin
```

Confirm what remains:

```bash
git branch -a | grep <branch-name>
```

Delete the **local** branch (safe when fully merged into `main`):

```bash
git branch -d <branch-name>
```

If Git refuses but the PR is merged, pull latest `main` and retry; use force delete only when you are sure:

```bash
git branch -D <branch-name>
```

If the remote branch was **not** deleted on GitHub:

```bash
git push origin --delete <branch-name>
```

Expected success line: `[deleted] <branch-name>`. `remote ref does not exist` means it is already gone.

### One-liner (after GitHub delete)

From repo root, on `main`:

```bash
git fetch origin && git remote prune origin && git branch -d <branch-name>
```

### Example — `feature/hermes-agent` (PR #9, 2026-06-06)

GitHub **Delete branch** on the merged PR, then locally:

```bash
git checkout main
git pull origin main
git fetch origin
git remote prune origin
git branch -d feature/hermes-agent
```

Verify:

```bash
git branch -a
git status
```

Expected: only `main` and `remotes/origin/main`; working tree clean and up to date with `origin/main`.

## Branch Info
**Local branches only:**
```bash
git branch
```

**Remote branches only:**
```bash
git branch -r
```

**Both:**
```bash
git branch -a
```

**Local branches with tracking info** (best everyday view):
```bash
git branch -vv
```
Example:
```text
* fix/hermes-dockerfile-openai-pep668 2593909 [origin/fix/hermes-dockerfile-openai-pep668] ...
  main                                23cb61a [origin/main] ...
```
`[origin/...]` means that local branch tracks that remote branch.

**Refresh remote list first** (important before comparing):
```bash
git fetch origin
git branch -r
```

**See what exists on GitHub without relying on local cache:**
```bash
git ls-remote --heads origin 'fix/hermes*'
```

**Remote branches you don’t have locally:**
```bash
git fetch origin
git branch -r | sed 's|origin/||' | while read rb; do
  git show-ref --verify --quiet "refs/heads/$rb" || echo "remote only: $rb"
done
```

**Local branches with no remote counterpart:**
```bash
git for-each-ref --format='%(refname:short) %(upstream:short)' refs/heads | awk '$2=="" {print "local only:", $1}'
```

### GitGraph in VS Code
1. **Fetch first** — Command Palette → `Git: Fetch` (or `GitGraph: Fetch`). Otherwise remote branches can be outdated.

2. **Open GitGraph** — Command Palette → `GitGraph: View Git Graph`.

3. **Read the graph:**
   - **Local branches** — labels without `origin/` (e.g. `fix/hermes-dockerfile-openai-pep668`).
   - **Remote branches** — labels with `origin/` (e.g. `origin/fix/hermes-dockerfile-openai-pep668`).
   - If they point at the same commit, you’ll see both labels on one node.

4. **Branch list in the graph UI** — Use the branches panel/filter (exact wording varies by GitGraph version). You can search `fix/hermes` to see both fix branches side by side.

5. **Tell local-only vs remote-only:**
   - Local-only: appears without `origin/` and has no matching `origin/...` at the same tip (or no upstream in `git branch -vv`).
   - Remote-only: `origin/some-branch` with no local `some-branch`.
   - Tracked pair: local `foo` + `origin/foo` on the same commit line.

6. **Compare two branches** — Right-click a branch in GitGraph → compare/checkout options (version-dependent), or in terminal:
   ```bash
   git log --oneline --graph origin/fix/hermes-dockerfile-openai-pep668 origin/fix/hermes-dockerfile-pep668
   ```
