"""SQLite schema and access helpers for Holodeck turns."""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

try:
    from apps.holodeck.turns import labels
except ImportError:
    from turns import labels

SCHEMA_VERSION = "7"
DEFAULT_DB_REL = Path("apps/holodeck/data/turns.db")
OPERATOR_ORIGIN = "operator"
DELEGATED_ORIGIN = "delegated"
SUBAGENT_PARENT_FALLBACK_HOURS = 2

### Paths
def repo_root():
    return Path(__file__).resolve().parents[3]
def default_db_path(root=None):
    return Path(root or repo_root()) / DEFAULT_DB_REL
def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")

### Connection
def connect(path=None):
    db_path = Path(path or default_db_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    try:
        conn.execute("PRAGMA journal_mode = WAL")
    except sqlite3.OperationalError:
        pass
    return conn
def init_db(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            platform TEXT,
            entrypoint TEXT,
            host TEXT,
            remote_control INTEGER DEFAULT 0,
            bridge_session_id TEXT,
            source_path TEXT,
            source_url TEXT,
            project TEXT,
            worktree TEXT,
            branch TEXT,
            label TEXT,
            model TEXT,
            interface TEXT,
            origin TEXT DEFAULT 'operator',
            parent_session_id TEXT NULL,
            title TEXT,
            started TEXT,
            last_activity TEXT,
            ingested_at TEXT
        );
        CREATE TABLE IF NOT EXISTS exchanges (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            idx INTEGER NOT NULL,
            kind TEXT CHECK(kind IN ('primary','quick','info')),
            user_ts TEXT,
            user_text TEXT,
            response_text TEXT,
            response_final_text TEXT,
            response_recap TEXT,
            response_end_ts TEXT,
            origin TEXT DEFAULT 'operator',
            follow_up_of TEXT NULL
        );
        CREATE TABLE IF NOT EXISTS commits (
            sha TEXT PRIMARY KEY,
            branch TEXT,
            worktree TEXT,
            author TEXT,
            author_email TEXT,
            author_date TEXT,
            committer_date TEXT,
            subject TEXT,
            body TEXT,
            is_agent_commit INTEGER
        );
        CREATE TABLE IF NOT EXISTS links (
            exchange_id TEXT NOT NULL REFERENCES exchanges(id) ON DELETE CASCADE,
            sha TEXT NOT NULL REFERENCES commits(sha) ON DELETE CASCADE,
            method TEXT,
            confidence REAL,
            PRIMARY KEY(exchange_id, sha)
        );
        CREATE TABLE IF NOT EXISTS digests (
            exchange_id TEXT PRIMARY KEY REFERENCES exchanges(id) ON DELETE CASCADE,
            title TEXT,
            asked_json TEXT,
            notes_json TEXT,
            recap TEXT,
            model_used TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS commit_hash_map (
            old_sha TEXT PRIMARY KEY,
            new_sha TEXT,
            status TEXT,
            author_date TEXT,
            author TEXT,
            subject TEXT,
            branches TEXT,
            new_exists TEXT,
            new_subject TEXT
        );
        CREATE TABLE IF NOT EXISTS branch_tip_map (
            branch TEXT PRIMARY KEY,
            old_tip TEXT,
            new_tip TEXT,
            old_date TEXT,
            old_subject TEXT,
            new_exists TEXT,
            new_subject TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_commit_hash_map_new_sha ON commit_hash_map(new_sha);
        """
    )
    migrate_schema(conn)
    set_meta(conn, "schema_version", SCHEMA_VERSION)
def table_columns(conn, table):
    return {row["name"] for row in conn.execute("PRAGMA table_info(" + table + ")").fetchall()}
def add_column_if_missing(conn, table, column, definition):
    if column in table_columns(conn, table):
        return
    conn.execute("ALTER TABLE " + table + " ADD COLUMN " + column + " " + definition)
def migrate_schema(conn):
    columns = table_columns(conn, "sessions")
    if "tool" in columns and "platform" not in columns:
        conn.execute("ALTER TABLE sessions RENAME COLUMN tool TO platform")
        columns = table_columns(conn, "sessions")
    add_column_if_missing(conn, "sessions", "entrypoint", "TEXT")
    add_column_if_missing(conn, "sessions", "host", "TEXT")
    add_column_if_missing(conn, "sessions", "remote_control", "INTEGER DEFAULT 0")
    add_column_if_missing(conn, "sessions", "bridge_session_id", "TEXT")
    add_column_if_missing(conn, "sessions", "origin", "TEXT DEFAULT 'operator'")
    add_column_if_missing(conn, "sessions", "source_url", "TEXT")
    add_column_if_missing(conn, "sessions", "parent_session_id", "TEXT")
    add_column_if_missing(conn, "exchanges", "origin", "TEXT DEFAULT 'operator'")
    add_column_if_missing(conn, "exchanges", "response_final_text", "TEXT")
    add_column_if_missing(conn, "exchanges", "response_recap", "TEXT")
    add_column_if_missing(conn, "digests", "title", "TEXT")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS commit_hash_map (
            old_sha TEXT PRIMARY KEY,
            new_sha TEXT,
            status TEXT,
            author_date TEXT,
            author TEXT,
            subject TEXT,
            branches TEXT,
            new_exists TEXT,
            new_subject TEXT
        );
        CREATE TABLE IF NOT EXISTS branch_tip_map (
            branch TEXT PRIMARY KEY,
            old_tip TEXT,
            new_tip TEXT,
            old_date TEXT,
            old_subject TEXT,
            new_exists TEXT,
            new_subject TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_commit_hash_map_new_sha ON commit_hash_map(new_sha);
        """
    )
    normalize_legacy_session_rows(conn)
def normalize_legacy_session_rows(conn):
    conn.execute(
        """
        UPDATE sessions
        SET entrypoint = CASE
            WHEN platform IN ('claude-cloud', 'codex-cloud') THEN 'app'
            WHEN platform = 'cursor' THEN 'app'
            WHEN platform = 'claude-code' AND (COALESCE(interface, '') LIKE '%App%' OR COALESCE(label, '') LIKE '%App%') THEN 'app'
            WHEN platform = 'claude-code' THEN 'cli'
            WHEN platform = 'codex' AND (COALESCE(entrypoint, '') IN ('codex-subagent', 'subagent')
                OR COALESCE(interface, '') LIKE '%Subagent%' OR COALESCE(label, '') LIKE '%Subagent%'
                OR REPLACE(LOWER(COALESCE(label, '')), ' ', '') LIKE '%autoreview%') THEN 'subagent'
            WHEN platform = 'codex' AND COALESCE(entrypoint, '') IN ('codex-cli', 'cli') THEN 'cli'
            WHEN platform = 'codex' AND (COALESCE(entrypoint, '') IN ('codex-desktop', 'codex-vscode', 'app')
                OR COALESCE(interface, '') LIKE '%App%' OR COALESCE(label, '') LIKE '%App%') THEN 'app'
            WHEN platform = 'codex' THEN 'cli'
            ELSE entrypoint
        END
        WHERE entrypoint IS NULL
            OR entrypoint IN ('claude-desktop', 'cursor', 'codex-cli', 'codex-desktop', 'codex-subagent', 'codex-vscode')
        """
    )
    conn.execute(
        """
        UPDATE sessions
        SET host = CASE WHEN platform IN ('claude-cloud', 'codex-cloud') THEN 'cloud' ELSE 'local' END
        WHERE host IS NULL OR host = ''
        """
    )
    conn.execute("UPDATE sessions SET remote_control = 0 WHERE remote_control IS NULL")
    conn.execute(
        """
        UPDATE sessions
        SET platform = CASE
            WHEN platform IN ('claude-code', 'claude-cloud') THEN 'claude'
            WHEN platform = 'codex-cloud' THEN 'codex'
            ELSE platform
        END
        WHERE platform IN ('claude-code', 'claude-cloud', 'codex-cloud')
        """
    )
def set_meta(conn, key, value):
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )
def get_meta(conn, key):
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None

### Upserts
def normalize_session_payload(session):
    payload = dict(session)
    labels.normalize_session_schema(payload)
    payload.setdefault("origin", OPERATOR_ORIGIN)
    payload.setdefault("source_url", None)
    payload.setdefault("parent_session_id", None)
    payload["remote_control"] = 1 if labels.truthy(payload.get("remote_control")) else 0
    return payload
def upsert_session(conn, session):
    payload = normalize_session_payload(session)
    conn.execute(
        """
        INSERT INTO sessions(id, platform, entrypoint, host, remote_control, bridge_session_id, source_path, source_url, project, worktree, branch, label, model, interface, origin, parent_session_id, title, started, last_activity, ingested_at)
        VALUES(:id, :platform, :entrypoint, :host, :remote_control, :bridge_session_id, :source_path, :source_url, :project, :worktree, :branch, :label, :model, :interface, :origin, :parent_session_id, :title, :started, :last_activity, :ingested_at)
        ON CONFLICT(id) DO UPDATE SET
            platform=excluded.platform,
            entrypoint=excluded.entrypoint,
            host=excluded.host,
            remote_control=excluded.remote_control,
            bridge_session_id=excluded.bridge_session_id,
            source_path=excluded.source_path,
            source_url=excluded.source_url,
            project=excluded.project,
            worktree=excluded.worktree,
            branch=excluded.branch,
            label=excluded.label,
            model=excluded.model,
            interface=excluded.interface,
            origin=excluded.origin,
            parent_session_id=excluded.parent_session_id,
            title=excluded.title,
            started=excluded.started,
            last_activity=excluded.last_activity,
            ingested_at=excluded.ingested_at
        """,
        payload,
    )
def upsert_exchange(conn, exchange):
    payload = dict(exchange)
    payload.setdefault("origin", OPERATOR_ORIGIN)
    payload.setdefault("response_final_text", "")
    payload.setdefault("response_recap", "")
    conn.execute(
        """
        INSERT INTO exchanges(id, session_id, idx, kind, user_ts, user_text, response_text, response_final_text, response_recap, response_end_ts, origin, follow_up_of)
        VALUES(:id, :session_id, :idx, :kind, :user_ts, :user_text, :response_text, :response_final_text, :response_recap, :response_end_ts, :origin, :follow_up_of)
        ON CONFLICT(id) DO UPDATE SET
            session_id=excluded.session_id,
            idx=excluded.idx,
            kind=excluded.kind,
            user_ts=excluded.user_ts,
            user_text=excluded.user_text,
            response_text=excluded.response_text,
            response_final_text=excluded.response_final_text,
            response_recap=excluded.response_recap,
            response_end_ts=excluded.response_end_ts,
            origin=excluded.origin,
            follow_up_of=excluded.follow_up_of
        """,
        payload,
    )
def upsert_commit(conn, commit):
    conn.execute(
        """
        INSERT INTO commits(sha, branch, worktree, author, author_email, author_date, committer_date, subject, body, is_agent_commit)
        VALUES(:sha, :branch, :worktree, :author, :author_email, :author_date, :committer_date, :subject, :body, :is_agent_commit)
        ON CONFLICT(sha) DO UPDATE SET
            branch=excluded.branch,
            worktree=excluded.worktree,
            author=excluded.author,
            author_email=excluded.author_email,
            author_date=excluded.author_date,
            committer_date=excluded.committer_date,
            subject=excluded.subject,
            body=excluded.body,
            is_agent_commit=excluded.is_agent_commit
        """,
        commit,
    )
def upsert_link(conn, link):
    conn.execute(
        """
        INSERT INTO links(exchange_id, sha, method, confidence)
        VALUES(:exchange_id, :sha, :method, :confidence)
        ON CONFLICT(exchange_id, sha) DO UPDATE SET
            method=excluded.method,
            confidence=excluded.confidence
        """,
        link,
    )
def upsert_commit_hash_map(conn, row):
    conn.execute(
        """
        INSERT INTO commit_hash_map(old_sha, new_sha, status, author_date, author, subject, branches, new_exists, new_subject)
        VALUES(:old_sha, :new_sha, :status, :author_date, :author, :subject, :branches, :new_exists, :new_subject)
        ON CONFLICT(old_sha) DO UPDATE SET
            new_sha=excluded.new_sha,
            status=excluded.status,
            author_date=excluded.author_date,
            author=excluded.author,
            subject=excluded.subject,
            branches=excluded.branches,
            new_exists=excluded.new_exists,
            new_subject=excluded.new_subject
        """,
        row,
    )
def upsert_branch_tip_map(conn, row):
    conn.execute(
        """
        INSERT INTO branch_tip_map(branch, old_tip, new_tip, old_date, old_subject, new_exists, new_subject)
        VALUES(:branch, :old_tip, :new_tip, :old_date, :old_subject, :new_exists, :new_subject)
        ON CONFLICT(branch) DO UPDATE SET
            old_tip=excluded.old_tip,
            new_tip=excluded.new_tip,
            old_date=excluded.old_date,
            old_subject=excluded.old_subject,
            new_exists=excluded.new_exists,
            new_subject=excluded.new_subject
        """,
        row,
    )
def upsert_digest(conn, exchange_id, digest):
    conn.execute(
        """
        INSERT INTO digests(exchange_id, title, asked_json, notes_json, recap, model_used, created_at)
        VALUES(?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(exchange_id) DO UPDATE SET
            title=excluded.title,
            asked_json=excluded.asked_json,
            notes_json=excluded.notes_json,
            recap=excluded.recap,
            model_used=excluded.model_used,
            created_at=excluded.created_at
        """,
        (
            exchange_id,
            digest.get("title") or "",
            json.dumps(digest.get("asked") or []),
            json.dumps(digest.get("notes") or []),
            digest.get("recap") or "",
            digest.get("model_used"),
            digest.get("created_at") or now_iso(),
        ),
    )

### Subagent links
def normalize_path_key(value):
    if not value:
        return None
    return os.path.normpath(os.path.expanduser(str(value)))
def session_path_keys(session):
    keys = set()
    for name in ("worktree", "project"):
        key = normalize_path_key(session.get(name))
        if key:
            keys.add(key)
    return keys
def sessions_share_work_context(left, right):
    return bool(session_path_keys(left) & session_path_keys(right))
def session_is_subagent_candidate(session):
    return session.get("platform") == "codex" and (session.get("origin") or OPERATOR_ORIGIN) == DELEGATED_ORIGIN
def session_is_operator_candidate(session):
    return (session.get("origin") or OPERATOR_ORIGIN) == OPERATOR_ORIGIN
def session_is_codex_operator(session):
    return session_is_operator_candidate(session) and session.get("platform") == "codex"
def session_started_at(session):
    return parse_time(session.get("started"))
def session_last_activity_at(session):
    return parse_time(session.get("last_activity")) or session_started_at(session)
def operator_contains_subagent(operator, subagent, subagent_start):
    parent_start = session_started_at(operator)
    parent_end = session_last_activity_at(operator)
    if not parent_start or not parent_end:
        return False
    return parent_start <= subagent_start and parent_end >= subagent_start
def contained_parent_sort_key(subagent_start, operator):
    parent_start = session_started_at(operator) or subagent_start
    parent_end = session_last_activity_at(operator) or parent_start
    return (
        0 if session_is_codex_operator(operator) else 1,
        abs((subagent_start - parent_start).total_seconds()),
        abs((parent_end - subagent_start).total_seconds()),
        operator.get("id") or "",
    )
def fallback_parent_sort_key(subagent_start, operator):
    parent_time = session_last_activity_at(operator) or session_started_at(operator)
    distance = abs((subagent_start - parent_time).total_seconds()) if parent_time else 10**12
    return (
        0 if session_is_codex_operator(operator) else 1,
        distance,
        operator.get("id") or "",
    )
def find_subagent_parent(subagent, operators):
    subagent_start = session_started_at(subagent)
    if not subagent_start:
        return None
    same_context = [operator for operator in operators if sessions_share_work_context(operator, subagent)]
    contained = [operator for operator in same_context if operator_contains_subagent(operator, subagent, subagent_start)]
    if contained:
        return sorted(contained, key=lambda operator: contained_parent_sort_key(subagent_start, operator))[0]
    fallback_cutoff = subagent_start - timedelta(hours=SUBAGENT_PARENT_FALLBACK_HOURS)
    fallbacks = []
    for operator in same_context:
        parent_time = session_last_activity_at(operator) or session_started_at(operator)
        if parent_time and fallback_cutoff <= parent_time <= subagent_start:
            fallbacks.append(operator)
    if not fallbacks:
        return None
    return sorted(fallbacks, key=lambda operator: fallback_parent_sort_key(subagent_start, operator))[0]
def rebuild_subagent_links(conn):
    rows = [dict(row) for row in conn.execute("SELECT * FROM sessions").fetchall()]
    operators = [row for row in rows if session_is_operator_candidate(row)]
    subagents = [row for row in rows if session_is_subagent_candidate(row)]
    conn.execute("UPDATE sessions SET parent_session_id = NULL WHERE parent_session_id IS NOT NULL")
    linked = 0
    for subagent in subagents:
        parent = find_subagent_parent(subagent, operators)
        if not parent:
            continue
        conn.execute("UPDATE sessions SET parent_session_id = ? WHERE id = ?", (parent["id"], subagent["id"]))
        linked += 1
    return linked

### Reads
def row_dict(row):
    return dict(row) if row else None
def row_value(row, key, default=None):
    if not row:
        return default
    if hasattr(row, "keys") and key not in row.keys():
        return default
    value = row[key]
    return default if value is None else value
def digest_from_row(row):
    if not row:
        return None
    title = row_value(row, "title", None)
    if title is None:
        title = row_value(row, "digest_title", "")
    if row_value(row, "asked_json") is None and row_value(row, "notes_json") is None and row_value(row, "recap") is None and not title:
        return None
    return {
        "title": title or "",
        "asked": json.loads(row["asked_json"] or "[]"),
        "notes": json.loads(row["notes_json"] or "[]"),
        "recap": row["recap"] or "",
        "model_used": row["model_used"],
        "created_at": row["created_at"],
    }
def digest_payload(row):
    digest = digest_from_row(row)
    if not digest:
        return None
    return {"title": digest["title"], "asked": digest["asked"], "notes": digest["notes"], "recap": digest["recap"]}
def preview(text, limit=300):
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit - 3] + "..."
def display_title(digest_title=None, session_title=None, user_text=None):
    for value in (digest_title, session_title):
        text = " ".join(str(value or "").split())
        if text:
            return text
    return preview(user_text, limit=80)
def commits_for_exchange(conn, exchange_id):
    rows = conn.execute(
        """
        SELECT commits.sha, commits.subject, commits.author_date, commits.is_agent_commit
        FROM links
        JOIN commits ON commits.sha = links.sha
        WHERE links.exchange_id = ?
        ORDER BY commits.author_date
        """,
        (exchange_id,),
    ).fetchall()
    return [dict(row) for row in rows]
def exchange_digest_row(conn, exchange_id):
    return conn.execute("SELECT * FROM digests WHERE exchange_id = ?", (exchange_id,)).fetchone()
def exchange_exists(conn, exchange_id):
    return conn.execute("SELECT 1 FROM exchanges WHERE id = ?", (exchange_id,)).fetchone() is not None
def validate_exchange_id(value):
    if not isinstance(value, str) or not value or len(value) > 300:
        return False
    if "/" in value or "\\" in value or "?" in value:
        return False
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return False
    return ":" in value and "#" in value
def origin_filter_sql():
    return "COALESCE(exchanges.origin, sessions.origin, 'operator') = 'operator' AND COALESCE(sessions.origin, 'operator') = 'operator'"
def list_turns(conn, branch=None, session_id=None, limit=20, include_delegated=False):
    params = []
    filters = []
    if not include_delegated:
        filters.append(origin_filter_sql())
    if branch:
        filters.append("(sessions.branch = ? OR EXISTS (SELECT 1 FROM links l JOIN commits c ON c.sha = l.sha WHERE l.exchange_id = exchanges.id AND c.branch = ?))")
        params.extend([branch, branch])
    if session_id:
        filters.append("exchanges.session_id = ?")
        params.append(session_id)
    where = "WHERE " + " AND ".join(filters) if filters else ""
    params.append(limit)
    rows = conn.execute(
        """
        SELECT exchanges.*, sessions.label AS session_label, sessions.platform AS session_platform,
            sessions.title AS session_title, sessions.origin AS session_origin, sessions.source_url AS session_source_url,
            digests.title AS digest_title, digests.asked_json, digests.notes_json, digests.recap, digests.model_used, digests.created_at
        FROM exchanges
        JOIN sessions ON sessions.id = exchanges.session_id
        LEFT JOIN digests ON digests.exchange_id = exchanges.id
        """ + where + """
        ORDER BY exchanges.user_ts DESC,
            CASE exchanges.kind WHEN 'primary' THEN 0 WHEN 'quick' THEN 1 ELSE 2 END,
            exchanges.id DESC
        LIMIT ?
        """,
        params,
    ).fetchall()
    payload = []
    for row in rows:
        digest = digest_payload(row)
        payload.append({
            "id": row["id"],
            "session_id": row["session_id"],
            "session_label": row["session_label"],
            "session_origin": row["session_origin"] or OPERATOR_ORIGIN,
            "source_url": row["session_source_url"],
            "origin": row["origin"] or row["session_origin"] or OPERATOR_ORIGIN,
            "turn_title": display_title(row["digest_title"], row["session_title"], row["user_text"]),
            "kind": row["kind"],
            "user_ts": row["user_ts"],
            "user_preview": preview(row["user_text"]),
            "has_digest": digest is not None,
            "digest": digest,
            "commits": commits_for_exchange(conn, row["id"]),
        })
    return payload
def list_subagents(conn, parent_session_id, limit=20):
    rows = conn.execute(
        """
        SELECT child.id, child.label, child.started, child.last_activity,
            first_exchange.user_text AS instruction,
            last_exchange.response_text AS recap
        FROM sessions child
        LEFT JOIN exchanges first_exchange ON first_exchange.id = (
            SELECT id FROM exchanges
            WHERE session_id = child.id AND LENGTH(TRIM(COALESCE(user_text, ''))) > 0
            ORDER BY idx ASC
            LIMIT 1
        )
        LEFT JOIN exchanges last_exchange ON last_exchange.id = (
            SELECT id FROM exchanges
            WHERE session_id = child.id AND LENGTH(TRIM(COALESCE(response_text, ''))) > 0
            ORDER BY idx DESC
            LIMIT 1
        )
        WHERE (child.parent_session_id = ?
               OR (instr(child.parent_session_id, ':') > 0
                   AND substr(child.parent_session_id, instr(child.parent_session_id, ':') + 1) = ?))
            AND child.platform = 'codex'
            AND COALESCE(child.origin, 'operator') = 'delegated'
        ORDER BY child.started DESC, child.last_activity DESC, child.id DESC
        LIMIT ?
        """,
        (parent_session_id, parent_session_id, limit),
    ).fetchall()
    return [{
        "id": row["id"],
        "label": row["label"],
        "started": row["started"],
        "last_activity": row["last_activity"],
        "instruction": preview(row["instruction"], limit=400),
        "recap": preview(row["recap"], limit=800),
    } for row in rows]
def get_exchange(conn, exchange_id):
    row = conn.execute(
        """
        SELECT exchanges.*, sessions.label AS session_label, sessions.platform AS session_platform,
            sessions.title AS session_title, sessions.origin AS session_origin, sessions.source_url AS session_source_url,
            digests.title AS digest_title, digests.asked_json, digests.notes_json, digests.recap, digests.model_used, digests.created_at
        FROM exchanges
        JOIN sessions ON sessions.id = exchanges.session_id
        LEFT JOIN digests ON digests.exchange_id = exchanges.id
        WHERE exchanges.id = ?
        """,
        (exchange_id,),
    ).fetchone()
    if not row:
        return None
    digest = digest_payload(row)
    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "session_label": row["session_label"],
        "session_origin": row["session_origin"] or OPERATOR_ORIGIN,
        "source_url": row["session_source_url"],
        "origin": row["origin"] or row["session_origin"] or OPERATOR_ORIGIN,
        "turn_title": display_title(row["digest_title"], row["session_title"], row["user_text"]),
        "kind": row["kind"],
        "user_ts": row["user_ts"],
        "user_text": row["user_text"],
        "response_text": row["response_text"],
        "response_final_text": row["response_final_text"],
        "response_recap": row["response_recap"],
        "response_end_ts": row["response_end_ts"],
        "has_digest": digest is not None,
        "digest": digest,
        "commits": commits_for_exchange(conn, exchange_id),
    }
def missing_digest_exchanges(conn, limit=20, since=None, operator_only=True):
    filters = [
        "digests.exchange_id IS NULL",
        "LENGTH(TRIM(COALESCE(exchanges.response_text, ''))) > 0",
    ]
    params = []
    if operator_only:
        filters.append(origin_filter_sql())
    if since:
        filters.append("exchanges.user_ts >= ?")
        params.append(since)
    params.append(limit)
    return conn.execute(
        """
        SELECT exchanges.*
        FROM exchanges
        JOIN sessions ON sessions.id = exchanges.session_id
        LEFT JOIN digests ON digests.exchange_id = exchanges.id
        WHERE """ + " AND ".join(filters) + """
        ORDER BY CASE exchanges.kind WHEN 'primary' THEN 0 WHEN 'quick' THEN 1 ELSE 2 END,
            exchanges.user_ts DESC
        LIMIT ?
        """,
        params,
    ).fetchall()
SESSION_END_COMMANDS = frozenset({"close", "exit", "quit"})
def parse_time(value):
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed
def is_session_end_command(text):
    """True for CLI close/exit/quit (with or without leading slash)."""
    cleaned = str(text or "").strip().lower()
    if cleaned.startswith("/"):
        cleaned = cleaned[1:].strip()
    return cleaned in SESSION_END_COMMANDS
def exchange_is_unanswered(row):
    return not str(row["response_text"] or "").strip()
def skip_exchange_for_turn_status(row):
    """Unanswered session-end commands are not a live wait on the AI."""
    return exchange_is_unanswered(row) and is_session_end_command(row["user_text"])
def status_state(row):
    if exchange_is_unanswered(row):
        if is_session_end_command(row["user_text"]):
            return "your-turn", row["user_ts"] or row["last_activity"]
        return "waiting-on-ai", row["user_ts"]
    return "your-turn", row["response_end_ts"] or row["last_activity"] or row["user_ts"]
def turn_status_payload(row):
    state, since = status_state(row)
    recap = row["recap"] or preview(row["user_text"])
    return {
        "worktree": row["worktree"],
        "branch": row["branch"],
        "state": state,
        "since": since,
        "exchange_id": row["id"],
        "session_id": row["session_id"],
        "session_label": row["session_label"],
        "source_url": row["source_url"],
        "turn_title": display_title(row["digest_title"], row["session_title"], row["user_text"]),
        "recap": recap,
        "user_preview": preview(row["user_text"]),
        "last_activity": row["last_activity"],
    }
def list_turn_status(conn, active_days=14, now=None):
    now_dt = now or datetime.now().astimezone()
    cutoff = now_dt - timedelta(days=active_days)
    rows = conn.execute(
        """
        SELECT exchanges.*, sessions.label AS session_label, sessions.title AS session_title,
            sessions.worktree, sessions.branch, sessions.last_activity, sessions.started, sessions.source_url,
            digests.title AS digest_title, digests.recap
        FROM sessions
        JOIN exchanges ON exchanges.session_id = sessions.id
        LEFT JOIN digests ON digests.exchange_id = exchanges.id
        WHERE sessions.worktree IS NOT NULL
            AND """ + origin_filter_sql() + """
        """
    ).fetchall()
    candidates = []
    for row in rows:
        active_time = parse_time(row["last_activity"]) or parse_time(row["started"])
        if not active_time or active_time < cutoff:
            continue
        user_time = parse_time(row["user_ts"]) or active_time
        candidates.append((active_time, user_time, row))
    candidates.sort(key=lambda item: (item[0], item[1], item[2]["idx"]), reverse=True)
    payload = []
    seen = set()
    fallbacks = {}
    for active_time, user_time, row in candidates:
        key = (row["worktree"], row["branch"])
        if key in seen:
            continue
        if skip_exchange_for_turn_status(row):
            if key not in fallbacks:
                fallbacks[key] = row
            continue
        seen.add(key)
        payload.append(turn_status_payload(row))
    for key, row in fallbacks.items():
        if key in seen:
            continue
        seen.add(key)
        payload.append(turn_status_payload(row))
    return payload

### Agent status
AGENT_STALL_MINUTES = 30
def classify_agent_state(user_text, response_text, user_ts, last_activity, now, response_end_ts=None):
    """No semantic parsing of the response: answered turns are always done. A stale
    unanswered turn is the data signature of an AI paused for user interaction (popped
    question or run-command permission), so it reads needs-you; 'error' is reserved for
    a future semantic-classification phase."""
    if exchange_is_unanswered({"response_text": response_text}):
        since = user_ts or last_activity
        if is_session_end_command(user_text):
            return "done", "session-end", since
        active_time = parse_time(user_ts) or parse_time(last_activity)
        if not active_time or now - active_time > timedelta(minutes=AGENT_STALL_MINUTES):
            return "needs-you", "paused", since
        return "thinking", "working", since
    return "done", "completed", response_end_ts or last_activity or user_ts
def list_agent_status(conn, hours=48, limit=16, now=None):
    now_dt = now or datetime.now().astimezone()
    cutoff = now_dt - timedelta(hours=hours)
    rows = conn.execute(
        """
        SELECT sessions.id AS session_id, sessions.label AS session_label, sessions.platform,
            sessions.entrypoint, sessions.host, sessions.remote_control, sessions.worktree,
            sessions.branch, sessions.source_url, sessions.title AS session_title,
            sessions.started, sessions.last_activity,
            exchanges.id AS exchange_id, exchanges.idx, exchanges.user_ts, exchanges.user_text,
            exchanges.response_text, exchanges.response_end_ts,
            digests.title AS digest_title, digests.recap
        FROM sessions
        JOIN exchanges ON exchanges.id = (
            SELECT latest.id
            FROM exchanges latest
            WHERE latest.session_id = sessions.id
            ORDER BY latest.idx DESC, latest.id DESC
            LIMIT 1
        )
        LEFT JOIN digests ON digests.exchange_id = exchanges.id
        WHERE """ + origin_filter_sql() + """
        """
    ).fetchall()
    candidates = []
    for row in rows:
        active_time = parse_time(row["last_activity"]) or parse_time(row["started"])
        if not active_time or active_time < cutoff:
            continue
        candidates.append((active_time, row))
    candidates.sort(key=lambda item: (item[0], item[1]["session_id"]), reverse=True)
    payload = []
    for active_time, row in candidates[:limit]:
        state, reason, since = classify_agent_state(
            row["user_text"],
            row["response_text"],
            row["user_ts"],
            row["last_activity"],
            now_dt,
            response_end_ts=row["response_end_ts"],
        )
        payload.append({
            "session_id": row["session_id"],
            "session_label": row["session_label"],
            "platform": row["platform"],
            "entrypoint": row["entrypoint"],
            "host": row["host"],
            "remote_control": bool(row["remote_control"]),
            "worktree": row["worktree"],
            "branch": row["branch"],
            "state": state,
            "state_reason": reason,
            "since": since,
            "last_activity": row["last_activity"],
            "started": row["started"],
            "exchange_id": row["exchange_id"],
            "turn_title": display_title(row["digest_title"], row["session_title"], row["user_text"]),
            "recap": row["recap"] or preview(row["user_text"]),
            "user_preview": preview(row["user_text"]),
            "source_url": row["source_url"],
        })
    return payload
