import os
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.holodeck import server as holodeck_server

### Fixtures
class CollectResult:
    returncode = 0
    stdout = "snapshot ok"
@pytest.fixture(autouse=True)
def reset_ai_sync_status():
    wait_for_ai_sync_idle()
    holodeck_server.set_ai_sync_status(holodeck_server.base_ai_sync_status())
    yield
    wait_for_ai_sync_idle()
    holodeck_server.set_ai_sync_status(holodeck_server.base_ai_sync_status())

### Helpers
def write_file(path, content, mtime):
    path.write_text(content, encoding="utf-8")
    os.utime(path, (mtime, mtime))
    return path
def wait_for_ai_sync_idle(timeout=2):
    deadline = time.time() + timeout
    while holodeck_server.AI_SYNC_LOCK.locked() and time.time() < deadline:
        time.sleep(0.01)
    return not holodeck_server.AI_SYNC_LOCK.locked()
def wait_for_ai_sync_status(timeout=2):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = holodeck_server.get_ai_sync_status()
        if not status.get("running"):
            return status
        time.sleep(0.01)
    return holodeck_server.get_ai_sync_status()

### Downloads pickup
def test_claude_export_pickup_moves_matching_files_and_skips_duplicates(tmp_path):
    downloads = tmp_path / "Downloads"
    target = tmp_path / "Documents/Code/_LOCAL_FILES/fof-mono/ai-sessions/cloud_claude"
    downloads.mkdir()
    target.mkdir(parents=True)
    duplicate = write_file(downloads / "holodeck-claude-cloud-duplicate.json", "same", 1784472600)
    duplicate_target = target / holodeck_server.claude_export_target_name(duplicate)
    write_file(duplicate_target, "same", 1784472600)
    first = write_file(downloads / "holodeck-claude-cloud-export.json", "one", 1784472601)
    second = write_file(downloads / "holodeck-cc-export.json", "two", 1784472602)
    write_file(downloads / ".holodeck-cc-hidden.json", "hidden", 1784472603)
    write_file(downloads / "not-holodeck.json", "no", 1784472604)
    moves = holodeck_server.claude_export_pickup_moves(home=tmp_path)
    assert [Path(move["source"]).name for move in moves] == [first.name, second.name]
    assert [Path(move["target"]).name for move in moves] == [
        holodeck_server.claude_export_target_name(first),
        holodeck_server.claude_export_target_name(second),
    ]

### Refresh orchestration
def test_refresh_status_reports_lock(monkeypatch):
    client = TestClient(holodeck_server.app)
    idle = client.get("/api/refresh/status")
    assert idle.status_code == 200
    assert idle.json() == {"running": False}
    assert holodeck_server.REFRESH_LOCK.acquire(blocking=False)
    try:
        busy = client.get("/api/refresh/status")
        assert busy.status_code == 200
        assert busy.json() == {"running": True}
        conflict = client.post("/api/refresh", json={})
        assert conflict.status_code == 409
    finally:
        holodeck_server.REFRESH_LOCK.release()
def test_refresh_starts_ai_sync_and_single_flights(monkeypatch):
    client = TestClient(holodeck_server.app)
    started = threading.Event()
    release = threading.Event()
    def fake_build(root, db_path):
        started.set()
        release.wait(2)
        return {"sessions": 5, "exchanges": 7, "cloud_tasks": 3, "claude_cloud_sessions": 2, "notes": [], "db_path": str(db_path)}
    monkeypatch.setattr(holodeck_server, "run_collect_subprocess", lambda layers=None: CollectResult())
    monkeypatch.setattr(holodeck_server, "pickup_downloaded_claude_exports", lambda: {"moved": 2, "files": ["one.json", "two.json"]})
    monkeypatch.setattr(holodeck_server.turns_ingest, "build", fake_build)
    monkeypatch.setattr(holodeck_server, "run_ai_sync_s3", lambda: {"ok": True, "tail": "uploaded 0"})
    response = client.post("/api/refresh", json={})
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "ai_sync" in payload
    assert {"downloads_moved", "turns", "s3", "running"} <= set(payload["ai_sync"])
    assert started.wait(1)
    second = client.post("/api/refresh", json={})
    assert second.status_code == 200
    assert second.json()["ai_sync"]["already_running"] is True
    release.set()
    status = wait_for_ai_sync_status()
    assert status["running"] is False
    assert status["downloads_moved"] == 2
    assert status["turns"]["cloud_tasks"] == 3
    assert status["turns"]["claude_cloud_sessions"] == 2
    assert status["s3"]["ok"] is True
def test_ai_sync_status_returns_last_result():
    client = TestClient(holodeck_server.app)
    result = holodeck_server.base_ai_sync_status("complete", "completed")
    result["ok"] = True
    result["downloads_moved"] = 1
    result["turns"] = {"cloud_tasks": 4, "claude_cloud_sessions": 1}
    result["s3"] = {"ok": True, "tail": "done"}
    holodeck_server.set_ai_sync_status(result)
    response = client.get("/api/ai-sync-status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["downloads_moved"] == 1
    assert payload["turns"]["cloud_tasks"] == 4

def test_turns_status_survives_concurrent_write(tmp_path, monkeypatch):
    """A read endpoint must not 500 while the AI-sync holds a turns.db write lock.

    Regression for 'database is locked': open_turns_db previously ran init_db (a WRITE)
    on every read, colliding with the background turns-build write.
    """
    from apps.holodeck.turns import db as turns_db
    db_path = tmp_path / "turns.db"
    monkeypatch.setattr(holodeck_server, "TURNS_DB_PATH", db_path)
    holodeck_server.ensure_turns_schema()
    writer = turns_db.connect(db_path)
    writer.execute("BEGIN IMMEDIATE")
    writer.execute("INSERT INTO meta(key, value) VALUES ('probe', '1') ON CONFLICT(key) DO UPDATE SET value=excluded.value")
    try:
        client = TestClient(holodeck_server.app)
        response = client.get("/api/turns/status")
        assert response.status_code == 200, response.text
        assert "worktrees" in response.json()
        conn = holodeck_server.open_turns_db()
        try:
            assert isinstance(turns_db.list_turns(conn, limit=5), list)
        finally:
            conn.close()
    finally:
        writer.rollback()
        writer.close()
def test_turns_subagents_api_returns_trimmed_payload_and_empty_rows(tmp_path, monkeypatch):
    from apps.holodeck.turns import db as turns_db
    db_path = tmp_path / "turns.db"
    monkeypatch.setattr(holodeck_server, "TURNS_DB_PATH", db_path)
    holodeck_server.ensure_turns_schema()
    conn = turns_db.connect(db_path)
    parent = {"id": "cursor:parent", "platform": "cursor", "entrypoint": "app", "host": "local", "source_path": "parent", "source_url": None, "project": "/repo/main", "worktree": "/repo/main", "branch": "feature/test", "label": "Cursor IDE", "model": None, "interface": "Cursor IDE", "origin": "operator", "title": None, "started": "2026-07-20T10:00:00-07:00", "last_activity": "2026-07-20T10:30:00-07:00", "ingested_at": "now"}
    empty_parent = dict(parent, id="cursor:empty")
    child = {"id": "codex:sub", "platform": "codex", "entrypoint": "subagent", "host": "local", "source_path": "sub", "source_url": None, "project": "/repo/main", "worktree": "/repo/main", "branch": "feature/test", "label": "Codex Auto Review", "model": None, "interface": "Codex Subagent (fable5-w-codex)", "origin": "delegated", "parent_session_id": "cursor:parent", "title": None, "started": "2026-07-20T10:05:00-07:00", "last_activity": "2026-07-20T10:08:00-07:00", "ingested_at": "now"}
    turns_db.upsert_session(conn, parent)
    turns_db.upsert_session(conn, empty_parent)
    turns_db.upsert_session(conn, child)
    turns_db.upsert_exchange(conn, {"id": "codex:sub#1", "session_id": "codex:sub", "idx": 1, "kind": "primary", "user_ts": "2026-07-20T10:05:00-07:00", "user_text": "I" * 450, "response_text": "first", "response_end_ts": "2026-07-20T10:06:00-07:00", "origin": "delegated", "follow_up_of": None})
    turns_db.upsert_exchange(conn, {"id": "codex:sub#2", "session_id": "codex:sub", "idx": 2, "kind": "quick", "user_ts": "2026-07-20T10:07:00-07:00", "user_text": "follow up", "response_text": "R" * 900, "response_end_ts": "2026-07-20T10:08:00-07:00", "origin": "delegated", "follow_up_of": None})
    conn.commit()
    conn.close()
    client = TestClient(holodeck_server.app)
    response = client.get("/api/turns/subagents", params={"session": "cursor:parent"})
    assert response.status_code == 200
    rows = response.json()["subagents"]
    assert len(rows) == 1
    assert rows[0]["id"] == "codex:sub"
    assert rows[0]["label"] == "Codex Auto Review"
    assert len(rows[0]["instruction"]) <= 400
    assert rows[0]["instruction"].endswith("...")
    assert len(rows[0]["recap"]) <= 800
    assert rows[0]["recap"].endswith("...")
    empty = client.get("/api/turns/subagents", params={"session": "cursor:empty"})
    assert empty.status_code == 200
    assert empty.json()["subagents"] == []
