"""Collect Claude Code cloud sessions for the Holodeck turns database."""

import itertools
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None

CURL_IMPERSONATE = "chrome"
PLAYWRIGHT_PROFILE = Path.home() / ".holodeck/playwright-claude"
PLAYWRIGHT_BROWSERS_PATH = Path.home() / "Library/Caches/ms-playwright"

try:
    from apps.holodeck.collectors import sessions as sessions_collector
    from apps.holodeck.turns import correlate
    from apps.holodeck.turns import db
    from apps.holodeck.turns import labels
except ImportError:
    from collectors import sessions as sessions_collector
    from turns import correlate
    from turns import db
    from turns import labels

BASE_URL = "https://claude.ai"
API_VERSION = "2023-06-01"
DEFAULT_STATUSES = ("active", "paused")
EVENT_PAGE_LIMIT = 500
EVENT_PAGE_CAP = 20
EVENT_COUNT_CAP = 10000
LOGIN_TIMEOUT_S = 600
LOGIN_POLL_S = 3
AUTH_LOGIN_NOTE = "run: turns_cli.py cloud-claude-login"
AUTH_EXPIRED_NOTE = "CLAUDE_AI_SESSION_KEY expired — refresh from claude.ai devtools"
AUTH_MISSING_NOTE = "CLAUDE_AI_SESSION_KEY missing; claude-cloud ingest skipped"
IMPORT_MISSING_NOTE = "claude-cloud import missing; download a browser export and run Refresh"
CLOUD_SESSION_PREFIX = "claude-cloud:"
FOF_REPO = "FocusOnFoundationsNonprofit/fof-mono"
FEATURE_BRANCH_PREFIXES = ("feature/", "fix/", "refactor/", "cleanup/", "import/", "export/")
logger = logging.getLogger(__name__)

### Return values
class CloudClaudeSessions(list):
    def __init__(self, values=None, note=None, messages_by_session=None):
        super().__init__(values or [])
        self.note = note
        self.messages_by_session = messages_by_session or {}
class CloudClaudeError(Exception):
    pass
class CloudClaudeAuthError(CloudClaudeError):
    pass
class CloudClaudeHttpError(CloudClaudeError):
    def __init__(self, status, body=""):
        super().__init__("claude cloud HTTP " + str(status) + (": " + str(body) if body else ""))
        self.status = status
        self.body = body

### Env and HTTP
def load_local_env(root=None):
    if load_dotenv is None:
        return
    root_path = Path(root or db.repo_root())
    load_dotenv(root_path / ".env", override=False)
def session_key_from_env(root=None, env=None):
    if env is not None:
        return env.get("CLAUDE_AI_SESSION_KEY")
    load_local_env(root)
    return os.environ.get("CLAUDE_AI_SESSION_KEY")
def cookie_value(session_key):
    value = str(session_key or "").strip()
    if value.startswith("sessionKey="):
        return value.split("=", 1)[1]
    return value
def request_headers(session_key):
    return {
        "anthropic-version": API_VERSION,
        "Cookie": "sessionKey=" + cookie_value(session_key),
    }
def api_url(path, params=None):
    query = urllib.parse.urlencode(params or [], doseq=True)
    return BASE_URL + path + ("?" + query if query else "")
def api_headers():
    return {"anthropic-version": API_VERSION}
def api_get_curl(session_key, path, params=None):
    url = api_url(path, params=params)
    response = curl_requests.get(
        url,
        headers=api_headers(),
        cookies={"sessionKey": cookie_value(session_key)},
        impersonate=CURL_IMPERSONATE,
        timeout=20,
    )
    status = response.status_code
    if status == 403:
        raise CloudClaudeHttpError(403, "Cloudflare challenge; browser transport required")
    if status == 401:
        raise CloudClaudeAuthError(AUTH_EXPIRED_NOTE)
    if status >= 400:
        raise CloudClaudeHttpError(status, response.text[:200])
    try:
        return response.json()
    except Exception as exc:
        raise CloudClaudeError("claude cloud returned invalid JSON: " + str(exc))
def api_get_urllib(session_key, path, params=None, urlopen=None):
    opener = urlopen or urllib.request.urlopen
    request = urllib.request.Request(api_url(path, params=params), headers=request_headers(session_key), method="GET")
    try:
        with opener(request, timeout=20) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise CloudClaudeAuthError(AUTH_EXPIRED_NOTE)
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        raise CloudClaudeHttpError(exc.code, body)
    except Exception as exc:
        raise CloudClaudeError(str(exc))
    try:
        return json.loads(payload or "{}")
    except json.JSONDecodeError as exc:
        raise CloudClaudeError("claude cloud returned invalid JSON: " + str(exc))
def playwright_available():
    try:
        import playwright.sync_api
    except ImportError:
        return False
    return True
def set_playwright_browsers_path():
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(PLAYWRIGHT_BROWSERS_PATH)
def import_sync_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise CloudClaudeError("playwright is not installed: " + str(exc))
    return sync_playwright
def playwright_status(response):
    try:
        return int(response.status)
    except (TypeError, ValueError):
        return None
def login_redirect_url(url):
    try:
        parsed = urllib.parse.urlparse(str(url or ""))
    except ValueError:
        return False
    return parsed.netloc.endswith("claude.ai") and parsed.path.startswith("/login")
def response_header(response, name):
    headers = getattr(response, "headers", None) or {}
    for key, value in headers.items():
        if str(key).lower() == name.lower():
            return value
    return None
def playwright_needs_login(response):
    return login_redirect_url(getattr(response, "url", None)) or login_redirect_url(response_header(response, "location"))
def playwright_response_text(response):
    try:
        return response.text()[:200]
    except Exception:
        return ""
def playwright_response_json(response):
    try:
        return response.json()
    except Exception as exc:
        raise CloudClaudeError("claude cloud returned invalid JSON: " + str(exc))
def playwright_page_get(page, path, params=None):
    response = page.request.get(api_url(path, params=params), headers=api_headers(), timeout=20000)
    status = playwright_status(response)
    if status == 401 or playwright_needs_login(response):
        raise CloudClaudeAuthError(AUTH_LOGIN_NOTE)
    if status is not None and status >= 400:
        raise CloudClaudeHttpError(status, playwright_response_text(response))
    return playwright_response_json(response)
@contextmanager
def playwright_session():
    set_playwright_browsers_path()
    sync_playwright = import_sync_playwright()
    playwright = None
    context = None
    try:
        try:
            playwright = sync_playwright().start()
            context = playwright.chromium.launch_persistent_context(str(PLAYWRIGHT_PROFILE), headless=True)
        except Exception as exc:
            raise CloudClaudeError("playwright launch failed: " + str(exc))
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=20000)
        except Exception as exc:
            raise CloudClaudeError("playwright navigation failed: " + str(exc))
        def get(path, params=None):
            return playwright_page_get(page, path, params=params)
        yield get
    finally:
        if context is not None:
            context.close()
        if playwright is not None:
            playwright.stop()
def playwright_api_get(path, params=None):
    with playwright_session() as get:
        return get(path, params=params)
def use_playwright_transport(urlopen=None):
    return urlopen is None and PLAYWRIGHT_PROFILE.exists() and playwright_available()
def api_get(session_key, path, params=None, urlopen=None, api_getter=None):
    if api_getter is not None:
        return api_getter(path, params=params)
    if urlopen is not None:
        return api_get_urllib(session_key, path, params=params, urlopen=urlopen)
    if use_playwright_transport():
        return playwright_api_get(path, params=params)
    if curl_requests is not None:
        return api_get_curl(session_key, path, params=params)
    return api_get_urllib(session_key, path, params=params)
def claude_login(headed=True):
    set_playwright_browsers_path()
    PLAYWRIGHT_PROFILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        sync_playwright = import_sync_playwright()
    except CloudClaudeError as exc:
        print(str(exc))
        return False
    playwright = None
    context = None
    try:
        playwright = sync_playwright().start()
        context = playwright.chromium.launch_persistent_context(str(PLAYWRIGHT_PROFILE), headless=not headed)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(BASE_URL + "/code", wait_until="domcontentloaded", timeout=20000)
        deadline = time.time() + LOGIN_TIMEOUT_S
        while time.time() < deadline:
            try:
                response = page.request.get(
                    api_url("/v1/code/sessions", params=[("statuses", "active"), ("limit", "1")]),
                    headers=api_headers(),
                    timeout=20000,
                )
                if playwright_status(response) == 200 and not playwright_needs_login(response):
                    print("Claude cloud login captured")
                    return True
            except Exception:
                pass
            time.sleep(LOGIN_POLL_S)
        print("login not detected; re-run cloud-claude-login")
        return False
    except Exception as exc:
        print("Claude cloud login failed: " + str(exc))
        return False
    finally:
        if context is not None:
            context.close()
        if playwright is not None:
            playwright.stop()

### API fetchers
def list_payload_sessions(payload):
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "sessions", "items"):
        values = payload.get(key)
        if isinstance(values, list):
            return [item for item in values if isinstance(item, dict)]
    return []
def status_subsets(statuses):
    values = [str(status) for status in statuses or [] if status]
    if not values:
        yield []
        return
    for size in range(len(values), 0, -1):
        for subset in itertools.combinations(values, size):
            yield list(subset)
def fetch_session_list(session_key=None, statuses=DEFAULT_STATUSES, urlopen=None, api_getter=None):
    last_error = None
    for subset in status_subsets(statuses):
        params = [("limit", "50")]
        for status in subset:
            params.append(("statuses", status))
        try:
            return list_payload_sessions(api_get(session_key, "/v1/code/sessions", params=params, urlopen=urlopen, api_getter=api_getter))
        except CloudClaudeHttpError as exc:
            if exc.status != 400:
                raise
            last_error = exc
    if last_error:
        raise last_error
    return []
def normalize_branch(value):
    text = str(value or "").strip()
    prefix = "refs/heads/"
    if text.startswith(prefix):
        return text[len(prefix):]
    return text or None
def unique_values(values):
    result = []
    for value in values or []:
        if value and value not in result:
            result.append(value)
    return result
def detail_config(payload):
    if not isinstance(payload, dict):
        return {}
    response_shape = payload.get("response_shape") or {}
    config = response_shape.get("config") if isinstance(response_shape, dict) else None
    return config if isinstance(config, dict) else {}
def branches_from_detail_config(config):
    branches = []
    for source in config.get("sources") or []:
        if isinstance(source, dict):
            branches.append(normalize_branch(source.get("revision")))
    for outcome in config.get("outcomes") or []:
        if not isinstance(outcome, dict):
            continue
        git_info = outcome.get("git_info") or {}
        for branch in git_info.get("branches") or []:
            branches.append(normalize_branch(branch))
    return unique_values(branches)
def repo_from_detail_config(config):
    for outcome in config.get("outcomes") or []:
        if not isinstance(outcome, dict):
            continue
        git_info = outcome.get("git_info") or {}
        if git_info.get("repo"):
            return git_info.get("repo")
    for source in config.get("sources") or []:
        if not isinstance(source, dict):
            continue
        url = source.get("url")
        if url and FOF_REPO in str(url):
            return FOF_REPO
    return config.get("repo")
def parse_session_detail(payload):
    config = detail_config(payload)
    return {
        "model": config.get("model"),
        "effort": config.get("effort_level") or config.get("effort"),
        "repo": repo_from_detail_config(config),
        "branches": branches_from_detail_config(config),
        "origin": config.get("origin"),
    }
def fetch_session_detail(session_key, sid, urlopen=None, api_getter=None):
    return parse_session_detail(api_get(session_key, "/v1/code/sessions/" + urllib.parse.quote(str(sid), safe=""), urlopen=urlopen, api_getter=api_getter))
def event_page_data(payload):
    if isinstance(payload, dict):
        data = payload.get("data") or []
        return [item for item in data if isinstance(item, dict)], payload.get("next_cursor")
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)], None
    return [], None
def fetch_session_events(session_key, sid, urlopen=None, api_getter=None):
    events = []
    cursor = None
    capped = False
    for page_index in range(EVENT_PAGE_CAP):
        params = [("limit", str(EVENT_PAGE_LIMIT)), ("sort_order", "asc")]
        if cursor:
            params.append(("cursor", cursor))
        payload = api_get(session_key, "/v1/code/sessions/" + urllib.parse.quote(str(sid), safe="") + "/events", params=params, urlopen=urlopen, api_getter=api_getter)
        data, cursor = event_page_data(payload)
        events.extend(data)
        if len(events) >= EVENT_COUNT_CAP:
            capped = True
            events = events[:EVENT_COUNT_CAP]
            break
        if not cursor:
            break
        if page_index == EVENT_PAGE_CAP - 1:
            capped = True
    if capped:
        logger.warning("claude cloud events capped for %s at %s pages / %s events", sid, EVENT_PAGE_CAP, len(events))
    return events

### Event parsing
def event_message_content(event):
    payload = event.get("payload") or {}
    message = payload.get("message") if isinstance(payload, dict) else None
    if isinstance(message, dict):
        return sessions_collector.content_to_text(message.get("content"))
    return sessions_collector.content_to_text(payload.get("content") if isinstance(payload, dict) else None)
def events_to_messages(events):
    messages = []
    for event in events or []:
        event_type = event.get("event_type")
        if event_type not in ("user", "assistant"):
            continue
        text = event_message_content(event)
        item = sessions_collector.detail_item(event_type, text, event.get("created_at"))
        if item:
            messages.append(item)
    return messages

### Session mapping
def cloud_session_id(sid):
    value = str(sid)
    while value.startswith(CLOUD_SESSION_PREFIX):
        value = value[len(CLOUD_SESSION_PREFIX):]
    return CLOUD_SESSION_PREFIX + value
def looks_feature_branch(branch):
    return str(branch or "").startswith(FEATURE_BRANCH_PREFIXES)
def choose_branch(branches):
    values = unique_values([normalize_branch(branch) for branch in branches or []])
    for branch in values:
        if looks_feature_branch(branch):
            return branch
    return values[0] if values else None
def repo_is_fof_mono(repo):
    text = str(repo or "")
    return text == FOF_REPO or text.endswith("/fof-mono") or text.endswith(":FocusOnFoundationsNonprofit/fof-mono.git")
def match_worktree_by_branch(branch, repo, worktrees=None):
    if not branch or not repo_is_fof_mono(repo):
        return None
    for worktree in worktrees or []:
        if worktree.get("branch") == branch:
            return worktree.get("path")
    return None
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
def timestamp_bounds(summary, events=None):
    values = []
    for key in ("created_at", "started_at", "updated_at"):
        if summary.get(key):
            values.append(summary.get(key))
    for event in events or []:
        if event.get("created_at"):
            values.append(event.get("created_at"))
    parsed = [(parse_time(value), value) for value in values]
    parsed = [item for item in parsed if item[0]]
    if not parsed:
        return summary.get("created_at") or summary.get("updated_at"), summary.get("updated_at") or summary.get("created_at")
    parsed.sort(key=lambda item: item[0])
    return parsed[0][0].isoformat(), parsed[-1][0].isoformat()
def to_session(summary, detail, sid, worktrees=None, events=None):
    detail = detail or {}
    summary = summary or {}
    branches = detail.get("branches") or []
    branch = choose_branch(branches)
    worktree = match_worktree_by_branch(branch, detail.get("repo") or summary.get("repo"), worktrees=worktrees)
    started, last_activity = timestamp_bounds(summary, events=events)
    pretty_model = labels.pretty_claude_model(detail.get("model"))
    interface = labels.session_interface({"platform": "claude", "entrypoint": "app", "host": "cloud"})
    label = interface
    if pretty_model:
        label += " - " + pretty_model
    return {
        "id": cloud_session_id(sid),
        "platform": "claude",
        "entrypoint": "app",
        "host": "cloud",
        "remote_control": False,
        "bridge_session_id": None,
        "source_path": None,
        "source_url": BASE_URL + "/code/" + str(sid),
        "project": None,
        "worktree": worktree,
        "branch": branch,
        "label": label,
        "model": pretty_model,
        "interface": interface,
        "origin": db.OPERATOR_ORIGIN,
        "title": summary.get("title"),
        "started": started,
        "last_activity": last_activity,
        "repo": detail.get("repo") or summary.get("repo"),
        "_branches": unique_values(branches),
    }
def add_session_previews(session, messages):
    user_texts = [message.get("text") for message in messages or [] if message.get("role") == "user"]
    first_user, last_user = sessions_collector.first_last_user_text(user_texts)
    session["messages"] = len(messages or [])
    session["first_user"] = first_user
    session["last_user"] = last_user
    return session
def auth_note(exc):
    return str(exc) or AUTH_EXPIRED_NOTE
def collect_sessions_from_api(worktrees=None, session_key=None, urlopen=None, statuses=DEFAULT_STATUSES, api_getter=None):
    try:
        summaries = fetch_session_list(session_key, statuses=statuses, urlopen=urlopen, api_getter=api_getter)
    except CloudClaudeAuthError as exc:
        return CloudClaudeSessions([], note=auth_note(exc))
    except Exception as exc:
        return CloudClaudeSessions([], note="claude-cloud ingest failed: " + str(exc))
    sessions = []
    messages_by_session = {}
    notes = []
    for summary in summaries:
        sid = summary.get("id")
        if not sid:
            continue
        try:
            detail = fetch_session_detail(session_key, sid, urlopen=urlopen, api_getter=api_getter)
            events = fetch_session_events(session_key, sid, urlopen=urlopen, api_getter=api_getter)
        except CloudClaudeAuthError as exc:
            return CloudClaudeSessions([], note=auth_note(exc))
        except Exception as exc:
            notes.append("claude-cloud session " + str(sid) + " failed: " + str(exc))
            continue
        messages = events_to_messages(events)
        session = to_session(summary, detail, sid, worktrees=worktrees, events=events)
        session = add_session_previews(session, messages)
        sessions.append(session)
        messages_by_session[session["id"]] = messages
    note = "; ".join(notes) if notes else None
    return CloudClaudeSessions(sessions_collector.sort_sessions(sessions), note=note, messages_by_session=messages_by_session)
def import_dir(root=None):
    if root is not None:
        return Path(root).expanduser().resolve(strict=False).parent / "_LOCAL_FILES/fof-mono/ai-sessions/cloud_claude"
    return Path.home() / "Documents/Code/_LOCAL_FILES/fof-mono/ai-sessions/cloud_claude"
def legacy_import_dir(root=None):
    return Path(root or db.repo_root()) / "apps/holodeck/data/cloud_claude_import"
def import_files(root=None):
    paths = []
    seen = set()
    for directory in (import_dir(root=root), legacy_import_dir(root=root)):
        if not directory.exists():
            continue
        for path in directory.glob("*.json"):
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            paths.append(key)
    return sorted(paths)
def collect_sessions_from_files(paths, worktrees=None):
    sessions = []
    messages_by_session = {}
    notes = []
    for path in paths:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            notes.append("claude-cloud import " + str(path) + " failed: " + str(exc))
            continue
        for item in payload.get("sessions") or []:
            summary = item.get("summary") or {}
            sid = summary.get("id") or summary.get("session_id")
            if not sid:
                continue
            events = item.get("events") or []
            messages = events_to_messages(events)
            session = to_session(summary, parse_session_detail(item.get("detail") or {}), sid, worktrees=worktrees, events=events)
            session = add_session_previews(session, messages)
            sessions.append(session)
            messages_by_session[session["id"]] = messages
    note = "; ".join(notes) if notes else None
    return CloudClaudeSessions(sessions_collector.sort_sessions(sessions), note=note, messages_by_session=messages_by_session)
def collect_sessions(worktrees=None, root=None, session_key=None, env=None, urlopen=None, statuses=DEFAULT_STATUSES, allow_live=False):
    key = session_key or session_key_from_env(root=root, env=env)
    if urlopen is None:
        files = import_files(root=root)
        if files:
            return collect_sessions_from_files(files, worktrees=worktrees)
        if not allow_live:
            return CloudClaudeSessions([], note=IMPORT_MISSING_NOTE)
    if urlopen is not None:
        if not key:
            return CloudClaudeSessions([], note=AUTH_MISSING_NOTE)
        return collect_sessions_from_api(worktrees=worktrees, session_key=key, urlopen=urlopen, statuses=statuses)
    if use_playwright_transport():
        try:
            with playwright_session() as get:
                return collect_sessions_from_api(worktrees=worktrees, statuses=statuses, api_getter=get)
        except CloudClaudeAuthError as exc:
            return CloudClaudeSessions([], note=auth_note(exc))
        except Exception as exc:
            return CloudClaudeSessions([], note="claude-cloud ingest failed: " + str(exc))
    if not key:
        return CloudClaudeSessions([], note=AUTH_MISSING_NOTE)
    return collect_sessions_from_api(worktrees=worktrees, session_key=key, statuses=statuses)

### Commit correlation
def cloud_session_refs(sessions=None):
    refs = {}
    for session in sessions or []:
        session_id = session.get("id")
        if not session_id:
            continue
        refs[session_id] = unique_values(session.get("_branches") or [session.get("branch")])
    return refs
def load_cloud_sessions(conn, sessions=None):
    refs = cloud_session_refs(sessions)
    rows = conn.execute("SELECT * FROM sessions WHERE platform = 'claude' AND host = 'cloud'").fetchall()
    items = []
    for row in rows:
        session = dict(row)
        session["_branches"] = refs.get(session["id"]) or unique_values([session.get("branch")])
        items.append(session)
    return items
def existing_link_keys(conn):
    return {(row["exchange_id"], row["sha"]) for row in conn.execute("SELECT exchange_id, sha FROM links").fetchall()}
def upsert_branch_link(conn, exchange_id, sha, linked, existing):
    key = (exchange_id, sha)
    if key in linked:
        return 0
    db.upsert_link(conn, {
        "exchange_id": exchange_id,
        "sha": sha,
        "method": "claude-cloud-branch",
        "confidence": 0.85,
    })
    linked.add(key)
    return 0 if key in existing else 1
def link_cloud_session_commits(conn, sessions=None):
    cloud_sessions = load_cloud_sessions(conn, sessions=sessions)
    exchanges_by_session = correlate.load_exchanges_by_session(conn)
    commits = correlate.load_commits(conn)
    existing = existing_link_keys(conn)
    linked = set()
    count = 0
    for session in cloud_sessions:
        branches = set(session.get("_branches") or [])
        if not branches:
            continue
        exchanges = exchanges_by_session.get(session["id"]) or []
        for commit in commits:
            branch = commit.get("branch")
            if branch not in branches:
                continue
            commit_time = correlate.parse_time(commit.get("committer_date"))
            if not commit_time:
                continue
            branch_session = dict(session)
            branch_session["branch"] = branch
            candidates = correlate.candidates_for_session(branch_session, exchanges, commit, commit_time)
            if not candidates:
                continue
            count += upsert_branch_link(conn, candidates[0]["exchange"]["id"], commit["sha"], linked, existing)
    return count
