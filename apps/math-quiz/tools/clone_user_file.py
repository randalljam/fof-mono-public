#!/usr/bin/env python3
"""
file: apps/math-quiz/tools/clone_user_file.py
title: Clone one learner's per-person .sqlite file as another user (testing utility)

Copies the SOURCE user's latest per-person file in a _data folder to a new file for
the TARGET user, renaming the user everywhere inside (Users.name, every table with a
user_name column, and the name embedded in Sessions.session_filename) and in the
filename itself. The replacement is prepared and validated before any existing target
file(s) are replaced — with a confirmation prompt unless --force is given.

Use case: make your own file an exact copy of a kid's live file so you can run any
mode as yourself against their data without touching their file. The source file is
never modified.

Usage (from apps/math-quiz/):
  python3 tools/clone_user_file.py <folder> <source_user> <target_user> [--force]

Examples:
  python3 tools/clone_user_file.py tlkids Kid1 Randy            # prompts if a Randy file exists
  python3 tools/clone_user_file.py tlkids Kid1 Randy --force    # deletes Randy's file without asking
"""
import argparse
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anchor_store  # noqa: E402

APP_DIR = Path(__file__).resolve().parent.parent   # apps/math-quiz
DATA_DIR = APP_DIR / "_data"

### Helpers: filenames
def _data_folder(folder):
    """Resolve one CLI folder under _data, rejecting traversal and symlink escapes."""
    root = DATA_DIR.resolve()
    candidate = (DATA_DIR / str(folder or "")).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate if candidate != root else None
def files_for_user(folder_dir, user, prefix=anchor_store.PREFIX):
    """Every .sqlite in folder_dir whose filename-encoded learner name == user.
    Public: dev_server's /api/clone-user-file snapshots these before the clone."""
    out = []
    for fn, _mod in anchor_store.local_entries(folder_dir):
        p = anchor_store.parse_filename(fn, prefix=prefix)
        if p and p["name"] == user:
            out.append(fn)
    return sorted(out)
def _renamed_filename(source_filename, target_user, prefix=anchor_store.PREFIX):
    """The source filename with its learner-name field swapped for target_user
    (rebuilt through the canonical naming helpers, not a string replace)."""
    p = anchor_store.parse_filename(source_filename, prefix=prefix)
    if p is None:
        raise ValueError(f"unrecognized filename: {source_filename}")
    if not p["multi"]:
        return anchor_store.single_session_name(target_user, f"{p['date']}_{p['time']}", prefix=prefix)
    return anchor_store.multi_session_name(target_user, p["date"], p["suffix"], prefix=prefix)

### Helpers: in-file rename
def _tables_with_column(conn, column):
    """Names of user tables that have the given column."""
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    return [t for t in tables if column in {row[1] for row in conn.execute(f'PRAGMA table_info("{t}")')}]
def rename_user_in_db(path, source_user, target_user):
    """Rewrite source_user -> target_user everywhere in the .sqlite at path: Users.name,
    every table with a user_name column, and the learner name embedded in
    Sessions.session_filename. Any pre-existing rows already under target_user are
    deleted first so primary keys (e.g. Profile.user_name) cannot collide.
    Returns {table: rows_renamed}."""
    conn = sqlite3.connect(str(path))
    changed = {}
    try:
        for table in _tables_with_column(conn, "user_name"):
            conn.execute(f'DELETE FROM "{table}" WHERE user_name = ?', (target_user,))
            cur = conn.execute(f'UPDATE "{table}" SET user_name = ? WHERE user_name = ?',
                               (target_user, source_user))
            if cur.rowcount:
                changed[table] = cur.rowcount
        for table in _tables_with_column(conn, "name"):
            if table != "Users":
                continue
            conn.execute("DELETE FROM Users WHERE name = ?", (target_user,))
            cur = conn.execute("UPDATE Users SET name = ? WHERE name = ?", (target_user, source_user))
            if cur.rowcount:
                changed["Users"] = cur.rowcount
        if "Sessions" in _tables_with_column(conn, "session_filename"):
            # REPLACE is a no-op on rows that don't contain the token, so no WHERE needed.
            conn.execute("UPDATE Sessions SET session_filename = REPLACE(session_filename, ?, ?)",
                         (f"_{source_user}_", f"_{target_user}_"))
        conn.commit()
    finally:
        conn.close()
    return changed

### Main operation
def clone_user_file(folder_dir, source_user, target_user, force=False, prompt=input,
                    source_filename=None):
    """Clone source_user's latest per-person file in folder_dir as target_user.
    When source_filename is given, clone that exact top-level file instead of the latest.
    Prepares the replacement before removing older target files; when force is False and
    any targets exist, calls prompt() and aborts unless the answer starts with 'y'. The
    source file is read-only throughout. Returns {ok, source_file, new_file, deleted,
    tables} or {ok: False, error}."""
    folder_dir = Path(folder_dir)
    if source_user == target_user:
        return {"ok": False, "error": "source and target user are the same"}
    source_fn = None
    if source_filename:
        candidate = Path(str(source_filename)).name
        parsed = anchor_store.parse_filename(candidate)
        if parsed and parsed["name"] == source_user and (folder_dir / candidate).is_file():
            source_fn = candidate
        else:
            return {"ok": False, "error": f"source file not found for '{source_user}': {candidate}"}
    else:
        source_fn = anchor_store.pick_latest(anchor_store.local_entries(folder_dir), source_user)
    if not source_fn:
        return {"ok": False, "error": f"no file found for source user '{source_user}' in {folder_dir}"}
    existing = files_for_user(folder_dir, target_user)
    if existing and not force:
        listing = ", ".join(existing)
        answer = prompt(f"Delete {len(existing)} existing file(s) for '{target_user}' ({listing})? [y/N] ")
        if not str(answer).strip().lower().startswith("y"):
            return {"ok": False, "error": "aborted by user (existing target file kept)"}
    new_fn = _renamed_filename(source_fn, target_user)
    # Prepare and validate the clone before replacing any target data. Keeping the
    # temporary file in this folder makes the final replace atomic on one filesystem.
    temp_handle = tempfile.NamedTemporaryFile(
        prefix=f".{new_fn}.", suffix=".tmp", dir=folder_dir, delete=False)
    temp_path = Path(temp_handle.name)
    temp_handle.close()
    try:
        shutil.copyfile(folder_dir / source_fn, temp_path)
        tables = rename_user_in_db(temp_path, source_user, target_user)
        temp_path.replace(folder_dir / new_fn)
        for fn in existing:
            if fn != new_fn:
                (folder_dir / fn).unlink()
    finally:
        temp_path.unlink(missing_ok=True)
    return {"ok": True, "source_file": source_fn, "new_file": new_fn,
            "deleted": existing, "tables": tables}

### CLI
def _main():
    ap = argparse.ArgumentParser(
        description="Clone one learner's latest per-person .sqlite as another user (for testing). "
                    "The source file is never modified; the target user's existing file(s) are deleted.")
    ap.add_argument("folder", help="_data subfolder holding the files (e.g. tlkids, real, test)")
    ap.add_argument("source_user", help="learner whose file to clone (e.g. Kid1)")
    ap.add_argument("target_user", help="user name for the clone (e.g. Randy)")
    ap.add_argument("--force", action="store_true",
                    help="delete the target user's existing file(s) without prompting")
    args = ap.parse_args()
    folder_dir = _data_folder(args.folder)
    if folder_dir is None or not folder_dir.is_dir():
        print(f"Folder not found or outside _data: {args.folder}")
        sys.exit(2)
    r = clone_user_file(folder_dir, args.source_user, args.target_user, force=args.force)
    if not r["ok"]:
        print(f"Error: {r['error']}")
        sys.exit(1)
    for fn in r["deleted"]:
        print(f"Deleted: {fn}")
    print(f"Cloned:  {r['source_file']} -> {r['new_file']}")
    renamed = ", ".join(f"{t} ({n})" for t, n in sorted(r["tables"].items())) or "none"
    print(f"Renamed '{args.source_user}' -> '{args.target_user}' in: {renamed}")

if __name__ == "__main__":
    _main()
