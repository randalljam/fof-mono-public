"""Collect Codex cloud tasks for the Holodeck turns database."""

import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

try:
    from apps.holodeck.collectors import sessions as sessions_collector
    from apps.holodeck.turns import db
    from apps.holodeck.turns import labels
except ImportError:
    from collectors import sessions as sessions_collector
    from turns import db
    from turns import labels

BASE_URL = "https://chatgpt.com"
CODEX_TIMEOUT = 20
DEFAULT_LIST_LIMIT = 20
DEFAULT_TOTAL_CAP = 60
WHAM_LIST_LIMIT = 20
DIFF_LIMIT = 20000
CLOUD_SESSION_PREFIX = "codex-cloud:"
AUTH_EXPIRED_NOTE = "codex cloud token expired; run `codex cloud list` or `codex login` to refresh"

### Return values
class CloudTaskList(list):
    def __init__(self, values=None, note=None, cursor=None):
        super().__init__(values or [])
        self.note = note
        self.cursor = cursor
class CloudCodexSessions(list):
    def __init__(self, values=None, note=None, messages_by_session=None, exchanges_by_session=None, task_items=None):
        super().__init__(values or [])
        self.note = note
        self.messages_by_session = messages_by_session or {}
        self.exchanges_by_session = exchanges_by_session or {}
        self.task_items = task_items or []
class CloudCodexError(Exception):
    pass
class CloudAuthError(CloudCodexError):
    pass
class CloudWhamError(CloudCodexError):
    pass

### Wham auth and HTTP
def codex_auth_path(root=None):
    if root:
        return Path(root).expanduser() / ".codex/auth.json"
    return Path.home() / ".codex/auth.json"
def codex_access_token(root=None):
    path = codex_auth_path(root=root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    tokens = data.get("tokens") if isinstance(data, dict) else {}
    token = tokens.get("access_token") if isinstance(tokens, dict) else None
    token = str(token or "").strip()
    return token or None
def wham_url(path):
    text = str(path or "")
    if text.startswith("http://") or text.startswith("https://"):
        return text
    if not text.startswith("/"):
        text = "/" + text
    return BASE_URL + text
def wham_headers(token):
    return {
        "Accept": "application/json",
        "Authorization": "Bearer " + str(token or ""),
    }
def wham_get(path, token, urlopen=None):
    if not token:
        raise CloudWhamError("codex cloud token missing")
    opener = urlopen or urllib.request.urlopen
    request = urllib.request.Request(wham_url(path), headers=wham_headers(token), method="GET")
    try:
        with opener(request, timeout=20) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise CloudAuthError(AUTH_EXPIRED_NOTE)
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        raise CloudWhamError("codex wham HTTP " + str(exc.code) + (": " + body if body else ""))
    except Exception as exc:
        raise CloudWhamError(str(exc))
    try:
        return json.loads(payload or "{}")
    except json.JSONDecodeError as exc:
        raise CloudWhamError("codex wham returned invalid JSON: " + str(exc))
def payload_list(payload, keys):
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in keys:
        values = payload.get(key)
        if isinstance(values, list):
            return [item for item in values if isinstance(item, dict)]
        if isinstance(values, dict):
            nested = payload_list(values, ("data", "items", "tasks"))
            if nested:
                return nested
    return []
def payload_cursor(payload):
    if not isinstance(payload, dict):
        return None
    for key in ("cursor", "next_cursor", "nextCursor"):
        if payload.get(key):
            return payload.get(key)
    pagination = payload.get("pagination")
    if isinstance(pagination, dict):
        for key in ("cursor", "next_cursor", "nextCursor"):
            if pagination.get(key):
                return pagination.get(key)
    return None
def list_wham_tasks(token, limit=WHAM_LIST_LIMIT, cursor=None, total_cap=DEFAULT_TOTAL_CAP, task_filter="current", urlopen=None):
    page_limit = min(int(limit or WHAM_LIST_LIMIT), 20)
    cap = int(total_cap or DEFAULT_TOTAL_CAP)
    tasks = []
    next_cursor = cursor
    seen_cursors = set()
    first = True
    while first or next_cursor:
        first = False
        params = [("limit", str(page_limit)), ("task_filter", task_filter)]
        if next_cursor:
            params.append(("cursor", str(next_cursor)))
            seen_cursors.add(str(next_cursor))
        payload = wham_get("/backend-api/wham/tasks/list?" + urllib.parse.urlencode(params), token, urlopen=urlopen)
        for task in payload_list(payload, ("tasks", "data", "items")):
            if len(tasks) >= cap:
                break
            tasks.append(task)
        next_cursor = payload_cursor(payload)
        if not next_cursor or len(tasks) >= cap or str(next_cursor) in seen_cursors:
            break
    return CloudTaskList(tasks, cursor=next_cursor)
def fetch_task_turns(token, task_id, urlopen=None):
    if not task_id:
        return {}
    task_path = urllib.parse.quote(str(task_id), safe="")
    return wham_get("/backend-api/wham/tasks/" + task_path + "/turns", token, urlopen=urlopen)

### CLI parsing
def parse_cloud_list_json(text):
    if not str(text or "").strip():
        return {"tasks": [], "cursor": None}
    data = json.loads(text)
    if not isinstance(data, dict):
        return {"tasks": [], "cursor": None}
    tasks = data.get("tasks") or []
    if not isinstance(tasks, list):
        tasks = []
    return {
        "tasks": [task for task in tasks if isinstance(task, dict)],
        "cursor": data.get("cursor") or None,
    }
def cloud_cli_missing_note():
    return "codex binary not found; cloud tasks skipped"
def cloud_cli_not_logged_in_note():
    return "codex cloud not logged in; cloud tasks skipped"
def output_mentions_not_logged_in(text):
    return "not logged in" in str(text or "").lower()
def executable_file(path):
    return bool(path and Path(path).is_file() and os.access(path, os.X_OK))
def vendor_codex_binaries(shim):
    if not shim:
        return []
    resolved = Path(shim).resolve()
    package_root = resolved.parent.parent if resolved.name == "codex.js" and resolved.parent.name == "bin" else resolved.parent
    binaries = []
    for path in package_root.glob("node_modules/@openai/codex-darwin-*/vendor/*/bin/codex"):
        if executable_file(path):
            binaries.append(str(path))
    binaries.sort(key=lambda item: (0 if "aarch64-apple-darwin" in item else 1, item))
    return binaries
def codex_command():
    env_path = os.environ.get("CODEX_BIN")
    if executable_file(env_path):
        return env_path
    shim = shutil.which("codex")
    binaries = vendor_codex_binaries(shim)
    if binaries:
        return binaries[0]
    return shim or "codex"
def run_codex_cloud_command(args, timeout=CODEX_TIMEOUT):
    command_path = codex_command()
    return subprocess.run(
        [command_path] + args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
def list_failure_note(command):
    combined = (command.stdout or "") + "\n" + (command.stderr or "")
    if output_mentions_not_logged_in(combined):
        return cloud_cli_not_logged_in_note()
    return "codex cloud list failed: " + ((command.stderr or command.stdout or "").strip() or "unknown error")
def list_page(limit, cursor=None, runner=None):
    args = ["cloud", "list", "--limit", str(limit), "--json"]
    if cursor:
        args.extend(["--cursor", str(cursor)])
    runner = runner or run_codex_cloud_command
    try:
        command = runner(args, timeout=CODEX_TIMEOUT)
    except FileNotFoundError:
        return {"tasks": [], "cursor": None, "note": cloud_cli_missing_note()}
    except subprocess.TimeoutExpired:
        return {"tasks": [], "cursor": None, "note": "codex cloud list timed out; cloud tasks skipped"}
    except Exception as exc:
        return {"tasks": [], "cursor": None, "note": "codex cloud list failed: " + str(exc)}
    if command.returncode != 0:
        return {"tasks": [], "cursor": None, "note": list_failure_note(command)}
    combined = (command.stdout or "") + "\n" + (command.stderr or "")
    if output_mentions_not_logged_in(combined):
        return {"tasks": [], "cursor": None, "note": cloud_cli_not_logged_in_note()}
    try:
        parsed = parse_cloud_list_json(command.stdout)
    except json.JSONDecodeError as exc:
        return {"tasks": [], "cursor": None, "note": "codex cloud list returned invalid JSON: " + str(exc)}
    parsed["note"] = None
    return parsed
def list_cloud_tasks(limit=DEFAULT_LIST_LIMIT, cursor=None, total_cap=DEFAULT_TOTAL_CAP, runner=None):
    page_limit = int(limit or DEFAULT_LIST_LIMIT)
    cap = int(total_cap or DEFAULT_TOTAL_CAP)
    tasks = []
    next_cursor = cursor
    first = True
    while first or next_cursor:
        first = False
        page = list_page(page_limit, cursor=next_cursor, runner=runner)
        if page.get("note"):
            return CloudTaskList([], note=page.get("note"))
        for task in page.get("tasks") or []:
            if len(tasks) >= cap:
                break
            tasks.append(task)
        next_cursor = page.get("cursor")
        if not next_cursor or len(tasks) >= cap:
            break
    return CloudTaskList(tasks, cursor=next_cursor)

### Transcript parsing
def turn_mapping_from_payload(payload):
    if isinstance(payload, dict):
        mapping = payload.get("turn_mapping")
        if isinstance(mapping, dict):
            return mapping
    return {}
def turn_from_node(node):
    if isinstance(node, dict) and isinstance(node.get("turn"), dict):
        return node.get("turn")
    return node if isinstance(node, dict) else {}
def turn_field(turn, key):
    if key in turn:
        return turn.get(key)
    metadata = turn.get("metadata")
    if isinstance(metadata, dict) and key in metadata:
        return metadata.get(key)
    return None
def turn_sort_value(turn):
    parsed = parse_time(turn_field(turn, "created_at"))
    if parsed:
        return (0, parsed.timestamp())
    return (1, str(turn_field(turn, "created_at") or ""))
def ordered_turns(turn_mapping):
    values = list((turn_mapping or {}).values()) if isinstance(turn_mapping, dict) else []
    indexed = [(index, turn_from_node(node)) for index, node in enumerate(values)]
    indexed.sort(key=lambda item: (turn_sort_value(item[1]), item[0]))
    return [item[1] for item in indexed]
def recursive_text_parts(value):
    parts = []
    if isinstance(value, dict):
        if value.get("content_type") == "text" and value.get("text"):
            text = sessions_collector.content_to_text(value.get("text"))
            if text:
                return [text]
        if value.get("type") == "text" and value.get("text"):
            text = sessions_collector.content_to_text(value.get("text"))
            if text:
                return [text]
        for child in value.values():
            parts.extend(recursive_text_parts(child))
        return parts
    if isinstance(value, list):
        for child in value:
            parts.extend(recursive_text_parts(child))
    return parts
def clean_text_parts(parts):
    return [str(part) for part in parts or [] if str(part or "").strip()]
def turn_text_from_items(items):
    parts = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        item_parts = recursive_text_parts(content)
        if not item_parts:
            fallback = sessions_collector.content_to_text(content)
            if fallback:
                item_parts = [fallback]
        parts.extend(item_parts)
    return "\n".join(clean_text_parts(parts))
def turn_text(turn):
    role = turn_field(turn, "role")
    if role == "user":
        return turn_text_from_items(turn.get("input_items") or [])
    if role == "assistant":
        return "\n".join(clean_text_parts(recursive_text_parts(turn.get("output_items") or [])))
    return ""
def turns_to_messages(turn_mapping):
    messages = []
    for turn in ordered_turns(turn_mapping):
        role = turn_field(turn, "role")
        if role not in ("user", "assistant"):
            continue
        item = sessions_collector.detail_item(role, turn_text(turn), turn_field(turn, "created_at"))
        if item:
            messages.append(item)
    return messages
def append_unique(values, value):
    if value and value not in values:
        values.append(value)
def unique_values(values):
    result = []
    for value in values or []:
        if value and value not in result:
            result.append(value)
    return result
def metadata_from_turns(turn_mapping):
    metadata = {"pushes": [], "branches": []}
    seen_pushes = set()
    for turn in ordered_turns(turn_mapping):
        if turn_field(turn, "role") != "assistant":
            continue
        for key in ("model_version", "branch_name", "base_commit_sha", "pull_request_data", "turn_status", "environment"):
            value = turn_field(turn, key)
            if value is not None:
                metadata[key] = value
        branch = turn_field(turn, "branch_name")
        append_unique(metadata["branches"], branch)
        sha = turn_field(turn, "direct_push_pushed_commit_sha")
        if not sha:
            continue
        key = (str(sha), str(turn_field(turn, "created_at") or ""))
        if key in seen_pushes:
            continue
        seen_pushes.add(key)
        metadata["pushes"].append({
            "sha": str(sha),
            "ts": turn_field(turn, "created_at"),
            "branch": branch,
        })
    return metadata

### Diff
def task_diff(task_id, runner=None):
    if not task_id:
        return ""
    runner = runner or run_codex_cloud_command
    try:
        command = runner(["cloud", "diff", str(task_id)], timeout=CODEX_TIMEOUT)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    except Exception:
        return ""
    if command.returncode != 0:
        return ""
    if output_mentions_not_logged_in((command.stdout or "") + "\n" + (command.stderr or "")):
        return ""
    return command.stdout or ""

### Task mapping
def cloud_session_id(task_id):
    return CLOUD_SESSION_PREFIX + str(task_id)
def normalize_match_token(value):
    text = str(value or "").strip().lower().replace("_", "-")
    text = re.sub(r"[^a-z0-9/.-]+", "-", text)
    return text.strip("-")
def slashless_token(value):
    return normalize_match_token(value).replace("/", "-")
def candidate_tokens(value):
    token = normalize_match_token(value)
    if not token:
        return []
    tokens = [token]
    slashless = slashless_token(token)
    if slashless != token:
        tokens.append(slashless)
    basename = slashless.split("-")[-1]
    if basename and basename != slashless:
        tokens.append(basename)
    return tokens
def worktree_match_tokens(worktree):
    tokens = []
    path = worktree.get("path")
    for value in (worktree.get("name"), Path(path).name if path else None, worktree.get("branch")):
        tokens.extend(candidate_tokens(value))
    for slug in worktree.get("apps_touched") or []:
        tokens.extend(candidate_tokens(slug))
    return [token for token in tokens if token]
def token_matches_environment(environment, token):
    if not environment or not token:
        return False
    if environment == token:
        return True
    if len(environment) >= 4 and environment in token:
        return True
    return len(token) >= 4 and token in environment
def match_environment_label(environment_label, worktrees=None):
    environment = slashless_token(environment_label)
    if not environment:
        return None, None
    for worktree in worktrees or []:
        for token in worktree_match_tokens(worktree):
            if token_matches_environment(environment, slashless_token(token)):
                return worktree.get("path"), worktree.get("branch")
    return None, None
def task_summary_value(task, key):
    summary = task.get("summary") or {}
    value = summary.get(key)
    return value if value is not None else 0
def task_summary_line(task):
    status = task.get("status") or "unknown"
    files_changed = task_summary_value(task, "files_changed")
    lines_added = task_summary_value(task, "lines_added")
    lines_removed = task_summary_value(task, "lines_removed")
    return "Codex cloud task {0}: {1} files changed, +{2}/-{3}".format(status, files_changed, lines_added, lines_removed)
def capped_diff(diff):
    text = str(diff or "")
    if len(text) <= DIFF_LIMIT:
        return text
    return text[:DIFF_LIMIT]
def task_id_value(task):
    return task.get("id") or task.get("task_id")
def task_url(task_id, task):
    for key in ("url", "source_url", "task_url"):
        if task.get(key):
            return task.get(key)
    return BASE_URL + "/codex/tasks/" + str(task_id)
def environment_label_value(value):
    if isinstance(value, dict):
        for key in ("label", "name", "display_name", "environment_label", "slug", "id"):
            if value.get(key):
                return str(value.get(key))
        return None
    if value:
        return str(value)
    return None
def task_environment_label(task, metadata=None):
    metadata = metadata or {}
    for value in (metadata.get("environment"), task.get("environment_label"), task.get("environment")):
        label = environment_label_value(value)
        if label:
            return label
    return None
def match_branch_worktree(branch, worktrees=None):
    if not branch:
        return None
    for worktree in worktrees or []:
        if worktree.get("branch") == branch:
            return worktree.get("path")
    return None
def timestamp_bounds(task, messages=None):
    values = []
    for key in ("created_at", "started_at", "updated_at"):
        if task.get(key):
            values.append(task.get(key))
    for message in messages or []:
        if message.get("ts"):
            values.append(message.get("ts"))
    parsed = [(parse_time(value), value) for value in values]
    parsed = [item for item in parsed if item[0]]
    if not parsed:
        fallback = task.get("updated_at") or task.get("created_at")
        return fallback, fallback
    parsed.sort(key=lambda item: item[0])
    return parsed[0][0].isoformat(), parsed[-1][0].isoformat()
def add_session_previews(session, messages):
    user_texts = [message.get("text") for message in messages or [] if message.get("role") == "user"]
    first_user, last_user = sessions_collector.first_last_user_text(user_texts)
    session["messages"] = len(messages or [])
    session["first_user"] = first_user
    session["last_user"] = last_user
    return session
def to_session(task, metadata=None, messages=None, worktrees=None):
    metadata = metadata or {}
    task_id = task_id_value(task)
    if not task_id:
        return None
    environment_label = task_environment_label(task, metadata=metadata)
    branch = metadata.get("branch_name") or task.get("branch_name") or task.get("branch")
    worktree = match_branch_worktree(branch, worktrees=worktrees)
    env_worktree, env_branch = match_environment_label(environment_label, worktrees=worktrees)
    if not worktree:
        worktree = env_worktree
    if not branch:
        branch = env_branch
    session_id = cloud_session_id(task_id)
    raw_model = metadata.get("model_version") or task.get("model_version")
    pretty_model = labels.pretty_codex_model(raw_model)
    interface = labels.session_interface({"platform": "codex", "entrypoint": "app", "host": "cloud"})
    label = interface + (" - " + pretty_model if pretty_model else "")
    started, last_activity = timestamp_bounds(task, messages=messages)
    session = {
        "id": session_id,
        "platform": "codex",
        "entrypoint": "app",
        "host": "cloud",
        "remote_control": False,
        "bridge_session_id": None,
        "source_path": None,
        "source_url": task_url(task_id, task),
        "project": None,
        "worktree": worktree,
        "branch": branch,
        "label": label,
        "model": pretty_model,
        "interface": interface,
        "origin": db.OPERATOR_ORIGIN,
        "title": task.get("title"),
        "environment_label": environment_label,
        "started": started,
        "last_activity": last_activity,
        "_pushes": metadata.get("pushes") or [],
        "_branches": unique_values((metadata.get("branches") or []) + [branch]),
        "_transcript": True,
    }
    return add_session_previews(session, messages or [])
def task_item_for_session(task, session, metadata=None):
    metadata = metadata or {}
    item = dict(task)
    item["_session_id"] = session.get("id")
    item["_pushes"] = metadata.get("pushes") or session.get("_pushes") or []
    item["_branches"] = unique_values((metadata.get("branches") or []) + (session.get("_branches") or []) + [session.get("branch")])
    item["_transcript"] = bool(session.get("_transcript"))
    item["url"] = session.get("source_url") or item.get("url")
    item["updated_at"] = session.get("last_activity") or item.get("updated_at")
    item["environment_label"] = task_environment_label(task, metadata=metadata) or item.get("environment_label")
    item["branch_name"] = session.get("branch") or item.get("branch_name")
    return item
def to_session_and_exchange(task, diff, worktrees=None):
    task_id = task_id_value(task)
    if not task_id:
        return None, None
    updated_at = task.get("updated_at")
    environment_label = task.get("environment_label")
    worktree, branch = match_environment_label(environment_label, worktrees=worktrees)
    session_id = cloud_session_id(task_id)
    interface = labels.session_interface({"platform": "codex", "entrypoint": "app", "host": "cloud"})
    session = {
        "id": session_id,
        "platform": "codex",
        "entrypoint": "app",
        "host": "cloud",
        "remote_control": False,
        "bridge_session_id": None,
        "source_path": None,
        "source_url": task_url(task_id, task),
        "project": None,
        "worktree": worktree,
        "branch": branch,
        "label": interface,
        "model": None,
        "interface": interface,
        "origin": db.OPERATOR_ORIGIN,
        "title": task.get("title"),
        "environment_label": environment_label,
        "started": updated_at,
        "last_activity": updated_at,
    }
    exchange = {
        "id": session_id + "#0",
        "session_id": session_id,
        "idx": 0,
        "kind": "primary",
        "user_ts": updated_at,
        "user_text": task.get("title") or "",
        "response_text": task_summary_line(task) + "\n\n" + capped_diff(diff),
        "response_end_ts": updated_at,
        "origin": db.OPERATOR_ORIGIN,
        "follow_up_of": None,
    }
    return session, exchange

### Collection
def collect_wham_sessions(token, tasks, worktrees=None, urlopen=None):
    sessions = []
    messages_by_session = {}
    task_items = []
    notes = []
    for task in tasks or []:
        task_id = task_id_value(task)
        if not task_id:
            continue
        try:
            turns_payload = fetch_task_turns(token, task_id, urlopen=urlopen)
        except CloudAuthError:
            raise
        except Exception as exc:
            notes.append("codex cloud task " + str(task_id) + " failed: " + str(exc))
            continue
        turn_mapping = turn_mapping_from_payload(turns_payload)
        messages = turns_to_messages(turn_mapping)
        metadata = metadata_from_turns(turn_mapping)
        session = to_session(task, metadata=metadata, messages=messages, worktrees=worktrees)
        if not session:
            continue
        sessions.append(session)
        messages_by_session[session["id"]] = messages
        task_items.append(task_item_for_session(task, session, metadata=metadata))
    note = "; ".join(notes) if notes else None
    return CloudCodexSessions(sessions_collector.sort_sessions(sessions), note=note, messages_by_session=messages_by_session, task_items=task_items)
def collect_cli_sessions(worktrees=None, runner=None, note_prefix=None):
    tasks = list_cloud_tasks(runner=runner)
    note = getattr(tasks, "note", None)
    if note_prefix:
        note = note_prefix + ("; " + note if note else "")
    sessions = []
    exchanges_by_session = {}
    task_items = list(tasks or [])
    for task in task_items:
        diff = task_diff(task_id_value(task), runner=runner)
        session, exchange = to_session_and_exchange(task, diff, worktrees=worktrees)
        if not session or not exchange:
            continue
        sessions.append(session)
        exchanges_by_session[session["id"]] = [exchange]
    return CloudCodexSessions(sessions_collector.sort_sessions(sessions), note=note, exchanges_by_session=exchanges_by_session, task_items=task_items)
def collect_sessions(worktrees=None, root=None, token=None, urlopen=None, runner=None):
    access_token = token if token is not None else codex_access_token(root=root)
    if not access_token:
        return collect_cli_sessions(worktrees=worktrees, runner=runner)
    try:
        tasks = list_wham_tasks(access_token, urlopen=urlopen)
        return collect_wham_sessions(access_token, tasks, worktrees=worktrees, urlopen=urlopen)
    except CloudAuthError:
        return CloudCodexSessions([], note=AUTH_EXPIRED_NOTE)
    except Exception as exc:
        return collect_cli_sessions(worktrees=worktrees, runner=runner, note_prefix="codex wham API failed: " + str(exc) + "; used codex CLI metadata fallback")

### Commit correlation
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
def task_files_changed(task):
    try:
        return int(task_summary_value(task, "files_changed"))
    except (TypeError, ValueError):
        return 0
def response_files_changed(text):
    match = re.search(r"(\d+)\s+files changed", str(text or ""))
    if not match:
        return 0
    return int(match.group(1))
def task_pushes(task):
    pushes = []
    for push in task.get("_pushes") or []:
        if isinstance(push, dict) and push.get("sha"):
            pushes.append(push)
    sha = task.get("direct_push_pushed_commit_sha")
    if sha:
        pushes.append({"sha": str(sha), "ts": task.get("updated_at"), "branch": task.get("branch_name") or task.get("branch")})
    return pushes
def task_branches(task):
    return unique_values((task.get("_branches") or []) + [task.get("branch_name"), task.get("branch")])
def task_refs_by_session(tasks):
    refs = {}
    for task in tasks or []:
        task_id = task_id_value(task)
        if not task_id:
            continue
        session_id = task.get("_session_id") or cloud_session_id(task_id)
        refs[session_id] = {
            "task_id": str(task_id),
            "url": task.get("url"),
            "updated_at": task.get("updated_at"),
            "files_changed": task_files_changed(task),
            "pushes": task_pushes(task),
            "branches": task_branches(task),
            "transcript": bool(task.get("_transcript")),
        }
    return refs
def push_matches_exchange(push, row):
    push_time = parse_time(push.get("ts"))
    if not push_time:
        return False
    user_time = parse_time(row["user_ts"])
    response_end = parse_time(row["response_end_ts"])
    if response_end and abs((push_time - response_end).total_seconds()) <= 1:
        return True
    if user_time and response_end and user_time <= push_time <= response_end:
        return True
    if user_time and not response_end and push_time >= user_time:
        return True
    return False
def matching_pushes(row, pushes):
    return [push for push in pushes or [] if push_matches_exchange(push, row)]
def load_cloud_records(conn, tasks=None):
    refs = task_refs_by_session(tasks)
    rows = conn.execute(
        """
        SELECT sessions.*, exchanges.id AS exchange_id, exchanges.user_ts, exchanges.response_end_ts, exchanges.response_text
        FROM sessions
        JOIN exchanges ON exchanges.session_id = sessions.id
        WHERE sessions.platform = 'codex' AND sessions.host = 'cloud'
        ORDER BY exchanges.idx
        """
    ).fetchall()
    records = []
    for row in rows:
        session_id = row["id"]
        task_id = session_id[len(CLOUD_SESSION_PREFIX):] if session_id.startswith(CLOUD_SESSION_PREFIX) else session_id
        ref = refs.get(session_id) or {}
        records.append({
            "session_id": session_id,
            "exchange_id": row["exchange_id"],
            "task_id": ref.get("task_id") or task_id,
            "url": ref.get("url") or row["source_url"],
            "updated_at": ref.get("updated_at") or row["response_end_ts"] or row["user_ts"] or row["last_activity"],
            "files_changed": ref.get("files_changed") if ref.get("files_changed") is not None else response_files_changed(row["response_text"]),
            "worktree": row["worktree"],
            "branch": row["branch"],
            "branches": unique_values((ref.get("branches") or []) + [row["branch"]]),
            "pushes": matching_pushes(row, ref.get("pushes") or []),
            "transcript": bool(ref.get("transcript")),
            "user_ts": row["user_ts"],
            "response_end_ts": row["response_end_ts"],
        })
    return records
def load_commit_rows(conn):
    return [dict(row) for row in conn.execute("SELECT * FROM commits ORDER BY committer_date").fetchall()]
def commit_text(commit):
    return "\n".join([str(commit.get("subject") or ""), str(commit.get("body") or "")])
def commit_mentions_task(commit, record):
    text = commit_text(commit)
    task_id = record.get("task_id")
    url = record.get("url")
    return bool((task_id and task_id in text) or (url and url in text))
def commit_matches_record_branch_or_worktree(commit, record):
    branches = set(record.get("branches") or [])
    if branches and commit.get("branch") in branches:
        return True
    return bool(record.get("worktree") and commit.get("worktree") == record.get("worktree"))
def commit_in_cloud_window(commit, record):
    if not commit_matches_record_branch_or_worktree(commit, record):
        return False
    if not record.get("transcript") and not record.get("files_changed"):
        return False
    updated_at = parse_time(record.get("updated_at"))
    commit_time = parse_time(commit.get("committer_date"))
    if not updated_at or not commit_time:
        return False
    return abs(commit_time - updated_at) <= timedelta(hours=24)
def existing_link_keys(conn):
    return {(row["exchange_id"], row["sha"]) for row in conn.execute("SELECT exchange_id, sha FROM links").fetchall()}
def upsert_cloud_link(conn, exchange_id, sha, method, confidence, linked, existing):
    key = (exchange_id, sha)
    if key in linked:
        return 0
    db.upsert_link(conn, {
        "exchange_id": exchange_id,
        "sha": sha,
        "method": method,
        "confidence": confidence,
    })
    linked.add(key)
    return 0 if key in existing else 1
def link_direct_pushes(conn, record, commits_by_sha, linked, existing):
    count = 0
    for push in record.get("pushes") or []:
        sha = push.get("sha")
        if sha not in commits_by_sha:
            continue
        count += upsert_cloud_link(conn, record["exchange_id"], sha, "codex-cloud-push", 0.97, linked, existing)
    return count
def link_cloud_task_commits(conn, tasks=None):
    commits = load_commit_rows(conn)
    commits_by_sha = {commit["sha"]: commit for commit in commits}
    existing = existing_link_keys(conn)
    records = load_cloud_records(conn, tasks=tasks)
    sessions_with_exact_push = {
        record["session_id"]
        for record in records
        if any(push.get("sha") in commits_by_sha for push in record.get("pushes") or [])
    }
    linked = set()
    count = 0
    for record in records:
        exact_count = link_direct_pushes(conn, record, commits_by_sha, linked, existing)
        count += exact_count
        if record["session_id"] in sessions_with_exact_push:
            continue
        url_linked_shas = set()
        for commit in commits:
            if not commit_mentions_task(commit, record):
                continue
            count += upsert_cloud_link(conn, record["exchange_id"], commit["sha"], "codex-cloud-url", 0.95, linked, existing)
            url_linked_shas.add(commit["sha"])
        for commit in commits:
            if commit["sha"] in url_linked_shas:
                continue
            if not commit_in_cloud_window(commit, record):
                continue
            count += upsert_cloud_link(conn, record["exchange_id"], commit["sha"], "codex-cloud-window", 0.5, linked, existing)
    return count
