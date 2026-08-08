file: skills/family/push-to-another-local-computer/README.md
title: Push to another local computer
source-github-url: original
source-guide-url: original
history:
  - 2026-08-07 · Randy · Cursor [Public-safe computer push skill](2026-08-07_public-safe_computer_push_skill_d08d31e9) — move live hosts to local-only TOML; ship synthetic example only
  - 2026-08-03 · Randy · Cursor [Push to another local computer](0b7f8723-d005-437a-9ab4-22f707c48ceb) — initial skill; first destination verified over SSH


**Push files from this machine to another Mac on the LAN over SSH/rsync.**

Use when an agent (or you) wants to copy files onto another registered host — especially into that machine's `_LOCAL_FILES/fof-mono` tree ("push local files").


## When to use
- User says **push to another local computer**, **push local files** to a named Mac, or similar.
- Need to drop a file/folder onto a remote `_LOCAL_FILES` mount root without committing it to git.
- Destination is on the local network and already has SSH key access.


## Private computer registry
Real hostnames, usernames, aliases, and destination paths stay **out of this skill**.

| Layer | Path | Purpose |
|-------|------|---------|
| Script config (machine-readable) | `docs/personal/push-computers.toml` (default) | Loaded by the script |
| Human inventory | `docs/personal/computer-info.md` | Admin notes for this repo |
| Public template | `skills/family/push-to-another-local-computer/references/computers.example.toml` | Placeholder only |

Setup:
1. Copy the example TOML to `docs/personal/push-computers.toml` (or any private path).
2. Fill in real `id` / `aliases` / `ssh` / absolute `primary_checkout` and `local_files_root` values.
3. Optionally set `FOF_PUSH_COMPUTERS_CONFIG` or pass `--config` if the file is not at the default path.

`docs/personal/` is gitignored and excluded from the public snapshot — do not put live values in tracked skill files.


## Destination shortcuts

| User says | Meaning |
|-----------|---------|
| **push local files** (to a named computer) | Destination root = that computer's `FOF_MONO_LOCAL_FILES_ROOT` / `_LOCAL_FILES/fof-mono` |
| **push to primary checkout** | Destination root = that computer's primary `fof-mono` clone |
| explicit remote path | Use that absolute path on the remote machine |

Under either shortcut, the user may also give a **relative path** under that root (e.g. `data/ai-coding/notes/`). Relative paths must not be absolute and must not contain `..`.


## Procedure
1. **Identify target computer** — match the user's name/alias against the private registry (`--list-computers`). If paths are missing, discover over SSH and update the private TOML (and human inventory) before transferring.
2. **Identify destination** — "local files" → `local_files_root`; or absolute `--dest-dir`; optional relative subpath via `--rel`.
3. **Identify source(s)** — local absolute paths on the machine running the agent. Confirm they exist.
4. **Confirm with the user** before any real write — state computer, SSH target, each source, and the full remote destination in plain language.
5. **Dry-run first**, then execute:
   ```bash
   .venv/bin/python3 skills/family/push-to-another-local-computer/scripts/push_to_computer.py \
     --computer target-laptop --local-files --rel 'data/ai-coding/notes' \
     /path/to/local/file.md
   ```
   Re-run the same command with `--execute` after the user approves.
6. **Report** — reachable yes/no, dry-run vs execute, remote destination, and rsync exit status. Do not claim success if rsync failed.


## Script
```bash
# List known computers from the private registry
.venv/bin/python3 skills/family/push-to-another-local-computer/scripts/push_to_computer.py --list-computers
```

Examples (synthetic names/paths — replace with your registry values):
```bash
# Dry-run: push a file into a remote local-files tree
.venv/bin/python3 skills/family/push-to-another-local-computer/scripts/push_to_computer.py \
  --computer target-laptop --local-files --rel 'data/ai-coding/notes' \
  /Users/your-user/Documents/Code/_LOCAL_FILES/fof-mono/data/ai-coding/notes/example.md

# Real transfer (only after user approval)
.venv/bin/python3 skills/family/push-to-another-local-computer/scripts/push_to_computer.py \
  --computer target-laptop --local-files --rel 'data/ai-coding/notes' \
  /Users/your-user/Documents/Code/_LOCAL_FILES/fof-mono/data/ai-coding/notes/example.md \
  --execute

# Explicit remote directory
.venv/bin/python3 skills/family/push-to-another-local-computer/scripts/push_to_computer.py \
  --computer target-laptop \
  --dest-dir '/Users/your-user/Code/_LOCAL_FILES/fof-mono/data/ai-coding/notes' \
  ./some-file.md --execute

# Custom config path
.venv/bin/python3 skills/family/push-to-another-local-computer/scripts/push_to_computer.py \
  --config /path/to/push-computers.toml --list-computers
```

Notes:
- Default is **dry-run**. Real writes require `--execute`.
- Uses `rsync -avh` over SSH with `BatchMode=yes`.
- Directory sources: a trailing `/` on the source copies *contents* into the dest; without it, rsync creates a named subdirectory. Prefer being explicit in the confirm step.
- Stdlib only; needs `ssh` and `rsync` on PATH.


## Safety
- **Confirm before `--execute`.** State source → remote destination clearly.
- **Do not push secrets** (`.env`, credentials, private keys) unless the user explicitly names them and confirms.
- **Do not invent remote paths.** If `local_files_root` is unknown for a computer, discover or ask — do not guess.
- Prefer pushing into **local-files**, not into a git working tree, unless the user asked for the primary checkout.
- Keep live host/user/path data in the private registry only.


## Related
- `apps/minecraft/prism-sync/` — similar LAN SSH/rsync pattern (different payload; private `computers.toml` + public `computers.example.toml`).
- `skills/repo-ops/clone-bootstrap/README.md` — per-machine `FOF_MONO_LOCAL_FILES_ROOT` setup.
- `skills/repo-ops/local-files-audit/README.md` — auditing local-only files on a checkout.
