"""FastAPI server for the holodeck snapshot."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_ROOT_STR = str(ROOT)
if sys.path[:1] != [_ROOT_STR]:
    while _ROOT_STR in sys.path:
        sys.path.remove(_ROOT_STR)
    sys.path.insert(0, _ROOT_STR)

import ipaddress
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

import uvicorn
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from apps.holodeck import state as state_store
from apps.holodeck.collectors import LAYER_NAMES
from apps.holodeck.collectors import branches as branches_collector
from apps.holodeck.collectors import sessions as sessions_collector
from apps.holodeck.collectors import worktrees as worktrees_collector
from apps.holodeck.turns import cloud_claude as turns_cloud_claude
from apps.holodeck.turns import db as turns_db
from apps.holodeck.turns import digest as turns_digest
from apps.holodeck.turns import hash_map as turns_hash_map
from apps.holodeck.turns import ingest as turns_ingest
from apps.holodeck.worktree_colors_palette import write_worktree_colors_palette

HOLODECK_DIR = ROOT / "apps/holodeck"
SNAPSHOT_PATH = HOLODECK_DIR / "data/snapshot.json"
STATE_PATH = HOLODECK_DIR / "data/state.json"
TODO_ARCHIVE_PATH = HOLODECK_DIR / "data/todo-archive.md"
TURNS_DB_PATH = HOLODECK_DIR / "data/turns.db"
WEB_DIR = HOLODECK_DIR / "web"
HOLODECK_HOST = "127.0.0.1"
HOLODECK_PORT = 8790
HOLODECK_URL = "http://{0}:{1}".format(HOLODECK_HOST, HOLODECK_PORT)
SERVER_PROCESS_MARKERS = ("uvicorn apps.holodeck", "apps.holodeck.server:app", "apps/holodeck/server.py")
REFRESH_LOCK = threading.Lock()
TURNS_REFRESH_LOCK = threading.Lock()
TURNS_DIGEST_LOCK = threading.Lock()
TURNS_AUTO_DIGEST_LOCK = threading.Lock()
AI_SYNC_LOCK = threading.Lock()
AI_SYNC_STATUS_LOCK = threading.Lock()
CLOUD_STATUS_LOCK = threading.Lock()
TURNS_DIGEST_RUNNING = set()
AI_SYNC_LAST_RESULT = {}
CLOUD_STATUS_CACHE = {}
STATE_LOCK = threading.Lock()
FOCUS_LOCK = threading.Lock()
FILE_READ_LIMIT = 200 * 1024
ALLOWED_FILE_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".txt", ".py", ".js", ".mjs", ".html", ".css", ".toml", ".sh"}
TODO_ARCHIVE_HEADING = "# Holodeck to-do archive"
TODO_ARCHIVE_ITEM_RE = re.compile(r"^- \[([ xX])\] (.+) \(added ([^,]+), archived (\d{2}:\d{2})\)$")
CLOUD_STATUS_TTL = 60
CLAUDE_CLOUD_STATUS_TTL = 300
CLOUD_STATUS_TIMEOUT = 8
CODEX_CLOUD_BASE_URL = "https://chatgpt.com"
CODEX_CLOUD_PROBE_PATH = "/backend-api/wham/tasks/list?limit=1&task_filter=current"
CLAUDE_CLOUD_BASE_URL = "https://claude.ai"
CLAUDE_CLOUD_API_VERSION = "2023-06-01"
CLAUDE_CLOUD_PROBE_PATH = "/v1/code/sessions"
CLAUDE_EXPORT_PATTERNS = ("holodeck-claude-cloud*.json", "holodeck-cc-*.json")
CLAUDE_EXPORT_SNIPPET_PATH = WEB_DIR / "claude-cloud-export-snippet.js"
CLAUDE_EXPORT_GUIDANCE = (
    "Claude cloud uses a browser export (Cloudflare blocks server-side access). "
    "Copy the Holodeck export snippet → paste it in the DevTools console on https://claude.ai/code → "
    "save holodeck-claude-cloud-export.json to Downloads → hit Refresh."
)
AI_SYNC_TAIL_LIMIT = 4000
AI_SYNC_S3_TIMEOUT = 600
FOCUS_ACTION_HEADER = "focus"
FOCUS_MATCHER_LIMIT = 4096
FOCUS_ERROR_STATUS = {
    "invalid_request": 400,
    "forbidden_client": 403,
    "app_not_running": 404,
    "target_not_found": 404,
    "ambiguous_match": 409,
    "focus_busy": 409,
    "unsupported_platform": 501,
    "automation_failed": 502,
    "permission_required": 503,
    "automation_timeout": 504,
}
FOCUS_ERROR_MESSAGES = {
    "invalid_request": "The focus request is invalid.",
    "forbidden_client": "The focus request is not authorized.",
    "app_not_running": "Cursor is not running.",
    "target_not_found": "The Cursor window is no longer open.",
    "ambiguous_match": "More than one Cursor window matched.",
    "focus_busy": "Another focus action is already running.",
    "unsupported_platform": "Window focus is supported only on macOS.",
    "automation_failed": "macOS could not focus the Cursor window.",
    "permission_required": "macOS Accessibility or Automation permission is required.",
    "automation_timeout": "The macOS focus action timed out.",
}
@asynccontextmanager
async def lifespan(server_app):
    try:
        ensure_turns_schema()
    except Exception:
        pass
    try:
        write_worktree_colors_palette(ROOT)
    except Exception:
        pass
    start_auto_refresh_if_needed()
    yield
app = FastAPI(lifespan=lifespan)
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

### Snapshot
def load_snapshot():
    if not SNAPSHOT_PATH.exists():
        return None
    with SNAPSHOT_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)
def route_platform(value):
    mapping = {
        "claude-code": "claude",
        "claude-cloud": "claude",
        "codex-cloud": "codex",
    }
    key = str(value or "")
    return mapping.get(key, key)
def session_platform(session):
    mapping = {
        "claude-code": "claude",
        "claude-cloud": "claude",
        "codex-cloud": "codex",
    }
    value = session.get("platform") or session.get("tool")
    return mapping.get(str(value or ""), str(value or ""))
def find_session(snapshot, platform, session_id):
    wanted = route_platform(platform)
    for session in snapshot.get("layers", {}).get("sessions", []):
        if session_platform(session) == wanted and session.get("id") == session_id:
            return session
    return None
def path_under(path, root):
    try:
        Path(path).expanduser().resolve(strict=False).relative_to(Path(root).expanduser().resolve(strict=False))
        return True
    except ValueError:
        return False
def snapshot_worktree_paths(snapshot_data):
    paths = []
    for worktree in (snapshot_data or {}).get("layers", {}).get("worktrees", []):
        path = worktree.get("path")
        if path and not worktree.get("missing"):
            paths.append(path)
    return paths
def snapshot_is_stale(path, max_age_s=1800):
    if not path.exists():
        return True
    try:
        with path.open("r", encoding="utf-8") as handle:
            generated_at = json.load(handle).get("generated_at")
        if not generated_at:
            return True
        generated = datetime.fromisoformat(generated_at)
        if generated.tzinfo is None:
            generated = generated.astimezone()
        return (datetime.now().astimezone() - generated).total_seconds() > max_age_s
    except Exception:
        return True
def run_collect_subprocess(layers=None):
    # Prefer -m so repo-root imports win over stale editable metadata.
    command = [sys.executable, "-m", "apps.holodeck.collect"]
    for layer in layers or []:
        command.extend(["--layer", layer])
    return subprocess.run(
        command,
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=300,
        check=False,
    )
def assert_holodeck_modules_under_root():
    holodeck_file = Path(branches_collector.__file__).resolve()
    if not path_under(holodeck_file, ROOT):
        raise RuntimeError(
            "Holodeck imports resolved outside this checkout: "
            + str(holodeck_file)
            + " (expected under "
            + str(ROOT)
            + ")"
        )
assert_holodeck_modules_under_root()

### Query helpers
def parse_query_int(value, default, name):
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(name + " must be an integer")
    if parsed < 0:
        raise ValueError(name + " must be non-negative")
    return parsed
def parse_branch_commit_paging(skip, limit):
    parsed_skip = parse_query_int(skip, 0, "skip")
    parsed_limit = parse_query_int(limit, 20, "limit")
    if parsed_limit < 1:
        raise ValueError("limit must be at least 1")
    if parsed_limit > 100:
        parsed_limit = 100
    return parsed_skip, parsed_limit
def snapshot_branch_names(snapshot_data):
    names = set()
    for branch in (snapshot_data or {}).get("layers", {}).get("branches", []):
        name = branch.get("name")
        if isinstance(name, str) and name:
            names.add(name)
    return names
def parse_turns_limit(limit):
    parsed = parse_query_int(limit, 20, "limit")
    if parsed < 1:
        raise ValueError("limit must be at least 1")
    if parsed > 100:
        parsed = 100
    return parsed
def ensure_turns_schema():
    conn = turns_db.connect(TURNS_DB_PATH)
    try:
        turns_db.init_db(conn)
        conn.commit()
    finally:
        conn.close()
def open_turns_db():
    # Read connections must NOT write (init_db writes set_meta) — that collides with a
    # concurrent turns-build write and raises "database is locked". Schema is ensured once
    # at startup (and by every build); reads just connect (WAL + busy_timeout for safety).
    return turns_db.connect(TURNS_DB_PATH)
def validate_turn_exchange_id(exchange_id):
    if not turns_db.validate_exchange_id(exchange_id):
        raise HTTPException(status_code=400, detail="invalid exchange id")
    return exchange_id
def validate_turn_session_id(session_id):
    if not isinstance(session_id, str) or not session_id or len(session_id) > 300:
        raise HTTPException(status_code=400, detail="invalid session id")
    if "/" in session_id or "\\" in session_id or "?" in session_id:
        raise HTTPException(status_code=400, detail="invalid session id")
    if any(ord(char) < 32 or ord(char) == 127 for char in session_id):
        raise HTTPException(status_code=400, detail="invalid session id")
    return session_id
def digest_running_add(exchange_id):
    with TURNS_DIGEST_LOCK:
        if exchange_id in TURNS_DIGEST_RUNNING:
            return False
        TURNS_DIGEST_RUNNING.add(exchange_id)
        return True
def digest_running_remove(exchange_id):
    with TURNS_DIGEST_LOCK:
        TURNS_DIGEST_RUNNING.discard(exchange_id)
def turns_auto_digest_worker():
    conn = None
    try:
        conn = open_turns_db()
        summary = turns_digest.auto_digest_recent(conn, root=ROOT)
        print("holodeck turns auto-digest:", json.dumps(summary), flush=True)
    finally:
        if conn is not None:
            conn.close()
        TURNS_AUTO_DIGEST_LOCK.release()
def start_turns_auto_digest():
    if not TURNS_AUTO_DIGEST_LOCK.acquire(blocking=False):
        return "already-running"
    thread = threading.Thread(target=turns_auto_digest_worker, daemon=True)
    thread.start()
    return "started"

### File safety
def resolve_client_path(path_value, repo_root):
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("path is required")
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = Path(repo_root) / path
    return path.resolve(strict=False)
def file_allowed_roots(repo_root, snapshot_data):
    return [Path(repo_root)] + [Path(path) for path in snapshot_worktree_paths(snapshot_data)]
def validate_file_root(path, roots):
    for root in roots:
        if path_under(path, root):
            return True
    return False
def validate_file_suffix(path):
    return path.suffix.lower() in ALLOWED_FILE_SUFFIXES
def validate_file_read_path(path_value, repo_root, snapshot_data):
    path = resolve_client_path(path_value, repo_root)
    if not validate_file_root(path, file_allowed_roots(repo_root, snapshot_data)):
        raise ValueError("path must be inside repo root or a known worktree")
    if not validate_file_suffix(path):
        raise ValueError("file suffix is not readable")
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(str(path))
    return path
def is_file_write_allowed(path):
    text = path.as_posix()
    if text.endswith("/apps/holodeck/registry.yaml"):
        return True
    if text.endswith("/apps/holodeck/worktree-colors.yaml"):
        return True
    if "/openspec/" in text and (path.suffix.lower() == ".md" or path.name == "config.yaml"):
        return True
    return False
def validate_file_write_path(path_value, repo_root, snapshot_data):
    path = resolve_client_path(path_value, repo_root)
    if not validate_file_root(path, file_allowed_roots(repo_root, snapshot_data)):
        raise ValueError("path must be inside repo root or a known worktree")
    if not validate_file_suffix(path):
        raise ValueError("file suffix is not writable")
    if not is_file_write_allowed(path):
        raise PermissionError("file is not in the write allowlist")
    if not path.parent.exists() or not path.parent.is_dir():
        raise FileNotFoundError(str(path.parent))
    return path
def read_limited_text(path):
    with Path(path).open("rb") as handle:
        data = handle.read(FILE_READ_LIMIT + 1)
    truncated = len(data) > FILE_READ_LIMIT
    if truncated:
        data = data[:FILE_READ_LIMIT]
    return data.decode("utf-8", errors="replace"), truncated
def atomic_write_text(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), prefix=path.name + ".", suffix=".tmp", delete=False)
    tmp_name = handle.name
    try:
        with handle:
            handle.write(content)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise

### State
def load_state_doc():
    return state_store.load_state(STATE_PATH)
def save_state_doc(state):
    return state_store.write_state(STATE_PATH, state)
def state_error(status_code, exc):
    raise HTTPException(status_code=status_code, detail=str(exc))

### To-do archive
def todo_archive_line(item, archived_at):
    done = "x" if item.get("done") is True else " "
    text = " ".join(str(item.get("text") or "").split())
    added_date = str(item.get("created_at") or "unknown")[:10]
    archived_time = archived_at.strftime("%H:%M")
    return f"- [{done}] {text} (added {added_date}, archived {archived_time})"
def todo_archive_lines(content):
    if not content.strip():
        return [TODO_ARCHIVE_HEADING, ""]
    lines = content.splitlines()
    if not lines or lines[0].strip() != TODO_ARCHIVE_HEADING:
        return [TODO_ARCHIVE_HEADING, ""] + lines
    return lines
def add_todo_archive_item(content, item, archived_at=None):
    archived_at = archived_at or datetime.now().astimezone()
    section = "## " + archived_at.date().isoformat()
    line = todo_archive_line(item, archived_at)
    lines = todo_archive_lines(content)
    for index, existing in enumerate(lines):
        if existing.strip() != section:
            continue
        insert_at = index + 1
        while insert_at < len(lines) and not lines[insert_at].startswith("## "):
            insert_at += 1
        while insert_at > index + 1 and lines[insert_at - 1] == "":
            insert_at -= 1
        lines.insert(insert_at, line)
        return "\n".join(lines).rstrip() + "\n"
    insert_at = 1
    if len(lines) > 1 and lines[1] == "":
        insert_at = 2
    lines[insert_at:insert_at] = [section, line, ""]
    return "\n".join(lines).rstrip() + "\n"
def append_todo_archive(path, item, archived_at=None):
    archive_path = Path(path)
    content = archive_path.read_text(encoding="utf-8") if archive_path.exists() else ""
    atomic_write_text(archive_path, add_todo_archive_item(content, item, archived_at=archived_at))
def parse_todo_archive(content):
    """Parse archive markdown into items, most recently archived first."""
    sections = []
    current_date = ""
    current_items = None
    for raw in str(content or "").splitlines():
        line = raw.strip()
        if line.startswith("## "):
            current_date = line[3:].strip()
            current_items = []
            sections.append((current_date, current_items))
            continue
        match = TODO_ARCHIVE_ITEM_RE.match(line)
        if not match or current_items is None:
            continue
        archived_time = match.group(4)
        current_items.append({
            "text": match.group(2).strip(),
            "done": match.group(1).lower() == "x",
            "added": match.group(3).strip(),
            "archived_date": current_date,
            "archived_time": archived_time,
            "archived_at": "{0}T{1}".format(current_date, archived_time) if current_date else archived_time,
        })
    # File order: newest date sections first; within a day, oldest first. Flip each day.
    items = []
    for _date, day_items in sections:
        items.extend(reversed(day_items))
    return items
def load_todo_archive(path):
    archive_path = Path(path)
    if not archive_path.exists():
        return []
    return parse_todo_archive(archive_path.read_text(encoding="utf-8"))

### Auto refresh
def auto_refresh_worker():
    try:
        run_collect_subprocess()
    finally:
        REFRESH_LOCK.release()
def start_auto_refresh_if_needed():
    if not snapshot_is_stale(SNAPSHOT_PATH):
        return
    if not REFRESH_LOCK.acquire(blocking=False):
        return
    print("holodeck auto-refresh started: snapshot missing or stale", flush=True)
    thread = threading.Thread(target=auto_refresh_worker, daemon=True)
    thread.start()

### AI sync
def now_iso():
    return datetime.now().astimezone().isoformat()
def home_relative_path(*parts, home=None):
    return Path(home or Path.home()).joinpath(*parts)
def downloads_dir(home=None):
    return home_relative_path("Downloads", home=home)
def local_files_mount(home=None):
    return home_relative_path("Documents", "Code", "_LOCAL_FILES", "fof-mono", home=home)
def claude_cloud_archive_dir(home=None):
    return local_files_mount(home=home) / "ai-sessions/cloud_claude"
def file_signature(path):
    stat = Path(path).stat()
    return stat.st_size, int(stat.st_mtime)
def same_file_signature(first, second):
    try:
        return file_signature(first) == file_signature(second)
    except OSError:
        return False
def claude_export_target_name(path):
    stamp = datetime.fromtimestamp(Path(path).stat().st_mtime).strftime("%Y-%m-%d_%H%M%S")
    return stamp + "_claude-cloud.json"
def unique_claude_export_target(source, target_dir, reserved=None):
    base = Path(target_dir) / claude_export_target_name(source)
    reserved = reserved or set()
    counter = 1
    while True:
        candidate = base if counter == 1 else base.with_name(base.stem + "-" + str(counter) + base.suffix)
        counter += 1
        if str(candidate) in reserved:
            continue
        if not candidate.exists():
            return candidate
        if same_file_signature(source, candidate):
            return None
def claude_export_candidates(downloads_path):
    if not Path(downloads_path).is_dir():
        return []
    paths = []
    seen = set()
    for pattern in CLAUDE_EXPORT_PATTERNS:
        for path in Path(downloads_path).glob(pattern):
            if path.name.startswith(".") or not path.is_file():
                continue
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            paths.append(path)
    return sorted(paths, key=lambda path: (path.stat().st_mtime, path.name))
def claude_export_pickup_moves(downloads_path=None, target_dir=None, home=None):
    source_dir = Path(downloads_path) if downloads_path is not None else downloads_dir(home=home)
    destination_dir = Path(target_dir) if target_dir is not None else claude_cloud_archive_dir(home=home)
    if not source_dir.is_dir() or not destination_dir.is_dir():
        return []
    moves = []
    reserved = set()
    for source in claude_export_candidates(source_dir):
        target = unique_claude_export_target(source, destination_dir, reserved=reserved)
        if target is None:
            continue
        reserved.add(str(target))
        moves.append({"source": str(source), "target": str(target)})
    return moves
def pickup_downloaded_claude_exports(home=None):
    source_dir = downloads_dir(home=home)
    mount = local_files_mount(home=home)
    target_dir = claude_cloud_archive_dir(home=home)
    if not source_dir.is_dir():
        return {"moved": 0, "files": [], "note": "Downloads directory absent"}
    if not mount.is_dir():
        return {"moved": 0, "files": [], "note": "AI session archive mount absent"}
    target_dir.mkdir(parents=True, exist_ok=True)
    moves = claude_export_pickup_moves(downloads_path=source_dir, target_dir=target_dir)
    moved = []
    for move in moves:
        shutil.move(move["source"], move["target"])
        moved.append(Path(move["target"]).name)
    print("holodeck ai-sync downloads moved:", len(moved), flush=True)
    return {"moved": len(moved), "files": moved}
def safe_text(value):
    text = " ".join(str(value or "").split())
    if len(text) > 500:
        text = text[:497].rstrip() + "..."
    return text
def sanitize_secret_text(text):
    value = str(text or "")
    value = re.sub(r"(AWS_(?:ACCESS_KEY_ID|SECRET_ACCESS_KEY|SESSION_TOKEN)\s*=\s*)\S+", r"\1[redacted]", value)
    value = re.sub(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b", "[redacted-aws-access-key]", value)
    return value
def command_tail(command):
    text = ((command.stdout or "") + "\n" + (command.stderr or "")).strip()
    return sanitize_secret_text(text[-AI_SYNC_TAIL_LIMIT:])
def run_s3_archive_command(args):
    command = [sys.executable, str(ROOT / "core/s3_archive.py")] + list(args)
    try:
        result = subprocess.run(
            command,
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=AI_SYNC_S3_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "returncode": None, "tail": sanitize_secret_text(str(exc)), "error": "s3_archive timed out"}
    except Exception as exc:
        return {"ok": False, "returncode": None, "tail": "", "error": safe_text(exc)}
    payload = {"ok": result.returncode == 0, "returncode": result.returncode, "tail": command_tail(result)}
    if result.returncode != 0:
        payload["error"] = "s3_archive exited " + str(result.returncode)
    return payload
def combine_s3_tails(build, upload):
    parts = []
    if build.get("tail"):
        parts.append("[build]\n" + build["tail"])
    if upload.get("tail"):
        parts.append("[upload]\n" + upload["tail"])
    return sanitize_secret_text("\n".join(parts)[-AI_SYNC_TAIL_LIMIT:])
def run_ai_sync_s3():
    build = run_s3_archive_command(["build", "--area", "ai_sessions"])
    if build.get("ok"):
        upload = run_s3_archive_command(["upload", "--area", "ai_sessions", "--execute"])
    else:
        upload = {"ok": False, "returncode": None, "tail": "", "error": "upload skipped because manifest build failed"}
    payload = {"ok": build.get("ok") is True and upload.get("ok") is True, "tail": combine_s3_tails(build, upload), "build": build, "upload": upload}
    if not payload["ok"]:
        payload["error"] = safe_text(upload.get("error") or build.get("error") or "S3 sync failed")
    return payload
def base_ai_sync_status(status="idle", message=None):
    return {
        "ok": None,
        "status": status,
        "running": status == "running",
        "message": message or status,
        "started_at": None,
        "finished_at": None,
        "downloads_moved": 0,
        "downloads": None,
        "turns": None,
        "s3": None,
    }
def copy_ai_sync_status(value):
    return json.loads(json.dumps(value))
def set_ai_sync_status(value):
    with AI_SYNC_STATUS_LOCK:
        AI_SYNC_LAST_RESULT.clear()
        AI_SYNC_LAST_RESULT.update(copy_ai_sync_status(value))
def get_ai_sync_status():
    with AI_SYNC_STATUS_LOCK:
        if not AI_SYNC_LAST_RESULT:
            return base_ai_sync_status()
        return copy_ai_sync_status(AI_SYNC_LAST_RESULT)
def update_ai_sync_status(patch):
    with AI_SYNC_STATUS_LOCK:
        current = copy_ai_sync_status(AI_SYNC_LAST_RESULT) if AI_SYNC_LAST_RESULT else base_ai_sync_status()
        current.update(copy_ai_sync_status(patch))
        AI_SYNC_LAST_RESULT.clear()
        AI_SYNC_LAST_RESULT.update(current)
        return copy_ai_sync_status(AI_SYNC_LAST_RESULT)
def ai_sync_worker(started_at):
    result = base_ai_sync_status("running", "syncing")
    result["started_at"] = started_at
    try:
        try:
            downloads = pickup_downloaded_claude_exports()
            result["downloads"] = downloads
            result["downloads_moved"] = int(downloads.get("moved") or 0)
        except Exception as exc:
            result["downloads"] = {"error": safe_text(exc)}
        update_ai_sync_status(result)
        try:
            turns_started = time.perf_counter()
            TURNS_REFRESH_LOCK.acquire()
            try:
                turns_summary = turns_ingest.build(root=ROOT, db_path=TURNS_DB_PATH)
            finally:
                TURNS_REFRESH_LOCK.release()
            turns_summary["ok"] = True
            turns_summary["took_s"] = round(time.perf_counter() - turns_started, 3)
            result["turns"] = turns_summary
        except Exception as exc:
            result["turns"] = {"ok": False, "error": safe_text(exc)}
        update_ai_sync_status(result)
        try:
            result["s3"] = run_ai_sync_s3()
        except Exception as exc:
            result["s3"] = {"ok": False, "tail": "", "error": safe_text(exc)}
        step_errors = []
        if isinstance(result.get("downloads"), dict) and result["downloads"].get("error"):
            step_errors.append("downloads")
        if isinstance(result.get("turns"), dict) and result["turns"].get("ok") is False:
            step_errors.append("turns")
        if isinstance(result.get("s3"), dict) and result["s3"].get("ok") is False:
            step_errors.append("s3")
        result["ok"] = not step_errors
        result["status"] = "complete" if result["ok"] else "error"
        result["running"] = False
        result["message"] = "completed" if result["ok"] else "completed with " + ", ".join(step_errors) + " error"
        result["finished_at"] = now_iso()
        set_ai_sync_status(result)
        print("holodeck ai-sync finished:", result["message"], "downloads_moved:", result["downloads_moved"], flush=True)
    finally:
        AI_SYNC_LOCK.release()
def start_ai_sync_background():
    if not AI_SYNC_LOCK.acquire(blocking=False):
        status = get_ai_sync_status()
        status["already_running"] = True
        status["message"] = "already running"
        return status
    started_at = now_iso()
    status = base_ai_sync_status("running", "started")
    status["started_at"] = started_at
    set_ai_sync_status(status)
    thread = threading.Thread(target=ai_sync_worker, args=(started_at,), daemon=True)
    thread.start()
    return get_ai_sync_status()

### macOS focus actions
class FocusRequestError(Exception):
    def __init__(self, code, message=None):
        self.code = code
        self.message = message or FOCUS_ERROR_MESSAGES.get(code, FOCUS_ERROR_MESSAGES["automation_failed"])
        super().__init__(self.message)
def focus_error_response(code, message=None):
    stable_code = code if code in FOCUS_ERROR_STATUS else "automation_failed"
    stable_message = message or FOCUS_ERROR_MESSAGES[stable_code]
    return JSONResponse(
        {"ok": False, "error": {"code": stable_code, "message": stable_message}},
        status_code=FOCUS_ERROR_STATUS[stable_code],
    )
def parse_loopback_host(value):
    if not isinstance(value, str) or not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        return None
    host = value
    port = None
    if value.startswith("["):
        closing = value.find("]")
        if closing < 0:
            return None
        host = value[1:closing]
        remainder = value[closing + 1:]
        if remainder:
            if not remainder.startswith(":") or not remainder[1:].isdigit():
                return None
            port = int(remainder[1:])
    elif ":" in value:
        if value.count(":") != 1:
            return None
        host, port_text = value.rsplit(":", 1)
        if not port_text.isdigit():
            return None
        port = int(port_text)
    if port is not None and not 1 <= port <= 65535:
        return None
    normalized_host = host.lower()
    if normalized_host == "localhost":
        return normalized_host, port
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return None
    if not address.is_loopback:
        return None
    return address.compressed, port
def request_peer_is_loopback(request):
    peer = request.client.host if request.client else None
    try:
        return ipaddress.ip_address(peer).is_loopback
    except (TypeError, ValueError):
        return False
def effective_port(scheme, port):
    if port is not None:
        return port
    return 443 if scheme == "https" else 80
def request_origin_is_allowed(request, request_host):
    origin = request.headers.get("origin")
    if not origin:
        return True
    try:
        parsed = urlsplit(origin)
        origin_port = parsed.port
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        return False
    origin_host = parse_loopback_host(parsed.netloc)
    if not origin_host:
        return False
    request_name, request_port = request_host
    origin_name, parsed_origin_port = origin_host
    return (
        parsed.scheme == request.url.scheme
        and origin_name == request_name
        and effective_port(parsed.scheme, origin_port if origin_port is not None else parsed_origin_port)
        == effective_port(request.url.scheme, request_port)
    )
def validate_focus_client(request):
    if not request_peer_is_loopback(request):
        raise FocusRequestError("forbidden_client")
    request_host = parse_loopback_host(request.headers.get("host"))
    if not request_host or not request_origin_is_allowed(request, request_host):
        raise FocusRequestError("forbidden_client")
    fetch_site = (request.headers.get("sec-fetch-site") or "").lower()
    if fetch_site and fetch_site not in {"same-origin", "none"}:
        raise FocusRequestError("forbidden_client")
    content_type = (request.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
    if content_type != "application/json" or request.headers.get("x-holodeck-action") != FOCUS_ACTION_HEADER:
        raise FocusRequestError("invalid_request")
def validate_focus_body(body):
    if not isinstance(body, dict) or set(body) != {"target", "matcher"}:
        raise FocusRequestError("invalid_request")
    if body.get("target") != "cursor":
        raise FocusRequestError("invalid_request")
    matcher = body.get("matcher")
    if not isinstance(matcher, dict) or set(matcher) != {"worktree_path"}:
        raise FocusRequestError("invalid_request")
    value = matcher.get("worktree_path")
    if not isinstance(value, str) or not value or len(value) > FOCUS_MATCHER_LIMIT:
        raise FocusRequestError("invalid_request")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise FocusRequestError("invalid_request")
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise FocusRequestError("invalid_request")
    return path.resolve(strict=False)
def load_live_worktree_entries(repo_root):
    command = worktrees_collector.run_git(repo_root, ["worktree", "list", "--porcelain"])
    if command.returncode != 0:
        raise FocusRequestError("automation_failed", "Live worktrees could not be verified.")
    return worktrees_collector.parse_worktree_porcelain(command.stdout)
def authorized_worktree_entry(requested_path, repo_root, entries=None):
    live_entries = load_live_worktree_entries(repo_root) if entries is None else entries
    for entry in live_entries:
        if entry.get("missing") or not entry.get("path"):
            continue
        live_path = Path(entry["path"]).expanduser().resolve(strict=False)
        if live_path == requested_path:
            return entry
    raise FocusRequestError("forbidden_client", "The requested path is not a live repo worktree.")
def cursor_title_candidates(entry, live_entries=None):
    path = entry.get("path")
    branch = entry.get("branch")
    folder_name = Path(path).name
    display_name = worktrees_collector.worktree_display_name(path, branch)
    # A .code-workspace stem is more authoritative than a commonly repeated
    # checkout basename such as "fof-mono". Supplying both can match two windows.
    value = display_name if display_name and display_name != folder_name else folder_name
    values = [value]
    if live_entries is not None:
        same_title_count = 0
        for live_entry in live_entries:
            live_path = live_entry.get("path")
            if live_entry.get("missing") or not live_path:
                continue
            live_folder = Path(live_path).name
            live_display = worktrees_collector.worktree_display_name(live_path, live_entry.get("branch"))
            live_value = live_display if live_display and live_display != live_folder else live_folder
            comparable_value = live_folder if value == folder_name else live_value
            if isinstance(comparable_value, str) and comparable_value.casefold() == value.casefold():
                same_title_count += 1
        # A repeated basename/title is not safe as a fallback. Path matching can
        # still focus the correct window, or fail closed when AXDocument is absent.
        if same_title_count != 1:
            values = []
    candidates = []
    for value in values:
        if not isinstance(value, str) or not value or value in candidates:
            continue
        if len(value) > 512 or any(ord(char) < 32 or ord(char) == 127 for char in value):
            continue
        candidates.append(value)
    return candidates
def cursor_document_roots(entry):
    path = Path(entry["path"]).expanduser().resolve(strict=False)
    roots = [path]
    workspace = worktrees_collector.find_codex_workspace_file(path, entry.get("branch"))
    if workspace:
        roots.extend(
            Path(root).expanduser().resolve(strict=False)
            for root in sorted(worktrees_collector.workspace_paths_from_config(workspace))
        )
    unique_roots = []
    seen = set()
    for root in roots:
        key = str(root).casefold()
        if key in seen:
            continue
        seen.add(key)
        unique_roots.append(root)
    return unique_roots
def invoke_cursor_focus(worktree_path, title_candidates, document_roots):
    # apps/mac is a namespace package (no __init__.py). Load by file path so the
    # server.py launch path (apps/holodeck on sys.path) cannot break apps.mac.
    import importlib.util
    module_path = ROOT / "apps/mac/window_activation.py"
    spec = importlib.util.spec_from_file_location("holodeck_window_activation", module_path)
    if spec is None or spec.loader is None:
        raise FocusRequestError("automation_failed", "Window activation module could not be loaded.")
    window_activation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(window_activation)
    return window_activation.focus_cursor_window(
        str(worktree_path),
        title_candidates=tuple(title_candidates),
        document_roots=tuple(str(root) for root in document_roots),
        timeout=15,
    )
def activation_error_code(exc):
    code = getattr(exc, "code", None)
    value = getattr(code, "value", code)
    return value if isinstance(value, str) and value in FOCUS_ERROR_STATUS else "automation_failed"
def activation_error_message(exc, code):
    message = getattr(exc, "message", None)
    if not isinstance(message, str) or not message or len(message) > 500:
        return FOCUS_ERROR_MESSAGES[code]
    if any(ord(char) < 32 and char not in "\t" for char in message):
        return FOCUS_ERROR_MESSAGES[code]
    return " ".join(message.split())
def focus_success_payload(result):
    if hasattr(result, "to_dict"):
        data = result.to_dict()
    elif isinstance(result, dict):
        data = result
    else:
        raise FocusRequestError("automation_failed")
    if not isinstance(data, dict) or data.get("ok") is not True:
        raise FocusRequestError("automation_failed")
    payload = {"ok": True, "target": "cursor", "status": "focused"}
    matched_by = data.get("matched_by")
    if isinstance(matched_by, str) and matched_by and len(matched_by) <= 64 and all(char.isalnum() or char in "_-" for char in matched_by):
        payload["matched_by"] = matched_by
    return payload
def execute_cursor_focus(requested_path):
    entries = load_live_worktree_entries(ROOT)
    entry = authorized_worktree_entry(requested_path, ROOT, entries)
    result = invoke_cursor_focus(
        requested_path,
        cursor_title_candidates(entry, entries),
        cursor_document_roots(entry),
    )
    return focus_success_payload(result)

### Cloud auth status
def cloud_status_source(key, state, detail):
    if state not in ("ok", "expired", "absent", "blocked"):
        state = "expired"
    text = " ".join(str(detail or "").split())
    if len(text) > 240:
        text = text[:237].rstrip() + "..."
    return {"key": key, "state": state, "detail": text}
def cached_cloud_status(key, loader, now=None, ttl=None):
    timestamp = time.time() if now is None else now
    max_age = CLOUD_STATUS_TTL if ttl is None else ttl
    with CLOUD_STATUS_LOCK:
        cached = CLOUD_STATUS_CACHE.get(key)
        if cached and timestamp - cached.get("ts", 0) < max_age:
            return dict(cached.get("source") or {})
    try:
        source = loader()
    except Exception:
        source = cloud_status_source(key, "expired", key + " status probe failed; check login and network.")
    with CLOUD_STATUS_LOCK:
        CLOUD_STATUS_CACHE[key] = {"ts": timestamp, "source": dict(source)}
    return dict(source)
def response_status(response):
    status = getattr(response, "status", None)
    if status is None and hasattr(response, "getcode"):
        status = response.getcode()
    try:
        return int(status)
    except (TypeError, ValueError):
        return None
def http_probe_status(url, headers, urlopen=None, method="GET"):
    opener = urlopen or urllib.request.urlopen
    request = urllib.request.Request(url, headers=headers, method=method)
    try:
        with opener(request, timeout=CLOUD_STATUS_TIMEOUT) as response:
            return response_status(response)
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:
        return None
def codex_access_token(home=None):
    auth_path = Path(home or Path.home()) / ".codex/auth.json"
    try:
        with auth_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    tokens = data.get("tokens") if isinstance(data, dict) else None
    token = tokens.get("access_token") if isinstance(tokens, dict) else None
    if not isinstance(token, str) or not token.strip():
        return None
    return token.strip()
def codex_cloud_status(urlopen=None, home=None):
    token = codex_access_token(home=home)
    if not token:
        return cloud_status_source("codex-cloud", "absent", "Codex cloud token not found; run codex login to enable cloud transcripts.")
    status = http_probe_status(
        CODEX_CLOUD_BASE_URL + CODEX_CLOUD_PROBE_PATH,
        {"Authorization": "Bearer " + token},
        urlopen=urlopen,
    )
    if status is not None and 200 <= status < 300:
        return cloud_status_source("codex-cloud", "ok", "Codex cloud token is valid.")
    if status in (401, 403):
        return cloud_status_source("codex-cloud", "expired", "Codex cloud token expired; run `codex cloud list` or `codex login` to refresh.")
    if status is None:
        return cloud_status_source("codex-cloud", "expired", "Codex cloud status probe failed (network). Token is present — retry, or run `codex cloud list` / `codex login`.")
    return cloud_status_source("codex-cloud", "expired", "Codex cloud status probe failed (HTTP {0}). Run `codex cloud list` or `codex login`.".format(status))
def unquote_env_value(value):
    text = str(value or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    return text.split(" #", 1)[0].strip()
def dotenv_value(path, name):
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, OSError):
        return None
    for line in lines:
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        if text.startswith("export "):
            text = text[len("export "):].strip()
        if "=" not in text:
            continue
        key, value = text.split("=", 1)
        if key.strip() == name:
            value = unquote_env_value(value)
            return value if value else None
    return None
def local_env_value(name, root=None, env=None):
    value = env.get(name) if env is not None else os.environ.get(name)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return dotenv_value(Path(root or ROOT) / ".env", name)
def claude_session_cookie(session_key):
    value = str(session_key or "").strip()
    if value.startswith("sessionKey="):
        return value.split("=", 1)[1]
    return value
def claude_export_paths(root=None):
    return [Path(path) for path in turns_cloud_claude.import_files(root=root)]
def latest_claude_export(root=None):
    paths = claude_export_paths(root=root)
    if not paths:
        return None
    return max(paths, key=lambda path: path.stat().st_mtime)
def claude_export_status_detail(path):
    stamp = datetime.fromtimestamp(Path(path).stat().st_mtime).astimezone().strftime("%Y-%m-%d %H:%M")
    return "Claude cloud export ready ({0} from {1}). Re-export from claude.ai when you want fresher cloud sessions.".format(Path(path).name, stamp)
def claude_cloud_browser_status():
    """Optional live Playwright probe. Export files are the primary Claude cloud path."""
    if not turns_cloud_claude.PLAYWRIGHT_PROFILE.exists():
        return None
    if not turns_cloud_claude.playwright_available():
        return None
    try:
        turns_cloud_claude.playwright_api_get("/v1/code/sessions", params=[("statuses", "active"), ("limit", "1")])
    except Exception:
        return None
    return cloud_status_source("claude-cloud", "ok", "Claude cloud browser session is valid.")
def claude_cloud_status(urlopen=None, root=None, env=None):
    # Holodeck ingests Claude cloud from browser exports (Cloudflare blocks server-side fetch).
    # Prefer export presence over live API probes so a normal Cloudflare 403 is not an alarm.
    latest = latest_claude_export(root=root)
    if latest is not None:
        return cloud_status_source("claude-cloud", "ok", claude_export_status_detail(latest))
    if urlopen is None:
        browser_status = claude_cloud_browser_status()
        if browser_status is not None:
            return browser_status
    session_key = local_env_value("CLAUDE_AI_SESSION_KEY", root=root, env=env)
    if session_key and urlopen is not None:
        status = http_probe_status(
            CLAUDE_CLOUD_BASE_URL + CLAUDE_CLOUD_PROBE_PATH + "?" + urllib.parse.urlencode({"limit": "1"}),
            {
                "anthropic-version": CLAUDE_CLOUD_API_VERSION,
                "Cookie": "sessionKey=" + claude_session_cookie(session_key),
            },
            urlopen=urlopen,
        )
        if status is not None and 200 <= status < 300:
            return cloud_status_source("claude-cloud", "ok", "Claude cloud session key is valid.")
        if status == 401:
            return cloud_status_source("claude-cloud", "expired", CLAUDE_EXPORT_GUIDANCE)
    return cloud_status_source("claude-cloud", "absent", CLAUDE_EXPORT_GUIDANCE)
def cloud_status_sources(urlopen=None, root=None, home=None, env=None, now=None):
    return [
        cached_cloud_status("codex-cloud", lambda: codex_cloud_status(urlopen=urlopen, home=home), now=now),
        cached_cloud_status("claude-cloud", lambda: claude_cloud_status(urlopen=urlopen, root=root, env=env), now=now, ttl=CLAUDE_CLOUD_STATUS_TTL),
    ]

### Routes
@app.get("/favicon.svg")
def favicon():
    path = WEB_DIR / "favicon.svg"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="favicon missing")
    return FileResponse(path, media_type="image/svg+xml")
@app.get("/")
def index():
    index_path = WEB_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return PlainTextResponse("Holodeck backend is running. The web UI is not present yet; use /api/snapshot.", status_code=200)
@app.get("/api/snapshot")
def snapshot():
    data = load_snapshot()
    if data is None:
        return JSONResponse({"error": "no snapshot \u2014 run collect.py or POST /api/refresh"}, status_code=404)
    return data
@app.get("/api/cloud-status")
def cloud_status_get():
    return {"sources": cloud_status_sources()}
@app.get("/api/ai-sync-status")
def ai_sync_status_get():
    return get_ai_sync_status()
@app.get("/api/branch-commits")
def branch_commits(branch, skip=0, limit=20):
    snapshot_data = load_snapshot()
    if snapshot_data is None:
        raise HTTPException(status_code=404, detail="snapshot missing")
    if branch not in snapshot_branch_names(snapshot_data):
        raise HTTPException(status_code=404, detail="branch not found")
    try:
        parsed_skip, parsed_limit = parse_branch_commit_paging(skip, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    ref = branches_collector.resolve_branch_ref(ROOT, branch)
    if not ref:
        raise HTTPException(status_code=404, detail="branch ref not found")
    try:
        commits = branches_collector.load_branch_commits(ROOT, ref, parsed_skip, parsed_limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    has_more = len(commits) > parsed_limit
    return {"branch": branch, "commits": commits[:parsed_limit], "has_more": has_more}
@app.get("/api/commit-hash-map/resolve/{sha}")
def commit_hash_map_resolve(sha, direction="to_new"):
    if direction not in ("to_new", "to_old", "either"):
        raise HTTPException(status_code=400, detail="direction must be to_new, to_old, or either")
    conn = open_turns_db()
    try:
        row = turns_hash_map.lookup_map_row(conn, sha)
        resolved = turns_hash_map.resolve_sha(conn, sha, direction=direction)
        if not row and resolved is None:
            raise HTTPException(status_code=404, detail="sha not found in commit hash map")
        payload = {
            "input": sha,
            "resolved": resolved,
            "mapped": bool(row),
            "old_sha": row.get("old_sha") if row else None,
            "new_sha": row.get("new_sha") if row else None,
            "status": row.get("status") if row else None,
            "subject": row.get("subject") if row else None,
            "branches": row.get("branches") if row else None,
        }
        return payload
    finally:
        conn.close()
@app.get("/api/turns")
def turns_list(branch=None, limit=20, session=None, include=None):
    try:
        parsed_limit = parse_turns_limit(limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    include_delegated = include == "delegated"
    conn = open_turns_db()
    try:
        exchanges = turns_db.list_turns(conn, branch=branch, session_id=session, limit=parsed_limit, include_delegated=include_delegated)
        return {"exchanges": exchanges}
    finally:
        conn.close()
@app.get("/api/turns/status")
def turns_status():
    conn = open_turns_db()
    try:
        return {"worktrees": turns_db.list_turn_status(conn)}
    finally:
        conn.close()
@app.get("/api/agents")
def agents_status(hours=48, limit=16):
    try:
        parsed_hours = parse_query_int(hours, 48, "hours")
        parsed_limit = parse_query_int(limit, 16, "limit")
        if parsed_hours < 1:
            raise ValueError("hours must be at least 1")
        if parsed_hours > 720:
            raise ValueError("hours must be at most 720")
        if parsed_limit < 1:
            raise ValueError("limit must be at least 1")
        if parsed_limit > 64:
            raise ValueError("limit must be at most 64")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    conn = open_turns_db()
    try:
        return {"generated_at": now_iso(), "agents": turns_db.list_agent_status(conn, hours=parsed_hours, limit=parsed_limit)}
    finally:
        conn.close()
@app.get("/api/turns/subagents")
def turns_subagents(session=None):
    session_id = validate_turn_session_id(session)
    conn = open_turns_db()
    try:
        return {"subagents": turns_db.list_subagents(conn, session_id, limit=20)}
    finally:
        conn.close()
@app.get("/api/turns/exchange/{exchange_id:path}")
def turns_exchange(exchange_id):
    validate_turn_exchange_id(exchange_id)
    conn = open_turns_db()
    try:
        exchange = turns_db.get_exchange(conn, exchange_id)
        if not exchange:
            raise HTTPException(status_code=404, detail="exchange not found")
        return exchange
    finally:
        conn.close()
@app.post("/api/turns/refresh")
def turns_refresh():
    if not TURNS_REFRESH_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="turns refresh already running")
    started = time.perf_counter()
    try:
        summary = turns_ingest.build(root=ROOT, db_path=TURNS_DB_PATH)
        summary["ok"] = True
        summary["took_s"] = round(time.perf_counter() - started, 3)
        summary["auto_digest"] = start_turns_auto_digest()
        return summary
    finally:
        TURNS_REFRESH_LOCK.release()
@app.post("/api/turns/digest/{exchange_id:path}")
def turns_digest_post(exchange_id):
    validate_turn_exchange_id(exchange_id)
    if not digest_running_add(exchange_id):
        raise HTTPException(status_code=409, detail="digest already running")
    conn = open_turns_db()
    try:
        if not turns_db.exchange_exists(conn, exchange_id):
            raise HTTPException(status_code=404, detail="exchange not found")
        try:
            digest = turns_digest.digest_exchange(conn, exchange_id, root=ROOT)
        except turns_digest.DigestConfigError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except turns_digest.DigestParseError as exc:
            raise HTTPException(status_code=502, detail=str(exc))
        except turns_digest.DigestProviderError as exc:
            raise HTTPException(status_code=502, detail=str(exc))
        return {"ok": True, "exchange_id": exchange_id, "digest": {"title": digest["title"], "asked": digest["asked"], "notes": digest["notes"], "recap": digest["recap"]}}
    finally:
        conn.close()
        digest_running_remove(exchange_id)
@app.get("/api/refresh/status")
def refresh_status():
    return {"running": REFRESH_LOCK.locked()}
@app.post("/api/refresh")
def refresh(body=Body(default=None)):
    if not REFRESH_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="refresh already running")
    started = time.perf_counter()
    try:
        layers = []
        if isinstance(body, dict):
            layers = body.get("layers") or []
        for layer in layers:
            if layer not in LAYER_NAMES:
                raise HTTPException(status_code=400, detail="unknown layer: " + str(layer))
        result = run_collect_subprocess(layers)
        stdout_tail = result.stdout[-4000:]
        ai_sync = start_ai_sync_background()
        return {"ok": result.returncode == 0, "took_s": round(time.perf_counter() - started, 3), "stdout_tail": stdout_tail, "ai_sync": ai_sync}
    finally:
        REFRESH_LOCK.release()
@app.post("/api/focus")
async def focus(request: Request):
    try:
        validate_focus_client(request)
        try:
            body = await request.json()
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            raise FocusRequestError("invalid_request")
        requested_path = validate_focus_body(body)
    except FocusRequestError as exc:
        return focus_error_response(exc.code, exc.message)
    if not FOCUS_LOCK.acquire(blocking=False):
        return focus_error_response("focus_busy")
    try:
        try:
            return await run_in_threadpool(execute_cursor_focus, requested_path)
        except FocusRequestError as exc:
            return focus_error_response(exc.code, exc.message)
        except Exception as exc:
            code = activation_error_code(exc)
            return focus_error_response(code, activation_error_message(exc, code))
    finally:
        FOCUS_LOCK.release()
@app.get("/api/state")
def state_get():
    return load_state_doc()
@app.put("/api/state/worktree/{branch:path}")
def state_worktree_put(branch, body=Body(default=None)):
    try:
        with STATE_LOCK:
            state, entry = state_store.merge_worktree_state(load_state_doc(), branch, body or {})
            save_state_doc(state)
        return entry
    except ValueError as exc:
        state_error(400, exc)
@app.put("/api/state/worktree-order")
def state_worktree_order_put(body=Body(default=None)):
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="body must be an object")
    try:
        with STATE_LOCK:
            state, worktrees = state_store.assign_worktree_order(load_state_doc(), body.get("order"))
            save_state_doc(state)
        return worktrees
    except ValueError as exc:
        state_error(400, exc)
@app.post("/api/next-steps")
def next_steps_post(body=Body(default=None)):
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="body must be an object")
    try:
        with STATE_LOCK:
            state, item = state_store.create_next_step(load_state_doc(), body.get("text"), source=body.get("source"))
            save_state_doc(state)
        return item
    except ValueError as exc:
        state_error(400, exc)
@app.put("/api/next-steps/{step_id}")
def next_steps_put(step_id, body=Body(default=None)):
    try:
        with STATE_LOCK:
            state, item = state_store.update_next_step(load_state_doc(), step_id, body or {})
            save_state_doc(state)
        return item
    except KeyError:
        raise HTTPException(status_code=404, detail="next step not found")
    except ValueError as exc:
        state_error(400, exc)
@app.put("/api/next-steps-order")
def next_steps_order_put(body=Body(default=None)):
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="body must be an object")
    try:
        with STATE_LOCK:
            state, items = state_store.assign_next_steps_order(load_state_doc(), body.get("order"))
            save_state_doc(state)
        return items
    except ValueError as exc:
        state_error(400, exc)
@app.post("/api/next-steps/{step_id}/archive")
def next_steps_archive_post(step_id):
    try:
        with STATE_LOCK:
            state, item = state_store.delete_next_step(load_state_doc(), step_id)
            append_todo_archive(TODO_ARCHIVE_PATH, item)
            save_state_doc(state)
        return {"ok": True}
    except KeyError:
        raise HTTPException(status_code=404, detail="next step not found")
@app.get("/api/next-steps-archive")
def next_steps_archive_get():
    return {"items": load_todo_archive(TODO_ARCHIVE_PATH)}
@app.delete("/api/next-steps/{step_id}")
def next_steps_delete(step_id):
    try:
        with STATE_LOCK:
            state, item = state_store.delete_next_step(load_state_doc(), step_id)
            save_state_doc(state)
        return {"ok": True}
    except KeyError:
        raise HTTPException(status_code=404, detail="next step not found")
@app.get("/api/file")
def file_get(path):
    snapshot_data = load_snapshot() or {}
    try:
        file_path = validate_file_read_path(path, ROOT, snapshot_data)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="file not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    content, truncated = read_limited_text(file_path)
    return {"path": str(file_path), "content": content, "truncated": truncated}
@app.put("/api/file")
def file_put(body=Body(default=None)):
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="body must be an object")
    if not isinstance(body.get("content"), str):
        raise HTTPException(status_code=400, detail="content must be a string")
    snapshot_data = load_snapshot() or {}
    try:
        file_path = validate_file_write_path(body.get("path"), ROOT, snapshot_data)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="parent directory not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    atomic_write_text(file_path, body["content"])
    return {"ok": True, "path": str(file_path)}
@app.get("/api/sessions/{platform}/{session_id}")
def session_detail(platform, session_id):
    snapshot_data = load_snapshot()
    if snapshot_data is None:
        raise HTTPException(status_code=404, detail="snapshot missing")
    platform = route_platform(platform)
    session = find_session(snapshot_data, platform, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    if session.get("host") == "cloud":
        return {"messages": []}
    source_path = session.get("source_path")
    if platform == "claude":
        base = Path.home() / ".claude/projects"
        if not source_path or not path_under(source_path, base):
            raise HTTPException(status_code=400, detail="invalid claude-code source path")
        return {"messages": sessions_collector.read_claude_messages(source_path)}
    if platform == "codex":
        base = Path.home() / ".codex/sessions"
        if not source_path or not path_under(source_path, base):
            raise HTTPException(status_code=400, detail="invalid codex source path")
        return {"messages": sessions_collector.read_codex_messages(source_path)}
    if platform == "cursor":
        if not source_path or source_path != session_id or "/" in source_path or "\\" in source_path:
            raise HTTPException(status_code=400, detail="invalid cursor source id")
        return {"messages": sessions_collector.read_cursor_messages(session_id)}
    raise HTTPException(status_code=404, detail="unknown platform")
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")

### Server launcher
def port_is_open(host, port):
    """Return True when something accepts TCP connections on host:port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0
def listeners_on_port(port):
    """Return PIDs listening on a TCP port, or [] when lsof is unavailable."""
    result = subprocess.run(
        ["lsof", "-ti", "tcp:{0}".format(port), "-sTCP:LISTEN"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    pids = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.isdigit():
            pids.append(int(line))
    return pids
def process_command(pid):
    """Return the command line for pid, or an empty string when unavailable."""
    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "command="],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()
def is_holodeck_process(command):
    """Return True when command looks like a Holodeck server process."""
    if not command:
        return False
    return any(marker in command for marker in SERVER_PROCESS_MARKERS)
def kill_holodeck_listeners(port=HOLODECK_PORT):
    """Stop Holodeck server processes bound to port and any stray uvicorn matches."""
    killed = set()
    for pid in listeners_on_port(port):
        if pid == os.getpid():
            continue
        command = process_command(pid)
        if is_holodeck_process(command):
            os.kill(pid, signal.SIGTERM)
            killed.add(pid)
    subprocess.run(["pkill", "-f", "uvicorn apps.holodeck"], check=False)
    return killed
def wait_for_port_free(host, port, timeout=5.0):
    """Wait until host:port stops accepting connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not port_is_open(host, port):
            return True
        time.sleep(0.2)
    return not port_is_open(host, port)
def confirm_restart():
    """Ask whether to stop an existing Holodeck server and start a new one."""
    try:
        answer = input(
            "Holodeck is already running on {0}. Kill and restart? [y/N] ".format(HOLODECK_URL)
        ).strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")
def run_server():
    """Start Holodeck, optionally replacing an already-running local instance."""
    if port_is_open(HOLODECK_HOST, HOLODECK_PORT):
        if not confirm_restart():
            print("Leaving the running Holodeck server as-is.")
            return
        print("Stopping existing Holodeck server...")
        kill_holodeck_listeners()
        if not wait_for_port_free(HOLODECK_HOST, HOLODECK_PORT):
            print("Port {0} is still in use. Stop the other process and retry.".format(HOLODECK_PORT))
            sys.exit(1)
    uvicorn.run(app, host=HOLODECK_HOST, port=HOLODECK_PORT)
if __name__ == "__main__":
    run_server()
