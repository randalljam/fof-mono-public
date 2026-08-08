file: skills/repo-ops/clone-bootstrap/README.md
title: Clone bootstrap
source-github-url: original
source-guide-url: original
history:
  - 2026-07-31 · Randy · Cursor [Permanent worktree import fix](permanent_worktree_import_fix) — primary venv setup uses metadata-only editable + import guard; never `pip install -e .` from shared worktrees
  - 2026-07-30 · Randy · Cursor [local-files-audit skill](a382ac41-327f-4a1d-acf2-960cc34a1971) — point WARN ignored-file review at local-files-audit (setup stays here)
  - 2026-07-02 · TL · Cursor — document per-machine `FOF_MONO_LOCAL_FILES_ROOT`; detect wrong default before mount check
  - 2026-06-30 · Randy · Cursor [Clone Bootstrap Skill](original) — global branch tracking as default; approval prompt with --local follow-up; sole doc for git config (removed from worktrees guide)
  - 2026-06-30 · Randy · Cursor [Clone Bootstrap Skill](original) — repo-local branch tracking config and approval-prompt wording for global fallback
  - 2026-06-30 · Randy · Cursor [Clone Bootstrap Skill](original) — added machine, user, repo, and branch metadata to bootstrap report
  - 2026-06-30 · Randy · Cursor [Clone Bootstrap Skill](original) — required audit-style bootstrap reporting
  - 2026-06-30 · Randy · Cursor [Clone Bootstrap Skill](original) — added global branch tracking config and Cursor extension setup
  - 2026-06-30 · Randy · Cursor [Clone Bootstrap Skill](original) — created repo clone readiness workflow for hooks and local files

**Use this skill after cloning `fof-mono`, or when a collaborator asks an agent to make sure their clone has the required repo-level setup.**


## When to use
- A collaborator has a fresh clone and needs the repo's local setup checked.
- The user says to run the clone bootstrap, clone setup, repo setup, hooks setup, local-files setup, or canonical local folders setup.
- Before a first commit in a clone, especially if the pre-commit large-file guard may not be installed.


## What it checks
- **One-time git branch tracking config (global)** — new local branches should auto-publish and branch switches should auto-link to matching remotes. Set once per developer machine via `~/.gitconfig`.
- **Git hooks** — `core.hooksPath` must be `scripts/git/hooks`, so the tracked pre-commit hook can block session DBs, media, archives, binaries, and new files over 512 KB.
- **Per-machine local-files root** — `FOF_MONO_LOCAL_FILES_ROOT` must point at **this developer's** canonical `_LOCAL_FILES/fof-mono` directory. Scripts default to the repo owner's path when unset; that default is not valid on other machines.
- **Canonical local files** — configured local-only roots in `scripts/local_files_mounts.txt` should be symlinks into `$FOF_MONO_LOCAL_FILES_ROOT` (each mount's subdirectory, e.g. `.../data`, `.../exchanges`).
- **Ignored files outside mounts** — if the checker emits `WARN: ignored`, follow `skills/repo-ops/local-files-audit/README.md` for disposition (this skill only sets up mounts; it is not the audit procedure).
- **Cursor Worktree Manager** — the editor should have `iceinveins.worktree-manager` installed for the Source Control `WORKTREES` UI.
- **Cursor Explorer local-files decoration** — symlinked local-only mount children should appear gray in Explorer via `tools/cursor-local-files-decorator/`.


## Run
From the repo root, verify the clone path:
```bash
git rev-parse --show-toplevel
git branch --show-current
```

Capture report metadata for the final audit response:
```bash
date '+%Y-%m-%d %H:%M:%S %Z'
hostname
whoami
git config user.name || true
git config user.email || true
git rev-parse --show-toplevel
git branch --show-current
git rev-parse --git-common-dir
```

Install one-time branch tracking defaults for this developer machine:
```bash
git config --global push.autoSetupRemote true
git config --global branch.autoSetupMerge always
git config --global push.autoSetupRemote
git config --global branch.autoSetupMerge
```
Expected final output:
```text
true
always
```

**Approval prompt** (when the harness asks the user to click Run on the global config command):
give exactly this message (two brief sentences, then decline/accept guidance, then local
fallback):

> This sets Git so the first push on a new branch auto-creates `origin/<same-name>` and sets
> upstream, and checkout of a branch whose remote twin exists auto-links upstream. The change
> applies globally on this machine (`~/.gitconfig`) to every Git repo, not just `fof-mono`.
>
> If you are an experienced developer who prefers manual `git push -u`, declining is fine and
> expected. If you are newer to Git on this project, we recommend you accept and run.
>
> If you prefer repo-only settings instead, tell the agent to execute the 2 git config changes
> with `--local` instead of `--global` as a follow-up.

If the user declines the global command, note it in the bootstrap report under **Needs
attention** and offer the `--local` follow-up verbatim above. Do not re-prompt for global
unless the user asks.

Install hooks when missing:
```bash
git config core.hooksPath || true
./scripts/git/install-hooks.sh
git config core.hooksPath
```
Expected final output:
```text
scripts/git/hooks
```

Resolve the per-machine local-files root before mount checks. Scripts read
`FOF_MONO_LOCAL_FILES_ROOT` when set; otherwise they fall back to a hardcoded default in
`scripts/local_files_check.py` and `scripts/local_files_mount.sh` (the repo owner's machine
path — not valid on other developers' machines).

Detect what the checker will use:
```bash
echo "FOF_MONO_LOCAL_FILES_ROOT=${FOF_MONO_LOCAL_FILES_ROOT:-(unset)}"
whoami
git rev-parse --show-toplevel
```

If `FOF_MONO_LOCAL_FILES_ROOT` is unset, infer this developer's root. Common layout:
`_LOCAL_FILES/fof-mono` sits beside the clone (same parent directory as the repo), i.e.
`<parent-of-repo>/_LOCAL_FILES/fof-mono` — e.g. repo at `/Users/<whoami>/Code/fof-mono`
means root `/Users/<whoami>/Code/_LOCAL_FILES/fof-mono`. Confirm with the user when
inference is unclear. The most reliable signal is an existing mount symlink that already
points at a valid directory on this machine: strip the mount subdirectory from its target
(e.g. drop the trailing `/data`) and use the remaining `.../_LOCAL_FILES/fof-mono` path as
the root.

When the env var is missing or wrong, persist it in the developer's shell profile (bash:
`~/.bash_profile` or `~/.bashrc`; zsh: `~/.zshrc`):
```bash
export FOF_MONO_LOCAL_FILES_ROOT="/Users/<whoami>/Code/_LOCAL_FILES/fof-mono"
```
Replace the path with the confirmed root for this machine. After editing the profile, source
it in the current session (`source ~/.bash_profile` or equivalent) before continuing.

Check local-file mounts in dry-run mode (uses `FOF_MONO_LOCAL_FILES_ROOT` when exported):
```bash
.venv/bin/python3 scripts/local_files_check.py --ignored-limit 999
```

If dry-run shows `FIX` rows that relink every mount to another user's home directory (e.g.
`/Users/randytrue/...`), **stop** — `FOF_MONO_LOCAL_FILES_ROOT` is unset or wrong. Set the
env var for this machine and re-run dry-run before `--apply`.

If the output has only `OK`, `FIX`, `BACKUP`, `WARN`, or `DETAIL` rows and no `BLOCK`, apply safe mount repairs:
```bash
.venv/bin/python3 scripts/local_files_check.py --apply --ignored-limit 999
```

Then re-run dry-run mode:
```bash
.venv/bin/python3 scripts/local_files_check.py --ignored-limit 999
```

Install Cursor Worktree Manager if the `cursor` CLI is available:
```bash
cursor --install-extension iceinveins.worktree-manager
```
If the CLI is unavailable, tell the user to install it manually:
```text
Extensions -> search Worktree Manager -> install iceinveins.worktree-manager
```

Install the local Cursor Explorer decorator so files and folders under symlinked local-only mounts are grayed out:
```bash
bash tools/cursor-local-files-decorator/install.sh
```
Expected output includes:
```text
Installed: ~/.cursor/extensions/fof-local-files-decorator -> <repo>/tools/cursor-local-files-decorator
```
Then tell the user to reload Cursor:
```text
Command Palette -> Developer: Reload Window
```


## Decision rules
- Set `push.autoSetupRemote` and `branch.autoSetupMerge` with `--global` when either is missing or
  wrong. Use the approval prompt above when the harness requires user confirmation. If the user
  declines global, offer `--local` as a follow-up (same two keys, from the repo root). If hooks
  are missing, run `./scripts/git/install-hooks.sh` without asking; this is required clone setup.
- Before local-files checks, ensure `FOF_MONO_LOCAL_FILES_ROOT` is set to this machine's
  `_LOCAL_FILES/fof-mono` directory. If unset, infer from existing mount symlinks or ask the
  user, then add `export FOF_MONO_LOCAL_FILES_ROOT=...` to their shell profile. Do not run
  `--apply` while dry-run wants to relink all mounts to another user's home path.
- If `.venv/bin/python3` is missing, stop and report that the project virtualenv must be created in the **primary checkout** via `README_external.md` (requirements + `pip install -e . --no-deps` + `scripts/python/install_worktree_import_guard.py`), or linked via worktree bootstrap.
- If local-files output includes `BLOCK`, stop and summarize the conflicting worktree, mount path, and detail rows. Do not run `--apply` until the user resolves or approves a resolution.
- If local-files output includes `WARN: ignored`, stop treating that as bootstrap setup work — hand off to `skills/repo-ops/local-files-audit/README.md` (classify and act only with user approval). The checker’s `--apply` here only repairs configured mount points.
- If `cursor` is on PATH, run `cursor --install-extension iceinveins.worktree-manager` without asking. If it is not on PATH or the command fails, report the manual install path.
- If `tools/cursor-local-files-decorator/install.sh` is present, run it without asking; it only creates or refreshes the owned extension symlink. If it refuses to replace a non-symlink path, stop and report the exact path.
- Use `--worktree <path>` only when the user asks to check one checkout instead of all worktrees in the clone.


## Reporting back
Give a concise audit-style report that can be copied into notes or reviewed by a senior engineer. Separate what was already in effect from what this run changed. Include final proof values or key command output lines, not vague claims.

Use this shape:
```text
Clone bootstrap report
Date/time: <local date/time with timezone>
Machine: <hostname>
Local shell user: <whoami>
Git user: <git config user.name> <<git config user.email>>
Repo: <git rev-parse --show-toplevel>
Branch/worktree run from: <git branch --show-current>
Git common dir: <git rev-parse --git-common-dir>

Already installed / already in effect:
- <item>: <proof value or key output>

Installed / changed during this run:
- <item>: <command run and resulting proof value or key output>

Needs attention:
- <item>: <exact blocker, WARN path, manual install step, or remaining command>
```

Include these items in the report:
- Global git branch tracking config and final values for `push.autoSetupRemote` and
  `branch.autoSetupMerge` (or note if the user declined global and whether `--local` was applied).
- Git hooks and final `core.hooksPath` value.
- `FOF_MONO_LOCAL_FILES_ROOT` — final value, whether it was already set, and whether it was
  added to the developer's shell profile during this run.
- Local-files mount status: all `OK`, repaired with `--apply`, or blocked.
- Any `WARN` paths outside configured mounts and whether they need user review.
- Cursor Worktree Manager status: already installed, installed by CLI, or manual installation needed.
- Cursor local-files decorator status: already installed, installed/refreshed, or blocked; remind the user to reload Cursor before Explorer colors update.
- The exact command that remains to be run, if setup could not be completed.
