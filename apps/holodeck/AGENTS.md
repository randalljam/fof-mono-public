file: apps/holodeck/AGENTS.md
title: Holodeck — agent instructions
last-updated: 2026-07-28_0620
ai: Cursor - Claude Fable 5


## turns.db backups (mandatory)
`apps/holodeck/data/turns.db` is an important compiled artifact (sessions, exchanges, digests, commit links). Treat it as fragile: a bad agent edit can destroy a good state.

**Before any mutation of `turns.db`** (SQL edits, relabel scripts, purge, schema experiments, or a rebuild you are unsure about), take a timestamped backup:

```bash
.venv/bin/python3 apps/holodeck/turns_cli.py backup --reason "short why"
```

Backups land in `apps/holodeck/data/backups/turns_YYYY-MM-DD_HHMMSS.db` (gitignored under `data/`). An optional `.reason.txt` sits beside the file. Older backups are pruned (keep last 20).

`turns_cli.py build` auto-backups first unless `--no-backup`.

Restore the newest backup, or a named one:

```bash
.venv/bin/python3 apps/holodeck/turns_cli.py restore
.venv/bin/python3 apps/holodeck/turns_cli.py restore --backup apps/holodeck/data/backups/turns_YYYY-MM-DD_HHMMSS.db
```

`restore` safety-backs up the current `turns.db` before overwriting.

Helpers: `apps/holodeck/turns/backup.py`. Do not skip backup because a change “looks small.”


## Related docs
- App overview / operator runbook: `apps/holodeck/README.md`
- AI session sources and label rules: `apps/holodeck/AI-SESSIONS.md`
