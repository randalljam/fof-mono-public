"""Ingest AI sessions and git commits into the turns database."""

import subprocess
from datetime import datetime, timedelta
from pathlib import Path

try:
    from apps.holodeck.collectors import sessions as sessions_collector
    from apps.holodeck.collectors import worktrees as worktrees_collector
    from apps.holodeck.turns import cloud_claude
    from apps.holodeck.turns import cloud_codex
    from apps.holodeck.turns import correlate
    from apps.holodeck.turns import db
    from apps.holodeck.turns import hash_map
except ImportError:
    from collectors import sessions as sessions_collector
    from collectors import worktrees as worktrees_collector
    from turns import cloud_claude
    from turns import cloud_codex
    from turns import correlate
    from turns import db
    from turns import hash_map

COMMIT_RECORD_SEPARATOR = "\x1e"
COMMIT_FIELD_SEPARATOR = "\x00"
COMMIT_LOG_FORMAT = "%x1e%H%x00%an%x00%ae%x00%aI%x00%ce%x00%cI%x00%B%x00"
CODE_MARKERS = (
    "[tool_use]",
    "[tool_result]",
    "```",
    "apply_patch",
    "exec_command",
    "pytest",
    "git ",
    "created ",
    "updated ",
    "modified ",
    "tests pass",
    "test passed",
)

### Time
def parse_time(value):
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None
def iso_or_none(value):
    parsed = parse_time(value)
    return parsed.isoformat() if parsed else value
def max_time(values):
    parsed = [parse_time(value) for value in values if parse_time(value)]
    if not parsed:
        return None
    return max(parsed).isoformat()

### Exchange segmentation
def message_text(message):
    return str(message.get("text") or "")
def message_time(message):
    return parse_time(message.get("ts"))
def append_user_text(exchange, text, follow_up=False):
    if not exchange.get("user_text"):
        exchange["user_text"] = text
        return
    prefix = "\n\nFollow-up:\n" if follow_up else "\n\n"
    exchange["user_text"] += prefix + text
def append_response_text(exchange, text):
    if not text:
        return
    if exchange.get("response_text"):
        exchange["response_text"] += "\n\n" + text
    else:
        exchange["response_text"] = text
def exchange_last_activity(exchange):
    return exchange.get("_last_activity")
def is_follow_up(message, exchange):
    text = message_text(message).strip()
    current_time = message_time(message)
    last_activity = exchange_last_activity(exchange)
    if not text or len(text) >= 200 or not current_time or not last_activity:
        return False
    return timedelta(0) <= current_time - last_activity <= timedelta(minutes=3)
def response_has_code_markers(text):
    lowered = str(text or "").lower()
    return any(marker in lowered for marker in CODE_MARKERS)
def classify_exchange(exchange):
    # Tunable heuristic: short questions with no tool/code evidence are info;
    # long prompts or long agent responses are primary; everything else is quick.
    user_text = exchange.get("user_text") or ""
    response_text = exchange.get("response_text") or ""
    if len(user_text) >= 400 or exchange.get("_response_messages", 0) >= 10:
        return "primary"
    if len(user_text) < 300 and not response_has_code_markers(response_text):
        return "info"
    return "quick"
def public_exchange(exchange, session_id, idx):
    exchange_id = session_id + "#" + str(idx)
    return {
        "id": exchange_id,
        "session_id": session_id,
        "idx": idx,
        "kind": classify_exchange(exchange),
        "user_ts": exchange.get("user_ts"),
        "user_text": exchange.get("user_text") or "",
        "response_text": exchange.get("response_text") or "",
        "response_final_text": exchange.get("response_final_text") or "",
        "response_recap": exchange.get("response_recap") or "",
        "response_end_ts": exchange.get("response_end_ts"),
        "origin": exchange.get("origin") or db.OPERATOR_ORIGIN,
        "follow_up_of": exchange.get("follow_up_of"),
    }
def segment_messages(messages, session_id):
    exchanges = []
    current = None
    for message in messages or []:
        role = message.get("role")
        text = message_text(message)
        if role == "user":
            if not text.strip() or sessions_collector.looks_injected(text):
                continue
            if db.is_session_end_command(text):
                # /close, close, /exit, etc. end the CLI session; they are not prompts.
                continue
            ts = message.get("ts")
            parsed_ts = message_time(message)
            if current and is_follow_up(message, current):
                append_user_text(current, text, follow_up=True)
                current["_last_activity"] = parsed_ts
                continue
            if current:
                exchanges.append(current)
            current = {
                "user_ts": iso_or_none(ts),
                "user_text": text,
                "response_text": "",
                "response_final_text": "",
                "response_recap": "",
                "response_end_ts": None,
                "follow_up_of": None,
                "_response_messages": 0,
                "_last_activity": parsed_ts,
            }
            continue
        if role == "recap":
            if current and text.strip():
                current["response_recap"] = text
                parsed_ts = message_time(message)
                if parsed_ts:
                    current["_last_activity"] = parsed_ts
            continue
        if role == "assistant" and current:
            append_response_text(current, text)
            if text.strip():
                current["response_final_text"] = text
            current["_response_messages"] += 1
            ts = message.get("ts")
            parsed_ts = message_time(message)
            if ts:
                current["response_end_ts"] = iso_or_none(ts)
            if parsed_ts:
                current["_last_activity"] = parsed_ts
    if current:
        exchanges.append(current)
    return [public_exchange(exchange, session_id, index + 1) for index, exchange in enumerate(exchanges)]

### Sessions
def legacy_session_prefix(session):
    session_id = str(session.get("id") or "")
    for prefix in ("claude-code", "claude-cloud", "codex", "codex-cloud", "cursor"):
        if session_id.startswith(prefix + ":"):
            return prefix
    tool = session.get("tool")
    if tool:
        return str(tool)
    platform = session.get("platform")
    host = session.get("host")
    if platform == "claude":
        return "claude-cloud" if host == "cloud" else "claude-code"
    if platform == "codex":
        return "codex-cloud" if host == "cloud" else "codex"
    if platform == "cursor":
        return "cursor"
    return None
def session_db_id(session):
    native_id = session.get("id")
    prefix = legacy_session_prefix(session)
    if not native_id or not prefix:
        return None
    native_id = str(native_id)
    return native_id if native_id.startswith(prefix + ":") else prefix + ":" + native_id
def session_payload(session, ingested_at):
    normalized = db.normalize_session_payload(session)
    return {
        "id": session_db_id(normalized),
        "platform": normalized.get("platform"),
        "entrypoint": normalized.get("entrypoint"),
        "host": normalized.get("host"),
        "remote_control": normalized.get("remote_control"),
        "bridge_session_id": normalized.get("bridge_session_id"),
        "source_path": normalized.get("source_path"),
        "source_url": normalized.get("source_url"),
        "project": normalized.get("project"),
        "worktree": normalized.get("worktree"),
        "branch": normalized.get("branch"),
        "label": normalized.get("label") or normalized.get("interface") or normalized.get("platform"),
        "model": normalized.get("model"),
        "interface": normalized.get("interface"),
        "origin": normalized.get("origin") or db.OPERATOR_ORIGIN,
        "title": normalized.get("title"),
        "started": normalized.get("started"),
        "last_activity": normalized.get("last_activity"),
        "ingested_at": ingested_at,
    }
def read_session_messages(session):
    normalized = db.normalize_session_payload(session)
    platform = normalized.get("platform")
    if platform == "claude" and normalized.get("host") != "cloud" and normalized.get("source_path"):
        return sessions_collector.read_claude_messages(session.get("source_path"), cap=None, sampled=False)
    if platform == "codex" and normalized.get("host") != "cloud" and normalized.get("source_path"):
        return sessions_collector.read_codex_messages(session.get("source_path"), cap=None, sampled=False)
    if platform == "cursor" and session.get("id"):
        return sessions_collector.read_cursor_messages(session.get("id"), cap=None)
    return []
def first_real_user_message(messages):
    fallback = None
    for message in messages or []:
        if message.get("role") != "user":
            continue
        text = message_text(message)
        if not text.strip():
            continue
        if fallback is None:
            fallback = text
        if not sessions_collector.looks_injected(text):
            return text
    return fallback
def normalize_session_for_ingest(session, messages):
    normalized = dict(session)
    db.normalize_session_payload(normalized)
    if normalized.get("platform") == "cursor":
        normalized["origin"] = db.OPERATOR_ORIGIN
        return normalized
    if normalized.get("platform") == "claude":
        normalized["origin"] = db.OPERATOR_ORIGIN
        return normalized
    if normalized.get("platform") == "codex":
        first_user = first_real_user_message(messages)
        if first_user:
            normalized["_first_user_text"] = first_user
        normalized = sessions_collector.apply_session_label(normalized)
    normalized["origin"] = normalized.get("origin") or db.OPERATOR_ORIGIN
    if normalized["origin"] not in (db.OPERATOR_ORIGIN, db.DELEGATED_ORIGIN):
        normalized["origin"] = db.OPERATOR_ORIGIN
    return normalized
def ingest_sessions(conn, session_items, messages_by_session=None, ingested_at=None):
    ingested_at = ingested_at or db.now_iso()
    session_count = 0
    exchange_count = 0
    for session in session_items or []:
        stable_id = session_db_id(session)
        if not stable_id:
            continue
        messages = None
        if messages_by_session is not None:
            messages = messages_by_session.get(stable_id) or messages_by_session.get(session.get("id")) or []
        else:
            messages = read_session_messages(session)
        session = normalize_session_for_ingest(session, messages)
        db.upsert_session(conn, session_payload(session, ingested_at))
        if "autoreview" in "".join(ch for ch in str(session.get("model") or "").lower() if ch.isalnum()):
            session_count += 1
            continue
        for exchange in segment_messages(messages, stable_id):
            exchange["origin"] = session.get("origin") or db.OPERATOR_ORIGIN
            db.upsert_exchange(conn, exchange)
            exchange_count += 1
        session_count += 1
    db.rebuild_subagent_links(conn)
    return {"sessions": session_count, "exchanges": exchange_count}
def merge_session_items(base, extra):
    merged = []
    seen = set()
    for session in list(base or []) + list(extra or []):
        stable_id = session_db_id(session)
        if not stable_id or stable_id in seen:
            continue
        seen.add(stable_id)
        merged.append(session)
    return merged
def collect_turn_sessions(root, worktrees):
    sessions, note = sessions_collector.collect_sessions(root, worktrees=worktrees)
    extra_notes = []
    try:
        sessions = merge_session_items(sessions, sessions_collector.collect_codex_sessions(worktrees, limit=120))
    except Exception as exc:
        extra_notes.append("deep codex sessions failed: " + str(exc))
    notes = [item for item in [note] + extra_notes if item]
    return sessions_collector.sort_sessions(sessions), "; ".join(notes) or None

### Cloud sessions
def ingest_cloud_codex(conn, worktrees, ingested_at=None):
    ingested_at = ingested_at or db.now_iso()
    cloud_sessions = cloud_codex.collect_sessions(worktrees=worktrees)
    note = getattr(cloud_sessions, "note", None)
    messages_by_session = getattr(cloud_sessions, "messages_by_session", {})
    exchanges_by_session = getattr(cloud_sessions, "exchanges_by_session", {})
    task_items = getattr(cloud_sessions, "task_items", [])
    session_items = list(cloud_sessions or [])
    session_count = 0
    exchange_count = 0
    for session in session_items:
        session["ingested_at"] = ingested_at
        db.upsert_session(conn, session)
        if session["id"] in messages_by_session:
            exchanges = segment_messages(messages_by_session.get(session["id"]) or [], session["id"])
            if exchanges:
                conn.execute("DELETE FROM exchanges WHERE id = ?", (session["id"] + "#0",))
        else:
            exchanges = exchanges_by_session.get(session["id"]) or []
        for exchange in exchanges:
            exchange["origin"] = session.get("origin") or db.OPERATOR_ORIGIN
            db.upsert_exchange(conn, exchange)
            exchange_count += 1
        session_count += 1
    db.rebuild_subagent_links(conn)
    return {
        "tasks": len(task_items),
        "sessions": session_count,
        "exchanges": exchange_count,
        "note": note,
        "task_items": task_items,
    }
def ingest_cloud_claude(conn, worktrees, root=None, ingested_at=None):
    ingested_at = ingested_at or db.now_iso()
    cloud_sessions = cloud_claude.collect_sessions(worktrees=worktrees, root=root)
    note = getattr(cloud_sessions, "note", None)
    messages_by_session = getattr(cloud_sessions, "messages_by_session", {})
    session_count = 0
    exchange_count = 0
    session_items = list(cloud_sessions or [])
    for session in session_items:
        session["ingested_at"] = ingested_at
        db.upsert_session(conn, session)
        messages = messages_by_session.get(session["id"]) or []
        for exchange in segment_messages(messages, session["id"]):
            exchange["origin"] = session.get("origin") or db.OPERATOR_ORIGIN
            db.upsert_exchange(conn, exchange)
            exchange_count += 1
        session_count += 1
    db.rebuild_subagent_links(conn)
    return {
        "sessions": session_count,
        "exchanges": exchange_count,
        "note": note,
        "session_items": session_items,
    }

### Commits
def run_git(path, args, timeout=30):
    return subprocess.run(
        ["git", "-C", str(path)] + args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
def split_commit_message(message):
    message = (message or "").strip("\n")
    if not message:
        return "", ""
    lines = message.splitlines()
    return lines[0], "\n".join(lines[1:]).lstrip("\n")
def is_agent_commit(message, committer_email):
    lowered_message = str(message or "").lower()
    lowered_email = str(committer_email or "").lower()
    if "co-authored-by: claude" in lowered_message:
        return 1
    if "bot" in lowered_email or "noreply" in lowered_email:
        return 1
    return 0
def parse_commit_log(text, branch=None, worktree=None):
    commits = []
    for raw_record in text.split(COMMIT_RECORD_SEPARATOR):
        record = raw_record.lstrip("\n")
        if not record:
            continue
        parts = record.split(COMMIT_FIELD_SEPARATOR, 6)
        if len(parts) < 7:
            continue
        sha, author, author_email, author_date, committer_email, committer_date, message = parts
        subject, body = split_commit_message(message)
        commits.append({
            "sha": sha,
            "branch": branch,
            "worktree": worktree,
            "author": author,
            "author_email": author_email,
            "author_date": author_date,
            "committer_date": committer_date,
            "subject": subject,
            "body": body,
            "is_agent_commit": is_agent_commit(message, committer_email),
        })
    return commits
def commits_for_worktree(worktree, since_days=60):
    path = worktree.get("path")
    branch = worktree.get("branch")
    if not path or worktree.get("missing"):
        return [], None
    ref = branch if branch and branch != "detached" else "HEAD"
    command = run_git(path, ["log", ref, "--since=" + str(since_days) + ".days", "--format=" + COMMIT_LOG_FORMAT], timeout=45)
    if command.returncode != 0:
        return [], command.stderr.strip() or "git log failed for " + str(path)
    return parse_commit_log(command.stdout, branch=branch, worktree=path), None
def ingest_commits(conn, commit_items):
    count = 0
    for commit in commit_items or []:
        if not commit.get("sha"):
            continue
        db.upsert_commit(conn, commit)
        count += 1
    return count
def collect_commit_items(worktrees):
    commits = []
    notes = []
    for worktree in worktrees or []:
        items, note = commits_for_worktree(worktree)
        commits.extend(items)
        if note:
            notes.append(note)
    return commits, notes

### Build
def fallback_worktree(root):
    command = run_git(root, ["branch", "--show-current"], timeout=10)
    branch = command.stdout.strip() if command.returncode == 0 else None
    return [{"path": str(root), "branch": branch or None, "missing": False}]
def collect_worktrees(root):
    try:
        return worktrees_collector.collect_worktrees(root), None
    except Exception as exc:
        return fallback_worktree(root), "worktrees failed: " + str(exc)
def build(root=None, db_path=None, worktrees=None, include_cloud=True):
    root = Path(root or db.repo_root())
    conn = db.connect(db_path or db.default_db_path(root))
    db.init_db(conn)
    hash_map_summary = hash_map.ensure_hash_map_loaded(conn, root=root, remap=True)
    worktree_note = None
    if worktrees is None:
        worktrees, worktree_note = collect_worktrees(root)
    sessions, sessions_note = collect_turn_sessions(root, worktrees)
    ingested_at = db.now_iso()
    session_counts = ingest_sessions(conn, sessions, ingested_at=ingested_at)
    cloud_counts = {"tasks": 0, "sessions": 0, "exchanges": 0, "note": None, "task_items": []}
    claude_cloud_counts = {"sessions": 0, "exchanges": 0, "note": None, "session_items": []}
    if include_cloud:
        cloud_counts = ingest_cloud_codex(conn, worktrees, ingested_at=ingested_at)
        claude_cloud_counts = ingest_cloud_claude(conn, worktrees, root=root, ingested_at=ingested_at)
    db.rebuild_subagent_links(conn)
    commits, commit_notes = collect_commit_items(worktrees)
    commit_count = ingest_commits(conn, commits)
    link_count = correlate.rebuild_links(conn)
    if include_cloud:
        link_count += cloud_codex.link_cloud_task_commits(conn, tasks=cloud_counts.get("task_items") or [])
        link_count += cloud_claude.link_cloud_session_commits(conn, sessions=claude_cloud_counts.get("session_items") or [])
    notes = [note for note in [worktree_note, sessions_note] if note]
    if cloud_counts.get("note"):
        notes.append(cloud_counts["note"])
    if claude_cloud_counts.get("note"):
        notes.append(claude_cloud_counts["note"])
    notes.extend(commit_notes)
    notes.extend(hash_map_summary.get("notes") or [])
    if hash_map_summary.get("loaded"):
        remapped = hash_map_summary.get("remapped") or {}
        notes.append(
            "hash map loaded: "
            + str(hash_map_summary.get("commit_map_rows") or 0)
            + " commit rows, remapped "
            + str(remapped.get("remapped_commits") or 0)
            + " stored commits"
        )
    db.set_meta(conn, "last_build", db.now_iso())
    db.set_meta(conn, "last_build_notes", "; ".join(notes))
    conn.commit()
    return {
        "sessions": session_counts["sessions"] + cloud_counts["sessions"] + claude_cloud_counts["sessions"],
        "exchanges": session_counts["exchanges"] + cloud_counts["exchanges"] + claude_cloud_counts["exchanges"],
        "cloud_tasks": cloud_counts["tasks"],
        "claude_cloud_sessions": claude_cloud_counts["sessions"],
        "commits": commit_count,
        "links": link_count,
        "hash_map": hash_map_summary,
        "notes": notes,
        "db_path": str(db_path or db.default_db_path(root)),
    }
