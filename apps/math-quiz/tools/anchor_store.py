#!/usr/bin/env python3
"""
file: apps/math-quiz/tools/anchor_store.py
title: Naming + append helpers for the per-person SQLite store (math-flu / any prefix)

Helpers used by tools/dev_server.py to route anchor ("math-flu") runs into the
real/test folders and to append a session into a person's existing file, and by
tools/ingest_drop_folder.py to ingest single-session files dropped by OTHER apps
(e.g. the MathQuest Minecraft mod, prefix "math-quest"). Naming rules: docs/SPEC.md §8a.

  single-session file:  <prefix>_<name>_<YYYY-MM-DD>_<HHMMSS>.sqlite   (date + time)
  multi-session file:   <prefix>_<name>_<YYYY-MM-DD>[_<suffix>].sqlite (date only; time dropped)

The prefix is a parameter (default "math-flu"); every naming function takes `prefix=`.
Appending a session to a single-session file renames it to the multi-session form
(drop the time, keep the initial date). Appending to a multi-session file keeps the
target's filename. When several lineages share one day, the renamed multi takes a
_2 / _3 … suffix so they don't collide. "Continue latest" appends to the most-recently-
modified lineage (pick_latest); "Start New" (force_new) begins a fresh single-session file.
"""
import re
import shutil
import sqlite3
from functools import lru_cache
from pathlib import Path

PREFIX = "math-flu"   # default per-person file prefix (configurable per source app)
_DATE = r"\d{4}-\d{2}-\d{2}"
_TIME = r"\d{6}"
# Child tables whose autoincrement PK must be dropped when copying rows.
_CHILD_PK = {"ProblemAttempts": "attempt_id", "WarmupAttempts": "warmup_id", "ModeEvents": "event_id"}

@lru_cache(maxsize=None)
def _patterns(prefix):
    """Compiled (single, multi) filename regexes for a prefix (cached). A 6-digit trailing
    segment after the date is read as a TIME (single-session)."""
    esc = re.escape(prefix)
    single = re.compile(rf"^{esc}_(?P<name>.+)_(?P<date>{_DATE})_(?P<time>{_TIME})\.sqlite$")
    multi = re.compile(rf"^{esc}_(?P<name>.+)_(?P<date>{_DATE})(?:_(?P<suffix>.+))?\.sqlite$")
    return single, multi

def parse_filename(fn, prefix=PREFIX):
    """Return {name,date,time,suffix,multi} for a <prefix> filename, else None."""
    single_re, multi_re = _patterns(prefix)
    m = single_re.match(fn)
    if m:
        return {"name": m["name"], "date": m["date"], "time": m["time"], "suffix": None, "multi": False}
    m = multi_re.match(fn)
    if m:
        return {"name": m["name"], "date": m["date"], "time": None, "suffix": m["suffix"], "multi": True}
    return None

def single_session_name(name, stamp, prefix=PREFIX):
    """stamp = 'YYYY-MM-DD_HHMMSS' (the session start timestamp)."""
    return f"{prefix}_{name}_{stamp}.sqlite"

def multi_session_name(name, date, suffix=None, prefix=PREFIX):
    return f"{prefix}_{name}_{date}{('_' + suffix) if suffix else ''}.sqlite"

def next_multi_name(existing_filenames, name, date, prefix=PREFIX):
    """Collision-free multi-session name for (name, date). Returns the bare
    <prefix>_<name>_<date>.sqlite when free, else appends _2, _3, … so several same-day
    lineages can coexist without overwriting each other."""
    existing = set(existing_filenames or [])
    bare = multi_session_name(name, date, prefix=prefix)
    if bare not in existing:
        return bare
    n = 2
    while multi_session_name(name, date, str(n), prefix=prefix) in existing:
        n += 1
    return multi_session_name(name, date, str(n), prefix=prefix)

def to_multi_name(single_filename, prefix=PREFIX):
    """Drop the time from a single-session filename -> multi-session name (keep the date)."""
    p = parse_filename(single_filename, prefix=prefix)
    if not p or p["multi"]:
        return single_filename
    return multi_session_name(p["name"], p["date"], prefix=prefix)

def pick_target(filenames, name, prefix=PREFIX):
    """The most-recent existing file for `name` by the filename-encoded date/time (a same-date
    multi sorts after a single, so the accumulated file is preferred). Returns a filename or None."""
    cands = []
    for fn in filenames:
        p = parse_filename(fn, prefix=prefix)
        if p and p["name"] == name:
            cands.append(((p["date"], p["time"] or "999999"), fn))
    if not cands:
        return None
    cands.sort()
    return cands[-1][1]

def _normalize_entries(existing):
    """Accept a list of filenames OR (filename, modified) tuples; return a list of
    (filename, modified) with modified=None when unknown. `modified` is any
    comparable recency marker (epoch seconds / S3 LastModified timestamp)."""
    out = []
    for e in existing or []:
        if isinstance(e, (tuple, list)):
            out.append((e[0], e[1] if len(e) > 1 else None))
        else:
            out.append((e, None))
    return out

def pick_latest(existing, name, prefix=PREFIX):
    """The most-recently-modified existing file for `name` — the lineage to append to.
    `existing` is a list of filenames or (filename, modified) tuples. Mod times decide
    recency when known (robust across same-day lineages whose multi names dropped their
    time); else falls back to the filename-encoded recency. Returns a filename or None."""
    entries = _normalize_entries(existing)
    matching = [(fn, mod) for (fn, mod) in entries if (parse_filename(fn, prefix=prefix) or {}).get("name") == name]
    if not matching:
        return None
    have_mod = [(fn, mod) for (fn, mod) in matching if mod is not None]
    if have_mod:
        # newest mod wins; tie-break by the filename's own date/time so it stays deterministic.
        def _key(item):
            fn, mod = item
            p = parse_filename(fn, prefix=prefix)
            return (mod, p["date"], p["time"] or "999999")
        have_mod.sort(key=_key)
        return have_mod[-1][0]
    return pick_target([fn for fn, _ in matching], name, prefix=prefix)

def list_landing_users(filenames, prefix=PREFIX):
    """Kid-landing buttons from .sqlite basenames: one entry per unique name, or one per
    file when a name appears more than once (label then includes the file date, and time
    or suffix if the date alone still collides). Returns
    [{name, label, filename}, ...] sorted by label (case-insensitive)."""
    by_name = {}
    for fn in filenames or []:
        p = parse_filename(fn, prefix=prefix)
        if not p:
            continue
        by_name.setdefault(p["name"], []).append((fn, p))
    out = []
    for name, items in by_name.items():
        if len(items) == 1:
            fn, _p = items[0]
            out.append({"name": name, "label": name, "filename": fn})
            continue
        # Disambiguate duplicate names with the file date; refine if still not unique.
        draft = []
        for fn, p in items:
            draft.append({"name": name, "filename": fn, "date": p["date"],
                          "extra": p["time"] or p["suffix"] or ""})
        date_counts = {}
        for d in draft:
            date_counts[d["date"]] = date_counts.get(d["date"], 0) + 1
        for d in draft:
            label = f"{name} {d['date']}"
            if date_counts[d["date"]] > 1 and d["extra"]:
                label = f"{label} {d['extra']}"
            out.append({"name": name, "label": label, "filename": d["filename"]})
    out.sort(key=lambda e: (e["label"].lower(), e["filename"]))
    return out

def _table_exists(conn, t):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None

def _cols(conn, t):
    return [r[1] for r in conn.execute(f"PRAGMA table_info({t})")]
def _ensure_table(dst, table, src):
    if _table_exists(dst, table) or not _table_exists(src, table):
        return
    row = src.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    if row and row[0]:
        dst.execute(row[0])
def _ensure_columns(dst, table, src):
    """ALTER `table` in dst to add any columns present in src but missing in dst, so an append
    PRESERVES newer columns (e.g. presented_at) instead of silently dropping them when the
    destination file's schema predates them. Column names come from our own schema (trusted)."""
    have = set(_cols(dst, table))
    for row in src.execute(f"PRAGMA table_info({table})"):
        name, ctype = row[1], (row[2] or "TEXT")
        if name not in have:
            dst.execute(f'ALTER TABLE {table} ADD COLUMN "{name}" {ctype}')

def append_session(target_path, individual_path):
    """Copy the session(s) from individual_path into target_path, deduping by
    session_id (idempotent). Returns the number of sessions added."""
    src = sqlite3.connect(individual_path)
    dst = sqlite3.connect(target_path)
    try:
        if _table_exists(src, "Users") and _table_exists(dst, "Users"):
            for (nm,) in src.execute("SELECT name FROM Users"):
                dst.execute("INSERT OR IGNORE INTO Users(name) VALUES(?)", (nm,))

        existing = set()
        new_sessions = []
        if _table_exists(dst, "Sessions"):
            existing = {r[0] for r in dst.execute("SELECT session_id FROM Sessions")}
        if _table_exists(src, "Sessions") and _table_exists(dst, "Sessions"):
            _ensure_columns(dst, "Sessions", src)   # keep newer columns instead of dropping them
            usecols = [c for c in _cols(dst, "Sessions") if c in set(_cols(src, "Sessions"))]
            sid_i = usecols.index("session_id") if "session_id" in usecols else None
            ph = ",".join("?" for _ in usecols)
            for row in src.execute(f"SELECT {','.join(usecols)} FROM Sessions").fetchall():
                sid = row[sid_i] if sid_i is not None else None
                if not sid or sid in existing:
                    continue
                new_sessions.append(sid)
                dst.execute(f"INSERT OR IGNORE INTO Sessions({','.join(usecols)}) VALUES({ph})", row)

        for table in ("ProblemAttempts", "WarmupAttempts", "ModeEvents",
                      "TargetedPracticeSessions", "TargetedPracticeTargets",
                      "TargetedPracticeAttemptRoles",
                      "VisualPracticeSessions", "VisualPracticeTargets",
                      "VisualPracticeAttemptRoles"):
            if not _table_exists(src, table) or not new_sessions:
                continue
            _ensure_table(dst, table, src)
            if not _table_exists(dst, table):
                continue
            _ensure_columns(dst, table, src)   # preserve newer columns (e.g. presented_at)
            pk = _CHILD_PK.get(table)
            usecols = [c for c in _cols(dst, table) if c in set(_cols(src, table)) and c != pk]
            if "session_id" not in usecols:
                continue
            ph = ",".join("?" for _ in usecols)
            qmarks = ",".join("?" for _ in new_sessions)
            rows = src.execute(
                f"SELECT {','.join(usecols)} FROM {table} WHERE session_id IN ({qmarks})", new_sessions
            ).fetchall()
            for row in rows:
                dst.execute(f"INSERT INTO {table}({','.join(usecols)}) VALUES({ph})", row)

        dst.commit()
        return len(new_sessions)
    finally:
        src.close()
        dst.close()

def resolve_save(folder, name, stamp, existing, force_new=False, prefix=PREFIX):
    """Decide where a finished run goes given the folder's files. `existing` is a list of
    filenames or (filename, modified) tuples (mod times let the pick follow recency). Returns:
      action 'create' -> write the individual file as `filename`
      action 'append' -> append into `target`, output named `filename` (multi-session)
    force_new=True ("Start New") begins a fresh single-session lineage."""
    filenames = [fn for fn, _ in _normalize_entries(existing)]
    target = None if force_new else pick_latest(existing, name, prefix=prefix)
    if target is None:
        return {"action": "create", "target": None, "filename": single_session_name(name, stamp, prefix=prefix)}
    p = parse_filename(target, prefix=prefix)
    if p and p["multi"]:
        out_name = target                                   # appending to a multi keeps its name
    else:
        # single -> multi: drop the time, keep the target's (initial-session) date, and
        # avoid colliding with another same-day lineage's multi file (_2, _3, …).
        out_name = next_multi_name(filenames, name, p["date"], prefix=prefix)
    return {"action": "append", "target": target, "filename": out_name}

def local_entries(folder_dir):
    """(filename, mtime) for each .sqlite directly in folder_dir (a Path)."""
    folder_dir = Path(folder_dir)
    out = []
    if folder_dir.exists():
        for p in folder_dir.glob("*.sqlite"):
            try:
                out.append((p.name, p.stat().st_mtime))
            except OSError:
                out.append((p.name, None))
    return out

def session_count(path):
    """Number of rows in the Sessions table of a .sqlite (0 if absent)."""
    c = sqlite3.connect(str(path))
    try:
        return c.execute("SELECT COUNT(*) FROM Sessions").fetchone()[0] if _table_exists(c, "Sessions") else 0
    finally:
        c.close()

def accumulate(dest_dir, name, stamp, src_path, prefix=PREFIX, force_new=False):
    """Accumulate the single-session file at src_path into the per-person file for `name`
    in dest_dir (a local folder Path) using the create/append/single->multi rules with
    `prefix`. Returns {action, filename, target, path, added}. Idempotent: re-ingesting a
    file already merged adds 0 sessions (append_session dedups by session_id)."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    plan = resolve_save(dest_dir.name, name, stamp, local_entries(dest_dir), force_new=force_new, prefix=prefix)
    out_name = plan["filename"]
    out_path = dest_dir / out_name
    if plan["action"] == "create":
        shutil.copyfile(src_path, out_path)
        added = session_count(out_path)
    else:
        target_path = dest_dir / plan["target"]
        if target_path.resolve() != out_path.resolve():
            shutil.copyfile(target_path, out_path)
        added = append_session(str(out_path), str(src_path))
        if plan["target"] != out_name:                      # single -> multi rename: drop the stale single
            old = dest_dir / plan["target"]
            if old.exists() and old.resolve() != out_path.resolve():
                old.unlink()
    return {"action": plan["action"], "filename": out_name, "target": plan.get("target"),
            "path": str(out_path), "added": added}
