#!/usr/bin/env python3
# SQLite store for confirmed homeschool lessons — the queryable layer behind the
# per-lesson JSON session files. `save_lesson.py` writes a JSON file AND upserts
# here (write-through), so the DB stays current as each lesson lands; `ingest`
# re-scans the dir to backfill / re-sync. Stdlib only (runs on the Hermes image).
#
# DB path: $HERMES_LESSONS_DB, else <lesson-logs dir>/lessons.db
# Usage:
#   python3 lessons_db.py ingest [--log-dir DIR] [--db PATH]   # upsert every JSON file
#   python3 lessons_db.py summary [--db PATH]                  # minutes by student + subject
import argparse
import glob
import json
import os
import sqlite3
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

### Config
PACIFIC = ZoneInfo("America/Los_Angeles")
SCHEMA_VERSION = 2
SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id                TEXT PRIMARY KEY,
    date              TEXT NOT NULL,            -- YYYY-MM-DD
    time              TEXT,                     -- display, e.g. '6:30 PM'
    students          TEXT,                     -- JSON array
    teachers          TEXT,                     -- JSON array
    subject           TEXT,
    curricula         TEXT,
    duration          INTEGER,                 -- minutes
    location          TEXT,
    notes             TEXT,
    transcript        TEXT NOT NULL,
    created_by        TEXT,
    created_at        TEXT NOT NULL,            -- ISO 8601
    extractor_version TEXT,
    raw_extraction    TEXT CHECK (raw_extraction IS NULL OR json_valid(raw_extraction)),
    source_file       TEXT,
    ingested_at       TEXT NOT NULL             -- ISO 8601 when the row was written/updated
);
CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(date);
CREATE INDEX IF NOT EXISTS idx_entries_subject ON entries(subject);
"""
### Paths
def default_log_dir():
    """Where the JSON session files live (agent volume, not the repo)."""
    env = os.environ.get("HERMES_LESSON_LOG_DIR")
    if env:
        return env
    home = os.environ.get("HERMES_HOME") or os.path.join(os.path.expanduser("~"), ".hermes")
    return os.path.join(home, "lesson-logs")
def default_db_path():
    return os.environ.get("HERMES_LESSONS_DB") or os.path.join(default_log_dir(), "lessons.db")

### DB
def connect(db_path=None):
    """Open (creating if needed) the lessons DB with schema applied."""
    path = db_path or default_db_path()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    _migrate(conn)
    return conn
def _migrate(conn):
    """Apply schema migrations. Forward-only; tracked via PRAGMA user_version."""
    ver = conn.execute("PRAGMA user_version").fetchone()[0]
    if ver < 1:
        conn.executescript(SCHEMA)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    elif ver < SCHEMA_VERSION:
        pass
    conn.commit()
def upsert_entry(conn, entry, source_file=None, raw_extraction=None, now=None):
    """Insert-or-replace an entry (keyed by id). Idempotent."""
    now = now or datetime.now(PACIFIC)
    conn.execute(
        "INSERT OR REPLACE INTO entries"
        " (id, date, time, students, teachers, subject, curricula, duration,"
        "  location, notes, transcript, created_by, created_at, extractor_version,"
        "  raw_extraction, source_file, ingested_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            entry["id"],
            entry["date"],
            entry.get("time", ""),
            json.dumps(entry.get("students", []), ensure_ascii=False),
            json.dumps(entry.get("teachers", []), ensure_ascii=False),
            entry.get("subject", ""),
            entry.get("curricula", ""),
            int(entry.get("duration", 0)),
            entry.get("location", ""),
            entry.get("notes", ""),
            entry.get("transcript", ""),
            entry.get("createdBy", ""),
            entry.get("createdAt", ""),
            entry.get("extractorVersion", ""),
            json.dumps(raw_extraction, ensure_ascii=False) if raw_extraction else None,
            source_file,
            now.isoformat(),
        ),
    )
    conn.commit()
    return entry["id"]

### Ingest / query
def ingest_dir(log_dir=None, db_path=None):
    """Upsert every *.json lesson file in log_dir into the DB; returns count."""
    log_dir = log_dir or default_log_dir()
    conn = connect(db_path)
    n = 0
    for path in sorted(glob.glob(os.path.join(log_dir, "*.json"))):
        try:
            entry = json.load(open(path))
        except (ValueError, OSError) as exc:
            print(f"skip (unreadable: {exc}): {path}", file=sys.stderr)
            continue
        if "id" not in entry:
            print(f"skip (no id): {path}", file=sys.stderr)
            continue
        upsert_entry(conn, entry, source_file=path)
        n += 1
    conn.close()
    return n
def summary(db_path=None):
    """Rows of (student, subject, total_minutes, lesson_count)."""
    conn = connect(db_path)
    rows = conn.execute(
        "SELECT j.value AS student, e.subject, SUM(e.duration), COUNT(*)"
        " FROM entries e, json_each(e.students) j"
        " GROUP BY j.value, e.subject ORDER BY j.value, e.subject"
    ).fetchall()
    conn.close()
    return rows

### CLI
def main():
    parser = argparse.ArgumentParser(description="Lessons SQLite store: ingest JSON session files / summarize.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    ip = sub.add_parser("ingest", help="Upsert all JSON session files into the DB.")
    ip.add_argument("--log-dir")
    ip.add_argument("--db")
    sp = sub.add_parser("summary", help="Print minutes by student + subject.")
    sp.add_argument("--db")
    args = parser.parse_args()
    if args.cmd == "ingest":
        n = ingest_dir(args.log_dir, args.db)
        print(f"Ingested/updated {n} lesson file(s) into {args.db or default_db_path()}")
    elif args.cmd == "summary":
        for student, subject, mins, n in summary(args.db):
            print(f"{student:12} {subject:10} {mins:5} min  ({n} lessons)")
if __name__ == "__main__":
    main()
