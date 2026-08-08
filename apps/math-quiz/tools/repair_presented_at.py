#!/usr/bin/env python3
"""
file: apps/math-quiz/tools/repair_presented_at.py
title: Backfill presented_at into accumulated per-person files from the single-session captures

A bug in anchor_store.append_session dropped the per-attempt `presented_at` column whenever an
accumulated per-person file's schema predated it (the append used the intersection of columns).
That column is fixed going forward, but files already accumulated still have null presented_at,
so the analysis page shows the session start time for every attempt instead of the per-problem
wall-clock time.

This repairs existing files NON-destructively: it reads the archived single-session captures
(which DO have presented_at), matches rows by `problem_id` (`<start>-<index>`, unique per
attempt), and fills in the missing presented_at on the accumulated files. Nothing else is
touched (flag edits etc. are preserved). Dry-run by default; pass --execute to write (a .bak
copy is made first).

Usage (from apps/math-quiz):
    python3 tools/repair_presented_at.py --folder tlkids                 # preview
    python3 tools/repair_presented_at.py --folder tlkids --execute       # apply
    python3 tools/repair_presented_at.py --file _data/tlkids/math-flu_K1_2026-06-21.sqlite --execute
"""
import os
import sys
import shutil
import sqlite3
import argparse
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = APP_DIR / os.environ.get("ANCHOR_DATA_DIR", "_data")
SINGLE_SESSION_DIR = "_single-session-sqlite-files"

def _table_exists(conn, t):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None
def _cols(conn, t):
    return [r[1] for r in conn.execute(f"PRAGMA table_info({t})")]
def build_presented_at_map(singles_dir):
    """{problem_id: presented_at} gathered from every single-session capture in singles_dir
    (a Path). Rows without a problem_id or presented_at are skipped; later files win ties."""
    singles_dir = Path(singles_dir)
    out = {}
    if not singles_dir.exists():
        return out
    for p in sorted(singles_dir.glob("*.sqlite")):
        try:
            c = sqlite3.connect(str(p))
        except Exception:
            continue
        try:
            if not _table_exists(c, "ProblemAttempts"):
                continue
            cols = set(_cols(c, "ProblemAttempts"))
            if "problem_id" not in cols or "presented_at" not in cols:
                continue
            for pid, at in c.execute("SELECT problem_id, presented_at FROM ProblemAttempts"):
                if pid and at:
                    out[pid] = at
        except Exception:
            pass
        finally:
            c.close()
    return out
def backfill_file(path, pa_map, execute=False):
    """Fill missing presented_at on one accumulated .sqlite using pa_map (problem_id->presented_at).
    Only rows whose presented_at IS NULL and whose problem_id is known are updated. Returns
    {file, total, already, filled, still_missing}. Writes (with a .bak) only when execute=True."""
    path = Path(path)
    c = sqlite3.connect(str(path))
    try:
        if not _table_exists(c, "ProblemAttempts"):
            return {"file": path.name, "total": 0, "already": 0, "filled": 0, "still_missing": 0, "skipped": "no-table"}
        cols = set(_cols(c, "ProblemAttempts"))
        rows = c.execute(
            "SELECT problem_id, presented_at FROM ProblemAttempts" if "presented_at" in cols
            else "SELECT problem_id, NULL FROM ProblemAttempts").fetchall()
        total = len(rows)
        already = sum(1 for _, at in rows if at)
        to_fill = [(pid, pa_map[pid]) for pid, at in rows if (not at) and pid in pa_map]
        still_missing = sum(1 for pid, at in rows if (not at) and pid not in pa_map)
        if execute and (to_fill or "presented_at" not in cols):
            shutil.copyfile(path, str(path) + ".bak")
            if "presented_at" not in cols:
                c.execute("ALTER TABLE ProblemAttempts ADD COLUMN presented_at TEXT")
            for pid, at in to_fill:
                c.execute("UPDATE ProblemAttempts SET presented_at = ? WHERE problem_id = ? AND presented_at IS NULL",
                          (at, pid))
            c.commit()
        return {"file": path.name, "total": total, "already": already, "filled": len(to_fill),
                "still_missing": still_missing}
    finally:
        c.close()

### CLI
def _accumulated_files(folder_dir):
    """Per-person .sqlite files directly under _data/<folder> (not the test subfolders)."""
    folder_dir = Path(folder_dir)
    return sorted(p for p in folder_dir.glob("*.sqlite")) if folder_dir.exists() else []
def main(argv=None):
    ap = argparse.ArgumentParser(description="Backfill presented_at into accumulated per-person files.")
    ap.add_argument("--folder", default=None, help="repair every accumulated file in _data/<folder>")
    ap.add_argument("--file", default=None, help="repair a single accumulated .sqlite (path)")
    ap.add_argument("--singles", default=None, help=f"single-session captures dir (default _data/{SINGLE_SESSION_DIR})")
    ap.add_argument("--data-dir", default=None, help="override _data/ root")
    ap.add_argument("--execute", action="store_true", help="write changes (default: dry-run preview)")
    args = ap.parse_args(argv)
    data_dir = Path(args.data_dir) if args.data_dir else DATA_DIR
    singles = Path(args.singles) if args.singles else (data_dir / SINGLE_SESSION_DIR)
    pa_map = build_presented_at_map(singles)
    print(f"single-session captures: {singles}  ({len(pa_map)} problem_id->presented_at entries)")
    if not args.folder and not args.file:
        ap.error("pass --folder <name> or --file <path>")
    targets = [Path(args.file)] if args.file else _accumulated_files(data_dir / args.folder)
    if not targets:
        print("no accumulated files found.")
        return 0
    grand = 0
    for t in targets:
        r = backfill_file(t, pa_map, execute=args.execute)
        grand += r.get("filled", 0)
        print(f"  {r['file']}: total {r['total']}, already {r['already']}, "
              f"{'filled' if args.execute else 'fillable'} {r['filled']}, no-capture {r['still_missing']}"
              + (r.get('skipped') and f" [skipped: {r['skipped']}]" or ""))
    tag = "filled" if args.execute else "fillable (dry run — pass --execute to write)"
    print(f"{grand} attempt(s) {tag}.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
