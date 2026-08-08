"""Timestamped backups for turns.db before agent/human mutations."""

import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    from apps.holodeck.turns import db
except ImportError:
    from turns import db

BACKUP_DIR_NAME = "backups"
DEFAULT_KEEP = 20
PACIFIC = ZoneInfo("America/Los_Angeles")

### Paths
def backup_dir(db_path=None):
    path = Path(db_path or db.default_db_path())
    return path.parent / BACKUP_DIR_NAME
def backup_name(prefix="turns", when=None):
    stamp = (when or datetime.now(PACIFIC)).strftime("%Y-%m-%d_%H%M%S")
    return f"{prefix}_{stamp}.db"

### Backup / restore
def backup_turns_db(db_path=None, reason=None, keep=DEFAULT_KEEP, when=None):
    """Copy turns.db to data/backups/turns_YYYY-MM-DD_HHMMSS.db. Returns backup Path or None if missing."""
    source = Path(db_path or db.default_db_path())
    if not source.exists():
        return None
    dest_dir = backup_dir(source)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / backup_name(when=when)
    shutil.copy2(source, dest)
    # Also copy WAL/SHM if present so a hot backup stays consistent enough for rollback.
    for suffix in ("-wal", "-shm"):
        side = Path(str(source) + suffix)
        if side.exists():
            shutil.copy2(side, Path(str(dest) + suffix))
    prune_backups(dest_dir, keep=keep)
    note_path = dest.with_suffix(dest.suffix + ".reason.txt")
    if reason:
        note_path.write_text(str(reason).strip() + "\n", encoding="utf-8")
    return dest
def list_backups(db_path=None):
    dest_dir = backup_dir(db_path)
    if not dest_dir.exists():
        return []
    return sorted(dest_dir.glob("turns_*.db"), key=lambda item: item.stat().st_mtime, reverse=True)
def latest_backup(db_path=None):
    items = list_backups(db_path)
    return items[0] if items else None
def prune_backups(dest_dir, keep=DEFAULT_KEEP):
    keep = max(int(keep or 0), 0)
    if keep == 0:
        return 0
    items = sorted(Path(dest_dir).glob("turns_*.db"), key=lambda item: item.stat().st_mtime, reverse=True)
    removed = 0
    for stale in items[keep:]:
        for path in (stale, Path(str(stale) + "-wal"), Path(str(stale) + "-shm"), Path(str(stale) + ".reason.txt")):
            if path.exists():
                path.unlink()
        removed += 1
    return removed
def restore_turns_db(backup_path, db_path=None):
    """Restore turns.db from a backup file. Makes a safety backup of the current DB first."""
    backup = Path(backup_path)
    if not backup.exists():
        raise FileNotFoundError(str(backup))
    target = Path(db_path or db.default_db_path())
    if target.exists():
        backup_turns_db(target, reason="pre-restore safety copy of current turns.db")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup, target)
    for suffix in ("-wal", "-shm"):
        side = Path(str(backup) + suffix)
        dest_side = Path(str(target) + suffix)
        if side.exists():
            shutil.copy2(side, dest_side)
        elif dest_side.exists():
            dest_side.unlink()
    return target
