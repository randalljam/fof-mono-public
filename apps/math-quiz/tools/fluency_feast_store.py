"""Per-file Fluency-feast preset: one row per user holding the parameters the kid's
one-click "Fluency feast" uses to build a list — list size, which sessions to read, and
the fluency-category mix (weights). Stored in the learner's own .sqlite (same file the
problem-list editor / targeted config live in) so each file remembers its own preset.

Mirrors targeted_store: get_config returns camelCase for the page (or None when unset, so
the page falls back to its code defaults); set_config upserts, keeping omitted fields.
"""
import json
import sqlite3
from datetime import datetime

### Defaults (the page's code default when a file has no saved preset)
DEFAULT_COUNT = 20
DEFAULT_OPERATION = "addition"
DEFAULT_SESSION_MODE = "all"     # all | recentN | sinceDate
DEFAULT_SESSION_N = 3
DEFAULT_MIX = {"fluent": 0, "almost": 10, "needs-practice": 10, "incorrect": 40, "missing": 40}
MIX_KEYS = ["fluent", "almost", "needs-practice", "incorrect", "missing"]
_SESSION_MODES = ("all", "recentN", "sinceDate")
_OPERATION_ALIASES = {
    "add": "addition", "addition": "addition", "+": "addition",
    "sub": "subtraction", "subtract": "subtraction", "subtraction": "subtraction", "minus": "subtraction", "-": "subtraction",
    "mul": "multiplication", "multiply": "multiplication", "multiplication": "multiplication", "times": "multiplication", "x": "multiplication",
    "div": "division", "divide": "division", "division": "division", "/": "division",
    "exp": "exponentiation", "pow": "exponentiation", "power": "exponentiation", "exponent": "exponentiation", "exponentiation": "exponentiation", "^": "exponentiation",
}

def connect(path):
    """Open a math-quiz .sqlite with row access by column name."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
def _normalize_operation(raw):
    if raw is None or str(raw).strip() == "":
        return DEFAULT_OPERATION
    return _OPERATION_ALIASES.get(str(raw).strip().lower(), DEFAULT_OPERATION)
def ensure_schema(conn):
    """Create the FluencyFeastConfig table if absent (one row per user)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS FluencyFeastConfig (
            user_name TEXT PRIMARY KEY,
            num_problems INTEGER NOT NULL DEFAULT 20,
            operation TEXT NOT NULL DEFAULT 'addition',
            session_mode TEXT NOT NULL DEFAULT 'all',
            session_n INTEGER NOT NULL DEFAULT 3,
            session_since TEXT,
            mix_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT
        )
    """)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(FluencyFeastConfig)").fetchall()]
    if "operation" not in cols:
        conn.execute("ALTER TABLE FluencyFeastConfig ADD COLUMN operation TEXT NOT NULL DEFAULT 'addition'")
    conn.commit()
def _clamp(value, lo, hi, default):
    """Coerce to int in [lo, hi]; fall back to default on bad input."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))
def _normalize_mix(mix, existing):
    """Keep only the five known category weights, each clamped to [0,100]."""
    base = dict(existing or DEFAULT_MIX)
    if isinstance(mix, dict):
        for k in MIX_KEYS:
            if k in mix:
                base[k] = _clamp(mix[k], 0, 100, base.get(k, 0))
    return {k: int(base.get(k, 0)) for k in MIX_KEYS}

### Read / write
def get_config(conn, user_name):
    """This user's feast preset as a dict (camelCase for the page), or None when unset."""
    ensure_schema(conn)
    row = conn.execute("SELECT * FROM FluencyFeastConfig WHERE user_name = ?", (user_name,)).fetchone()
    if row is None:
        return None
    try:
        mix = json.loads(row["mix_json"] or "{}")
    except Exception:
        mix = {}
    operation = _normalize_operation(row["operation"]) if "operation" in row.keys() else DEFAULT_OPERATION
    return {
        "count": row["num_problems"],
        "operation": operation,
        "session": {"mode": row["session_mode"], "n": row["session_n"], "since": row["session_since"]},
        "mix": {k: int(mix.get(k, 0)) for k in MIX_KEYS},
        "updatedAt": row["updated_at"],
    }
def set_config(conn, user_name, count=None, operation=None, session_mode=None, session_n=None,
               session_since=None, mix=None, updated_at=None):
    """Upsert this user's feast preset. Omitted fields keep the existing value (or the
    default on first write). count is clamped [1,500]; session_n [1,99]; mix weights [0,100]."""
    ensure_schema(conn)
    existing = get_config(conn, user_name) or {}
    ex_session = existing.get("session") or {}
    new_count = _clamp(count, 1, 500, existing.get("count", DEFAULT_COUNT)) \
        if count is not None else existing.get("count", DEFAULT_COUNT)
    new_operation = _normalize_operation(operation) if operation is not None \
        else existing.get("operation", DEFAULT_OPERATION)
    mode = session_mode if session_mode in _SESSION_MODES else ex_session.get("mode", DEFAULT_SESSION_MODE)
    n = _clamp(session_n, 1, 99, ex_session.get("n") or DEFAULT_SESSION_N) \
        if session_n is not None else (ex_session.get("n") or DEFAULT_SESSION_N)
    if session_since is not None:
        since = str(session_since).strip() or None
    else:
        since = ex_session.get("since")
    new_mix = _normalize_mix(mix, existing.get("mix")) if mix is not None \
        else (existing.get("mix") or dict(DEFAULT_MIX))
    stamp = updated_at or datetime.now().strftime("%Y-%m-%d_%H%M%S")
    conn.execute("""
        INSERT INTO FluencyFeastConfig (user_name, num_problems, operation, session_mode, session_n,
            session_since, mix_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_name) DO UPDATE SET
            num_problems = excluded.num_problems,
            operation = excluded.operation,
            session_mode = excluded.session_mode,
            session_n = excluded.session_n,
            session_since = excluded.session_since,
            mix_json = excluded.mix_json,
            updated_at = excluded.updated_at
    """, (user_name, new_count, new_operation, mode, n, since, json.dumps(new_mix), stamp))
    conn.commit()
    return get_config(conn, user_name)
