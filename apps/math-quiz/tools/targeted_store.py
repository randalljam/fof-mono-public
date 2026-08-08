#!/usr/bin/env python3
"""
file: apps/math-quiz/tools/targeted_store.py
title: Manage targeted-practice config in math-quiz SQLite files

Stores a per-learner targeted-practice config IN the per-user .sqlite file (the
same file "Use internal" runs and the quiz appends to), read/written exactly like
the internal problem lists. One row per user in a TargetedConfig table:
  - targets        (JSON array of fact strings, e.g. ["6+3","6+8",...]; up to 5)
  - filler         (JSON array of fact strings — the "target filler" list)
  - graduation_streak / fast_ms / percent_target (the practice parameters)
  - reward_image     (path to the right-side animation on EACH target graduation)
  - completion_image (path to the animation shown only when the WHOLE session
                      completes; both fall back to a single code default when unset)

There is no max-bursts: a session ends only when every target has graduated; the
coach can Quit & save at any break and the partial session is still stored.
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
def ensure_targeted_schema(conn):
    """Create the TargetedConfig table if absent (one row per user) and migrate
    older tables that predate the reward-image columns."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS TargetedConfig (
            user_name TEXT PRIMARY KEY,
            graduation_streak INTEGER NOT NULL DEFAULT 3,
            fast_ms INTEGER NOT NULL DEFAULT 2000,
            percent_target INTEGER NOT NULL DEFAULT 50,
            targets_json TEXT NOT NULL DEFAULT '[]',
            filler_json TEXT NOT NULL DEFAULT '[]',
            reward_image TEXT,
            completion_image TEXT,
            updated_at TEXT
        )
    """)
    have = {r[1] for r in conn.execute("PRAGMA table_info(TargetedConfig)")}
    for col in ("reward_image", "completion_image"):
        if col not in have:
            conn.execute(f"ALTER TABLE TargetedConfig ADD COLUMN {col} TEXT")
    conn.commit()

### Defaults
DEFAULT_GRADUATION_STREAK = 3
DEFAULT_FAST_MS = 2000
DEFAULT_PERCENT_TARGET = 50
def _clamp(value, lo, hi, default):
    """Coerce to int in [lo, hi]; fall back to default on bad input."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))

### Read / write
def get_config(conn, user_name):
    """Return this user's targeted config as a dict (camelCase for the page), or
    None when no row exists yet (the page falls back to its code defaults)."""
    ensure_targeted_schema(conn)
    row = conn.execute("SELECT * FROM TargetedConfig WHERE user_name = ?", (user_name,)).fetchone()
    if row is None:
        return None
    keys = row.keys()
    return {
        "graduationStreak": row["graduation_streak"],
        "fastMs": row["fast_ms"],
        "percentTarget": row["percent_target"],
        "targets": json.loads(row["targets_json"] or "[]"),
        "filler": json.loads(row["filler_json"] or "[]"),
        "rewardImage": row["reward_image"] if "reward_image" in keys else None,
        "completionImage": row["completion_image"] if "completion_image" in keys else None,
        "updatedAt": row["updated_at"],
    }
def _clean_path(value):
    """Trim a path string; empty/whitespace becomes None (clears the field)."""
    if value is None:
        return None
    s = str(value).strip()
    return s or None
def set_config(conn, user_name, targets=None, filler=None, graduation_streak=None,
               fast_ms=None, percent_target=None, reward_image=None,
               completion_image=None, updated_at=None):
    """Upsert this user's targeted config. targets/filler are lists of fact strings
    (or newline text); they're normalized to compact forms. Numeric params are
    clamped; reward_image/completion_image are stored as-is (empty -> cleared).
    Omitted fields keep the existing value (or the default on first write)."""
    ensure_targeted_schema(conn)
    existing = get_config(conn, user_name) or {}
    targets_list = normalize_facts(targets)[:5] if targets is not None else existing.get("targets", [])
    filler_list = normalize_facts(filler, spaced=True) if filler is not None else existing.get("filler", [])
    streak = _clamp(graduation_streak, 1, 9, existing.get("graduationStreak", DEFAULT_GRADUATION_STREAK)) \
        if graduation_streak is not None else existing.get("graduationStreak", DEFAULT_GRADUATION_STREAK)
    fast = _clamp(fast_ms, 200, 60000, existing.get("fastMs", DEFAULT_FAST_MS)) \
        if fast_ms is not None else existing.get("fastMs", DEFAULT_FAST_MS)
    pct = _clamp(percent_target, 1, 100, existing.get("percentTarget", DEFAULT_PERCENT_TARGET)) \
        if percent_target is not None else existing.get("percentTarget", DEFAULT_PERCENT_TARGET)
    reward = _clean_path(reward_image) if reward_image is not None else existing.get("rewardImage")
    completion = _clean_path(completion_image) if completion_image is not None else existing.get("completionImage")
    stamp = updated_at or datetime.now().strftime("%Y-%m-%d_%H%M%S")
    conn.execute("""
        INSERT INTO TargetedConfig (user_name, graduation_streak, fast_ms, percent_target,
            targets_json, filler_json, reward_image, completion_image, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_name) DO UPDATE SET
            graduation_streak = excluded.graduation_streak,
            fast_ms = excluded.fast_ms,
            percent_target = excluded.percent_target,
            targets_json = excluded.targets_json,
            filler_json = excluded.filler_json,
            reward_image = excluded.reward_image,
            completion_image = excluded.completion_image,
            updated_at = excluded.updated_at
    """, (user_name, streak, fast, pct, json.dumps(targets_list), json.dumps(filler_list),
          reward, completion, stamp))
    conn.commit()
    return get_config(conn, user_name)

### CLI
def _main():
    ap = argparse.ArgumentParser(description="Show/set targeted-practice config in a math-quiz .sqlite")
    ap.add_argument("db", help="path to the per-user .sqlite file")
    ap.add_argument("user", help="learner name")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show", help="print the stored config")
    sp = sub.add_parser("set", help="set config fields")
    sp.add_argument("--targets", help="comma- or newline-separated target problems (e.g. '6+3,6+8')")
    sp.add_argument("--filler", help="comma- or newline-separated filler problems")
    sp.add_argument("--streak", type=int)
    sp.add_argument("--fast-ms", type=int)
    sp.add_argument("--percent-target", type=int)
    sp.add_argument("--reward-image", help="path to the per-target graduation animation")
    sp.add_argument("--completion-image", help="path to the whole-session completion animation")
    args = ap.parse_args()
    conn = connect(args.db)
    try:
        if args.cmd == "show":
            print(json.dumps(get_config(conn, args.user), indent=2))
        else:
            targets = re.split(r"[\n,]", args.targets) if args.targets is not None else None
            filler = re.split(r"[\n,]", args.filler) if args.filler is not None else None
            cfg = set_config(conn, args.user, targets=targets, filler=filler,
                             graduation_streak=args.streak, fast_ms=args.fast_ms,
                             percent_target=args.percent_target,
                             reward_image=args.reward_image,
                             completion_image=args.completion_image)
            print(json.dumps(cfg, indent=2))
    finally:
        conn.close()

if __name__ == "__main__":
    _main()
