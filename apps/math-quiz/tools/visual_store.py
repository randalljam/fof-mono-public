#!/usr/bin/env python3
"""
file: apps/math-quiz/tools/visual_store.py
title: Manage visual-practice config in math-quiz SQLite files

Stores a per-learner visual-practice config IN the per-user .sqlite file (the
same file "Use internal" runs and the quiz appends to), read/written exactly like
the internal problem lists. One row per user in a VisualPracticeConfig table:
  - targets        (JSON array of fact strings, e.g. ["8+3","4+9",...]; up to 5)
  - filler         (JSON array of fact strings — secure facts used between targets)
  - fast_ms / retrievals_to_clear / hesitation_ms (the practice parameters)
"""
import argparse
import json
import re
import sqlite3
from datetime import datetime

_FACT_RE = re.compile(r"^\s*(-?\d+)\s*([+\-*/xX×÷−])\s*(-?\d+)\s*$")

### Helpers: parsing / normalizing facts
def _normalize_operation(op):
    """Normalize a display operator to the canonical problem_text operator."""
    if op in ('x', 'X', '×', '*'):
        return '*'
    if op in ('−', '-'):
        return '-'
    if op in ('÷', '/'):
        return '/'
    return '+'
def normalize_fact(text, spaced=False):
    """Normalized problem form from a typed string, or None.

    Whitespace around the operator is accepted on input. `spaced=False` returns the
    compact form ("3+6", used for the small target fields); `spaced=True` returns the
    problem-list form with a space on each side ("3 + 6", used for the filler list).
    Orientation is preserved (6+0 stays 6+0); blanks/unparseable return None.
    """
    m = _FACT_RE.match(str(text or ''))
    if not m:
        return None
    n1, op, n2 = int(m.group(1)), _normalize_operation(m.group(2)), int(m.group(3))
    return f"{n1} {op} {n2}" if spaced else f"{n1}{op}{n2}"
def normalize_facts(items, spaced=False):
    """Normalize a list of problem strings (or a newline-joined text block), dropping
    blanks/unparseable. Targets/filler are stored as these normalized strings."""
    if isinstance(items, str):
        items = items.splitlines()
    out = []
    for it in (items or []):
        norm = normalize_fact(it, spaced=spaced)
        if norm is not None:
            out.append(norm)
    return out

### Helpers: sqlite
def connect(path):
    """Open a math-quiz .sqlite with row access by column name."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
def ensure_visual_schema(conn):
    """Create the VisualPracticeConfig table if absent (one row per user)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS VisualPracticeConfig (
            user_name TEXT PRIMARY KEY,
            targets_json TEXT NOT NULL DEFAULT '[]',
            filler_json TEXT NOT NULL DEFAULT '[]',
            fast_ms INTEGER NOT NULL DEFAULT 2000,
            retrievals_to_clear INTEGER NOT NULL DEFAULT 2,
            hesitation_ms INTEGER NOT NULL DEFAULT 6000,
            updated_at TEXT
        )
    """)
    have = {r[1] for r in conn.execute("PRAGMA table_info(VisualPracticeConfig)")}
    migrations = [
        ("targets_json", "TEXT NOT NULL DEFAULT '[]'"),
        ("filler_json", "TEXT NOT NULL DEFAULT '[]'"),
        ("fast_ms", "INTEGER NOT NULL DEFAULT 2000"),
        ("retrievals_to_clear", "INTEGER NOT NULL DEFAULT 2"),
        ("hesitation_ms", "INTEGER NOT NULL DEFAULT 6000"),
        ("updated_at", "TEXT"),
    ]
    for col, spec in migrations:
        if col not in have:
            conn.execute(f"ALTER TABLE VisualPracticeConfig ADD COLUMN {col} {spec}")
    conn.commit()

### Defaults
DEFAULT_FAST_MS = 2000
DEFAULT_RETRIEVALS_TO_CLEAR = 2
DEFAULT_HESITATION_MS = 6000
def _clamp(value, lo, hi, default):
    """Coerce to int in [lo, hi]; fall back to default on bad input."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))

### Read / write
def _json_list(value):
    """Decode a stored JSON list; corrupt/non-list values degrade to an empty config."""
    try:
        decoded = json.loads(value or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return decoded if isinstance(decoded, list) else []
def get_config(conn, user_name):
    """Return this user's visual config as a dict (camelCase for the page), or
    None when no row exists yet (the page falls back to its code defaults)."""
    ensure_visual_schema(conn)
    row = conn.execute("SELECT * FROM VisualPracticeConfig WHERE user_name = ?", (user_name,)).fetchone()
    if row is None:
        return None
    fast = row["fast_ms"] if row["fast_ms"] is not None else DEFAULT_FAST_MS
    retrievals = row["retrievals_to_clear"] if row["retrievals_to_clear"] is not None \
        else DEFAULT_RETRIEVALS_TO_CLEAR
    hesitation = row["hesitation_ms"] if row["hesitation_ms"] is not None else DEFAULT_HESITATION_MS
    return {
        "targets": _json_list(row["targets_json"]),
        "filler": _json_list(row["filler_json"]),
        "fastMs": fast,
        "retrievalsToClear": retrievals,
        "hesitationMs": hesitation,
        "updatedAt": row["updated_at"],
    }
def set_config(conn, user_name, targets=None, filler=None, fast_ms=None,
               retrievals_to_clear=None, hesitation_ms=None, updated_at=None):
    """Upsert this user's visual config. targets/filler are lists of fact strings
    (or newline text); they're normalized to compact forms. Numeric params are
    clamped. Omitted fields keep the existing value (or the default on first write)."""
    ensure_visual_schema(conn)
    existing = get_config(conn, user_name) or {}
    targets_list = normalize_facts(targets)[:5] if targets is not None else existing.get("targets", [])
    filler_list = normalize_facts(filler, spaced=True) if filler is not None else existing.get("filler", [])
    fast = _clamp(fast_ms, 200, 60000, existing.get("fastMs", DEFAULT_FAST_MS)) \
        if fast_ms is not None else existing.get("fastMs", DEFAULT_FAST_MS)
    retrievals = _clamp(retrievals_to_clear, 1, 9, existing.get("retrievalsToClear", DEFAULT_RETRIEVALS_TO_CLEAR)) \
        if retrievals_to_clear is not None else existing.get("retrievalsToClear", DEFAULT_RETRIEVALS_TO_CLEAR)
    hesitation = _clamp(hesitation_ms, 0, 60000, existing.get("hesitationMs", DEFAULT_HESITATION_MS)) \
        if hesitation_ms is not None else existing.get("hesitationMs", DEFAULT_HESITATION_MS)
    stamp = updated_at or datetime.now().strftime("%Y-%m-%d_%H%M%S")
    conn.execute("""
        INSERT INTO VisualPracticeConfig (user_name, targets_json, filler_json,
            fast_ms, retrievals_to_clear, hesitation_ms, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_name) DO UPDATE SET
            targets_json = excluded.targets_json,
            filler_json = excluded.filler_json,
            fast_ms = excluded.fast_ms,
            retrievals_to_clear = excluded.retrievals_to_clear,
            hesitation_ms = excluded.hesitation_ms,
            updated_at = excluded.updated_at
    """, (user_name, json.dumps(targets_list), json.dumps(filler_list),
          fast, retrievals, hesitation, stamp))
    conn.commit()
    return get_config(conn, user_name)

### CLI
def _main():
    ap = argparse.ArgumentParser(description="Show/set visual-practice config in a math-quiz .sqlite")
    ap.add_argument("db", help="path to the per-user .sqlite file")
    ap.add_argument("user", help="learner name")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show", help="print the stored config")
    sp = sub.add_parser("set", help="set config fields")
    sp.add_argument("--targets", help="comma- or newline-separated target problems (e.g. '8+3,4+9')")
    sp.add_argument("--filler", help="comma- or newline-separated filler problems")
    sp.add_argument("--fast-ms", type=int)
    sp.add_argument("--retrievals-to-clear", type=int)
    sp.add_argument("--hesitation-ms", type=int)
    args = ap.parse_args()
    conn = connect(args.db)
    try:
        if args.cmd == "show":
            print(json.dumps(get_config(conn, args.user), indent=2))
        else:
            targets = re.split(r"[\n,]", args.targets) if args.targets is not None else None
            filler = re.split(r"[\n,]", args.filler) if args.filler is not None else None
            cfg = set_config(conn, args.user, targets=targets, filler=filler,
                             fast_ms=args.fast_ms,
                             retrievals_to_clear=args.retrievals_to_clear,
                             hesitation_ms=args.hesitation_ms)
            print(json.dumps(cfg, indent=2))
    finally:
        conn.close()

if __name__ == "__main__":
    _main()
