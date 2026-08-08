"""Per-file learner profile: one row per user holding display/UX preferences and the fluency
rubric thresholds that travel with the learner's own .sqlite (the same file the problem-list
editor, targeted config, and feast preset live in). Holds:
  - showFluencyPercent: whether the anchor end-of-quiz summary shows the start→end fluency %.
  - thresholds: the per-file fluency rubric (greenMs / redMs / windowSize / minAccuracy) used
    for the end-of-quiz % and the generate-by-fluency calculations; defaults to the system
    rubric when unset.

Mirrors targeted_store / fluency_feast_store: get_config returns camelCase for the page (with
code defaults baked in so the page always has a value); set_config upserts, keeping omitted
fields. retentionSessions is not per-file editable — the page carries the system default.
"""
import sqlite3
from datetime import datetime

### Defaults (the page's code default when a file has no saved profile) — mirror
### defaultFluencyThresholds in fluency_core.js. minAccuracy is a fraction (0.8 = 80%).
DEFAULT_SHOW_FLUENCY_PERCENT = True
DEFAULT_GREEN_MS = 2000
DEFAULT_RED_MS = 4000
DEFAULT_WINDOW_SIZE = 5
DEFAULT_MIN_ACCURACY = 0.8

def connect(path):
    """Open a math-quiz .sqlite with row access by column name."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
def ensure_schema(conn):
    """Create the Profile table if absent (one row per user); add threshold columns on
    older files that predate them (best-effort ALTER)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Profile (
            user_name TEXT PRIMARY KEY,
            show_fluency_percent INTEGER NOT NULL DEFAULT 1,
            green_ms INTEGER,
            red_ms INTEGER,
            window_size INTEGER,
            min_accuracy REAL,
            updated_at TEXT
        )
    """)
    existing = {r["name"] for r in conn.execute("PRAGMA table_info(Profile)").fetchall()}
    for col, decl in (("green_ms", "INTEGER"), ("red_ms", "INTEGER"),
                      ("window_size", "INTEGER"), ("min_accuracy", "REAL")):
        if col not in existing:
            conn.execute(f"ALTER TABLE Profile ADD COLUMN {col} {decl}")
    conn.commit()
def _as_bool(value, default):
    """Coerce a JSON/db value to bool; fall back to default on None."""
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() not in ("", "0", "false", "no", "off")
    return bool(value)
def _as_int(value, lo, hi, default):
    """Coerce to int in [lo, hi]; fall back to default on bad/None input."""
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))
def _as_accuracy(value, default):
    """Coerce a fraction in (0,1] (accepts a percent > 1 and divides by 100)."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return default
    if f > 1:
        f = f / 100.0
    return max(0.01, min(1.0, f))
def _thresholds(row):
    """Assemble the rubric dict from a row, filling system defaults for any unset column."""
    g = row["green_ms"] if row["green_ms"] is not None else DEFAULT_GREEN_MS
    r = row["red_ms"] if row["red_ms"] is not None else DEFAULT_RED_MS
    w = row["window_size"] if row["window_size"] is not None else DEFAULT_WINDOW_SIZE
    a = row["min_accuracy"] if row["min_accuracy"] is not None else DEFAULT_MIN_ACCURACY
    return {"greenMs": int(g), "redMs": int(r), "windowSize": int(w), "minAccuracy": float(a)}
def _default_thresholds():
    return {"greenMs": DEFAULT_GREEN_MS, "redMs": DEFAULT_RED_MS,
            "windowSize": DEFAULT_WINDOW_SIZE, "minAccuracy": DEFAULT_MIN_ACCURACY}

### Read / write
def get_config(conn, user_name):
    """This user's profile as a dict (camelCase), with code defaults for any unset field. Never
    returns None — the page always gets a usable value (defaults: show the readout, system
    rubric)."""
    ensure_schema(conn)
    row = conn.execute("SELECT * FROM Profile WHERE user_name = ?", (user_name,)).fetchone()
    if row is None:
        return {"showFluencyPercent": DEFAULT_SHOW_FLUENCY_PERCENT,
                "thresholds": _default_thresholds(), "updatedAt": None}
    return {
        "showFluencyPercent": _as_bool(row["show_fluency_percent"], DEFAULT_SHOW_FLUENCY_PERCENT),
        "thresholds": _thresholds(row),
        "updatedAt": row["updated_at"],
    }
def set_config(conn, user_name, show_fluency_percent=None, thresholds=None, updated_at=None):
    """Upsert this user's profile. Omitted fields keep the existing value (or the default on
    first write). thresholds is a partial dict {greenMs, redMs, windowSize, minAccuracy}."""
    ensure_schema(conn)
    existing = get_config(conn, user_name)
    new_show = _as_bool(show_fluency_percent, existing["showFluencyPercent"]) \
        if show_fluency_percent is not None else existing["showFluencyPercent"]
    th = dict(existing["thresholds"])
    if isinstance(thresholds, dict):
        if "greenMs" in thresholds:
            th["greenMs"] = _as_int(thresholds["greenMs"], 100, 60000, th["greenMs"])
        if "redMs" in thresholds:
            th["redMs"] = _as_int(thresholds["redMs"], 100, 60000, th["redMs"])
        if "windowSize" in thresholds:
            th["windowSize"] = _as_int(thresholds["windowSize"], 1, 100, th["windowSize"])
        if "minAccuracy" in thresholds:
            th["minAccuracy"] = _as_accuracy(thresholds["minAccuracy"], th["minAccuracy"])
    stamp = updated_at or datetime.now().strftime("%Y-%m-%d_%H%M%S")
    conn.execute("""
        INSERT INTO Profile (user_name, show_fluency_percent, green_ms, red_ms, window_size,
            min_accuracy, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_name) DO UPDATE SET
            show_fluency_percent = excluded.show_fluency_percent,
            green_ms = excluded.green_ms,
            red_ms = excluded.red_ms,
            window_size = excluded.window_size,
            min_accuracy = excluded.min_accuracy,
            updated_at = excluded.updated_at
    """, (user_name, 1 if new_show else 0, th["greenMs"], th["redMs"], th["windowSize"],
          th["minAccuracy"], stamp))
    conn.commit()
    return get_config(conn, user_name)
