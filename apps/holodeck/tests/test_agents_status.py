import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from apps.holodeck import server as holodeck_server
from apps.holodeck.turns import db

VALID_STATES = {"thinking", "done", "needs-you", "error"}
REQUIRED_AGENT_KEYS = (
    "session_id",
    "session_label",
    "platform",
    "entrypoint",
    "host",
    "remote_control",
    "worktree",
    "branch",
    "state",
    "state_reason",
    "since",
    "last_activity",
    "started",
    "exchange_id",
    "turn_title",
    "recap",
    "user_preview",
    "source_url",
)

### Fixtures
def iso_at(value):
    return value.isoformat(timespec="seconds")
def init_memory_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    db.init_db(conn)
    return conn
def init_tmp_db(path):
    conn = db.connect(path)
    db.init_db(conn)
    return conn
def make_session(session_id, platform="claude", entrypoint="cli", host="local", worktree="/repo/main", branch="feature/test", origin="operator", started="2026-07-23T10:00:00-07:00", last_activity="2026-07-23T10:20:00-07:00", remote_control=False, label=None, title=None, source_url=None):
    return {
        "id": session_id,
        "platform": platform,
        "entrypoint": entrypoint,
        "host": host,
        "remote_control": remote_control,
        "bridge_session_id": None,
        "source_path": session_id,
        "source_url": source_url,
        "project": worktree,
        "worktree": worktree,
        "branch": branch,
        "label": label or platform.title() + " Session",
        "model": None,
        "interface": entrypoint,
        "origin": origin,
        "parent_session_id": None,
        "title": title,
        "started": started,
        "last_activity": last_activity,
        "ingested_at": "now",
    }
def make_exchange(exchange_id, session_id, idx=None, user_ts="2026-07-23T10:00:00-07:00", user_text="Build the thing", response_text="Done.", response_end_ts="2026-07-23T10:10:00-07:00", origin="operator"):
    return {
        "id": exchange_id,
        "session_id": session_id,
        "idx": idx if idx is not None else int(exchange_id.rsplit("#", 1)[1]),
        "kind": "primary",
        "user_ts": user_ts,
        "user_text": user_text,
        "response_text": response_text,
        "response_end_ts": response_end_ts,
        "origin": origin,
        "follow_up_of": None,
    }
def state_reason(result):
    return result[0], result[1]

### Classification
def test_classify_agent_state_cases():
    now = datetime.fromisoformat("2026-07-23T12:00:00-07:00")
    assert state_reason(db.classify_agent_state("Build", "", "2026-07-23T11:55:00-07:00", "2026-07-23T11:55:00-07:00", now)) == ("thinking", "working")
    assert state_reason(db.classify_agent_state("Build", "", "2026-07-23T11:29:00-07:00", "2026-07-23T11:29:00-07:00", now)) == ("needs-you", "paused")
    assert state_reason(db.classify_agent_state("Build", "", None, None, now)) == ("needs-you", "paused")
    assert state_reason(db.classify_agent_state("/quit", "", "2026-07-23T11:00:00-07:00", "2026-07-23T11:00:00-07:00", now)) == ("done", "session-end")
    assert state_reason(db.classify_agent_state("Build", "I found two paths.\nWhich one should I use?", "2026-07-23T11:00:00-07:00", "2026-07-23T11:10:00-07:00", now, response_end_ts="2026-07-23T11:10:00-07:00")) == ("done", "completed")
    assert state_reason(db.classify_agent_state("Build", "Failed.\nTraceback (most recent call last)\nValueError: bad", "2026-07-23T11:00:00-07:00", "2026-07-23T11:10:00-07:00", now)) == ("done", "completed")
    assert state_reason(db.classify_agent_state("Build", "Implemented and verified.", "2026-07-23T11:00:00-07:00", "2026-07-23T11:10:00-07:00", now)) == ("done", "completed")

### Listing
def test_list_agent_status_filters_orders_latest_limit_and_null_worktree():
    conn = init_memory_db()
    now = datetime.fromisoformat("2026-07-23T12:00:00-07:00")
    db.upsert_session(conn, make_session("claude-code:thinking", worktree=None, branch="feature/null", last_activity="2026-07-23T11:59:00-07:00", remote_control=True, label="Claude CLI - Fable 5", title="Thinking session"))
    db.upsert_exchange(conn, make_exchange("claude-code:thinking#1", "claude-code:thinking", user_ts="2026-07-23T11:59:00-07:00", user_text="Keep working", response_text="", response_end_ts=None))
    db.upsert_session(conn, make_session("cursor:needs", platform="cursor", entrypoint="app", worktree="/repo/main", branch="feature/test", last_activity="2026-07-23T11:50:00-07:00", label="Cursor IDE - Composer", title="Needs session"))
    db.upsert_exchange(conn, make_exchange("cursor:needs#1", "cursor:needs", idx=1, user_ts="2026-07-23T11:00:00-07:00", user_text="Build the first part", response_text="Done.", response_end_ts="2026-07-23T11:05:00-07:00"))
    db.upsert_exchange(conn, make_exchange("cursor:needs#2", "cursor:needs", idx=2, user_ts="2026-07-23T11:45:00-07:00", user_text="Pick a branch", response_text="Which branch should I target?", response_end_ts="2026-07-23T11:50:00-07:00"))
    db.upsert_digest(conn, "cursor:needs#2", {"title": "Latest branch question", "asked": [], "notes": [], "recap": "Asked which branch to target.", "model_used": "mock", "created_at": "now"})
    conn.execute("UPDATE digests SET asked_json = ? WHERE exchange_id = ?", ("not-json", "cursor:needs#2"))
    db.upsert_session(conn, make_session("codex:old", platform="codex", last_activity="2026-07-23T08:00:00-07:00"))
    db.upsert_exchange(conn, make_exchange("codex:old#1", "codex:old", user_ts="2026-07-23T08:00:00-07:00"))
    db.upsert_session(conn, make_session("codex:delegated", platform="codex", origin="delegated", last_activity="2026-07-23T11:58:00-07:00"))
    db.upsert_exchange(conn, make_exchange("codex:delegated#1", "codex:delegated", user_ts="2026-07-23T11:58:00-07:00", origin="delegated", response_text="", response_end_ts=None))
    db.upsert_session(conn, make_session("cursor:no-exchanges", platform="cursor", last_activity="2026-07-23T11:57:00-07:00"))
    rows = db.list_agent_status(conn, hours=2, limit=16, now=now)
    assert [row["session_id"] for row in rows] == ["claude-code:thinking", "cursor:needs"]
    assert rows[0]["state"] == "thinking"
    assert rows[0]["worktree"] is None
    assert rows[0]["remote_control"] is True
    assert rows[1]["state"] == "done"
    assert rows[1]["state_reason"] == "completed"
    assert rows[1]["exchange_id"] == "cursor:needs#2"
    assert rows[1]["turn_title"] == "Latest branch question"
    assert rows[1]["recap"] == "Asked which branch to target."
    limited = db.list_agent_status(conn, hours=2, limit=1, now=now)
    assert [row["session_id"] for row in limited] == ["claude-code:thinking"]
    conn.close()

### Endpoint
def test_agents_endpoint_returns_temp_db_and_validates(tmp_path, monkeypatch):
    db_path = tmp_path / "turns.db"
    conn = init_tmp_db(db_path)
    now = datetime.now().astimezone()
    started = iso_at(now - timedelta(minutes=20))
    active = iso_at(now - timedelta(minutes=5))
    db.upsert_session(conn, make_session("codex:endpoint", platform="codex", started=started, last_activity=active, label="Codex CLI - GPT 5.6", source_url="https://chatgpt.com/codex/tasks/codex-endpoint"))
    db.upsert_exchange(conn, make_exchange("codex:endpoint#1", "codex:endpoint", user_ts=started, user_text="Build endpoint", response_text="Implemented.", response_end_ts=active))
    conn.commit()
    conn.close()
    monkeypatch.setattr(holodeck_server, "TURNS_DB_PATH", db_path)
    client = TestClient(holodeck_server.app)
    response = client.get("/api/agents")
    assert response.status_code == 200
    payload = response.json()
    assert "generated_at" in payload
    assert len(payload["agents"]) == 1
    assert payload["agents"][0]["session_id"] == "codex:endpoint"
    assert payload["agents"][0]["state"] == "done"
    assert payload["agents"][0]["remote_control"] is False
    assert client.get("/api/agents?hours=0").status_code == 400
    assert client.get("/api/agents?limit=999").status_code == 400

### Sample payload
def test_sample_agents_json_parses_and_has_required_shape():
    path = Path(__file__).resolve().parents[1] / "web" / "sample-agents.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    agents = data.get("agents")
    assert data.get("generated_at")
    assert isinstance(agents, list)
    assert len(agents) == 6
    assert {agent["state"] for agent in agents} >= VALID_STATES
    assert {agent["platform"] for agent in agents} >= {"claude", "codex", "cursor"}
    assert any(agent["host"] == "cloud" for agent in agents)
    assert any(agent["worktree"] is None for agent in agents)
    for agent in agents:
        assert set(REQUIRED_AGENT_KEYS) <= agent.keys()
        assert agent["state"] in VALID_STATES
        assert isinstance(agent["remote_control"], bool)
