# FOF Mono

## Description

Monorepo for Focus on Foundations applications and shared Python tooling: file processing, transcription, LLM integration, RAG, and related tasks.

## Installation

### 1. Clone the Repository
Start by cloning this repository to your local machine. You can do this using the following command in your terminal or command prompt:

```
git clone https://github.com/FocusOnFoundationsNonprofit/fof-mono
```

### 2. Install Python and Pip
Make sure you have Python and pip (Python package installer) installed on your system. You can download Python from the official website (https://www.python.org/) and pip is usually included in Python 3.4 and later versions.

### 3. Create a Virtual Environment (primary checkout only)
Required. Navigate to the primary `fof-mono` checkout's root directory and create a virtual environment named ".venv" (Python 3.12):

```
python3 -m venv .venv
source .venv/bin/activate
```

Local worktrees do not get their own venv — they symlink this one (see step 6). Cloud agent sessions are unrelated: each works in its own fresh clone with its own isolated venv, so nothing is shared.

### 4. Install dependencies and import guard (primary checkout only)
While in the project's root directory with the virtual environment activated, run:

```
pip install -r dependencies/requirements_2026-07-11.txt
pip install -e . --no-deps
python3 scripts/python/install_worktree_import_guard.py
```

Run these **only in the primary `fof-mono` checkout**. Worktrees symlink the shared `.venv`.

Yes, `pip install -e . --no-deps` is still part of primary-checkout setup after the 2026-07-31 fix, and it is safe: `setup.py` is now metadata-only — it records dependency pins for `pip check` but installs **no code** (`apps/` and `core/` are never mapped into site-packages, so the venv can no longer redirect imports to one checkout). The import guard prepends the invoking checkout root at Python startup, so each checkout imports its own code.

**Do not run `pip install -e .` (any form) from a shared-venv worktree** — it rewrites venv metadata for every checkout. See `docs/2026-07-31_worktree-shared-venv-editable-import-trap.md`.

### 5. Delete and Restart Virtual Environment
Only needed for a full dependency reset (e.g. broken or badly drifted packages) — it was NOT needed for the 2026-07-31 import fix, which was applied to the live venv in place. Run only in the primary checkout; the worktree symlinks keep working unchanged because the venv path stays the same. Restart any long-lived Python processes (e.g. the Holodeck server) afterward.

```
deactivate
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r dependencies/requirements_2026-07-11.txt
pip install -e . --no-deps
python3 scripts/python/install_worktree_import_guard.py
```

### 6. Local Worktrees
This section covers the **local worktree setup on a single machine** (multiple git worktrees under `Documents/Code/*`, all sharing one venv). Local worktrees require **no** Python setup: each worktree's `.venv` is a symlink to the primary checkout's `.venv`, and the import guard makes every checkout import its own `apps/` and `core/` automatically. Never run `pip install -e .` (or any install of the repo itself) from a local worktree; adding pinned third-party packages is allowed from any checkout — it installs into the single shared venv, available everywhere instantly — per the policy in `docs/worktrees-guide.md` → "Adding a package to the shared venv". To create a worktree, use skill `skills/repo-ops/create-worktree/README.md` (runs `scripts/worktree_bootstrap.sh`, which verifies the import guard).

Cloud agents (Claude Code web, Codex cloud) do not use this setup: each cloud session clones the repo fresh into an ephemeral container and builds its own isolated venv (Codex: `.codex/environments/environment.toml`), so the shared-venv rules above don't apply there — but the branch rules in `AGENTS.md` always do.

Sanity check from any local worktree:

```
.venv/bin/python3 scripts/python/diagnose_worktree_imports.py
```
