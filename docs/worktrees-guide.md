file: docs/worktrees-guide.md
title: Git Worktrees Guide — parallel branches in separate Cursor windows
last-updated: 2026-07-31_0745
ai: Cursor - Grok 4.5
session: `local-files-audit skill`

Guide for using git worktrees in `fof-mono`: one branch per Cursor window, shared
virtualenv by default, shared local-only files through `_LOCAL_FILES`, bootstrap for new
checkouts, and **automatic publish** so local feature branches match their remotes (required
for cloud agents). **First clone on a machine:** run **clone bootstrap**
(`skills/repo-ops/clone-bootstrap/README.md`) — hooks, local-file mounts, and one-time git
branch-tracking defaults live there, not in this guide. **Local-files audit / pre-removal
WARN review:** `skills/repo-ops/local-files-audit/README.md` (sole source of truth).

**How to read this guide:** removal and UI sections list **menus and clicks first** where
helpful. Terminal commands are under **Command alternative**.


## Creating a worktree

**Creation moved to `skills/repo-ops/create-worktree/README.md` on 2026-07-02.** That skill is
the **sole source of truth** for new worktrees: branch-state decision table, fuzzy branch
resolution, bootstrap, title-bar color, Cursor window open, and verification.

Ask a Cursor agent: *"Create a worktree for `<branch>`"* — or follow the skill procedure
yourself. **Do not use** Worktree Manager → **Create Worktree** (`+`); the menu-driven creation
flow is **retired** (it could not anchor remote-only branches correctly and stranded branches on
stale local `main`).

When the PR merges, follow [Remove a worktree after PR merge](#remove-a-worktree-after-pr-merge-branch-cleanup).


## Remove a worktree after PR merge (branch cleanup)
Use this when a feature branch's PR is ready to merge and you are ready to retire its worktree
folder and branch. Run the **local-files audit** **before** merging so any
gitignored-but-important files are found while the feature worktree still exists. You can leave
the feature worktree Cursor window open until that audit is done — close it only in
[Step 4](#step-4--close-the-feature-worktree-window).

The agent runs `skills/repo-ops/local-files-audit/README.md` (checks mounts, classifies WARN
paths, proposes preserve moves); **you** remove the worktree and delete the branch.

### Quick version to closeout worktree
1. In the worktree window being closed, ask the Cursor agent to run the local-files audit / pre-removal check (`skills/repo-ops/local-files-audit/README.md`); approve verdicts and any preserve moves before continuing.
2. Merge the PR — in the browser at the GitHub PR URL. If requesting squash or rebase merge, explain why; for squash requests, follow the PR merge strategy in `AGENTS.md`.
3. Switch to the main `fof-mono` window in Cursor and sync `main`, or to the parent branch worktree window and sync there.
4. Close the feature worktree Cursor window.
5. In the `fof-mono` window: **Source Control** → **WORKTREES** → right-click that worktree → **Remove Worktree** → **Remove**.
6. In **Git Graph**: right-click the merged branch → **Delete branch** → check **Delete remote branch as well** → confirm.

### Step 1 — Local-files audit (Cursor agent, from feature worktree window)
**Source of truth:** `skills/repo-ops/local-files-audit/README.md`.

In the **feature worktree window being closed**, ask the Cursor agent to run that skill.
Example prompt:

> Run the local-files pre-removal check for this worktree before I merge and remove it.

When the agent reports the worktree is safe to remove from a local-files perspective, continue
with Steps 2–6 below. If there are unresolved `BLOCK` items or unapproved preserve paths,
resolve those first.

### Step 2 — Merge the PR
On GitHub, merge the pull request for the feature branch. Preserve individual commits by default.
If you request a squash or rebase merge, explain why. For squash requests, agents should follow
the PR merge strategy in `AGENTS.md` so the squash commit message includes the PR number and URL.

### Step 3 — Switch to the main `fof-mono` window and sync `main`
Do this in your **main Cursor window** — title bar **fof-mono**, bottom-left branch **`main`**.

**Menu / UI**
1. If you are not already in the main window, switch to it (not the feature worktree window).
2. Confirm bottom-left shows **`main`** — if not, click the branch name and pick **`main`**.
3. Click **Sync** in the bottom-left (or Source Control → **`…`** → **Pull**) to pull the
   merged PR commits into local `main`.

**Command alternative**
```bash
cd /Users/randytrue/Documents/Code/fof-mono
git checkout main
git pull origin main
```

### Step 4 — Close the feature worktree window
Close the Cursor window for the feature worktree (e.g. title bar shows
`feature-math-quiz-dynamic`). You do not need to delete files manually — removal happens in
Step 5.

### Step 5 — Remove the worktree (main window)
In the **main `fof-mono` window**:

**Menu / UI**
1. Open **Source Control** (`⌘⇧G`).
2. Scroll to **WORKTREES**.
3. Right-click the retired worktree (e.g. `feature-math-quiz-dynamic`) → **Remove Worktree**.

**Command alternative**
```bash
cd /Users/randytrue/Documents/Code/fof-mono
git worktree remove /Users/randytrue/Documents/Code/feature-<slug>
git worktree prune
```

### Step 6 — Delete the branch (local and remote)
After the worktree is removed, delete the merged feature branch so it does not clutter branch
lists.

**Menu / UI (Git Graph extension)**
1. Open **Git Graph** (Source Control sidebar or Command Palette → **Git Graph: View Git Graph**).
2. Find the merged feature branch (e.g. `feature/math-quiz-dynamic`).
3. **Right-click** the branch → **Delete branch**.
4. Check **Delete remote branch as well** (or equivalent) → confirm.

**Command alternative**
```bash
cd /Users/randytrue/Documents/Code/fof-mono
git branch -d feature/<branch-name>
git push origin --delete feature/<branch-name>
```


## What worktrees are

A worktree is a **second checkout directory** that shares one git repo (same commits,
branches, remotes). Each folder can be on a **different branch**.

Typical layout on this machine:
```
/Users/randytrue/Documents/Code/
  fof-mono/                      ← main checkout (usually on main)
  feature-math-quiz-dynamic/     ← worktree (feature/math-quiz-dynamic)
  feature-hermes-mom-plan/       ← worktree (feature/hermes-mom-plan)
  fof-mono-<other-branch>/       ← worktrees created via git CLI (optional naming)
```

**Rule:** a branch can only be checked out in **one** worktree at a time. Switch the main
checkout to `main` before adding a worktree for a branch that is currently checked out there.

**Menu / UI — see all worktrees**
1. Source Control → scroll to **WORKTREES** — lists every worktree path and branch.

**Command alternative**
```bash
git worktree list
```


## Cursor extension: Worktree Manager

Install once: **Extensions** (`⌘⇧X`) → search **Worktree Manager**
(`iceinveins.worktree-manager`) → **Install**.

What it adds (still valid):
- **WORKTREES** section at the bottom of Source Control — **view** all worktrees and their branches
- **Remove Worktree** — right-click a worktree in WORKTREES (see [Remove a worktree after PR merge](#remove-a-worktree-after-pr-merge-branch-cleanup))
- **Git: Open Worktree in New Window** in the Command Palette — open an existing worktree folder
- May show **both** worktrees in Source Control even when each window has one folder — that
  is normal. Commit only in the block that matches your window’s branch and has an active
  **Commit** button.

**Do not use Worktree Manager to create worktrees** (`+` / Create Worktree). Use
`skills/repo-ops/create-worktree/README.md` instead.

**If `.vscode/settings.json` got replaced** with only title-bar colors: run bootstrap again
(`./scripts/worktree_bootstrap.sh` in the worktree window) — it merges the full file from main
and keeps your worktree title-bar colors. Or discard the stripped file to restore the branch
version from git:

**Menu / UI**
1. In the worktree window: Source Control → **Changes** → click `.vscode/settings.json`.
2. Right-click the file → **Discard Changes** (restores the version from git).

**Command alternative**
```bash
git checkout -- .vscode/settings.json
```


## Bootstrap script

**Script:** `scripts/worktree_bootstrap.sh` (settings merge: `scripts/worktree_copy_settings.py`)

**Default (recommended): shared virtualenv + publish + git hooks** — symlinks `.env` and `.venv` from the
main repo checkout, merges `.vscode/settings.json` from main (preserving worktree title-bar
colors when the create-worktree skill or a prior bootstrap already set them), **copies
`.vscode/tasks.json` from main** (folderOpen task opens a bottom terminal and activates
`.venv`), **checks that pre-commit hooks are installed**
(`core.hooksPath` → `scripts/git/hooks`; installs when missing), and **publishes the current branch to
`origin`** (creates the remote branch and sets upstream, or syncs with an existing remote).
One venv, less disk, less setup, and local/remotes paired for cloud agents. Run **once** per
new worktree (the [create-worktree skill](../skills/repo-ops/create-worktree/README.md) calls
bootstrap automatically).

**Git hooks:** bootstrap verifies `./scripts/git/install-hooks.sh` has been run for this clone
(repo-wide config — not per worktree folder). If hooks are missing, it reports that and either
prompts `[Y/n]` on an interactive terminal or **auto-installs in non-interactive sessions**
(cloud agents should let it install). Pass `--install-hooks` to install without prompting.

**Optional: siloed virtualenv** — separate `.venv` in the worktree; pip installs on that
branch do not touch main’s venv until you merge a requirements update.

**Optional: local-only branch** — pass `--no-publish` to skip push and upstream setup.

**Menu / UI** — in the **worktree** window: Terminal → New Terminal, then:
```bash
./scripts/worktree_bootstrap.sh              # shared venv + publish + hooks check (default)
./scripts/worktree_bootstrap.sh --local-venv   # siloed venv + publish
./scripts/worktree_bootstrap.sh --no-publish   # shared venv, no push
./scripts/worktree_bootstrap.sh --install-hooks  # install hooks without prompting
```

**Command alternative**
```bash
./scripts/worktree_bootstrap.sh                                    # current checkout
./scripts/worktree_bootstrap.sh /path/to/worktree                # explicit path
./scripts/worktree_bootstrap.sh --local-venv                     # current, siloed
./scripts/worktree_bootstrap.sh /path/to/worktree --local-venv   # explicit, siloed
./scripts/worktree_bootstrap.sh --no-publish                     # skip publish
./scripts/worktree_bootstrap.sh /path/to/worktree --no-publish   # explicit, skip publish
```

### Publish vs upstream (Cursor **Publish branch**)

These are related but not identical:

| Term | What it is |
|------|------------|
| **Publish branch** (Cursor UI) | First push of a local branch to GitHub. Creates `origin/<branch>` on the remote. |
| **Set upstream** | Tell Git which remote branch this local branch tracks (`origin/<branch>`). Enables **Sync**, ahead/behind counts, and default `git pull` / `git push` targets. |
| **`git push -u origin <branch>`** | Does both: pushes commits **and** sets upstream in one step. Bootstrap uses this for new branches. |

After bootstrap, `git branch -vv` should show `[origin/feature/<branch>]`. Cursor bottom-left
shows **Sync** instead of **Publish branch**.


## Shared vs siloed virtualenv

| | Shared `.venv` (default) | Siloed `.venv` (`--local-venv`) |
|---|--------------------------|----------------------------------|
| **Setup** | Symlink to `fof-mono/.venv` | `python3 -m venv .venv` + pip install |
| **`pip install` in worktree** | Affects **all** worktrees immediately | Only that worktree |
| **Cursor Python extension** | May warn “invalid interpreter” (real venv path is sibling folder) | Usually works cleanly |
| **Terminal** | `.venv/bin/python` works | `.venv/bin/python` works |
| **When main gets new packages** | Immediately in shared venv; **still commit** `dependencies/requirements_*.txt` in the PR | After PR merges requirements + `pip install` on main |

**Current choice for this monorepo:** shared venv — less overhead while parallel work is
mostly non-overlapping code, not conflicting dependencies. Switch a worktree to
`--local-venv` when a feature branch needs isolated or experimental packages.

**Import guard (mandatory):** bootstrap installs `scripts/python/fof_worktree_import_guard.py`
into the shared venv so nested script launches resolve `apps/` and `core/` from the invoking
checkout. Do **not** reinstall code-bearing editable `fof-mono` on shared venvs. See
`docs/2026-07-31_worktree-shared-venv-editable-import-trap.md`.

**Dependencies source of truth:** git (`dependencies/requirements_2026-07-11.txt`), not venv
state. Always update and commit requirements when adding packages on a feature branch.

### Adding a package to the shared venv (agent policy, 2026-07-31)
Agents may add a new third-party package the task needs without asking, from any checkout — the venv is one physical directory, so the install lands everywhere instantly (no per-worktree action, no deactivate/reactivate; restart long-lived processes that need the new package). Required sequence:
1. Check it isn't already installed: `.venv/bin/python3 -m pip show <pkg>`.
2. Install pinned: `.venv/bin/python3 -m pip install '<pkg>==X.Y.Z'`. Never broad `-U` sweeps. Run `pip install --dry-run` first if resolver fallout is plausible.
3. `.venv/bin/python3 -m pip check` — must be no worse than the pre-existing baseline conflicts.
4. Record the pin the same session: append it to the current dated `dependencies/requirements_*.txt` with a date comment, e.g. `some-package==1.2.3  # added 2026-07-31, feature/foo`, and commit it on the working branch. Cutting a **new** dated requirements file is reserved for version upgrades / resolver events per the playbook in `docs/2026-07-11_openai-httpx-venv-compat.md`.
5. State in the report/PR that a shared-venv-wide package was added.

Still forbidden: installing a **different version** of an already-pinned package, uninstalling or upgrading shared pins outside the playbook, and any `pip install -e .` / `pip install .` of the repo itself (the metadata-only `pip install -e . --no-deps` from the primary checkout is the only exception). If a branch needs conflicting or experimental versions, ask the user about switching that worktree to a siloed venv (`--local-venv` above).


## `.env`, `.gitignore`, and local-only files

| Item | Behavior across worktrees |
|------|---------------------------|
| **`.env`** | Gitignored; **per folder** unless symlinked. Bootstrap symlinks from main — same secrets on one machine. |
| **`.vscode/settings.json`** | Tracked in git; the create-worktree skill applies per-worktree title-bar colors (uncommitted). Bootstrap merges the full file from main and keeps those colors. |
| **`.gitignore`** | **Tracked in git** — each worktree uses the version on **its branch**. Not duplicated per folder. |
| **Local-only files under symlinked roots** (`data/`, `exchanges/`, app `_data/`) | Shared across local worktrees because the worktree path points into `_LOCAL_FILES`. |
| **Other untracked / gitignored files** (`.hermes_sync_state.json`, caches) | Separate per worktree unless explicitly symlinked. Not copied when creating a worktree. |
| **Tracked files** | Come from the branch tip when the worktree is created/updated. |

Do not commit `.env`, real lesson data, or PII. Use gitignored fixture DBs under `data/` as
documented in root `AGENTS.md`.


## Canonical Local Files
Durable local-only files live outside every checkout under:
```bash
/Users/randytrue/Documents/Code/_LOCAL_FILES/fof-mono/
```
Each worktree should expose approved local-file roots as symlinks into that canonical folder.
This keeps local data available in every local Cursor window without putting it in git and
without maintaining separate per-worktree copies.

Mount list (authoritative file): `scripts/local_files_mounts.txt`. Typical mounts:
```text
data/                              -> _LOCAL_FILES/fof-mono/data/
exchanges/                         -> _LOCAL_FILES/fof-mono/exchanges/
_archive/                          -> _LOCAL_FILES/fof-mono/_archive/
logs/                              -> _LOCAL_FILES/fof-mono/logs/
apps/math-quiz/_data/              -> _LOCAL_FILES/fof-mono/apps/math-quiz/_data/
apps/math-quiz/_assets/            -> _LOCAL_FILES/fof-mono/apps/math-quiz/_assets/
apps/minecraft/prism-sync/_data/   -> _LOCAL_FILES/fof-mono/apps/minecraft/prism-sync/_data/
apps/content_studio/_data/         -> _LOCAL_FILES/fof-mono/apps/content_studio/_data/
apps/holodeck/data/                -> _LOCAL_FILES/fof-mono/apps/holodeck/data/
apps/autolearner/data/             -> _LOCAL_FILES/fof-mono/apps/autolearner/data/
apps/voice-router/data/            -> _LOCAL_FILES/fof-mono/apps/voice-router/data/
apps/education/lesson-logger/data/  -> _LOCAL_FILES/fof-mono/apps/education/lesson-logger/data/
```

Rule of thumb: create durable local-only files inside one of these symlinked roots, usually
an app's `_data/` folder. New files created inside a symlinked folder are physically created
in `_LOCAL_FILES` and immediately visible through the same symlink in other worktrees. New
folders created outside a symlinked root remain real folders in that one worktree only.

**Audit / pre-removal / WARN disposition (sole source of truth):**
`skills/repo-ops/local-files-audit/README.md` — run before removing a worktree; also covers
all-worktrees health checks and labels (disposable / move to existing mount / create new mount).

**First-time mount setup on a machine:** `skills/repo-ops/clone-bootstrap/README.md`.

### Explorer graying for symlinked local-file mounts
Cursor / VS Code normally grays ignored files in Explorer using Git file decorations. For
symlinked local-file mount roots, Git may decorate the symlink itself but not every child path
under the symlink. Clone-bootstrap installs a small local extension that reads
`scripts/local_files_mounts.txt` and grays Explorer items under those mounts:

```bash
bash tools/cursor-local-files-decorator/install.sh
```
Then reload the window (`Command Palette → Developer: Reload Window`). Details:
`tools/cursor-local-files-decorator/README.md`.


## Cloud-agent → local worktree workflow

1. Cloud agent creates `feature/<name>`, commits, pushes to GitHub.
2. Locally: follow `skills/repo-ops/create-worktree/README.md` (or ask a Cursor agent to
   create the worktree) — the skill fetches, anchors on `origin/<branch>`, bootstraps, and opens
   a new Cursor window.
3. Do feature work in the **second** window; commit and push from Source Control there.
4. Open PR on GitHub → merge → [Remove a worktree after PR merge](#remove-a-worktree-after-pr-merge-branch-cleanup).

You do **not** re-run bootstrap every session — only when adding a **new** worktree folder.


## Troubleshooting

| Problem | Fix (menu / UI first) |
|---------|------------------------|
| Invalid Python interpreter in Cursor | Dismiss the popup; shared venv still works in Terminal. Or re-bootstrap with `--local-venv`. |
| Two repos in Source Control one window | Normal Worktree Manager behavior; Explorer should still show one root folder per window. |
| WORKTREES section missing | Extensions → confirm **Worktree Manager** is installed and enabled; reload window (`⌘⇧P` → **Developer: Reload Window**). |
| Bottom-left shows **Publish branch** instead of **Sync** | Bootstrap not run yet, or bootstrap was run with `--no-publish`. Run `./scripts/worktree_bootstrap.sh` in the worktree window (or `git push -u origin <branch>` manually). |
| Pre-commit hook not running / commits allow `.sqlite` etc. | Run `./scripts/git/install-hooks.sh` once per clone (or re-run bootstrap — it installs when missing). Verify: `git config core.hooksPath` → `scripts/git/hooks`. |
| Worktree creation / branch anchoring issues | Use `skills/repo-ops/create-worktree/README.md` — do not use Worktree Manager **+** create. |

## Codex local worktrees and Cursor window naming
_see ChatGPT thread in FOF account `Codex Local vs Cloud`_
Here’s a concise block you can paste into worktrees-guide.md. I’m grounding the basic mechanics in Git’s worktree docs, OpenAI’s Codex worktree/local-environment docs, and VS Code’s workspace docs: Git worktrees are separate working directories for one repo; Codex can create local worktrees and run local environment setup scripts; VS Code/Cursor workspaces can be saved as named .code-workspace files.  

Codex local worktrees are useful when an agent needs to work locally but isolated from the main checkout. Use them for tasks that need local build/test access, especially Minecraft/Gradle work where the build artifacts need to land locally.

### Core conventions
* Keep the original checkout at /Users/randytrue/Documents/Code/fof-mono on main most of the time.
* Use the [create-worktree skill](../skills/repo-ops/create-worktree/README.md) for normal human/Cursor feature worktrees.
* Use Codex-created worktrees as temporary agent workspaces unless intentionally creating a permanent worktree.
* Do not rename Codex-created worktree folders manually. Codex may track those exact paths.
* Treat ~/.codex/worktrees/<id>/fof-mono as disposable unless there is active work to preserve.

### Codex local environment
The Codex local environment is project-level configuration. It belongs under the original project root:

/Users/randytrue/Documents/Code/fof-mono/.codex/environments/environment.toml

This file is auto-generated by Codex settings. Do not edit it manually unless necessary. Change setup/cleanup scripts through Codex settings.

Decision made: commit .codex/environments/environment.toml separately from feature work, preferably on main, so it does not get mixed into unrelated app commits.

### Lightweight Codex setup decision
Do not run full `pip install -e .` during every Codex worktree setup. The monorepo has a large legacy dependency tree, and full install can be slow or fail on old packages such as pyobjc.

Use a lightweight setup instead:
* create `.venv` (isolated per Codex worktree — not shared with Cursor worktrees)
* prefer Python 3.11.15 if locally available
* install basic packaging/tooling packages only
* install metadata-only editable: `pip install --no-deps -e .` (no `apps`/`core` mapping)
* run `python scripts/python/install_worktree_import_guard.py`
* for Python tasks, install additional pinned packages only when a missing import proves they are needed
* for Minecraft work, rely mainly on Java/Gradle and shared Gradle caches

### New worktree vs local vs permanent worktree
Use New worktree in Codex when starting a fresh isolated agent task. This creates a new temporary Codex worktree.

Use Local in Codex when pointing the agent at an already-existing folder/worktree.

Use Permanent worktree when the Codex-managed worktree should be reused across sessions.

For long-lived branches, use `skills/repo-ops/create-worktree/README.md`, then open the
worktree in Cursor and use Codex Local if needed.

### Removing failed Codex worktrees
Remove worktrees with Git, not Finder:
```bash
cd /Users/randytrue/Documents/Code/fof-mono
git worktree list
git worktree remove /Users/randytrue/.codex/worktrees/<id>/fof-mono
git worktree prune
```

If setup failed and the worktree only contains disposable generated files:
```bash
git worktree remove --force /Users/randytrue/.codex/worktrees/<id>/fof-mono
git worktree prune
```

### Cursor window naming for Codex worktrees
Codex-created worktrees may open in Cursor with the generic repo name fof-mono, because the final folder is named fof-mono.

To make the window recognizable, save the Cursor window as a named workspace:

1. Open the Codex-created worktree in Cursor.
2. Choose File → Save Workspace As…
3. Save the workspace file in the Codex worktree folder.
4. Use a name like:

Codex - feature-minecraft-mod-build-local.code-workspace

This renames the workspace/window for practical navigation without renaming the Codex worktree folder or changing Git metadata.

Convention adopted: for Codex-created worktrees, use a saved workspace name beginning with Codex -  followed by the branch or task slug.

### Commit hygiene with Codex config files
When Codex creates or updates .codex/environments/environment.toml, do not accidentally stage it with unrelated feature changes.

Recommended flow:
1. Stage and commit only the feature files.
2. Leave .codex/environments/environment.toml unstaged.
3. Switch original checkout back to main.
4. Commit the Codex environment file separately.
5. Continue feature work in a separate worktree window.
