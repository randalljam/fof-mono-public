file: skills/ai/migrate-cursor-ai-sessions/README.md
title: Migrate Cursor AI sessions across a worktree rename
source-github-url: original
source-guide-url: original
history:
  - 2026-08-06 · Randy · Cursor [Migrate Cursor AI sessions](migrate-cursor-ai-sessions) — workspace-ID discover/remap + dual-bind fix; one-off repair_export_public_workspace_id.py
  - 2026-08-06 · Randy · Cursor [Migrate Cursor AI sessions](migrate-cursor-ai-sessions) — preflight prompts to kill Holodeck/other DB openers, rechecks until clear; never kills Cursor itself
  - 2026-08-06 · Randy · Cursor [Migrate Cursor AI sessions](migrate-cursor-ai-sessions) — gate distinguishes Holodeck/other state.vscdb openers from Cursor; clearer kill guidance
  - 2026-08-06 · Randy · Cursor [Migrate Cursor AI sessions](migrate-cursor-ai-sessions) — hard Cursor-closed PID gate (--check-cursor); agent handoff ends with copy-paste Terminal execute command
  - 2026-08-06 · Randy · Cursor [Migrate Cursor AI sessions](migrate-cursor-ai-sessions) — tilde ~/ path rewrite + lsof Cursor-open check; live dry-run validated on state.vscdb copy
  - 2026-08-06 · Randy · Cursor [Migrate Cursor AI sessions](migrate-cursor-ai-sessions) — initial skill: dry-run DB copy, backups, logs, projects + workspaceStorage retarget


Migrate Cursor Agent/Chat session bindings when a local worktree folder is renamed or moved (for example `.../Code/flex` → `.../Code/export-public`). Cursor keys project data by absolute path **and** by a `workspaceStorage` hash (`composerHeaders.workspaceId`), so a renamed worktree usually opens with blank history unless both are retargeted.


## Critical lesson (why history looked empty)
Path rewrite + transcript copy is not enough. If you open the renamed folder before remapping, Cursor creates a **new** workspace hash. The UI binds to that empty hash while chats remain on the old hash → blank Agent history.

Required fix: remap `composerHeaders.workspaceId` from the old hash → the new hash Cursor assigned after the first open of the renamed folder.


## Correct workflow (next time)
1. Close the source worktree window (other Cursor windows may stay open for now).
2. Rename/move the worktree on disk (`flex` → `export-public`).
3. Open the **new** folder once in Cursor. Expect empty AI history — that open creates the new workspace ID.
4. Close that new worktree window.
5. Discover IDs (read-only; Cursor may still be open elsewhere):

```bash
/Users/randytrue/Documents/Code/fof-mono/.venv/bin/python3 \
  /Users/randytrue/Documents/Code/fof-mono/skills/ai/migrate-cursor-ai-sessions/scripts/migrate_cursor_ai_sessions.py \
  --source-worktree /Users/randytrue/Documents/Code/flex \
  --target-worktree /Users/randytrue/Documents/Code/export-public \
  --since 2026-07-01 \
  --discover-workspace-ids
```

6. Copy the printed `--execute` command (includes `--source-workspace-id` / `--target-workspace-id`).
7. Quit Cursor completely (Cmd+Q). Stop Holodeck if prompted (`--check-cursor` / execute gate will offer `kill`).
8. Paste/run the execute command in **Terminal.app**.
9. Reopen Cursor on the new worktree and confirm history.

`--execute` refuses unless both workspace IDs are known (or you pass `--skip-workspace-id-remap`, which you should not for a normal rename).


## When to use
- Renaming/moving a git worktree and keeping prior Cursor AI sessions in the new window.
- Need a Terminal script that runs with Cursor closed for live DB writes.
- Dry-run that copies `state.vscdb`, applies changes on the copy, and reviews.


## What it migrates
| Store | Path | Action |
|-------|------|--------|
| Agent transcripts | `~/.cursor/projects/<worktree-token>/agent-transcripts/` | Rename project folder, or copy selected transcript dirs when `--since` / target already exists |
| Workspace binding | `.../workspaceStorage/<hash>/workspace.json` | Retarget only if target has no workspace yet; skips retarget when that would dual-bind the same folder URI |
| Composer workspace id | `composerHeaders.workspaceId` in `state.vscdb` | Remap old hash → new hash (required for sidebar history) |
| Global chat DB paths | `state.vscdb` | Rewrite source path / URI / project-token / `~/...` strings |


## Safety model
1. Default is dry-run (live files untouched).
2. `--execute` runs the Cursor/Holodeck closed-gate (`ps` + `pgrep` + `lsof`). Non-Cursor DB openers (often Holodeck on `127.0.0.1:8790`) are identified and you are prompted to `kill` them; Cursor itself is never auto-killed.
3. Live runs backup `state.vscdb` under `~/.cursor/ai-session-migrate/backups/` first.
4. Logs + JSON summaries under `~/.cursor/ai-session-migrate/logs/`.
5. End-of-run backup prune prompt (keep newest).


## One-off repair (flex → export-public blank history, 2026-08-06)
If path rewrite already ran but history is still empty because of dual workspace hashes, use:

`skills/ai/migrate-cursor-ai-sessions/scripts/repair_export_public_workspace_id.py`

Defaults:
- source `2a796caeaa48812ed7d2446c2e1d7c15`
- target `13d8b44d4ba89c651f0ddd8ee58b3323`

Dry-run:

```bash
/Users/randytrue/Documents/Code/fof-mono/.venv/bin/python3 \
  /Users/randytrue/Documents/Code/fof-mono/skills/ai/migrate-cursor-ai-sessions/scripts/repair_export_public_workspace_id.py
```

Live repair (quit Cursor + Holodeck first):

```bash
/Users/randytrue/Documents/Code/fof-mono/.venv/bin/python3 \
  /Users/randytrue/Documents/Code/fof-mono/skills/ai/migrate-cursor-ai-sessions/scripts/repair_export_public_workspace_id.py \
  --execute \
  --yes
```

This creates a new backup `state.vscdb.backup-before-repair.<stamp>` and does **not** modify the earlier `backup-before-execute` file except via the optional prune prompt at the end (decline prune if you want to keep every backup).


## Preflight: confirm Cursor + Holodeck closed
```bash
/Users/randytrue/Documents/Code/fof-mono/.venv/bin/python3 \
  /Users/randytrue/Documents/Code/fof-mono/skills/ai/migrate-cursor-ai-sessions/scripts/migrate_cursor_ai_sessions.py \
  --check-cursor
```

Need `CURSOR_RUNNING=no` before `--execute` / repair `--execute`.


## Useful flags
| Flag | Meaning |
|------|---------|
| `--discover-workspace-ids` | Print source/target workspace hashes + copy-paste execute command |
| `--source-workspace-id` / `--target-workspace-id` | Explicit hashes for remap |
| `--check-cursor` | Detect Cursor/Holodeck DB openers; optional kill prompt |
| `--since YYYY-MM-DD` | Filter which transcript dirs are copied |
| `--execute` | Live changes; requires closed gate + workspace IDs |
| `--skip-workspace-id-remap` | Skip hash remap (not recommended for renames) |
| `--yes` | Non-interactive confirmations |
| `--force` | DANGEROUS bypass of closed-gate |


## Outputs
```text
~/.cursor/ai-session-migrate/
  backups/   state.vscdb.backup-before-*.<stamp>
  dry-run/   state.vscdb.dry-run.<stamp>
  logs/      migrate-cursor-ai-sessions_<mode>_<stamp>.log|.summary.json
             repair_export_public_workspace_id_<mode>_<stamp>.log|.summary.json
```


## Verification (mock)
```bash
.venv/bin/python3 skills/ai/migrate-cursor-ai-sessions/eval/test_migrate_cursor_ai_sessions.py
```


## Related
- `skills/ai/access-cursor-chat/` — read/format transcripts and model metadata from `state.vscdb`.
