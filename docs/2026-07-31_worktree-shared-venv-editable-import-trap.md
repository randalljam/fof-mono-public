file: docs/2026-07-31_worktree-shared-venv-editable-import-trap.md
title: Worktree shared-venv editable install can silently import primary-checkout code
last-updated: 2026-07-31_0745
ai: Cursor - GPT-5.6 Sol
session: `Permanent worktree import fix`

Implementation plan: [Permanent worktree import fix](.cursor/plans/permanent_worktree_import_fix_bcc1ba37.plan.md)

**Worktree shared-venv editable import trap**

Discovered 2026-07-31 while adding Holodeck branch “last merge from main” collection on worktree `/Users/randytrue/Documents/Code/holodeck` (branch `holodeck-next`). Refresh appeared to run, but new collector fields never appeared in `snapshot.json`. Root cause was not “the worktree venv is broken”; it was a silent import of `apps.*` from the primary checkout via the shared editable install.


## Symptom
Holodeck UI refresh updated timestamps, but new Python collector fields added only on the feature worktree were missing from `apps/holodeck/data/snapshot.json`.

Concrete case:
- Worktree code in `holodeck` had `last_merge_from_main` in `apps/holodeck/collectors/branches.py`.
- Primary checkout `fof-mono` (on `main`) did not.
- After `POST /api/refresh` / `python apps/holodeck/collect.py --layer branches`, snapshot branches had **no** `last_merge_from_main` key.
- Calling the new helper **directly** inside the worktree (importing that worktree’s module) returned correct merge dates.

So the UI/JS from the worktree was live, but the collect subprocess was executing **primary-checkout** collector code.


## Environment that makes this possible
Standard local setup (intentional and still desirable):
- Many git worktrees under `Documents/Code/*`.
- Each worktree’s `.venv` is a **symlink** to the primary checkout’s venv, e.g. `holodeck/.venv` → `fof-mono/.venv`.
- That shared venv has an **editable install** of the monorepo package `fof-mono`, created roughly 2026-07-23:

```text
.venv/lib/python3.12/site-packages/__editable__.fof_mono-1.0.pth
→ installs finder that maps:
  apps → /Users/randytrue/Documents/Code/fof-mono/apps
  core → /Users/randytrue/Documents/Code/fof-mono/core
```

`direct_url.json` records: `file:///Users/randytrue/Documents/Code/fof-mono`.

Sharing the venv across worktrees is fine. Pinning editable `apps`/`core` to the **primary working tree path** is the hazard.


## Root cause
Python package resolution order:
1. Find `apps` on `sys.path` (normally the **current worktree root** when cwd is that worktree).
2. If that fails, the editable meta-path finder returns **`fof-mono/apps`**.

### Why most day-to-day work looked fine
These entrypoints put the worktree root on `sys.path` (often as `''`):
- Holodeck server / uvicorn started from the worktree
- `python -c 'import apps…'` from the worktree root
- pytest from the worktree root
- `python -m apps.holodeck…` from the worktree root

For those, PathFinder finds `./apps` in **this** worktree first. Editable never wins. Edits to `apps/` and `core/` in the worktree behave as expected. That matches long-standing experience on `holodeck-start`, `holodeck/swing-v2`, etc.

### The failing entrypoint
Holodeck refresh ran collect as a **script path**:

```bash
.venv/bin/python3 apps/holodeck/collect.py
# server equivalent: subprocess [sys.executable, str(HOLODECK_DIR / "collect.py"), ...]
```

For a script invocation, `sys.path[0]` becomes the script’s directory:

```text
…/holodeck/apps/holodeck
```

That directory is **not** a parent of the top-level `apps` package. PathFinder cannot find `apps` there. The editable finder then supplies `fof-mono/apps`.

`collect.py` was written with a try/except that assumed “script mode” would fall back to local imports:

```python
try:
    from apps.holodeck.collectors import branches as branches_collector
except ImportError:
    from collectors import branches as branches_collector  # same folder as the script
```

With the editable install present, the `try` **succeeds** — but against the **primary checkout**, not the worktree. The `except` path (correct for script-dir execution) never runs.

### Why this looked “new” on holodeck-next
Nothing about the symlink-venv layout newly broke on this branch. The footgun was already there whenever collect was launched as a script from a secondary worktree.

It became obvious only when:
1. New collector logic existed **only** on the feature worktree (`last_merge_from_main`).
2. Primary `fof-mono` working tree stayed on `main` without that logic.
3. UI refresh depended on the collect subprocess, which silently used primary code.

Earlier Holodeck branches often exercised UI/server/static paths (worktree wins), or collector changes had already landed on `main` / matched the primary tree after merge — so the wrong import was invisible.


## Proof commands (reproduced on 2026-07-31)
From the `holodeck` worktree:

```bash
# A — normal import (worktree wins)
.venv/bin/python3 -c "import apps.holodeck.collectors.branches as b; print(b.__file__)"
# → …/holodeck/apps/holodeck/collectors/branches.py

# B — script-path style (editable / primary wins) before fix
.venv/bin/python3 -v apps/holodeck/collect.py --layer branches 2>&1 | rg 'collectors/branches'
# → loaded …/fof-mono/apps/holodeck/collectors/branches.py
```

Also confirmed: editable mapping is hardcoded to primary paths in `__editable___fof_mono_1_0_finder.py` (`MAPPING['apps']`, `MAPPING['core']`).


## What must not be the “fix”
Do **not** re-point the editable install at the current feature worktree (`holodeck`, etc.). That would invert the bug for every other worktree still sharing the same venv.

Do **not** “fix” this only by remembering to restart the Holodeck server. Collect runs in a **subprocess**; stale in-memory server imports were not the primary failure mode here.


## Recommended fix (for second opinion / apply on primary)
Goal: **never silently execute another worktree’s `apps`/`core`**. Prefer ImportError over wrong code.

### Preferred: remove the repo editable install from the shared venv
On the primary checkout (where the real `.venv` lives):

```bash
cd /Users/randytrue/Documents/Code/fof-mono
.venv/bin/python3 -m pip uninstall -y fof-mono
# confirm gone:
ls .venv/lib/python3.12/site-packages/__editable__.fof_mono* 2>/dev/null || echo 'editable removed'
.venv/bin/python3 -c "import apps"  # from a random directory should fail
```

Then rely on worktree-root-on-`sys.path` for all real work:
- always start processes with cwd = the worktree you mean, or
- set `PYTHONPATH=<that-worktree-root>`, or
- use `python -m …` from that root

After removal, the old `collect.py` script invocation should hit `ImportError` on `apps.holodeck…` and fall through to `from collectors import …`, which loads **the script’s own worktree files**. That is fail-closed / worktree-correct behavior.

Update docs that still say `pip install -e .` / `pip install --no-deps -e .` for routine worktree setup (e.g. `docs/worktrees-guide.md`, Codex lightweight setup notes) so agents do not reinstall the trap.

### Optional hardening (keep even if editable is removed)
1. Holodeck collect bootstrap: insert this checkout’s repo root at `sys.path[0]` before importing `apps.*` (bandage already drafted on `holodeck-next`).
2. Prefer `python -m apps.holodeck.collect` over `python apps/holodeck/collect.py` for server refresh subprocesses.
3. Startup assert in Holodeck collect/server: imported `apps.holodeck` path must be under `repo_root()`; otherwise exit with a loud error naming both paths.

Bandages (1)–(2) are useful; they are not a substitute for removing the editable map if the policy is “never use primary `apps`/`core` from another worktree.”


## Verification after the primary fix
From a **secondary** worktree (e.g. `holodeck`):

```bash
cd /Users/randytrue/Documents/Code/holodeck

# Must resolve into THIS worktree
.venv/bin/python3 -c "import apps, core; import apps.holodeck.collectors.branches as b; print(apps.__file__); print(core.__file__); print(b.__file__)"

# Script collect must not load fof-mono collectors
.venv/bin/python3 -v apps/holodeck/collect.py --layer branches 2>&1 | rg 'collectors/branches'

# From a directory that is not a checkout root, import should fail (desired)
cd /tmp && /Users/randytrue/Documents/Code/fof-mono/.venv/bin/python3 -c "import apps"
```

From primary `fof-mono`, same checks with paths under `fof-mono`.


## Propagation notes
- The editable metadata lives in the **shared** venv under primary `fof-mono/.venv`. Uninstall once there; every worktree that symlinks `.venv` → that venv picks it up automatically.
- No need to re-point each worktree’s editable install.
- After uninstall, restart long-lived processes (Holodeck server, etc.) in each window so they do not keep old imported modules in memory.
- Re-run Holodeck refresh on the feature worktree and confirm new collector fields appear in that worktree’s `apps/holodeck/data/snapshot.json`.
- If any tool/docs re-run `pip install -e .` against primary, the trap returns; treat that as a regression.


## Related local bandages on holodeck-next (not yet the global policy fix)
As of this write-up, `holodeck-next` contains defensive changes so Holodeck collect/refresh prefers the current checkout even while the editable install still exists:
- `apps/holodeck/collect.py` — pin repo root on `sys.path` before `apps.*` imports
- `apps/holodeck/server.py` — refresh via `python -m apps.holodeck.collect`

Those should be reviewed together with the primary editable-uninstall decision; they may remain as belt-and-suspenders after uninstall.


## Final policy (2026-07-31)
Adopted after second opinion:
1. **Remove code-bearing editable `fof-mono`** from the shared venv. Keep dependency metadata via metadata-only `setup.py` (`pip install -e . --no-deps` installs pins, not `apps`/`core`).
2. **Auto-detect invoking worktree** via a venv startup hook (`scripts/python/fof_worktree_import_guard.py` installed through a `.pth` file). The hook prepends the checkout root inferred from the real script path or cwd.
3. **Holodeck belt-and-suspenders** — pin repo root before `apps.*` imports in `collect.py` and `server.py`; refresh subprocess uses `python -m apps.holodeck.collect`.
4. **Do not re-point editable** at feature worktrees. Isolated Codex worktree venvs may still use `--no-deps -e .` locally; that is safe because each venv is not shared.

### Additional vulnerability (direct `server.py` launch)
On `holodeck-next` before the full fix, `server.py` imported `apps.holodeck.*` **before** inserting `ROOT` on `sys.path`. Running `python apps/holodeck/server.py` could load primary-checkout modules even when cwd was the feature worktree. Uvicorn/`python -m` paths were less affected. The permanent fix moves root selection ahead of all `apps.*` imports.


## Verification checklist (post-fix)
Run from each worktree (shared venv):
```bash
.venv/bin/python3 scripts/python/diagnose_worktree_imports.py
.venv/bin/python3 -v apps/holodeck/collect.py --list 2>&1 | rg 'holodeck/collect|fof-mono/apps/holodeck/collect'
```
From `/tmp`, `import apps` should fail unless `PYTHONPATH` is set.

Verified 2026-07-31 on this machine: all nine worktrees resolve `core.llm` from their own checkout; Holodeck-bearing worktrees pass nested `collect.py --list`; guard check passes on shared venv; `/tmp` import of `apps` fails closed.


## Docs/bootstrap paths updated
- `README_external.md`, `setup.py` comments — primary checkout only for full venv create
- `docs/worktrees-guide.md` — no routine `pip install -e .` on worktrees; shared venv + import guard
- `scripts/worktree_bootstrap.sh` — installs/verifies import guard after venv setup
- `skills/repo-ops/clone-bootstrap/README.md`, `skills/repo-ops/create-worktree/README.md`
- `docs/2026-07-11_openai-httpx-venv-compat.md` — metadata-only editable note
- `AGENTS.md` Python rules — never `pip install -e .` from a shared-venv worktree

## Fable5 Review and Verification
Push confirmed (2d7b93b..aec012a main -> main). Here's the full review.

Review verdict: the fix is correct and genuinely verified â I found and fixed one small defect

### I independently re-verified everything rather than trusting the report:
- Shared venv state: the code-bearing editable install is gone. A __editable___fof_mono_1_0_finder.py file still exists (regenerated by the metadata-only reinstall), but its mapping is empty (MAPPING = {}), so it cannot redirect imports anywhere â harmless, and the installer's --check correctly distinguishes this from the hazardous version. Worth knowing so you're not alarmed if you see that file.
- All 9 checkouts (fof-mono + 8 worktrees, all symlinking fof-mono/.venv): import core resolves to each worktree's own core/__init__.py. Verified live, per worktree.
- The exact originally-failing case â running collect.py as a script from the holodeck worktree â now loads /Users/randytrue/Documents/Code/holodeck/apps/holodeck/collectors/branches.py, not fof-mono's copy. Confirmed with python -v module tracing.
- Fail-closed behavior: import apps from /tmp raises ModuleNotFoundError as designed.
- Tests: 10/10 pass (I re-ran both suites myself).
- Design soundness: even if someone accidentally reinstalls the bad editable mapping later, the guard still wins â Python consults sys.path (where the guard prepends your checkout) before the editable finder. Real belt-and-suspenders.

Defect found and fixed: worktree_bootstrap.sh executes install_worktree_import_guard.py directly, but both new scripts were committed without the execute bit â the next bootstrap run would have died with "Permission denied" at exactly the guard-install step. I added +x, verified direct invocation works, committed and pushed (aec012a).

One correction to the agent's report: it said "nothing committed yet," but the work now sits on main as 4 clean stepwise commits, already pushed. Presumably committed after that message â just so you know main and origin are in sync.

### TLDR: what actually happened, in plain terms
The problem. Back when the venv was set up, pip install -e . was run. That writes a note inside the venv saying "the packages apps and core live at /Users/.../fof-mono" â a hardcoded absolute path to the primary checkout. Since all worktrees share that venv, every worktree carried that note around.

Normally it didn't matter: when you run Python from a worktree's root, Python looks in your current folder first, finds the worktree's own apps/ and core/, and never consults the note. That's why you never saw this before.

The trap springs on one specific invocation style: running a script by file path, like python apps/holodeck/collect.py (which is exactly how the Holodeck server launched its refresh subprocess). In that mode, Python puts the script's folder (apps/holodeck/) first on its search path â not the repo root. The search for apps fails there, so Python falls back to the venv's note and silently loads the primary fof-mono checkout's code instead of your worktree's. No error, no warning â your edits just don't run. That's why the refresh "worked" but your new fields never appeared.

### The permanent fix, three layers:
1. Defused the venv. setup.py is now metadata-only â it records the dependency list but installs zero code, so the shared venv can never again point imports at one particular checkout. If nothing supplies a repo root, you now get a loud ImportError instead of silently wrong code.
2. The import guard â a tiny module installed into the venv that runs at every Python startup. It figures out which checkout you're actually invoking from (from the script's location, or failing that your current directory) and puts that checkout's root first on the import path. Result: each worktree always imports its own code, regardless of invocation style.
3. Holodeck hardening â collect.py and server.py pin their own repo root before any imports, refresh uses the safe python -m form, and the server refuses to start if its modules somehow resolved outside its own checkout.

Your two operator to-dos (from the agent's notes, still valid): restart any long-running Holodeck servers in open Cursor windows, and remember the new rule â never run pip install -e . from a worktree (AGENTS.md and the docs now say this, and the guard's --check will catch it if it happens).

Crunched for 5m 10s

### recap:
Reviewed the shared-venv worktree import fix: it's correct and verified across all 9 worktrees, and I fixed one missing execute-bit defect (committed and pushed). Next action: restart any long-running Holodeck servers so they pick up the fix. (disable recaps in /config)

### Operator runbook — exact per-worktree steps (2026-07-31)
The venv repair was a one-time central fix to the shared `.venv` in the primary `fof-mono` checkout. Because all 8 secondary worktrees symlink that venv, they are all already protected. There is nothing venv-related to do per worktree:
- Do **not** delete or recreate any `.venv`.
- Do **not** deactivate/reactivate — activation only affects your shell prompt and PATH. The import guard lives in the venv's `site-packages` and loads automatically in every newly started Python process, activated or not.
- No `pip install` was needed anywhere for this repair. (Ongoing policy for adding packages later: `docs/worktrees-guide.md` → "Adding a package to the shared venv".)

**Step 1 — restart stale long-lived processes (do this first).** Any Python process launched before the repair (~06:30 on 2026-07-31) still holds the old import behavior in memory. In each Cursor window running a Holodeck server: Ctrl+C and relaunch as usual. Every process started after the repair is automatically safe.

**Step 2 — commit the dirty doc edits on `main`** (this runbook, `README_external.md`, `README_internal.md`, `AGENTS.md`), so the merges in Step 3 carry the final documents to each branch.

**Step 3 — merge main into each worktree (recommended; any order).** Not required for import safety — the shared venv protects branches even without the new code. Merging is what brings each branch the new scripts (`scripts/python/diagnose_worktree_imports.py`, installer), the hardened Holodeck files, and updated docs/AGENTS.md.

Branch worktrees (`dragon-baby`, `fof-website`, `holodeck`):
```bash
cd /Users/randytrue/Documents/Code/<worktree>
git fetch origin
git merge origin/main
git push
```
- `dragon-baby/finish-100`: the merge done earlier on 2026-07-31 (`5c49141`) landed **before** the fix commits — merge again.
- `holodeck-next`: expect conflicts in exactly three files (verified by merge dry run): `apps/holodeck/collect.py`, `apps/holodeck/server.py`, and this doc. In all three, **take main's version** — the branch's copies are the early bandages/draft that main superseded (verified: the branch's only changes to those files since fork are the bandages; its real feature work in `collectors/branches.py` merges cleanly on its own):
```bash
git checkout --theirs apps/holodeck/collect.py apps/holodeck/server.py docs/2026-07-31_worktree-shared-venv-editable-import-trap.md
git add apps/holodeck/collect.py apps/holodeck/server.py docs/2026-07-31_worktree-shared-venv-editable-import-trap.md
git commit
git push
```

Detached-HEAD worktrees (`deutsch`, `flex`, `math-quiz`, `minecraft`, `stellar-transcriber`) are parked on a commit, not a branch. If `git status` is clean, re-park on the new main:
```bash
cd /Users/randytrue/Documents/Code/<worktree>
git fetch origin
git switch --detach origin/main
```

**Step 4 — optional per-worktree sanity check.** After a worktree has the new code:
```bash
.venv/bin/python3 scripts/python/diagnose_worktree_imports.py
```
Expected: `branches under checkout: True` and `nested collect --list: OK`. For a worktree that has not merged main yet (script not present there), use the one-liner instead:
```bash
.venv/bin/python3 -c "import core; print(core.__file__)"
```
It must print a path inside **that** worktree.

**Order of operations:** server restarts first (Step 1); everything else in any order. The merges have no dependency on the venv fix — it is already live everywhere.

