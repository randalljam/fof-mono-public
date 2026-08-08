"""Collect recent AI coding sessions for this repo."""

import json
import os
import sqlite3
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from apps.holodeck.turns import labels as label_helpers
except ImportError:
    try:
        from turns import labels as label_helpers
    except ImportError:
        label_helpers = None

FALLBACK_REPO = "/Users/randytrue/Documents/Code/fof-mono"
CLAUDE_ROOT = Path.home() / ".claude/projects"
CLAUDE_APP_SESSIONS_ROOT = Path.home() / "Library/Application Support/Claude/claude-code-sessions"
CODEX_ROOT = Path.home() / ".codex/sessions"
CODEX_INDEX = Path.home() / ".codex/session_index.jsonl"
CURSOR_DB = Path.home() / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"
MAX_PREVIEW = 240

### Shared parsing
def iso_from_epoch_ms(value):
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc).astimezone().isoformat()
    except (TypeError, ValueError, OSError):
        return None
def iso_from_mtime(path):
    return datetime.fromtimestamp(Path(path).stat().st_mtime).astimezone().isoformat()
def truncate_text(text, limit):
    if text is None:
        return None
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[:limit - 3] + "..."
def json_records(lines):
    for line in lines:
        if not line or not line.strip():
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue
SKIP_BLOCK_TYPES = {
    "thinking", "reasoning", "redacted_thinking", "encrypted_reasoning",
    "tool_use", "tool_result", "tool_call", "tool_calls",
    "function_call", "function_call_output", "custom_tool_call", "custom_tool_call_output",
    "image", "document", "code_diff", "diff", "patch",
}
def content_to_text(content):
    # Keep only substantive prose: user text and the agent's response text. Drop reasoning
    # traces, tool calls/results, and file diffs — those are the guts that cause bloat and
    # are not what the operator reads. The raw sessions remain in their native stores / the
    # archived cloud exports for the rare full-detail case.
    if content is None:
        return None
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        block_type = content.get("type") or content.get("content_type")
        if block_type in SKIP_BLOCK_TYPES:
            return None
        text = content.get("text")
        if text:
            return text
        inner = content.get("content")
        if inner is not None and inner is not content:
            return content_to_text(inner)
        return None
    if isinstance(content, list):
        parts = []
        for block in content:
            piece = content_to_text(block)
            if piece:
                parts.append(piece)
        return "\n".join(parts) if parts else None
    return str(content)
def message_content(record):
    message = record.get("message")
    if isinstance(message, dict):
        return content_to_text(message.get("content"))
    return content_to_text(record.get("content"))
INJECTED_PREFIXES = ("<", "[SYSTEM NOTIFICATION", "Base directory for this skill", "Caveat: the messages below were generated")
def looks_injected(text):
    return text.lstrip().startswith(INJECTED_PREFIXES)
def first_last_user_text(texts):
    real = [text for text in texts if text and not looks_injected(text)]
    if not real:
        real = [text for text in texts if text]
    if not real:
        return None, None
    return truncate_text(real[0], MAX_PREVIEW), truncate_text(real[-1], MAX_PREVIEW)
def first_real_user_text(texts):
    real = [text for text in texts if text and not looks_injected(text)]
    if real:
        return real[0]
    for text in texts:
        if text:
            return text
    return None
def normalize_path_string(path):
    if not path:
        return None
    return os.path.normpath(os.path.expanduser(str(path)))
def path_is_prefix(path, prefix):
    path = normalize_path_string(path)
    prefix = normalize_path_string(prefix)
    if not path or not prefix:
        return False
    return path == prefix or path.startswith(prefix.rstrip(os.sep) + os.sep)
def match_project_to_worktree(project, worktrees):
    project = normalize_path_string(project)
    if not project:
        return None, None
    sorted_worktrees = sorted(worktrees or [], key=lambda item: len(item.get("path") or ""), reverse=True)
    for worktree in sorted_worktrees:
        path = worktree.get("path")
        if path and path_is_prefix(project, path):
            return path, worktree.get("branch")
    return None, None
def project_matches_repo(project, worktrees):
    worktree, branch = match_project_to_worktree(project, worktrees)
    if worktree:
        return True, worktree, branch
    if path_is_prefix(project, FALLBACK_REPO):
        return True, None, None
    return False, None, None
def sort_sessions(items):
    return sorted(items, key=lambda item: item.get("last_activity") or "", reverse=True)
def apply_session_label(session):
    if label_helpers is not None:
        return label_helpers.apply_session_label(session)
    session["label"] = session.get("platform") or "AI Session"
    session["model"] = session.get("raw_model")
    session["interface"] = session.get("entrypoint")
    session["origin"] = "operator"
    session.pop("_first_user_text", None)
    return session
def cutoff_timestamp(days=30):
    return (datetime.now().astimezone() - timedelta(days=days)).timestamp()
def recent_files(root, pattern, limit=40):
    root = Path(root)
    if not root.exists():
        return []
    cutoff = cutoff_timestamp()
    paths = []
    for path in root.rglob(pattern):
        if path.is_file() and path.stat().st_mtime >= cutoff:
            paths.append(path)
    paths.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return paths[:limit]
def recent_child_files(root, pattern, limit=40):
    root = Path(root)
    if not root.exists():
        return []
    cutoff = cutoff_timestamp()
    paths = []
    for directory in root.iterdir():
        if not directory.is_dir():
            continue
        for path in directory.glob(pattern):
            if path.is_file() and path.stat().st_mtime >= cutoff:
                paths.append(path)
    paths.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return paths[:limit]
def sampled_jsonl_lines(path):
    path = Path(path)
    if path.stat().st_size <= 20 * 1024 * 1024:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    first = []
    last = deque(maxlen=400)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for index, line in enumerate(handle):
            if index < 200:
                first.append(line.rstrip("\n"))
            last.append(line.rstrip("\n"))
    return first + list(last)
def full_jsonl_lines(path):
    return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
def detail_item(role, text, ts):
    if not text:
        return None
    return {"role": role, "text": text, "ts": ts}
def claude_entrypoint_from_lines(lines):
    for record in json_records(lines):
        if record.get("type") == "user" and record.get("entrypoint"):
            raw_entrypoint = str(record.get("entrypoint"))
            if label_helpers is not None:
                return label_helpers.normalized_entrypoint("claude", raw_entrypoint, tool="claude-code")
            return "app" if raw_entrypoint == "claude-desktop" else "cli"
    return "cli"
def claude_model_from_lines(lines):
    model = None
    for record in json_records(lines):
        if record.get("type") != "assistant":
            continue
        message = record.get("message")
        if isinstance(message, dict) and message.get("model"):
            model = message.get("model")
    return model
def codex_entrypoint_from_meta(payload):
    if not isinstance(payload, dict):
        return None
    source = payload.get("source")
    originator = payload.get("originator")
    thread_source = payload.get("thread_source")
    if isinstance(source, dict) or thread_source == "subagent":
        return "subagent"
    # Interactive Codex CLI (TUI) writes source=cli / originator=codex-tui.
    # Non-interactive / rescue exec writes source=exec / originator=codex_exec.
    if source in ("exec", "cli") or originator in ("codex_exec", "codex-tui"):
        return "cli"
    if originator in ("Codex Desktop", "codex_work_desktop"):
        return "app"
    if originator == "Claude Code" and source == "vscode":
        return "cli"
    return "app" if isinstance(source, str) and source else None

### Claude Code
def non_empty_string_values(values):
    result = []
    for value in values or []:
        text = str(value or "").strip()
        if text:
            result.append(text)
    return result
def claude_app_payloads(data):
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []
def claude_app_metadata_from_payload(payload):
    cli_session_id = str(payload.get("cliSessionId") or "").strip()
    if not cli_session_id:
        return None, None
    bridge_session_ids = non_empty_string_values(payload.get("bridgeSessionIds") or payload.get("bridge_session_ids") or [])
    return cli_session_id, {
        "model": payload.get("model"),
        "effort": payload.get("effort"),
        "title": payload.get("title"),
        "permission_mode": payload.get("permission_mode") or payload.get("permissionMode"),
        "bridge_session_ids": bridge_session_ids,
    }
def load_claude_app_metadata(root=None):
    root = Path(root or CLAUDE_APP_SESSIONS_ROOT)
    if not root.exists():
        return {}
    index = {}
    try:
        paths = sorted(root.rglob("local_*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    except OSError:
        return {}
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, json.JSONDecodeError):
            continue
        for payload in claude_app_payloads(data):
            cli_session_id, metadata = claude_app_metadata_from_payload(payload)
            if cli_session_id and cli_session_id not in index:
                index[cli_session_id] = metadata
    return index
def enrich_claude_session_from_app(session, app_metadata):
    metadata = (app_metadata or {}).get(session.get("id")) or {}
    if metadata.get("model") and not session.get("raw_model"):
        session["raw_model"] = metadata.get("model")
    if metadata.get("title") and not session.get("title"):
        session["title"] = metadata.get("title")
    if metadata.get("effort") and not session.get("effort"):
        session["effort"] = metadata.get("effort")
    if metadata.get("permission_mode") and not session.get("permission_mode"):
        session["permission_mode"] = metadata.get("permission_mode")
    bridge_session_ids = metadata.get("bridge_session_ids") or []
    if bridge_session_ids and not session.get("bridge_session_id"):
        session["remote_control"] = True
        session["bridge_session_id"] = bridge_session_ids[0]
    return session
def claude_bridge_session_id_from_lines(lines):
    for record in json_records(lines):
        if record.get("type") != "bridge-session":
            continue
        bridge_session_id = str(record.get("bridgeSessionId") or record.get("bridge_session_id") or "").strip()
        if bridge_session_id:
            return bridge_session_id
    return None
def parse_claude_jsonl_lines(lines, source_path=None, fallback_mtime=None, worktrees=None, app_metadata=None):
    session_id = Path(source_path).stem if source_path else None
    title = None
    project = None
    branch = None
    raw_model = claude_model_from_lines(lines)
    bridge_session_id = claude_bridge_session_id_from_lines(lines)
    timestamps = []
    user_texts = []
    messages = 0
    for record in json_records(lines):
        record_type = record.get("type")
        if record_type == "ai-title" and record.get("title"):
            title = record.get("title")
        if record_type not in ("user", "assistant"):
            continue
        messages += 1
        if record.get("cwd"):
            project = record.get("cwd")
        if record.get("gitBranch"):
            branch = record.get("gitBranch")
        if record.get("timestamp"):
            timestamps.append(record.get("timestamp"))
        if record_type == "user":
            text = message_content(record)
            if text:
                user_texts.append(text)
    first_user, last_user = first_last_user_text(user_texts)
    matched, worktree, matched_branch = project_matches_repo(project, worktrees or [])
    if branch is None:
        branch = matched_branch
    session = {
        "platform": "claude",
        "id": session_id,
        "title": title,
        "entrypoint": claude_entrypoint_from_lines(lines),
        "host": "local",
        "remote_control": bool(bridge_session_id),
        "bridge_session_id": bridge_session_id,
        "raw_model": raw_model,
        "project": project,
        "worktree": worktree,
        "branch": branch,
        "started": min(timestamps) if timestamps else None,
        "last_activity": max(timestamps) if timestamps else fallback_mtime,
        "messages": messages,
        "exchanges": len(user_texts),
        "first_user": first_user,
        "last_user": last_user,
        "origin": "operator",
        "source_path": str(source_path) if source_path else None,
        "_matches_repo": matched,
    }
    session = enrich_claude_session_from_app(session, app_metadata)
    return apply_session_label(session)
def claude_messages_from_lines(lines, cap=200):
    messages = []
    for record in json_records(lines):
        record_type = record.get("type")
        if record_type == "system" and record.get("subtype") == "away_summary":
            item = detail_item("recap", record.get("content"), record.get("timestamp"))
            if item:
                messages.append(item)
            if cap is not None and len(messages) >= cap:
                break
            continue
        if record_type not in ("user", "assistant"):
            continue
        text = message_content(record)
        item = detail_item(record_type, text, record.get("timestamp"))
        if item:
            messages.append(item)
        if cap is not None and len(messages) >= cap:
            break
    return messages
def collect_claude_sessions(worktrees):
    items = []
    try:
        app_metadata = load_claude_app_metadata()
    except Exception:
        app_metadata = {}
    for path in recent_child_files(CLAUDE_ROOT, "*.jsonl", limit=40):
        session = parse_claude_jsonl_lines(sampled_jsonl_lines(path), source_path=path, fallback_mtime=iso_from_mtime(path), worktrees=worktrees, app_metadata=app_metadata)
        if session.pop("_matches_repo", False):
            items.append(session)
    return sort_sessions(items)[:40]

### Cursor
def cursor_project_path(data):
    workspace = data.get("workspaceIdentifier") or {}
    uri = workspace.get("uri") or {}
    if isinstance(uri, dict):
        return uri.get("path") or uri.get("fsPath")
    return workspace.get("fsPath") or workspace.get("path")
def parse_cursor_composer_data(data, worktrees=None):
    project = cursor_project_path(data)
    matched, worktree, branch = project_matches_repo(project, worktrees or [])
    headers = data.get("fullConversationHeadersOnly") or []
    model_config = data.get("modelConfig") or {}
    session = {
        "platform": "cursor",
        "id": data.get("composerId") or data.get("id"),
        "title": data.get("name"),
        "entrypoint": "app",
        "host": "local",
        "remote_control": False,
        "bridge_session_id": None,
        "raw_model": model_config.get("modelName"),
        "model_config": model_config,
        "selected_models": data.get("selectedModels") or model_config.get("selectedModels") or [],
        "unified_mode": data.get("unifiedMode") or model_config.get("unifiedMode"),
        "plan_mode_suggestion_used": data.get("planModeSuggestionUsed"),
        "project": project,
        "worktree": worktree,
        "branch": branch,
        "started": iso_from_epoch_ms(data.get("createdAt")),
        "last_activity": iso_from_epoch_ms(data.get("lastUpdatedAt")),
        "messages": len(headers),
        "exchanges": len([h for h in headers if isinstance(h, dict) and h.get("type") == 1]),
        "first_user": None,
        "last_user": None,
        "origin": "operator",
        "source_path": data.get("composerId") or data.get("id"),
        "_matches_repo": matched,
    }
    return apply_session_label(session)
def cursor_user_bubble_ids(data):
    ids = []
    for header in data.get("fullConversationHeadersOnly") or []:
        if header.get("type") == 1:
            bubble_id = header.get("bubbleId") or header.get("id")
            if bubble_id:
                ids.append(bubble_id)
    return ids
def parse_cursor_bubble_text(value):
    try:
        data = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None
    return content_to_text(data.get("text") or data.get("content") or data.get("message"))
def cursor_bubble_text(db, composer_id, bubble_id):
    key = "bubbleId:" + composer_id + ":" + bubble_id
    row = db.execute("SELECT value FROM cursorDiskKV WHERE key = ?", (key,)).fetchone()
    if not row:
        return None
    return parse_cursor_bubble_text(row[0])
def cursor_header_ts(header):
    for key in ("timestamp", "createdAt", "lastUpdatedAt"):
        value = header.get(key)
        if value is None:
            continue
        if isinstance(value, (int, float)):
            return iso_from_epoch_ms(value)
        return str(value)
    return None
def cursor_preview_texts(db, composer_id, data):
    texts = []
    for bubble_id in cursor_user_bubble_ids(data):
        text = cursor_bubble_text(db, composer_id, bubble_id)
        if text:
            texts.append(text)
    return first_last_user_text(texts)
def collect_cursor_sessions(worktrees):
    if not CURSOR_DB.exists():
        return []
    uri = "file:" + str(CURSOR_DB) + "?mode=ro"
    sessions = []
    data_by_id = {}
    with sqlite3.connect(uri, uri=True, timeout=5) as db:
        rows = db.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE 'composerData:%'").fetchall()
        for key, value in rows:
            try:
                data = json.loads(value)
            except (TypeError, json.JSONDecodeError):
                continue
            session = parse_cursor_composer_data(data, worktrees=worktrees)
            if session.get("id") and session.pop("_matches_repo", False):
                sessions.append(session)
                data_by_id[session["id"]] = data
        sessions = sort_sessions(sessions)[:40]
        for session in sessions[:15]:
            first_user, last_user = cursor_preview_texts(db, session["id"], data_by_id.get(session["id"]) or {})
            session["first_user"] = first_user
            session["last_user"] = last_user
    return sessions

### Codex
def parse_codex_index(text):
    index = {}
    for record in json_records(text.splitlines()):
        session_id = record.get("id")
        if session_id:
            index[session_id] = {"title": record.get("thread_name"), "updated_at": record.get("updated_at")}
    return index
def codex_payload_text(payload):
    return content_to_text(payload.get("content"))
def parse_codex_jsonl_lines(lines, source_path=None, fallback_mtime=None, titles=None, worktrees=None):
    session_id = None
    started = None
    project = None
    branch = None
    entrypoint = None
    originator = None
    source = None
    raw_model = None
    effort = None
    user_texts = []
    messages = 0
    for record in json_records(lines):
        if record.get("type") == "session_meta":
            payload = record.get("payload") or {}
            session_id = payload.get("id") or payload.get("session_id")
            started = payload.get("timestamp")
            project = payload.get("cwd")
            git_data = payload.get("git") or {}
            branch = git_data.get("branch")
            originator = payload.get("originator")
            source = payload.get("source")
            entrypoint = codex_entrypoint_from_meta(payload)
            continue
        if record.get("type") == "turn_context":
            payload = record.get("payload") or {}
            raw_model = payload.get("model") or raw_model
            effort = payload.get("effort") or effort
            continue
        if record.get("type") != "response_item":
            continue
        payload = record.get("payload") or {}
        role = payload.get("role")
        if role in ("user", "assistant"):
            messages += 1
        if role == "user":
            text = codex_payload_text(payload)
            if text:
                user_texts.append(text)
    first_user, last_user = first_last_user_text(user_texts)
    first_user_full = first_real_user_text(user_texts)
    matched, worktree, matched_branch = project_matches_repo(project, worktrees or [])
    if branch is None:
        branch = matched_branch
    title_data = (titles or {}).get(session_id) or {}
    session = {
        "platform": "codex",
        "id": session_id or (Path(source_path).stem if source_path else None),
        "title": title_data.get("title"),
        "entrypoint": entrypoint,
        "host": "local",
        "remote_control": False,
        "bridge_session_id": None,
        "originator": originator,
        "source": source,
        "raw_model": raw_model,
        "effort": effort,
        "project": project,
        "worktree": worktree,
        "branch": branch,
        "started": started,
        "last_activity": fallback_mtime,
        "messages": messages,
        "exchanges": len(user_texts),
        "first_user": first_user,
        "last_user": last_user,
        "_first_user_text": first_user_full,
        "source_path": str(source_path) if source_path else None,
        "_matches_repo": matched,
    }
    return apply_session_label(session)
def codex_messages_from_lines(lines, cap=200):
    messages = []
    for record in json_records(lines):
        if record.get("type") != "response_item":
            continue
        payload = record.get("payload") or {}
        role = payload.get("role")
        if role not in ("user", "assistant"):
            continue
        item = detail_item(role, codex_payload_text(payload), record.get("timestamp") or payload.get("timestamp"))
        if item:
            messages.append(item)
        if cap is not None and len(messages) >= cap:
            break
    return messages
def load_codex_titles():
    if not CODEX_INDEX.exists():
        return {}
    return parse_codex_index(CODEX_INDEX.read_text(encoding="utf-8", errors="replace"))
def collect_codex_sessions(worktrees, limit=40):
    titles = load_codex_titles()
    items = []
    for path in recent_files(CODEX_ROOT, "rollout-*.jsonl", limit=limit):
        session = parse_codex_jsonl_lines(sampled_jsonl_lines(path), source_path=path, fallback_mtime=iso_from_mtime(path), titles=titles, worktrees=worktrees)
        if session.pop("_matches_repo", False):
            items.append(session)
    return sort_sessions(items)[:limit]

### Details
def read_claude_messages(path, cap=200, sampled=True):
    lines = sampled_jsonl_lines(path) if sampled else full_jsonl_lines(path)
    return claude_messages_from_lines(lines, cap=cap)
def read_codex_messages(path, cap=200, sampled=True):
    lines = sampled_jsonl_lines(path) if sampled else full_jsonl_lines(path)
    return codex_messages_from_lines(lines, cap=cap)
def read_cursor_messages(composer_id, cap=200):
    if not CURSOR_DB.exists():
        return []
    uri = "file:" + str(CURSOR_DB) + "?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=5) as db:
        row = db.execute("SELECT value FROM cursorDiskKV WHERE key = ?", ("composerData:" + composer_id,)).fetchone()
        if not row:
            return []
        try:
            data = json.loads(row[0])
        except json.JSONDecodeError:
            return []
        messages = []
        for header in data.get("fullConversationHeadersOnly") or []:
            bubble_id = header.get("bubbleId") or header.get("id")
            if not bubble_id:
                continue
            text = cursor_bubble_text(db, composer_id, bubble_id)
            role = "user" if header.get("type") == 1 else "assistant"
            item = detail_item(role, text, cursor_header_ts(header))
            if item:
                messages.append(item)
            if cap is not None and len(messages) >= cap:
                break
        return messages

### Gathering
def cloud_session_preview(conn, session_id):
    rows = conn.execute(
        "SELECT user_text FROM exchanges WHERE session_id = ? AND origin = 'operator' ORDER BY idx",
        (session_id,),
    ).fetchall()
    texts = [row["user_text"] for row in rows if row["user_text"]]
    count = conn.execute("SELECT COUNT(*) AS c FROM exchanges WHERE session_id = ?", (session_id,)).fetchone()["c"]
    first = truncate_text(texts[0], MAX_PREVIEW) if texts else None
    last = truncate_text(texts[-1], MAX_PREVIEW) if texts else None
    return first, last, count
def cloud_session_to_item(conn, row):
    first_user, last_user, messages = cloud_session_preview(conn, row["id"])
    return {
        "platform": row["platform"],
        "id": row["id"],
        "label": row["label"],
        "model": row["model"],
        "interface": row["interface"],
        "entrypoint": row["entrypoint"],
        "host": row["host"],
        "remote_control": bool(row["remote_control"]),
        "bridge_session_id": row["bridge_session_id"],
        "title": row["title"],
        "project": row["project"],
        "worktree": row["worktree"],
        "branch": row["branch"],
        "started": row["started"],
        "last_activity": row["last_activity"],
        "origin": row["origin"] or "operator",
        "source_url": row["source_url"],
        "first_user": first_user,
        "last_user": last_user,
        "messages": messages,
        "exchanges": messages,
        "subagent_count": 0,
    }
def snapshot_session_db_id(session):
    for prefix in ("claude-code", "claude-cloud", "codex", "codex-cloud", "cursor"):
        if str(session.get("id") or "").startswith(prefix + ":"):
            return str(session.get("id"))
    tool = session.get("tool")
    session_id = session.get("id")
    platform = session.get("platform")
    host = session.get("host")
    prefix = tool
    if not prefix:
        if platform == "claude":
            prefix = "claude-cloud" if host == "cloud" else "claude-code"
        elif platform == "codex":
            prefix = "codex-cloud" if host == "cloud" else "codex"
        elif platform == "cursor":
            prefix = "cursor"
    if not prefix or not session_id:
        return None
    session_id = str(session_id)
    if session_id.startswith(str(prefix) + ":"):
        return session_id
    return str(prefix) + ":" + session_id
def subagent_counts_from_turns(repo_root):
    db_path = os.path.join(str(repo_root), "apps/holodeck/data/turns.db")
    if not os.path.exists(db_path):
        return {}
    conn = sqlite3.connect("file:" + db_path + "?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT parent_session_id, COUNT(*) AS count
            FROM sessions
            WHERE parent_session_id IS NOT NULL
            GROUP BY parent_session_id
            """
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()
    return {row["parent_session_id"]: row["count"] for row in rows}
def add_subagent_counts(repo_root, items):
    counts = subagent_counts_from_turns(repo_root)
    for item in items or []:
        stable_id = snapshot_session_db_id(item)
        item["subagent_count"] = int(counts.get(stable_id, 0))
    return items
def collect_cloud_sessions_from_turns(repo_root, worktrees=None, limit=40):
    db_path = os.path.join(str(repo_root), "apps/holodeck/data/turns.db")
    if not os.path.exists(db_path):
        return []
    items = []
    conn = sqlite3.connect("file:" + db_path + "?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        for platform in ("claude", "codex"):
            rows = conn.execute(
                "SELECT * FROM sessions WHERE platform = ? AND host = 'cloud' ORDER BY last_activity DESC LIMIT ?",
                (platform, limit),
            ).fetchall()
            for row in rows:
                items.append(cloud_session_to_item(conn, row))
    finally:
        conn.close()
    return items
def dedupe_sessions_by_id(items):
    # Codex writes several rollout files per logical session (main + subagents), all tagged
    # with the same session_id, so the same session can appear multiple times. Keep one row
    # per id — the richest (most messages), which is the main rollout.
    best = {}
    for item in items:
        sid = item.get("id")
        if not sid:
            continue
        prior = best.get(sid)
        if prior is None or (item.get("messages") or 0) > (prior.get("messages") or 0):
            best[sid] = item
    return list(best.values())
def collect_sessions(repo_root, worktrees=None, include_cloud=False):
    items = []
    notes = []
    for label, collector in (("claude", collect_claude_sessions), ("cursor", collect_cursor_sessions), ("codex", collect_codex_sessions)):
        try:
            items.extend(collector(worktrees or []))
        except Exception as exc:
            notes.append(
                f"{label.capitalize()} local sessions incomplete — scan failed ({exc}). "
                "Other session sources from this refresh may still be current."
            )
    # Cloud sessions are read from turns.db for DISPLAY (the snapshot layer) only. The turns
    # build must NOT include them here — it also calls collect_sessions to ingest local
    # sessions, and re-ingesting the cloud rows would feed prefixed ids back through ingest.
    if include_cloud:
        try:
            items.extend(collect_cloud_sessions_from_turns(repo_root, worktrees or []))
        except Exception as exc:
            notes.append(
                f"Cloud sessions incomplete — turns.db read failed ({exc}). "
                "Local sessions from this refresh may still be current."
            )
    items = dedupe_sessions_by_id(items)
    items = add_subagent_counts(repo_root, items)
    return sort_sessions(items), "; ".join(notes) or None
