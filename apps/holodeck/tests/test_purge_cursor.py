"""Tests for standalone Cursor chat scrubbing from Holodeck stores."""

import json
import sqlite3

from apps.holodeck.turns import db
from apps.holodeck.turns import purge_cursor

### Fixtures
def make_cursor_db(path, composer_ids):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE cursorDiskKV (key TEXT PRIMARY KEY, value BLOB)")
    for composer_id in composer_ids:
        conn.execute(
            "INSERT INTO cursorDiskKV(key, value) VALUES (?, ?)",
            ("composerData:" + composer_id, json.dumps({"composerId": composer_id, "name": "Chat"})),
        )
        conn.execute(
            "INSERT INTO cursorDiskKV(key, value) VALUES (?, ?)",
            ("bubbleId:" + composer_id + ":b1", json.dumps({"text": "hello"})),
        )
    conn.commit()
    conn.close()
def seed_turns(conn, composer_id, with_child=False):
    session_id = "cursor:" + composer_id
    db.upsert_session(conn, {
        "id": session_id,
        "platform": "cursor",
        "entrypoint": "app",
        "host": "local",
        "source_path": composer_id,
        "project": "/repo/main",
        "worktree": "/repo/main",
        "branch": "feature/test",
        "label": "Cursor IDE",
        "model": None,
        "interface": "Cursor IDE",
        "origin": "operator",
        "title": "Secret chat",
        "started": "2026-07-16T10:00:00-07:00",
        "last_activity": "2026-07-16T10:20:00-07:00",
        "ingested_at": "now",
    })
    db.upsert_exchange(conn, {
        "id": session_id + "#1",
        "session_id": session_id,
        "idx": 1,
        "kind": "primary",
        "user_ts": "2026-07-16T10:00:00-07:00",
        "user_text": "do not keep this",
        "response_text": "ok",
        "response_end_ts": "2026-07-16T10:20:00-07:00",
        "follow_up_of": None,
    })
    db.upsert_digest(conn, session_id + "#1", {
        "title": "Secret",
        "asked": ["do not keep this"],
        "notes": [],
        "recap": "kept",
        "model_used": "mock",
        "created_at": "now",
    })
    db.upsert_commit(conn, {
        "sha": "aaa111",
        "branch": "feature/test",
        "worktree": "/repo/main",
        "author": "Agent",
        "author_email": "a@b.c",
        "author_date": "2026-07-16T10:21:00-07:00",
        "committer_date": "2026-07-16T10:21:00-07:00",
        "subject": "feat: secret",
        "body": "",
        "is_agent_commit": 1,
    })
    db.upsert_link(conn, {
        "exchange_id": session_id + "#1",
        "sha": "aaa111",
        "method": "window",
        "confidence": 0.5,
    })
    if with_child:
        db.upsert_session(conn, {
            "id": "codex:child",
            "platform": "codex",
            "entrypoint": "subagent",
            "host": "local",
            "source_path": "child",
            "project": "/repo/main",
            "worktree": "/repo/main",
            "branch": "feature/test",
            "label": "Codex Subagent",
            "model": None,
            "interface": "Codex Subagent",
            "origin": "delegated",
            "parent_session_id": session_id,
            "title": "Child",
            "started": "2026-07-16T10:05:00-07:00",
            "last_activity": "2026-07-16T10:08:00-07:00",
            "ingested_at": "now",
        })
    conn.commit()
def write_snapshot(path, composer_id):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "layers": {
            "sessions": [
                {"platform": "cursor", "id": composer_id, "title": "Secret chat"},
                {"platform": "codex", "id": "keep-me", "title": "Keep"},
            ]
        }
    }
    path.write_text(json.dumps(data), encoding="utf-8")

### Tests
def test_normalize_composer_id():
    assert purge_cursor.normalize_composer_id("abc") == "abc"
    assert purge_cursor.normalize_composer_id("cursor:abc") == "abc"
    assert purge_cursor.normalize_composer_id("composerData:abc") == "abc"
    assert purge_cursor.normalize_composer_id("  ") is None
def test_inspect_and_skip_when_still_in_cursor(tmp_path):
    composer_id = "comp-live"
    cursor_db = tmp_path / "state.vscdb"
    make_cursor_db(cursor_db, [composer_id])
    turns_path = tmp_path / "turns.db"
    conn = db.connect(turns_path)
    db.init_db(conn)
    seed_turns(conn, composer_id)
    conn.close()
    snapshot = tmp_path / "snapshot.json"
    write_snapshot(snapshot, composer_id)
    report = purge_cursor.purge_deleted_cursor_session(
        composer_id,
        execute=True,
        cursor_db=cursor_db,
        root=tmp_path,
        turns_db_path=turns_path,
        snapshot_path=snapshot,
    )
    assert report["skipped"] is True
    assert report["purged"] is False
    assert report["in_cursor"] is True
    conn = db.connect(turns_path)
    assert conn.execute("SELECT COUNT(*) FROM sessions WHERE id = ?", ("cursor:" + composer_id,)).fetchone()[0] == 1
    conn.close()
def test_dry_run_does_not_mutate(tmp_path):
    composer_id = "comp-gone"
    cursor_db = tmp_path / "state.vscdb"
    make_cursor_db(cursor_db, [])
    turns_path = tmp_path / "turns.db"
    conn = db.connect(turns_path)
    db.init_db(conn)
    seed_turns(conn, composer_id, with_child=True)
    conn.close()
    snapshot = tmp_path / "snapshot.json"
    write_snapshot(snapshot, composer_id)
    report = purge_cursor.purge_deleted_cursor_session(
        composer_id,
        execute=False,
        cursor_db=cursor_db,
        root=tmp_path,
        turns_db_path=turns_path,
        snapshot_path=snapshot,
    )
    assert report["dry_run"] is True
    assert report["would_purge"] is True
    assert report["purged"] is False
    conn = db.connect(turns_path)
    assert conn.execute("SELECT COUNT(*) FROM sessions WHERE id = ?", ("cursor:" + composer_id,)).fetchone()[0] == 1
    assert conn.execute("SELECT parent_session_id FROM sessions WHERE id = 'codex:child'").fetchone()[0] == "cursor:" + composer_id
    conn.close()
    data = json.loads(snapshot.read_text(encoding="utf-8"))
    assert any(s.get("id") == composer_id for s in data["layers"]["sessions"])
def test_execute_purges_turns_and_snapshot_and_verifies(tmp_path):
    composer_id = "comp-purge"
    cursor_db = tmp_path / "state.vscdb"
    make_cursor_db(cursor_db, [])
    turns_path = tmp_path / "turns.db"
    conn = db.connect(turns_path)
    db.init_db(conn)
    seed_turns(conn, composer_id, with_child=True)
    conn.close()
    snapshot = tmp_path / "snapshot.json"
    write_snapshot(snapshot, composer_id)
    projects = tmp_path / "projects"
    transcript = projects / "proj" / "agent-transcripts" / (composer_id + ".jsonl")
    transcript.parent.mkdir(parents=True)
    transcript.write_text('{"role":"user"}\n', encoding="utf-8")
    report = purge_cursor.purge_deleted_cursor_session(
        composer_id,
        execute=True,
        include_agent_transcripts=True,
        cursor_db=cursor_db,
        root=tmp_path,
        turns_db_path=turns_path,
        snapshot_path=snapshot,
        projects_root=projects,
    )
    assert report["purged"] is True
    assert report["verification"]["ok"] is True
    conn = db.connect(turns_path)
    assert conn.execute("SELECT COUNT(*) FROM sessions WHERE id = ?", ("cursor:" + composer_id,)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM exchanges WHERE session_id = ?", ("cursor:" + composer_id,)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM digests").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM links").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM commits WHERE sha = 'aaa111'").fetchone()[0] == 1
    assert conn.execute("SELECT parent_session_id FROM sessions WHERE id = 'codex:child'").fetchone()[0] is None
    conn.close()
    data = json.loads(snapshot.read_text(encoding="utf-8"))
    assert [s["id"] for s in data["layers"]["sessions"]] == ["keep-me"]
    assert not transcript.exists()
def test_force_purges_even_if_still_in_cursor(tmp_path):
    composer_id = "comp-force"
    cursor_db = tmp_path / "state.vscdb"
    make_cursor_db(cursor_db, [composer_id])
    turns_path = tmp_path / "turns.db"
    conn = db.connect(turns_path)
    db.init_db(conn)
    seed_turns(conn, composer_id)
    conn.close()
    snapshot = tmp_path / "snapshot.json"
    write_snapshot(snapshot, composer_id)
    report = purge_cursor.purge_deleted_cursor_session(
        "cursor:" + composer_id,
        execute=True,
        force=True,
        cursor_db=cursor_db,
        root=tmp_path,
        turns_db_path=turns_path,
        snapshot_path=snapshot,
    )
    assert report["in_cursor"] is True
    assert report["purged"] is True
    conn = db.connect(turns_path)
    assert conn.execute("SELECT COUNT(*) FROM sessions WHERE id = ?", ("cursor:" + composer_id,)).fetchone()[0] == 0
    conn.close()
def test_purge_all_missing_only_targets_absent(tmp_path):
    live_id = "live-1"
    gone_id = "gone-1"
    cursor_db = tmp_path / "state.vscdb"
    make_cursor_db(cursor_db, [live_id])
    turns_path = tmp_path / "turns.db"
    conn = db.connect(turns_path)
    db.init_db(conn)
    seed_turns(conn, live_id)
    seed_turns(conn, gone_id)
    conn.close()
    snapshot = tmp_path / "snapshot.json"
    write_snapshot(snapshot, gone_id)
    summary = purge_cursor.purge_all_deleted_cursor_sessions(
        execute=True,
        cursor_db=cursor_db,
        root=tmp_path,
        turns_db_path=turns_path,
        snapshot_path=snapshot,
    )
    assert summary["checked"] == 2
    assert summary["purged_count"] == 1
    assert summary["skipped_still_in_cursor"] == 1
    conn = db.connect(turns_path)
    assert conn.execute("SELECT COUNT(*) FROM sessions WHERE id = ?", ("cursor:" + live_id,)).fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM sessions WHERE id = ?", ("cursor:" + gone_id,)).fetchone()[0] == 0
    conn.close()
