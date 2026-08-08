"""Purge Holodeck copies of Cursor chats that were deleted from Cursor's DB.

Standalone entry point — not wired into collect/build/refresh. Call explicitly via
`turns_cli.py purge-cursor` or `purge_deleted_cursor_session(...)`.

Safety:
- By default only acts when `composerData:{id}` is absent from Cursor's state.vscdb.
- Default is dry-run; pass execute=True / `--execute` to write deletes.
- `--force` skips the "must be gone from Cursor" gate (use only when sure).
"""

import json
import os
import sqlite3
import tempfile
from pathlib import Path

try:
    from apps.holodeck.collectors import sessions as sessions_collector
    from apps.holodeck.turns import db
except ImportError:
    from collectors import sessions as sessions_collector
    from turns import db

### Ids
def normalize_composer_id(value):
    text = str(value or "").strip()
    if not text:
        return None
    if text.startswith("composerData:"):
        text = text[len("composerData:"):]
    if text.startswith("cursor:"):
        text = text[len("cursor:"):]
    text = text.strip()
    return text or None
def session_id_for(composer_id):
    return "cursor:" + composer_id
def composer_id_from_session_id(session_id):
    text = str(session_id or "")
    if text.startswith("cursor:"):
        return text[len("cursor:"):] or None
    return None

### Cursor presence
def cursor_db_path(path=None):
    return Path(path) if path else sessions_collector.CURSOR_DB
def composer_exists_in_cursor(composer_id, cursor_db=None):
    """True when composerData:{composer_id} is still present in Cursor's global DB."""
    composer_id = normalize_composer_id(composer_id)
    if not composer_id:
        return False
    path = cursor_db_path(cursor_db)
    if not path.exists():
        return False
    uri = "file:" + str(path) + "?mode=ro"
    key = "composerData:" + composer_id
    with sqlite3.connect(uri, uri=True, timeout=5) as conn:
        row = conn.execute("SELECT 1 FROM cursorDiskKV WHERE key = ? LIMIT 1", (key,)).fetchone()
    return row is not None
def count_cursor_bubbles(composer_id, cursor_db=None):
    composer_id = normalize_composer_id(composer_id)
    if not composer_id:
        return 0
    path = cursor_db_path(cursor_db)
    if not path.exists():
        return 0
    uri = "file:" + str(path) + "?mode=ro"
    prefix = "bubbleId:" + composer_id + ":%"
    with sqlite3.connect(uri, uri=True, timeout=5) as conn:
        return conn.execute("SELECT COUNT(*) FROM cursorDiskKV WHERE key LIKE ?", (prefix,)).fetchone()[0]

### Holodeck inventory
def snapshot_path_for(root=None):
    return Path(root or db.repo_root()) / "apps/holodeck/data/snapshot.json"
def turns_traces(conn, composer_id):
    session_id = session_id_for(composer_id)
    session_row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    exchanges = conn.execute(
        "SELECT id FROM exchanges WHERE session_id = ? ORDER BY idx",
        (session_id,),
    ).fetchall()
    exchange_ids = [row["id"] for row in exchanges]
    digest_count = 0
    link_count = 0
    if exchange_ids:
        placeholders = ",".join("?" for _ in exchange_ids)
        digest_count = conn.execute(
            "SELECT COUNT(*) FROM digests WHERE exchange_id IN (" + placeholders + ")",
            exchange_ids,
        ).fetchone()[0]
        link_count = conn.execute(
            "SELECT COUNT(*) FROM links WHERE exchange_id IN (" + placeholders + ")",
            exchange_ids,
        ).fetchone()[0]
    child_rows = conn.execute(
        """
        SELECT id FROM sessions
        WHERE parent_session_id = ?
           OR parent_session_id = ?
           OR (instr(parent_session_id, ':') > 0
               AND substr(parent_session_id, instr(parent_session_id, ':') + 1) = ?)
        ORDER BY id
        """,
        (session_id, composer_id, composer_id),
    ).fetchall()
    return {
        "session_id": session_id,
        "session_present": session_row is not None,
        "session": dict(session_row) if session_row else None,
        "exchange_ids": exchange_ids,
        "exchange_count": len(exchange_ids),
        "digest_count": digest_count,
        "link_count": link_count,
        "child_session_ids": [row["id"] for row in child_rows],
    }
def snapshot_traces(snapshot_path, composer_id):
    path = Path(snapshot_path)
    if not path.exists():
        return {"path": str(path), "present": False, "indexes": [], "titles": []}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    sessions = ((data.get("layers") or {}).get("sessions")) or []
    indexes = []
    titles = []
    for idx, session in enumerate(sessions):
        if not isinstance(session, dict):
            continue
        platform = session.get("platform") or session.get("tool")
        sid = str(session.get("id") or "")
        if platform in ("cursor", None) and (sid == composer_id or sid == session_id_for(composer_id)):
            indexes.append(idx)
            titles.append(session.get("title"))
        elif sid == composer_id and platform == "cursor":
            indexes.append(idx)
            titles.append(session.get("title"))
    return {
        "path": str(path),
        "present": bool(indexes),
        "indexes": indexes,
        "titles": titles,
        "match_count": len(indexes),
    }
def agent_transcript_paths(composer_id, projects_root=None):
    """Optional Cursor leftover JSONL files keyed by composer UUID (not Holodeck-owned)."""
    root = Path(projects_root) if projects_root else Path.home() / ".cursor/projects"
    if not root.exists():
        return []
    matches = []
    for path in root.glob("*/agent-transcripts/" + composer_id + ".jsonl"):
        matches.append(path)
    for path in root.glob("*/agent-transcripts/" + composer_id + "/*.jsonl"):
        matches.append(path)
    return sorted(matches)
def inventory_holodeck(composer_id, root=None, turns_db_path=None, snapshot_path=None, projects_root=None):
    composer_id = normalize_composer_id(composer_id)
    root = Path(root or db.repo_root())
    turns_path = Path(turns_db_path) if turns_db_path else db.default_db_path(root)
    snap_path = Path(snapshot_path) if snapshot_path else snapshot_path_for(root)
    result = {
        "composer_id": composer_id,
        "session_id": session_id_for(composer_id) if composer_id else None,
        "turns_db_path": str(turns_path),
        "turns": None,
        "snapshot": snapshot_traces(snap_path, composer_id) if composer_id else None,
        "agent_transcripts": [str(p) for p in agent_transcript_paths(composer_id, projects_root)] if composer_id else [],
    }
    if not composer_id:
        return result
    if turns_path.exists():
        conn = db.connect(turns_path)
        try:
            db.init_db(conn)
            result["turns"] = turns_traces(conn, composer_id)
        finally:
            conn.close()
    else:
        result["turns"] = {
            "session_id": session_id_for(composer_id),
            "session_present": False,
            "session": None,
            "exchange_ids": [],
            "exchange_count": 0,
            "digest_count": 0,
            "link_count": 0,
            "child_session_ids": [],
            "missing_db": True,
        }
    return result

### Mutations
def _atomic_write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(path.parent),
        prefix=path.name + ".",
        suffix=".tmp",
        delete=False,
    )
    try:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.close()
        os.replace(handle.name, path)
    except Exception:
        handle.close()
        try:
            os.unlink(handle.name)
        except OSError:
            pass
        raise
def purge_turns_db(conn, composer_id):
    session_id = session_id_for(composer_id)
    before = turns_traces(conn, composer_id)
    cleared_children = 0
    if before["child_session_ids"]:
        cur = conn.execute(
            """
            UPDATE sessions
            SET parent_session_id = NULL
            WHERE parent_session_id = ?
               OR parent_session_id = ?
               OR (instr(parent_session_id, ':') > 0
                   AND substr(parent_session_id, instr(parent_session_id, ':') + 1) = ?)
            """,
            (session_id, composer_id, composer_id),
        )
        cleared_children = cur.rowcount
    deleted_sessions = 0
    if before["session_present"]:
        cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        deleted_sessions = cur.rowcount
    conn.commit()
    after = turns_traces(conn, composer_id)
    return {
        "before": before,
        "after": after,
        "deleted_sessions": deleted_sessions,
        "cleared_parent_refs": cleared_children,
        "deleted_exchanges": before["exchange_count"],
        "deleted_digests": before["digest_count"],
        "deleted_links": before["link_count"],
    }
def purge_snapshot(snapshot_path, composer_id):
    path = Path(snapshot_path)
    before = snapshot_traces(path, composer_id)
    if not path.exists() or not before["present"]:
        return {"before": before, "after": before, "removed": 0, "written": False}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    layers = data.setdefault("layers", {})
    sessions = list(layers.get("sessions") or [])
    kept = []
    removed = 0
    for session in sessions:
        if not isinstance(session, dict):
            kept.append(session)
            continue
        platform = session.get("platform") or session.get("tool")
        sid = str(session.get("id") or "")
        is_match = platform == "cursor" and (sid == composer_id or sid == session_id_for(composer_id))
        if is_match:
            removed += 1
            continue
        kept.append(session)
    layers["sessions"] = kept
    _atomic_write_json(path, data)
    after = snapshot_traces(path, composer_id)
    return {"before": before, "after": after, "removed": removed, "written": True}
def purge_agent_transcripts(composer_id, projects_root=None):
    deleted = []
    errors = []
    for path in agent_transcript_paths(composer_id, projects_root):
        try:
            path.unlink()
            deleted.append(str(path))
            parent = path.parent
            if parent.name == composer_id and parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
        except OSError as exc:
            errors.append({"path": str(path), "error": str(exc)})
    return {"deleted": deleted, "errors": errors}

### Verify
def verify_purged(composer_id, root=None, turns_db_path=None, snapshot_path=None, projects_root=None, check_agent_transcripts=False):
    composer_id = normalize_composer_id(composer_id)
    inv = inventory_holodeck(
        composer_id,
        root=root,
        turns_db_path=turns_db_path,
        snapshot_path=snapshot_path,
        projects_root=projects_root,
    )
    turns = inv["turns"] or {}
    snapshot = inv["snapshot"] or {}
    problems = []
    if turns.get("session_present"):
        problems.append("turns.db still has session " + inv["session_id"])
    if turns.get("exchange_count"):
        problems.append("turns.db still has %d exchange(s)" % turns["exchange_count"])
    if turns.get("digest_count"):
        problems.append("turns.db still has %d digest(s)" % turns["digest_count"])
    if turns.get("link_count"):
        problems.append("turns.db still has %d link(s)" % turns["link_count"])
    if turns.get("child_session_ids"):
        problems.append("turns.db still has parent_session_id refs: " + ", ".join(turns["child_session_ids"]))
    if snapshot.get("present"):
        problems.append("snapshot.json still lists this cursor session")
    if check_agent_transcripts and inv.get("agent_transcripts"):
        problems.append("agent transcript files remain: " + ", ".join(inv["agent_transcripts"]))
    return {
        "ok": not problems,
        "problems": problems,
        "inventory": inv,
        "still_in_cursor": composer_exists_in_cursor(composer_id),
    }

### Public API
def inspect_cursor_session(composer_id, cursor_db=None, root=None, turns_db_path=None, snapshot_path=None, projects_root=None):
    composer_id = normalize_composer_id(composer_id)
    if not composer_id:
        return {"ok": False, "error": "missing composer id", "composer_id": None}
    in_cursor = composer_exists_in_cursor(composer_id, cursor_db=cursor_db)
    inv = inventory_holodeck(
        composer_id,
        root=root,
        turns_db_path=turns_db_path,
        snapshot_path=snapshot_path,
        projects_root=projects_root,
    )
    return {
        "ok": True,
        "composer_id": composer_id,
        "session_id": session_id_for(composer_id),
        "in_cursor": in_cursor,
        "cursor_bubble_count": count_cursor_bubbles(composer_id, cursor_db=cursor_db) if in_cursor else 0,
        "deleted_from_cursor": not in_cursor,
        "holodeck": inv,
    }
def purge_deleted_cursor_session(
    composer_id,
    *,
    execute=False,
    force=False,
    include_agent_transcripts=False,
    cursor_db=None,
    root=None,
    turns_db_path=None,
    snapshot_path=None,
    projects_root=None,
):
    """Scrub one Cursor composer from Holodeck stores if it is gone from Cursor.

    Returns a report dict. Without execute=True, only inspects (dry-run).
    """
    report = inspect_cursor_session(
        composer_id,
        cursor_db=cursor_db,
        root=root,
        turns_db_path=turns_db_path,
        snapshot_path=snapshot_path,
        projects_root=projects_root,
    )
    if not report.get("ok"):
        report["purged"] = False
        report["executed"] = False
        return report
    composer_id = report["composer_id"]
    if report["in_cursor"] and not force:
        report["purged"] = False
        report["executed"] = False
        report["skipped"] = True
        report["skip_reason"] = "still present in Cursor state.vscdb; delete it in Cursor History first, or pass force=True"
        return report
    holodeck = report["holodeck"]
    has_traces = bool(
        (holodeck.get("turns") or {}).get("session_present")
        or (holodeck.get("turns") or {}).get("exchange_count")
        or (holodeck.get("turns") or {}).get("child_session_ids")
        or (holodeck.get("snapshot") or {}).get("present")
        or (include_agent_transcripts and holodeck.get("agent_transcripts"))
    )
    report["had_holodeck_traces"] = has_traces
    report["executed"] = bool(execute)
    if not execute:
        report["purged"] = False
        report["dry_run"] = True
        report["would_purge"] = has_traces
        return report
    root = Path(root or db.repo_root())
    turns_path = Path(turns_db_path) if turns_db_path else db.default_db_path(root)
    snap_path = Path(snapshot_path) if snapshot_path else snapshot_path_for(root)
    actions = {"turns": None, "snapshot": None, "agent_transcripts": None}
    if turns_path.exists():
        conn = db.connect(turns_path)
        try:
            db.init_db(conn)
            actions["turns"] = purge_turns_db(conn, composer_id)
        finally:
            conn.close()
    actions["snapshot"] = purge_snapshot(snap_path, composer_id)
    if include_agent_transcripts:
        actions["agent_transcripts"] = purge_agent_transcripts(composer_id, projects_root=projects_root)
    verification = verify_purged(
        composer_id,
        root=root,
        turns_db_path=turns_path,
        snapshot_path=snap_path,
        projects_root=projects_root,
        check_agent_transcripts=include_agent_transcripts,
    )
    report["actions"] = actions
    report["verification"] = verification
    report["purged"] = verification["ok"]
    report["holodeck_after"] = verification["inventory"]
    return report
def list_cursor_sessions_in_turns(turns_db_path=None, root=None):
    root = Path(root or db.repo_root())
    turns_path = Path(turns_db_path) if turns_db_path else db.default_db_path(root)
    if not turns_path.exists():
        return []
    conn = db.connect(turns_path)
    try:
        db.init_db(conn)
        rows = conn.execute(
            """
            SELECT id, title, project, worktree, branch, last_activity
            FROM sessions
            WHERE platform = 'cursor'
            ORDER BY last_activity DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
def purge_all_deleted_cursor_sessions(
    *,
    execute=False,
    force=False,
    include_agent_transcripts=False,
    cursor_db=None,
    root=None,
    turns_db_path=None,
    snapshot_path=None,
    projects_root=None,
):
    """For every cursor session in turns.db, purge it if missing from Cursor (or force)."""
    sessions = list_cursor_sessions_in_turns(turns_db_path=turns_db_path, root=root)
    reports = []
    for session in sessions:
        composer_id = composer_id_from_session_id(session.get("id"))
        if not composer_id:
            continue
        reports.append(
            purge_deleted_cursor_session(
                composer_id,
                execute=execute,
                force=force,
                include_agent_transcripts=include_agent_transcripts,
                cursor_db=cursor_db,
                root=root,
                turns_db_path=turns_db_path,
                snapshot_path=snapshot_path,
                projects_root=projects_root,
            )
        )
    purged = [r for r in reports if r.get("purged")]
    skipped = [r for r in reports if r.get("skipped")]
    dry = [r for r in reports if r.get("dry_run") and r.get("would_purge")]
    return {
        "session_count": len(sessions),
        "checked": len(reports),
        "purged_count": len(purged),
        "skipped_still_in_cursor": len(skipped),
        "would_purge_count": len(dry),
        "reports": reports,
        "executed": bool(execute),
    }
