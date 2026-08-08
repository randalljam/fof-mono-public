import json
import urllib.error
from contextlib import contextmanager
from datetime import datetime

from apps.holodeck.collectors.sessions import claude_messages_from_lines, load_claude_app_metadata, parse_claude_jsonl_lines, parse_codex_jsonl_lines, parse_cursor_composer_data
from apps.holodeck.turns import cloud_claude
from apps.holodeck.turns import cloud_codex
from apps.holodeck.turns import correlate
from apps.holodeck.turns import db
from apps.holodeck.turns import digest
from apps.holodeck.turns import hash_map
from apps.holodeck.turns import ingest
from apps.holodeck.turns import labels

### Fixtures
def repo_worktrees():
    return [{"path": "/repo/main", "branch": "feature/test"}]
def json_line(value):
    return json.dumps(value)
def init_tmp_db(tmp_path):
    conn = db.connect(tmp_path / "turns.db")
    db.init_db(conn)
    return conn
def make_session(session_id, worktree="/repo/main", branch="feature/test", origin="operator", last_activity="2026-07-16T10:20:00-07:00"):
    prefix = session_id.split(":", 1)[0]
    platform = {"claude-code": "claude", "claude-cloud": "claude", "codex": "codex", "codex-cloud": "codex", "cursor": "cursor"}.get(prefix, prefix)
    host = "cloud" if prefix in ("claude-cloud", "codex-cloud") else "local"
    entrypoint = "app" if host == "cloud" or platform == "cursor" else "cli"
    return {
        "id": session_id,
        "platform": platform,
        "entrypoint": entrypoint,
        "host": host,
        "remote_control": False,
        "bridge_session_id": None,
        "source_path": session_id,
        "project": worktree,
        "worktree": worktree,
        "branch": branch,
        "label": "Cursor",
        "model": None,
        "interface": "Cursor",
        "origin": origin,
        "title": None,
        "started": "2026-07-16T10:00:00-07:00",
        "last_activity": last_activity,
        "ingested_at": "now",
    }
def make_exchange(exchange_id, session_id, user_ts="2026-07-16T10:00:00-07:00", response_text="Done", response_end_ts="2026-07-16T10:20:00-07:00", kind="primary", origin="operator", user_text="Build the backend"):
    return {
        "id": exchange_id,
        "session_id": session_id,
        "idx": int(exchange_id.rsplit("#", 1)[1]),
        "kind": kind,
        "user_ts": user_ts,
        "user_text": user_text,
        "response_text": response_text,
        "response_end_ts": response_end_ts,
        "origin": origin,
        "follow_up_of": None,
    }

### Claude cloud
def test_claude_cloud_events_to_messages_reuses_claude_blocks():
    events = [
        {"event_type": "user", "created_at": "2026-07-18T10:00:00Z", "payload": {"message": {"content": "Build the cloud poller"}}},
        {"event_type": "assistant", "created_at": "2026-07-18T10:05:00Z", "payload": {"message": {"content": [{"type": "text", "text": "Implemented it"}, {"type": "tool_use", "name": "Bash"}]}}},
        {"event_type": "result", "created_at": "2026-07-18T10:06:00Z", "payload": {"duration_ms": 1000}},
        {"event_type": "system", "created_at": "2026-07-18T10:07:00Z", "payload": {"message": {"content": "ignored"}}},
        {"event_type": "tool_progress", "created_at": "2026-07-18T10:08:00Z", "payload": {"message": {"content": "ignored"}}},
    ]
    messages = cloud_claude.events_to_messages(events)
    assert messages == [
        {"role": "user", "text": "Build the cloud poller", "ts": "2026-07-18T10:00:00Z"},
        {"role": "assistant", "text": "Implemented it", "ts": "2026-07-18T10:05:00Z"},
    ]
def test_claude_cloud_events_paginates():
    class Response:
        def __init__(self, payload):
            self.payload = payload
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def read(self):
            return json.dumps(self.payload).encode("utf-8")
    calls = []
    pages = [
        {"data": [{"event_id": "one", "event_type": "user"}], "next_cursor": "next"},
        {"data": [{"event_id": "two", "event_type": "assistant"}], "next_cursor": None},
    ]
    def urlopen(request, timeout=20):
        calls.append(request.full_url)
        return Response(pages.pop(0))
    events = cloud_claude.fetch_session_events("key", "session_abc", urlopen=urlopen)
    assert [event["event_id"] for event in events] == ["one", "two"]
    assert "cursor=next" in calls[1]
def test_claude_cloud_list_retries_unknown_status():
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def read(self):
            return json.dumps({"data": [{"id": "session_ok"}]}).encode("utf-8")
    calls = []
    def urlopen(request, timeout=20):
        calls.append(request.full_url)
        if "bogus" in request.full_url:
            raise urllib.error.HTTPError(request.full_url, 400, "Bad Request", {}, None)
        return Response()
    sessions = cloud_claude.fetch_session_list("key", statuses=("bogus", "active"), urlopen=urlopen)
    assert [session["id"] for session in sessions] == ["session_ok"]
    assert len(calls) >= 2
def test_claude_cloud_transport_selection_keeps_injected_urlopen(monkeypatch, tmp_path):
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def read(self):
            return json.dumps({"data": [{"id": "session_urlopen"}]}).encode("utf-8")
    profile = tmp_path / "profile"
    calls = []
    def urlopen(request, timeout=20):
        calls.append(request.full_url)
        return Response()
    def fail_playwright(path, params=None):
        raise AssertionError("playwright should not run with injected urlopen")
    monkeypatch.setattr(cloud_claude, "PLAYWRIGHT_PROFILE", profile)
    monkeypatch.setattr(cloud_claude, "playwright_available", lambda: True)
    monkeypatch.setattr(cloud_claude, "playwright_api_get", fail_playwright)
    assert not cloud_claude.use_playwright_transport(urlopen=urlopen)
    assert not cloud_claude.use_playwright_transport()
    profile.mkdir()
    assert cloud_claude.use_playwright_transport()
    monkeypatch.setattr(cloud_claude, "playwright_available", lambda: False)
    assert not cloud_claude.use_playwright_transport()
    sessions = cloud_claude.fetch_session_list("key", statuses=("active",), urlopen=urlopen)
    assert [session["id"] for session in sessions] == ["session_urlopen"]
    assert calls and "/v1/code/sessions" in calls[0]
def test_claude_cloud_collect_uses_single_playwright_context(monkeypatch, tmp_path):
    profile = tmp_path / "profile"
    profile.mkdir()
    summary = {"id": "session_abc", "title": "Branch naming convention for Holodeck", "created_at": "2026-07-18T10:00:00Z", "updated_at": "2026-07-18T10:30:00Z"}
    detail = {
        "response_shape": {
            "config": {
                "model": "claude-opus-4-8",
                "sources": [{"revision": "refs/heads/feature/test", "url": "https://github.com/FocusOnFoundationsNonprofit/fof-mono"}],
                "outcomes": [{"git_info": {"repo": "FocusOnFoundationsNonprofit/fof-mono", "branches": ["refs/heads/feature/test"]}}],
            }
        }
    }
    events = [
        {"event_type": "user", "created_at": "2026-07-18T10:01:00Z", "payload": {"message": {"content": "Name the branch"}}},
        {"event_type": "assistant", "created_at": "2026-07-18T10:05:00Z", "payload": {"message": {"content": "Use feature/holodeck-commits"}}},
    ]
    calls = []
    @contextmanager
    def fake_playwright_session():
        calls.append("open")
        def get(path, params=None):
            calls.append((path, tuple(params or [])))
            if path == "/v1/code/sessions":
                return {"data": [summary]}
            if path == "/v1/code/sessions/session_abc":
                return detail
            if path == "/v1/code/sessions/session_abc/events":
                return {"data": events, "next_cursor": None}
            raise AssertionError(path)
        yield get
        calls.append("close")
    monkeypatch.setattr(cloud_claude, "PLAYWRIGHT_PROFILE", profile)
    monkeypatch.setattr(cloud_claude, "playwright_available", lambda: True)
    monkeypatch.setattr(cloud_claude, "playwright_session", fake_playwright_session)
    sessions = cloud_claude.collect_sessions(root=tmp_path, env={}, worktrees=repo_worktrees(), allow_live=True)
    assert len(sessions) == 1
    assert sessions[0]["id"] == "claude-cloud:session_abc"
    assert sessions[0]["branch"] == "feature/test"
    assert sessions.messages_by_session["claude-cloud:session_abc"] == [
        {"role": "user", "text": "Name the branch", "ts": "2026-07-18T10:01:00Z"},
        {"role": "assistant", "text": "Use feature/holodeck-commits", "ts": "2026-07-18T10:05:00Z"},
    ]
    assert calls[0] == "open"
    assert calls[-1] == "close"
    assert calls.count("open") == 1
def test_claude_cloud_to_session_prefers_feature_branch_and_matches_worktree():
    summary = {"id": "session_abc", "title": "Review branch commits", "created_at": "2026-07-18T10:00:00Z", "updated_at": "2026-07-18T10:30:00Z", "repo": "FocusOnFoundationsNonprofit/fof-mono"}
    detail = {"model": "claude-opus-4-8", "effort": "high", "repo": "FocusOnFoundationsNonprofit/fof-mono", "branches": ["claude/random-auto", "feature/test"], "origin": "desktop_app"}
    worktrees = [{"path": "/repo/main", "branch": "feature/test"}]
    session = cloud_claude.to_session(summary, detail, "session_abc", worktrees=worktrees)
    assert session["id"] == "claude-cloud:session_abc"
    assert session["platform"] == "claude"
    assert session["entrypoint"] == "app"
    assert session["host"] == "cloud"
    assert session["remote_control"] is False
    assert session["bridge_session_id"] is None
    assert session["label"] == "Claude App (Cloud) - Opus 4.8"
    assert session["interface"] == "Claude App (Cloud)"
    assert session["model"] == "Opus 4.8"
    assert session["origin"] == "operator"
    assert session["branch"] == "feature/test"
    assert session["worktree"] == "/repo/main"
    assert session["source_url"] == "https://claude.ai/code/session_abc"
def test_claude_cloud_auth_missing_and_401_skip(monkeypatch, tmp_path):
    monkeypatch.setattr(cloud_claude, "PLAYWRIGHT_PROFILE", tmp_path / "missing-profile")
    missing = cloud_claude.collect_sessions(root=tmp_path, env={})
    assert missing == []
    assert missing.note == cloud_claude.IMPORT_MISSING_NOTE
    def urlopen(request, timeout=20):
        raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, None)
    expired = cloud_claude.collect_sessions(session_key="expired", urlopen=urlopen)
    assert expired == []
    assert expired.note == cloud_claude.AUTH_EXPIRED_NOTE
def test_claude_cloud_playwright_auth_skip_note(monkeypatch, tmp_path):
    profile = tmp_path / "profile"
    profile.mkdir()
    @contextmanager
    def fake_playwright_session():
        raise cloud_claude.CloudClaudeAuthError(cloud_claude.AUTH_LOGIN_NOTE)
        yield
    monkeypatch.setattr(cloud_claude, "PLAYWRIGHT_PROFILE", profile)
    monkeypatch.setattr(cloud_claude, "playwright_available", lambda: True)
    monkeypatch.setattr(cloud_claude, "playwright_session", fake_playwright_session)
    sessions = cloud_claude.collect_sessions(root=tmp_path, env={})
    assert sessions == []
    assert sessions.note == cloud_claude.IMPORT_MISSING_NOTE
    sessions = cloud_claude.collect_sessions(root=tmp_path, env={}, allow_live=True)
    assert sessions == []
    assert sessions.note == cloud_claude.AUTH_LOGIN_NOTE
def test_claude_cloud_branch_correlation_links_branch_commits(tmp_path):
    conn = init_tmp_db(tmp_path)
    session = cloud_claude.to_session(
        {"id": "session_branch", "title": "Branch work", "created_at": "2026-07-18T10:00:00Z", "updated_at": "2026-07-18T10:30:00Z"},
        {"model": "claude-opus-4-8", "repo": "FocusOnFoundationsNonprofit/fof-mono", "branches": ["claude/auto", "feature/test"]},
        "session_branch",
        worktrees=[{"path": "/repo/main", "branch": "feature/test"}],
    )
    session["ingested_at"] = "now"
    db.upsert_session(conn, session)
    db.upsert_exchange(conn, {"id": "claude-cloud:session_branch#1", "session_id": "claude-cloud:session_branch", "idx": 1, "kind": "primary", "user_ts": "2026-07-18T10:00:00Z", "user_text": "Build", "response_text": "Done", "response_end_ts": "2026-07-18T10:20:00Z", "origin": "operator", "follow_up_of": None})
    db.upsert_commit(conn, {"sha": "aaa", "branch": "feature/test", "worktree": "/repo/other", "author": "Randy", "author_email": "randy@example.test", "author_date": "2026-07-18T10:25:00Z", "committer_date": "2026-07-18T10:25:00Z", "subject": "Cloud branch commit", "body": "", "is_agent_commit": 0})
    assert cloud_claude.link_cloud_session_commits(conn, sessions=[session]) == 1
    row = conn.execute("SELECT * FROM links").fetchone()
    assert row["exchange_id"] == "claude-cloud:session_branch#1"
    assert row["sha"] == "aaa"
    assert row["method"] == "claude-cloud-branch"
    assert row["confidence"] == 0.85

### Codex cloud
def test_codex_access_token_reads_fixture_auth_json(tmp_path):
    auth_dir = tmp_path / ".codex"
    auth_dir.mkdir()
    (auth_dir / "auth.json").write_text(json.dumps({"tokens": {"access_token": "token_abc", "refresh_token": "secret"}}), encoding="utf-8")
    assert cloud_codex.codex_access_token(root=tmp_path) == "token_abc"
    assert cloud_codex.codex_access_token(root=tmp_path / "missing") is None
def test_wham_turns_to_messages_extracts_nested_text_and_skips_empty():
    turn_mapping = {
        "assistant_empty": {
            "turn": {
                "role": "assistant",
                "created_at": "2026-07-18T10:02:00Z",
                "output_items": [{"content": [{"content_type": "text", "text": "   "}]}],
            }
        },
        "assistant": {
            "turn": {
                "role": "assistant",
                "created_at": "2026-07-18T10:01:00Z",
                "output_items": [
                    {
                        "kind": "message",
                        "content": [
                            {"content_type": "text", "text": "Implemented it"},
                            {"content_type": "image", "text": "ignored"},
                            {"nested": [{"content_type": "text", "text": "Nested detail"}]},
                        ],
                    }
                ],
            }
        },
        "user": {
            "turn": {
                "role": "user",
                "created_at": "2026-07-18T10:00:00Z",
                "input_items": [{"content": [{"content_type": "text", "text": "Build the backend"}]}],
            }
        },
    }
    assert cloud_codex.turns_to_messages(turn_mapping) == [
        {"role": "user", "text": "Build the backend", "ts": "2026-07-18T10:00:00Z"},
        {"role": "assistant", "text": "Implemented it\nNested detail", "ts": "2026-07-18T10:01:00Z"},
    ]
def test_codex_cloud_wham_collects_transcript_session_metadata():
    class Response:
        def __init__(self, payload):
            self.payload = payload
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def read(self):
            return json.dumps(self.payload).encode("utf-8")
    payloads = {
        "tasks/list": {
            "tasks": [
                {
                    "id": "task_wham",
                    "title": "Wham task",
                    "url": "https://chatgpt.com/codex/tasks/task_wham",
                    "created_at": "2026-07-18T10:00:00Z",
                }
            ],
            "cursor": None,
        },
        "task_wham/turns": {
            "turn_mapping": {
                "u": {"turn": {"role": "user", "created_at": "2026-07-18T10:00:00Z", "input_items": [{"content": [{"content_type": "text", "text": "Please build it"}]}]}},
                "a": {"turn": {"role": "assistant", "created_at": "2026-07-18T10:10:00Z", "model_version": "gpt-5.6-sol", "branch_name": "feature/test", "environment": {"name": "test-env"}, "direct_push_pushed_commit_sha": "abc123", "output_items": [{"content": [{"content_type": "text", "text": "Built it"}]}]}},
            }
        },
    }
    def urlopen(request, timeout=20):
        for key, payload in payloads.items():
            if key in request.full_url:
                return Response(payload)
        raise AssertionError(request.full_url)
    sessions = cloud_codex.collect_sessions(token="token", urlopen=urlopen, worktrees=repo_worktrees())
    assert len(sessions) == 1
    session = sessions[0]
    assert session["id"] == "codex-cloud:task_wham"
    assert session["label"] == "Codex App (Cloud) - GPT 5.6 Sol"
    assert session["model"] == "GPT 5.6 Sol"
    assert session["branch"] == "feature/test"
    assert session["worktree"] == "/repo/main"
    assert sessions.messages_by_session[session["id"]][0]["text"] == "Please build it"
    assert sessions.task_items[0]["_pushes"] == [{"sha": "abc123", "ts": "2026-07-18T10:10:00Z", "branch": "feature/test"}]
def test_codex_cloud_auth_401_skip_note():
    def urlopen(request, timeout=20):
        raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, None)
    sessions = cloud_codex.collect_sessions(token="expired", urlopen=urlopen)
    assert sessions == []
    assert sessions.note == cloud_codex.AUTH_EXPIRED_NOTE
def test_codex_cloud_collect_sessions_falls_back_to_cli_without_token(tmp_path):
    class Result:
        def __init__(self, returncode, stdout="", stderr=""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr
    calls = []
    def runner(args, timeout=20):
        calls.append(args)
        if args[:2] == ["cloud", "list"]:
            return Result(0, json.dumps({"tasks": [{"id": "task_cli", "title": "CLI task", "updated_at": "2026-07-18T10:00:00Z", "summary": {"files_changed": 1}}], "cursor": None}))
        if args[:2] == ["cloud", "diff"]:
            return Result(0, "diff body")
        return Result(1, "", "unexpected")
    sessions = cloud_codex.collect_sessions(root=tmp_path, runner=runner)
    assert [session["id"] for session in sessions] == ["codex-cloud:task_cli"]
    assert sessions.messages_by_session == {}
    assert sessions.exchanges_by_session["codex-cloud:task_cli"][0]["id"] == "codex-cloud:task_cli#0"
    assert "diff body" in sessions.exchanges_by_session["codex-cloud:task_cli"][0]["response_text"]
    assert calls == [
        ["cloud", "list", "--limit", "20", "--json"],
        ["cloud", "diff", "task_cli"],
    ]
def test_list_cloud_tasks_paginates_and_handles_empty_error():
    class Result:
        def __init__(self, returncode, stdout="", stderr=""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr
    calls = []
    pages = [
        {"tasks": [{"id": "task_one"}, {"id": "task_two"}], "cursor": "next"},
        {"tasks": [], "cursor": None},
    ]
    def runner(args, timeout=20):
        calls.append(args)
        return Result(0, json.dumps(pages.pop(0)))
    tasks = cloud_codex.list_cloud_tasks(limit=20, runner=runner)
    assert [task["id"] for task in tasks] == ["task_one", "task_two"]
    assert tasks.note is None
    assert calls == [
        ["cloud", "list", "--limit", "20", "--json"],
        ["cloud", "list", "--limit", "20", "--json", "--cursor", "next"],
    ]
    empty = cloud_codex.list_cloud_tasks(runner=lambda args, timeout=20: Result(0, json.dumps({"tasks": [], "cursor": None})))
    failed = cloud_codex.list_cloud_tasks(runner=lambda args, timeout=20: Result(1, "", "not logged in"))
    assert empty == []
    assert failed == []
    assert "not logged in" in failed.note
def test_cloud_task_maps_to_operator_session_exchange_and_caps_diff():
    task = {
        "id": "task_abc",
        "url": "https://codex.openai.com/tasks/task_abc",
        "title": "Set up virtual machine in Codex app",
        "status": "completed",
        "updated_at": "2026-07-17T10:00:00Z",
        "environment_label": "learnbox",
        "summary": {"files_changed": 2, "lines_added": 30, "lines_removed": 4},
    }
    worktrees = [{"path": "/repo/feature-learnbox", "branch": "feature/learnbox", "apps_touched": ["learnbox"]}]
    session, exchange = cloud_codex.to_session_and_exchange(task, "D" * (cloud_codex.DIFF_LIMIT + 50), worktrees=worktrees)
    assert session["id"] == "codex-cloud:task_abc"
    assert session["platform"] == "codex"
    assert session["entrypoint"] == "app"
    assert session["host"] == "cloud"
    assert session["remote_control"] is False
    assert session["bridge_session_id"] is None
    assert session["label"] == "Codex App (Cloud)"
    assert session["interface"] == "Codex App (Cloud)"
    assert session["origin"] == "operator"
    assert session["worktree"] == "/repo/feature-learnbox"
    assert session["branch"] == "feature/learnbox"
    assert session["source_url"] == "https://codex.openai.com/tasks/task_abc"
    assert exchange["id"] == "codex-cloud:task_abc#0"
    assert exchange["idx"] == 0
    assert exchange["kind"] == "primary"
    assert exchange["user_text"] == "Set up virtual machine in Codex app"
    assert exchange["origin"] == "operator"
    assert exchange["response_text"].split("\n\n", 1)[1] == "D" * cloud_codex.DIFF_LIMIT
def test_cloud_task_commit_correlation_url_window_and_unmatched(tmp_path):
    conn = init_tmp_db(tmp_path)
    worktrees = [
        {"path": "/repo/url", "branch": "feature/url", "name": "url-env"},
        {"path": "/repo/window", "branch": "feature/window", "name": "window-env"},
        {"path": "/repo/unmatched", "branch": "feature/unmatched", "name": "unmatched-env"},
    ]
    tasks = [
        {"id": "task_url", "url": "https://codex.openai.com/tasks/task_url", "title": "URL task", "status": "completed", "updated_at": "2026-07-17T10:00:00Z", "environment_label": "url-env", "summary": {"files_changed": 1, "lines_added": 1, "lines_removed": 0}},
        {"id": "task_window", "url": "https://codex.openai.com/tasks/task_window", "title": "Window task", "status": "completed", "updated_at": "2026-07-17T11:00:00Z", "environment_label": "window-env", "summary": {"files_changed": 2, "lines_added": 4, "lines_removed": 1}},
        {"id": "task_unmatched", "url": "https://codex.openai.com/tasks/task_unmatched", "title": "Unmatched task", "status": "completed", "updated_at": "2026-07-17T12:00:00Z", "environment_label": "unmatched-env", "summary": {"files_changed": 0, "lines_added": 0, "lines_removed": 0}},
    ]
    for task in tasks:
        session, exchange = cloud_codex.to_session_and_exchange(task, "", worktrees=worktrees)
        session["ingested_at"] = "now"
        db.upsert_session(conn, session)
        db.upsert_exchange(conn, exchange)
    for commit in [
        {"sha": "aaa", "branch": "feature/other", "worktree": "/repo/other", "author": "Randy", "author_email": "randy@example.test", "author_date": "2026-07-17T09:00:00Z", "committer_date": "2026-07-17T09:00:00Z", "subject": "Land task_url", "body": "https://codex.openai.com/tasks/task_url", "is_agent_commit": 0},
        {"sha": "bbb", "branch": "feature/window", "worktree": "/repo/window", "author": "Randy", "author_email": "randy@example.test", "author_date": "2026-07-17T13:00:00Z", "committer_date": "2026-07-17T13:00:00Z", "subject": "Window fallback", "body": "", "is_agent_commit": 0},
        {"sha": "ccc", "branch": "feature/unmatched", "worktree": "/repo/unmatched", "author": "Randy", "author_email": "randy@example.test", "author_date": "2026-07-17T12:30:00Z", "committer_date": "2026-07-17T12:30:00Z", "subject": "Should not link", "body": "", "is_agent_commit": 0},
    ]:
        db.upsert_commit(conn, commit)
    assert cloud_codex.link_cloud_task_commits(conn, tasks=tasks) == 2
    rows = conn.execute("SELECT * FROM links ORDER BY sha").fetchall()
    assert [(row["sha"], row["exchange_id"], row["method"], row["confidence"]) for row in rows] == [
        ("aaa", "codex-cloud:task_url#0", "codex-cloud-url", 0.95),
        ("bbb", "codex-cloud:task_window#0", "codex-cloud-window", 0.5),
    ]
def test_cloud_task_exact_push_sha_correlation_wins_over_window(tmp_path):
    conn = init_tmp_db(tmp_path)
    session = {
        "id": "codex-cloud:task_push",
        "platform": "codex",
        "entrypoint": "app",
        "host": "cloud",
        "remote_control": False,
        "bridge_session_id": None,
        "source_path": None,
        "source_url": "https://chatgpt.com/codex/tasks/task_push",
        "project": None,
        "worktree": "/repo/main",
        "branch": "feature/test",
        "label": "Codex App (Cloud)",
        "model": "gpt-5.6-sol",
        "interface": "Codex App (Cloud)",
        "origin": "operator",
        "title": "Push task",
        "started": "2026-07-18T10:00:00Z",
        "last_activity": "2026-07-18T10:20:00Z",
        "ingested_at": "now",
    }
    db.upsert_session(conn, session)
    db.upsert_exchange(conn, {"id": "codex-cloud:task_push#1", "session_id": "codex-cloud:task_push", "idx": 1, "kind": "primary", "user_ts": "2026-07-18T10:00:00Z", "user_text": "Build", "response_text": "Done", "response_end_ts": "2026-07-18T10:20:00Z", "origin": "operator", "follow_up_of": None})
    db.upsert_commit(conn, {"sha": "pushsha", "branch": "feature/test", "worktree": "/repo/main", "author": "Randy", "author_email": "randy@example.test", "author_date": "2026-07-18T10:25:00Z", "committer_date": "2026-07-18T10:25:00Z", "subject": "Direct push", "body": "", "is_agent_commit": 0})
    task = {"id": "task_push", "url": "https://chatgpt.com/codex/tasks/task_push", "updated_at": "2026-07-18T10:20:00Z", "_session_id": "codex-cloud:task_push", "_transcript": True, "_branches": ["feature/test"], "_pushes": [{"sha": "pushsha", "ts": "2026-07-18T10:20:00Z", "branch": "feature/test"}]}
    assert cloud_codex.link_cloud_task_commits(conn, tasks=[task]) == 1
    rows = conn.execute("SELECT * FROM links").fetchall()
    assert [(row["exchange_id"], row["sha"], row["method"], row["confidence"]) for row in rows] == [
        ("codex-cloud:task_push#1", "pushsha", "codex-cloud-push", 0.97),
    ]

### Labels
def test_legacy_session_mapping_to_platform_entrypoint_host():
    cases = [
        ({"tool": "claude-code", "entrypoint": "cli"}, ("claude", "cli", "local")),
        ({"tool": "claude-code", "entrypoint": "claude-desktop"}, ("claude", "app", "local")),
        ({"tool": "claude-cloud"}, ("claude", "app", "cloud")),
        ({"tool": "cursor", "entrypoint": "cursor"}, ("cursor", "app", "local")),
        ({"tool": "codex", "entrypoint": "codex-cli"}, ("codex", "cli", "local")),
        ({"tool": "codex", "entrypoint": "codex-desktop"}, ("codex", "app", "local")),
        ({"tool": "codex", "entrypoint": "codex-subagent"}, ("codex", "subagent", "local")),
        ({"tool": "codex-cloud"}, ("codex", "app", "cloud")),
    ]
    for session, expected in cases:
        labels.normalize_session_schema(session)
        assert (session["platform"], session["entrypoint"], session["host"]) == expected
        assert "tool" not in session
def test_label_format_examples():
    examples = [
        ({"platform": "claude", "entrypoint": "cli", "host": "local", "raw_model": "claude-fable-5"}, "Claude CLI - Fable 5", "Claude CLI"),
        ({"platform": "codex", "entrypoint": "app", "host": "local", "raw_model": "gpt-5.6-sol", "effort": "xhigh"}, "Codex App - GPT 5.6 Sol xhigh", "Codex App"),
        ({"platform": "claude", "entrypoint": "app", "host": "cloud", "raw_model": "claude-opus-4-8"}, "Claude App (Cloud) - Opus 4.8", "Claude App (Cloud)"),
        ({"platform": "claude", "entrypoint": "cli", "host": "local", "remote_control": True, "raw_model": "claude-fable-5"}, "Claude CLI (Remote Control) - Fable 5", "Claude CLI (Remote Control)"),
    ]
    for session, expected_label, expected_interface in examples:
        labels.apply_session_label(session)
        assert session["label"] == expected_label
        assert session["interface"] == expected_interface
def test_cursor_label_derivation_fast_and_plan_mode():
    fast = parse_cursor_composer_data({
        "composerId": "composer-fast",
        "workspaceIdentifier": {"uri": {"path": "/repo/main"}},
        "modelConfig": {"modelName": "composer-2.5"},
        "selectedModels": [{"parameters": [{"id": "fast", "value": "true"}]}],
        "unifiedMode": "agent",
    }, worktrees=repo_worktrees())
    plan = parse_cursor_composer_data({
        "composerId": "composer-plan",
        "workspaceIdentifier": {"uri": {"path": "/repo/main"}},
        "modelConfig": {"modelName": "opus-4.8-1m-high"},
        "selectedModels": [],
        "unifiedMode": "plan",
        "planModeSuggestionUsed": False,
    }, worktrees=repo_worktrees())
    assert fast["label"] == "Cursor IDE - Composer 2.5 Fast"
    assert fast["model"] == "Composer 2.5 Fast"
    assert fast["interface"] == "Cursor IDE"
    assert fast["origin"] == "operator"
    assert plan["label"] == "Cursor IDE - Opus 4.8 1M High (.plan.md)"
def test_claude_code_label_derivation_fable_model():
    lines = [
        json_line({"type": "user", "cwd": "/repo/main", "gitBranch": "feature/test", "timestamp": "2026-07-16T10:00:00-07:00", "entrypoint": "cli", "message": {"content": "Build it"}}),
        json_line({"type": "assistant", "cwd": "/repo/main", "gitBranch": "feature/test", "timestamp": "2026-07-16T10:05:00-07:00", "message": {"model": "claude-fable-5", "content": "Done"}}),
    ]
    session = parse_claude_jsonl_lines(lines, source_path="/tmp/claude-session.jsonl", worktrees=repo_worktrees())
    assert session["raw_model"] == "claude-fable-5"
    assert session["label"] == "Claude CLI - Fable 5"
    assert session["model"] == "Fable 5"
    assert session["origin"] == "operator"
def test_claude_jsonl_bridge_session_marks_remote_control():
    lines = [
        json_line({"type": "bridge-session", "bridgeSessionId": "cse_01VnehJRZZYAXCLBNvufCG7p"}),
        json_line({"type": "user", "cwd": "/repo/main", "gitBranch": "feature/test", "timestamp": "2026-07-16T10:00:00-07:00", "entrypoint": "cli", "message": {"content": "Build it"}}),
        json_line({"type": "assistant", "timestamp": "2026-07-16T10:01:00-07:00", "message": {"model": "claude-fable-5", "content": "Done"}}),
    ]
    session = parse_claude_jsonl_lines(lines, source_path="/tmp/7224a4fe.jsonl", worktrees=repo_worktrees())
    assert session["host"] == "local"
    assert session["remote_control"] is True
    assert session["bridge_session_id"] == "cse_01VnehJRZZYAXCLBNvufCG7p"
    assert session["interface"] == "Claude CLI (Remote Control)"
def test_claude_app_bridge_session_metadata_marks_remote_control(tmp_path):
    app_root = tmp_path / "Claude/claude-code-sessions"
    app_dir = app_root / "project"
    app_dir.mkdir(parents=True)
    (app_dir / "local_rc.json").write_text(json.dumps({"cliSessionId": "fdbf0bdb", "bridgeSessionIds": ["cse_app_bridge"], "model": "claude-fable-5"}), encoding="utf-8")
    (app_dir / "local_empty.json").write_text(json.dumps({"cliSessionId": "47891de6", "bridgeSessionIds": [], "model": "claude-fable-5"}), encoding="utf-8")
    metadata = load_claude_app_metadata(app_root)
    rc_lines = [json_line({"type": "user", "cwd": "/repo/main", "gitBranch": "feature/test", "timestamp": "2026-07-16T10:00:00-07:00", "entrypoint": "cli", "message": {"content": "Build it"}})]
    rc = parse_claude_jsonl_lines(rc_lines, source_path="/tmp/fdbf0bdb.jsonl", worktrees=repo_worktrees(), app_metadata=metadata)
    empty = parse_claude_jsonl_lines(rc_lines, source_path="/tmp/47891de6.jsonl", worktrees=repo_worktrees(), app_metadata=metadata)
    plain = parse_claude_jsonl_lines(rc_lines, source_path="/tmp/18887b6a.jsonl", worktrees=repo_worktrees(), app_metadata=metadata)
    assert rc["remote_control"] is True
    assert rc["bridge_session_id"] == "cse_app_bridge"
    assert empty["remote_control"] is False
    assert empty["bridge_session_id"] is None
    assert plain["remote_control"] is False
    assert plain["bridge_session_id"] is None
def test_claude_app_metadata_enriches_missing_values_without_override(tmp_path):
    app_root = tmp_path / "Claude/claude-code-sessions"
    app_dir = app_root / "project"
    app_dir.mkdir(parents=True)
    (app_dir / "local_empty.json").write_text(json.dumps({"cliSessionId": "", "model": "claude-wrong"}), encoding="utf-8")
    (app_dir / "local_valid.json").write_text(
        json.dumps({
            "cliSessionId": "abc123",
            "model": "claude-fable-5",
            "effort": "high",
            "title": "App-provided title",
            "permissionMode": "acceptEdits",
        }),
        encoding="utf-8",
    )
    metadata = load_claude_app_metadata(app_root)
    assert "" not in metadata
    assert metadata["abc123"] == {
        "model": "claude-fable-5",
        "effort": "high",
        "title": "App-provided title",
        "permission_mode": "acceptEdits",
        "bridge_session_ids": [],
    }
    missing_lines = [
        json_line({"type": "user", "cwd": "/repo/main", "gitBranch": "feature/test", "timestamp": "2026-07-16T10:00:00-07:00", "message": {"content": "Build it"}}),
    ]
    enriched = parse_claude_jsonl_lines(missing_lines, source_path="/tmp/abc123.jsonl", worktrees=repo_worktrees(), app_metadata=metadata)
    assert enriched["raw_model"] == "claude-fable-5"
    assert enriched["model"] == "Fable 5"
    assert enriched["title"] == "App-provided title"
    assert enriched["permission_mode"] == "acceptEdits"
    present_lines = [
        json_line({"type": "ai-title", "title": "CLI title"}),
        json_line({"type": "user", "cwd": "/repo/main", "gitBranch": "feature/test", "timestamp": "2026-07-16T10:00:00-07:00", "message": {"content": "Build it"}}),
        json_line({"type": "assistant", "timestamp": "2026-07-16T10:01:00-07:00", "message": {"model": "claude-sonnet-5", "content": "Done"}}),
    ]
    present = parse_claude_jsonl_lines(present_lines, source_path="/tmp/abc123.jsonl", worktrees=repo_worktrees(), app_metadata=metadata)
    assert present["raw_model"] == "claude-sonnet-5"
    assert present["title"] == "CLI title"
def test_codex_label_derivation_fable_delegated_cli():
    lines = [
        json_line({"type": "session_meta", "payload": {"id": "codex-session", "timestamp": "2026-07-16T10:00:00-07:00", "cwd": "/repo/main", "git": {"branch": "feature/test"}, "source": "vscode", "originator": "Claude Code"}}),
        json_line({"type": "turn_context", "payload": {"model": "gpt-5.6-sol", "effort": "xhigh"}}),
        json_line({"type": "response_item", "payload": {"role": "user", "content": [{"text": "Implement the delegated work"}]}}),
    ]
    session = parse_codex_jsonl_lines(lines, source_path="/tmp/rollout.jsonl", worktrees=repo_worktrees())
    assert session["entrypoint"] == "cli"
    assert session["label"] == "Codex CLI (fable5-w-codex) - GPT 5.6 Sol xhigh"
    assert session["interface"] == "Codex CLI (fable5-w-codex)"
    assert session["origin"] == "delegated"
def test_looks_delegated_preamble_cases_and_cursor_never_delegated():
    assert labels.looks_delegated("You are the implementation executor for task 1")
    assert labels.looks_delegated("You are the implementation lead for task 2")
    assert labels.looks_delegated("Please build this. Do not commit or push. Stay scoped.")
    assert not labels.looks_delegated(("x" * 401) + "Do not commit or push.")
    cursor = parse_cursor_composer_data({
        "composerId": "composer-delegated-looking",
        "workspaceIdentifier": {"uri": {"path": "/repo/main"}},
        "modelConfig": {"modelName": "composer-2.5"},
        "name": "You are the implementation executor",
    }, worktrees=repo_worktrees())
    assert cursor["origin"] == "operator"
def test_codex_exec_preamble_relabels_to_fable_interface():
    lines = [
        json_line({"type": "session_meta", "payload": {"id": "codex-exec", "timestamp": "2026-07-16T10:00:00-07:00", "cwd": "/repo/main", "git": {"branch": "feature/test"}, "source": "exec", "originator": "codex_exec"}}),
        json_line({"type": "turn_context", "payload": {"model": "gpt-5.5", "effort": "xhigh"}}),
        json_line({"type": "response_item", "payload": {"role": "user", "content": [{"text": "You are the implementation executor for holodeck. Do not commit or push."}]}}),
    ]
    session = parse_codex_jsonl_lines(lines, source_path="/tmp/rollout.jsonl", worktrees=repo_worktrees())
    assert session["entrypoint"] == "cli"
    assert session["origin"] == "delegated"
    assert session["label"] == "Codex CLI (fable5-w-codex) - GPT 5.5 xhigh"
    assert session["interface"] == "Codex CLI (fable5-w-codex)"

### Exchanges
def test_segment_messages_folds_short_follow_up():
    messages = [
        {"role": "user", "text": "Build the turns database backend", "ts": "2026-07-16T10:00:00-07:00"},
        {"role": "assistant", "text": "Implemented db.py", "ts": "2026-07-16T10:20:00-07:00"},
        {"role": "user", "text": "Also add labels.", "ts": "2026-07-16T10:22:00-07:00"},
        {"role": "assistant", "text": "Updated labels.py", "ts": "2026-07-16T10:23:00-07:00"},
        {"role": "user", "text": "What changed?", "ts": "2026-07-16T10:30:00-07:00"},
        {"role": "assistant", "text": "A short explanation.", "ts": "2026-07-16T10:31:00-07:00"},
    ]
    exchanges = ingest.segment_messages(messages, "cursor:composer-1")
    assert len(exchanges) == 2
    assert exchanges[0]["id"] == "cursor:composer-1#1"
    assert "Follow-up:\nAlso add labels." in exchanges[0]["user_text"]
    assert "Updated labels.py" in exchanges[0]["response_text"]
    assert exchanges[0]["response_end_ts"] == "2026-07-16T10:23:00-07:00"
def test_segment_messages_tracks_last_assistant_text_as_final_response():
    messages = [
        {"role": "user", "text": "Build the recap fields", "ts": "2026-07-16T10:00:00-07:00"},
        {"role": "assistant", "text": "I will inspect the code.", "ts": "2026-07-16T10:01:00-07:00"},
        {"role": "assistant", "text": "The schema needs two fields.", "ts": "2026-07-16T10:02:00-07:00"},
        {"role": "assistant", "text": "Done: final response and recap now persist.", "ts": "2026-07-16T10:03:00-07:00"},
    ]
    exchanges = ingest.segment_messages(messages, "claude-code:final")
    assert len(exchanges) == 1
    assert exchanges[0]["response_text"] == "I will inspect the code.\n\nThe schema needs two fields.\n\nDone: final response and recap now persist."
    assert exchanges[0]["response_final_text"] == "Done: final response and recap now persist."
def test_segment_messages_attaches_recap_without_response_leakage():
    messages = [
        {"role": "user", "text": "Explain the drawer data.", "ts": "2026-07-16T10:00:00-07:00"},
        {"role": "assistant", "text": "Use the exchange payload.", "ts": "2026-07-16T10:01:00-07:00"},
        {"role": "recap", "text": "Recap mentions ```diff``` but should not affect kind.", "ts": "2026-07-16T10:02:00-07:00"},
        {"role": "user", "text": "Now explain the next exchange.", "ts": "2026-07-16T10:10:00-07:00"},
        {"role": "assistant", "text": "Second exchange stays separate.", "ts": "2026-07-16T10:11:00-07:00"},
    ]
    exchanges = ingest.segment_messages(messages, "claude-code:recap")
    assert len(exchanges) == 2
    assert exchanges[0]["response_recap"] == "Recap mentions ```diff``` but should not affect kind."
    assert exchanges[0]["response_text"] == "Use the exchange payload."
    assert exchanges[0]["response_end_ts"] == "2026-07-16T10:01:00-07:00"
    assert exchanges[0]["kind"] == "info"
    assert exchanges[1]["response_recap"] == ""
def test_segment_messages_ignores_recap_before_user():
    messages = [
        {"role": "recap", "text": "No active turn exists yet.", "ts": "2026-07-16T09:59:00-07:00"},
    ]
    assert ingest.segment_messages(messages, "claude-code:no-user") == []
def test_classification_info_primary_and_quick():
    assert ingest.classify_exchange({"user_text": "What is this?", "response_text": "It is a local dashboard.", "_response_messages": 1}) == "info"
    assert ingest.classify_exchange({"user_text": "x" * 400, "response_text": "Done", "_response_messages": 1}) == "primary"
    assert ingest.classify_exchange({"user_text": "Fix typo", "response_text": "```diff\n+fixed\n```", "_response_messages": 1}) == "quick"
    assert ingest.classify_exchange({"user_text": "Do several things", "response_text": "Done", "_response_messages": 10}) == "primary"

### Correlation
def test_correlation_agent_window_after_response_and_unmatched(tmp_path):
    conn = init_tmp_db(tmp_path)
    db.upsert_session(conn, {"id": "cursor:s1", "platform": "cursor", "entrypoint": "app", "host": "local", "source_path": "s1", "project": "/repo/main", "worktree": "/repo/main", "branch": "feature/test", "label": "Cursor IDE", "model": None, "interface": "Cursor IDE", "title": None, "started": "2026-07-16T10:00:00-07:00", "last_activity": "2026-07-16T11:10:00-07:00", "ingested_at": "now"})
    db.upsert_exchange(conn, {"id": "cursor:s1#1", "session_id": "cursor:s1", "idx": 1, "kind": "primary", "user_ts": "2026-07-16T10:00:00-07:00", "user_text": "Build", "response_text": "Done", "response_end_ts": "2026-07-16T10:20:00-07:00", "follow_up_of": None})
    db.upsert_exchange(conn, {"id": "cursor:s1#2", "session_id": "cursor:s1", "idx": 2, "kind": "quick", "user_ts": "2026-07-16T11:00:00-07:00", "user_text": "Tweak", "response_text": "Done", "response_end_ts": "2026-07-16T11:05:00-07:00", "follow_up_of": None})
    db.upsert_session(conn, {"id": "cursor:s2", "platform": "cursor", "entrypoint": "app", "host": "local", "source_path": "s2", "project": "/repo/after", "worktree": "/repo/after", "branch": "feature/after", "label": "Cursor IDE", "model": None, "interface": "Cursor IDE", "title": None, "started": "2026-07-16T10:00:00-07:00", "last_activity": "2026-07-16T10:20:00-07:00", "ingested_at": "now"})
    db.upsert_exchange(conn, {"id": "cursor:s2#1", "session_id": "cursor:s2", "idx": 1, "kind": "primary", "user_ts": "2026-07-16T10:00:00-07:00", "user_text": "Build", "response_text": "Done", "response_end_ts": "2026-07-16T10:20:00-07:00", "follow_up_of": None})
    for commit in [
        {"sha": "aaa", "branch": "feature/test", "worktree": "/repo/main", "author": "Randy", "author_email": "randy@example.test", "author_date": "2026-07-16T10:30:00-07:00", "committer_date": "2026-07-16T10:30:00-07:00", "subject": "Agent commit", "body": "", "is_agent_commit": 0},
        {"sha": "bbb", "branch": "feature/after", "worktree": "/repo/after", "author": "Randy", "author_email": "randy@example.test", "author_date": "2026-07-16T10:50:00-07:00", "committer_date": "2026-07-16T10:50:00-07:00", "subject": "After response", "body": "", "is_agent_commit": 0},
        {"sha": "ccc", "branch": "feature/after", "worktree": "/repo/after", "author": "Randy", "author_email": "randy@example.test", "author_date": "2026-07-16T12:00:00-07:00", "committer_date": "2026-07-16T12:00:00-07:00", "subject": "Unmatched", "body": "", "is_agent_commit": 0},
    ]:
        db.upsert_commit(conn, commit)
    assert correlate.rebuild_links(conn) == 2
    rows = conn.execute("SELECT * FROM links ORDER BY sha").fetchall()
    assert [(row["sha"], row["exchange_id"], row["method"]) for row in rows] == [
        ("aaa", "cursor:s1#1", "agent-window"),
        ("bbb", "cursor:s2#1", "after-response"),
    ]

### Digest
def test_digest_json_parsing_and_long_response_windowing():
    parsed = digest.parse_digest_json('```json\n{"title":"Turns database build","asked":["one"],"notes":["two"],"recap":"Done."}\n```')
    assert parsed == {"title": "Turns database build", "asked": ["one"], "notes": ["two"], "recap": "Done."}
    long_response = "A" * 7000 + "MIDDLE" * 2000 + "Z" * 19000
    truncated = digest.truncate_response_text(long_response)
    assert len(truncated) == digest.RESPONSE_HEAD_LIMIT + len("\n\n[...middle truncated for digest...]\n\n") + digest.RESPONSE_TAIL_LIMIT
    assert truncated.startswith("A" * digest.RESPONSE_HEAD_LIMIT)
    assert truncated.endswith("Z" * digest.RESPONSE_TAIL_LIMIT)
    assert "MIDDLEMIDDLE" not in truncated
def test_digest_generation_retries_json_parse_with_mocked_anthropic():
    calls = []
    class Messages:
        def create(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return type("Response", (), {"content": [type("Block", (), {"text": "not json"})()]})()
            return type("Response", (), {"content": [type("Block", (), {"text": '{"title":"Turns digest test","asked":["a"],"notes":[],"recap":"Done."}'})()]})()
    class Client:
        def __init__(self, api_key):
            self.messages = Messages()
    result = digest.generate_digest("ask", "response", env={"ANTHROPIC_API_KEY_LOCAL": "key"}, anthropic_client_factory=Client)
    assert result["title"] == "Turns digest test"
    assert result["asked"] == ["a"]
    assert result["model_used"] == digest.ANTHROPIC_MODEL
    assert len(calls) == 2
    assert "Return ONLY the JSON object" in calls[1]["messages"][0]["content"]

### DB
def test_session_schema_migration_renames_tool_and_adds_new_fields(tmp_path):
    conn = db.connect(tmp_path / "legacy.db")
    conn.execute(
        """
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            tool TEXT,
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
        )
        """
    )
    conn.execute(
        """
        INSERT INTO sessions(id, tool, source_path, source_url, project, worktree, branch, label, model, interface, origin, parent_session_id, title, started, last_activity, ingested_at)
        VALUES('claude-cloud:abc', 'claude-cloud', NULL, 'https://claude.ai/code/abc', NULL, '/repo/main', 'feature/test', 'Claude Code Cloud - Opus 4.8', 'claude-opus-4-8', 'Claude Code App (Cloud)', 'operator', NULL, 'Cloud', 'start', 'last', 'now')
        """
    )
    db.init_db(conn)
    columns = db.table_columns(conn, "sessions")
    assert "tool" not in columns
    for column in ("platform", "entrypoint", "host", "remote_control", "bridge_session_id"):
        assert column in columns
    row = conn.execute("SELECT * FROM sessions WHERE id = 'claude-cloud:abc'").fetchone()
    assert row["platform"] == "claude"
    assert row["entrypoint"] == "app"
    assert row["host"] == "cloud"
    assert row["remote_control"] == 0
    assert row["source_url"] == "https://claude.ai/code/abc"
def test_db_idempotent_reingest_preserves_digests(tmp_path):
    conn = init_tmp_db(tmp_path)
    session = {"platform": "cursor", "entrypoint": "app", "host": "local", "id": "composer-1", "source_path": "composer-1", "project": "/repo/main", "worktree": "/repo/main", "branch": "feature/test", "label": "Cursor IDE - Composer 2.5 Fast", "model": "Composer 2.5 Fast", "interface": "Cursor IDE", "title": "Build", "started": "2026-07-16T10:00:00-07:00", "last_activity": "2026-07-16T10:20:00-07:00"}
    messages = {
        "cursor:composer-1": [
            {"role": "user", "text": "Build the backend", "ts": "2026-07-16T10:00:00-07:00"},
            {"role": "assistant", "text": "Done", "ts": "2026-07-16T10:20:00-07:00"},
        ]
    }
    ingest.ingest_sessions(conn, [session], messages_by_session=messages, ingested_at="first")
    db.upsert_digest(conn, "cursor:composer-1#1", {"asked": ["Build backend"], "notes": [], "recap": "Built.", "model_used": "mock", "created_at": "digest-time"})
    ingest.ingest_sessions(conn, [session], messages_by_session=messages, ingested_at="second")
    assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM exchanges").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM digests").fetchone()[0] == 1
    assert db.digest_from_row(db.exchange_digest_row(conn, "cursor:composer-1#1"))["recap"] == "Built."
def test_ingest_relabels_codex_exec_from_full_messages(tmp_path):
    conn = init_tmp_db(tmp_path)
    session = {"platform": "codex", "entrypoint": "cli", "host": "local", "id": "codex-1", "source_path": "codex-1", "project": "/repo/main", "worktree": "/repo/main", "branch": "feature/test", "originator": "codex_exec", "raw_model": "gpt-5.5", "effort": "xhigh", "label": "Codex CLI (fable5-w-codex) - GPT 5.5 xhigh", "model": "GPT 5.5 xhigh", "interface": "Codex CLI (fable5-w-codex)", "title": None, "started": "2026-07-16T10:00:00-07:00", "last_activity": "2026-07-16T10:20:00-07:00"}
    messages = {
        "codex:codex-1": [
            {"role": "user", "text": "You are the implementation executor. Do not commit or push.", "ts": "2026-07-16T10:00:00-07:00"},
            {"role": "assistant", "text": "Done", "ts": "2026-07-16T10:20:00-07:00"},
        ]
    }
    ingest.ingest_sessions(conn, [session], messages_by_session=messages, ingested_at="now")
    row = conn.execute("SELECT label, interface, origin FROM sessions WHERE id = 'codex:codex-1'").fetchone()
    assert row["origin"] == "delegated"
    assert row["interface"] == "Codex CLI (fable5-w-codex)"
    assert row["label"] == "Codex CLI (fable5-w-codex) - GPT 5.5 xhigh"
    exchange = conn.execute("SELECT origin FROM exchanges WHERE id = 'codex:codex-1#1'").fetchone()
    assert exchange["origin"] == "delegated"
def test_subagent_parent_linkage_matches_operator_window_and_worktree(tmp_path):
    conn = init_tmp_db(tmp_path)
    sessions = [
        {"platform": "codex", "id": "parent", "source_path": "parent", "project": "/repo/main", "worktree": "/repo/main", "branch": "feature/test", "originator": "Codex Desktop", "entrypoint": "app", "raw_model": "gpt-5.5", "title": "Parent", "started": "2026-07-20T10:00:00-07:00", "last_activity": "2026-07-20T10:30:00-07:00"},
        {"platform": "codex", "id": "inside", "source_path": "inside", "project": "/repo/main", "worktree": "/repo/main", "branch": "feature/test", "originator": "Codex Desktop", "entrypoint": "subagent", "raw_model": "gpt-5.5", "title": "Inside", "started": "2026-07-20T10:05:00-07:00", "last_activity": "2026-07-20T10:10:00-07:00"},
        {"platform": "codex", "id": "outside", "source_path": "outside", "project": "/repo/main", "worktree": "/repo/main", "branch": "feature/test", "originator": "Codex Desktop", "entrypoint": "subagent", "raw_model": "gpt-5.5", "title": "Outside", "started": "2026-07-20T13:00:00-07:00", "last_activity": "2026-07-20T13:05:00-07:00"},
        {"platform": "codex", "id": "other", "source_path": "other", "project": "/repo/other", "worktree": "/repo/other", "branch": "feature/other", "originator": "Codex Desktop", "entrypoint": "subagent", "raw_model": "gpt-5.5", "title": "Other", "started": "2026-07-20T10:06:00-07:00", "last_activity": "2026-07-20T10:11:00-07:00"},
    ]
    messages = {
        "codex:parent": [{"role": "user", "text": "Parent operator prompt", "ts": "2026-07-20T10:00:00-07:00"}],
        "codex:inside": [{"role": "user", "text": "Inside subagent prompt", "ts": "2026-07-20T10:05:00-07:00"}],
        "codex:outside": [{"role": "user", "text": "Outside subagent prompt", "ts": "2026-07-20T13:00:00-07:00"}],
        "codex:other": [{"role": "user", "text": "Other subagent prompt", "ts": "2026-07-20T10:06:00-07:00"}],
    }
    ingest.ingest_sessions(conn, sessions, messages_by_session=messages, ingested_at="now")
    rows = {row["id"]: row["parent_session_id"] for row in conn.execute("SELECT id, parent_session_id FROM sessions").fetchall()}
    assert rows["codex:inside"] == "codex:parent"
    assert rows["codex:outside"] is None
    assert rows["codex:other"] is None
def test_subagent_parent_linkage_falls_back_to_nearest_earlier_operator(tmp_path):
    conn = init_tmp_db(tmp_path)
    db.upsert_session(conn, make_session("cursor:earlier", last_activity="2026-07-20T10:30:00-07:00"))
    db.upsert_session(conn, make_session("codex:child", origin="delegated", last_activity="2026-07-20T11:20:00-07:00"))
    conn.execute("UPDATE sessions SET started = ? WHERE id = ?", ("2026-07-20T11:15:00-07:00", "codex:child"))
    linked = db.rebuild_subagent_links(conn)
    row = conn.execute("SELECT parent_session_id FROM sessions WHERE id = 'codex:child'").fetchone()
    assert linked == 1
    assert row["parent_session_id"] == "cursor:earlier"
def test_list_turns_filters_delegated_by_default(tmp_path):
    conn = init_tmp_db(tmp_path)
    db.upsert_session(conn, make_session("cursor:operator"))
    db.upsert_exchange(conn, make_exchange("cursor:operator#1", "cursor:operator"))
    db.upsert_session(conn, make_session("codex:delegated", origin="delegated"))
    db.upsert_exchange(conn, make_exchange("codex:delegated#1", "codex:delegated", user_ts="2026-07-16T10:01:00-07:00", origin="delegated"))
    default_ids = [item["id"] for item in db.list_turns(conn, limit=10)]
    all_ids = [item["id"] for item in db.list_turns(conn, limit=10, include_delegated=True)]
    assert default_ids == ["cursor:operator#1"]
    assert all_ids == ["codex:delegated#1", "cursor:operator#1"]
def test_turn_status_waiting_and_your_turn_derivation(tmp_path):
    conn = init_tmp_db(tmp_path)
    db.upsert_session(conn, make_session("cursor:waiting", worktree="/repo/wait", branch="feature/wait", last_activity="2026-07-17T10:05:00-07:00"))
    db.upsert_exchange(conn, make_exchange("cursor:waiting#1", "cursor:waiting", user_ts="2026-07-17T10:05:00-07:00", response_text="", response_end_ts=None))
    db.upsert_session(conn, make_session("cursor:done", worktree="/repo/done", branch="feature/done", last_activity="2026-07-17T10:20:00-07:00"))
    db.upsert_exchange(conn, make_exchange("cursor:done#1", "cursor:done", user_ts="2026-07-17T10:00:00-07:00", response_text="Done", response_end_ts="2026-07-17T10:18:00-07:00"))
    db.upsert_digest(conn, "cursor:done#1", {"title": "Turns status build", "asked": ["Build status"], "notes": [], "recap": "Status was built.", "model_used": "mock", "created_at": "now"})
    rows = db.list_turn_status(conn, now=datetime.fromisoformat("2026-07-17T12:00:00-07:00"))
    by_branch = {row["branch"]: row for row in rows}
    assert by_branch["feature/wait"]["state"] == "waiting-on-ai"
    assert by_branch["feature/wait"]["since"] == "2026-07-17T10:05:00-07:00"
    assert by_branch["feature/done"]["state"] == "your-turn"
    assert by_branch["feature/done"]["since"] == "2026-07-17T10:18:00-07:00"
    assert by_branch["feature/done"]["turn_title"] == "Turns status build"
    assert by_branch["feature/done"]["recap"] == "Status was built."
def test_session_end_command_detection():
    assert db.is_session_end_command("close")
    assert db.is_session_end_command("/close")
    assert db.is_session_end_command("  /EXIT  ")
    assert db.is_session_end_command("quit")
    assert not db.is_session_end_command("please close the PR")
    assert not db.is_session_end_command("Build the backend")
def test_turn_status_skips_unanswered_session_end_command(tmp_path):
    conn = init_tmp_db(tmp_path)
    db.upsert_session(conn, make_session("claude-code:closed", worktree="/repo/web", branch="feature/web-site-redo-fof", last_activity="2026-07-20T16:27:00-07:00"))
    db.upsert_exchange(conn, make_exchange(
        "claude-code:closed#1", "claude-code:closed",
        user_ts="2026-07-20T16:00:00-07:00",
        response_text="Merged the PR.",
        response_end_ts="2026-07-20T16:20:00-07:00",
        user_text="Create the PR and merge it",
    ))
    db.upsert_exchange(conn, make_exchange(
        "claude-code:closed#2", "claude-code:closed",
        user_ts="2026-07-20T16:27:00-07:00",
        response_text="",
        response_end_ts=None,
        user_text="close",
    ))
    db.upsert_digest(conn, "claude-code:closed#1", {"title": "PR merged", "asked": ["Merge PR"], "notes": [], "recap": "PR was merged.", "model_used": "mock", "created_at": "now"})
    rows = db.list_turn_status(conn, now=datetime.fromisoformat("2026-07-20T17:00:00-07:00"))
    by_branch = {row["branch"]: row for row in rows}
    assert by_branch["feature/web-site-redo-fof"]["state"] == "your-turn"
    assert by_branch["feature/web-site-redo-fof"]["exchange_id"] == "claude-code:closed#1"
    assert by_branch["feature/web-site-redo-fof"]["since"] == "2026-07-20T16:20:00-07:00"
    assert by_branch["feature/web-site-redo-fof"]["turn_title"] == "PR merged"
def test_segment_messages_skips_session_end_command():
    messages = [
        {"role": "user", "text": "Ship it", "ts": "2026-07-20T16:00:00-07:00"},
        {"role": "assistant", "text": "Shipped.", "ts": "2026-07-20T16:05:00-07:00"},
        {"role": "user", "text": "/close", "ts": "2026-07-20T16:06:00-07:00"},
    ]
    exchanges = ingest.segment_messages(messages, "claude-code:end")
    assert len(exchanges) == 1
    assert exchanges[0]["user_text"] == "Ship it"
    assert exchanges[0]["response_text"] == "Shipped."
def test_claude_messages_from_lines_surfaces_away_summary_recap():
    lines = [
        json_line({"type": "system", "subtype": "away_summary", "content": "The assistant finished the implementation.", "timestamp": "2026-07-16T10:02:00-07:00"}),
        json_line({"type": "system", "subtype": "turn_duration", "content": "ignored", "timestamp": "2026-07-16T10:03:00-07:00"}),
    ]
    assert claude_messages_from_lines(lines) == [
        {"role": "recap", "text": "The assistant finished the implementation.", "ts": "2026-07-16T10:02:00-07:00"},
    ]
def test_digest_title_column_migration_and_payload(tmp_path):
    conn = db.connect(tmp_path / "old.db")
    conn.execute("CREATE TABLE digests (exchange_id TEXT PRIMARY KEY, asked_json TEXT, notes_json TEXT, recap TEXT, model_used TEXT, created_at TEXT)")
    db.init_db(conn)
    assert "title" in db.table_columns(conn, "digests")
    db.upsert_session(conn, make_session("cursor:title"))
    db.upsert_exchange(conn, make_exchange("cursor:title#1", "cursor:title"))
    db.upsert_digest(conn, "cursor:title#1", {"title": "Digest title storage", "asked": ["Store title"], "notes": [], "recap": "Stored.", "model_used": "mock", "created_at": "now"})
    payload = db.get_exchange(conn, "cursor:title#1")
    assert payload["digest"]["title"] == "Digest title storage"
    assert payload["turn_title"] == "Digest title storage"
def test_source_url_column_migration_and_payloads(tmp_path):
    conn = db.connect(tmp_path / "old-source.db")
    conn.execute(
        """
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            tool TEXT,
            source_path TEXT,
            project TEXT,
            worktree TEXT,
            branch TEXT,
            label TEXT,
            model TEXT,
            interface TEXT,
            origin TEXT DEFAULT 'operator',
            title TEXT,
            started TEXT,
            last_activity TEXT,
            ingested_at TEXT
        )
        """
    )
    db.init_db(conn)
    assert "source_url" in db.table_columns(conn, "sessions")
    session = make_session("codex-cloud:task-source", worktree="/repo/source", branch="feature/source", last_activity="2026-07-17T10:20:00-07:00")
    session["source_url"] = "https://codex.openai.com/tasks/task-source"
    db.upsert_session(conn, session)
    db.upsert_exchange(conn, make_exchange("codex-cloud:task-source#0", "codex-cloud:task-source", user_ts="2026-07-17T10:00:00-07:00", response_end_ts="2026-07-17T10:20:00-07:00"))
    turns = db.list_turns(conn, limit=1)
    exchange = db.get_exchange(conn, "codex-cloud:task-source#0")
    statuses = db.list_turn_status(conn, now=datetime.fromisoformat("2026-07-17T12:00:00-07:00"))
    assert turns[0]["source_url"] == "https://codex.openai.com/tasks/task-source"
    assert exchange["source_url"] == "https://codex.openai.com/tasks/task-source"
    assert statuses[0]["source_url"] == "https://codex.openai.com/tasks/task-source"
def test_exchange_final_text_and_recap_round_trip(tmp_path):
    conn = init_tmp_db(tmp_path)
    db.upsert_session(conn, make_session("cursor:final-recap"))
    exchange = make_exchange("cursor:final-recap#1", "cursor:final-recap", response_text="First answer\n\nFinal answer")
    exchange["response_final_text"] = "Final answer"
    exchange["response_recap"] = "The assistant summarized the completed turn."
    db.upsert_exchange(conn, exchange)
    payload = db.get_exchange(conn, "cursor:final-recap#1")
    assert payload["response_final_text"] == "Final answer"
    assert payload["response_recap"] == "The assistant summarized the completed turn."
def test_exchange_final_text_and_recap_column_migration(tmp_path):
    conn = db.connect(tmp_path / "old-exchanges.db")
    conn.execute(
        """
        CREATE TABLE exchanges (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            idx INTEGER NOT NULL,
            kind TEXT CHECK(kind IN ('primary','quick','info')),
            user_ts TEXT,
            user_text TEXT,
            response_text TEXT,
            response_end_ts TEXT,
            origin TEXT DEFAULT 'operator',
            follow_up_of TEXT NULL
        )
        """
    )
    db.init_db(conn)
    columns = db.table_columns(conn, "exchanges")
    assert "response_final_text" in columns
    assert "response_recap" in columns
    assert db.get_meta(conn, "schema_version") == "7"
def test_sample_turns_exchange_details_include_response_final_text():
    payload = json.loads((db.repo_root() / "apps/holodeck/web/sample-turns.json").read_text(encoding="utf-8"))
    assert payload["exchange_details"]
    for exchange in payload["exchange_details"].values():
        assert exchange["response_final_text"].strip()
def test_auto_digest_selection_is_recent_operator_only_and_capped(tmp_path):
    conn = init_tmp_db(tmp_path)
    rows = [
        ("cursor:recent-primary", "cursor:recent-primary#1", "operator", "primary", "2026-07-17T10:00:00-07:00", "Done"),
        ("cursor:recent-quick", "cursor:recent-quick#1", "operator", "quick", "2026-07-17T11:00:00-07:00", "Done"),
        ("codex:delegated", "codex:delegated#1", "delegated", "primary", "2026-07-17T11:30:00-07:00", "Done"),
        ("cursor:old", "cursor:old#1", "operator", "primary", "2026-07-14T10:00:00-07:00", "Done"),
        ("cursor:waiting", "cursor:waiting#1", "operator", "primary", "2026-07-17T12:00:00-07:00", ""),
    ]
    for session_id, exchange_id, origin, kind, user_ts, response_text in rows:
        db.upsert_session(conn, make_session(session_id, origin=origin, last_activity=user_ts))
        db.upsert_exchange(conn, make_exchange(exchange_id, session_id, user_ts=user_ts, response_text=response_text, response_end_ts=user_ts if response_text else None, kind=kind, origin=origin))
    cutoff = digest.auto_digest_cutoff(now=datetime.fromisoformat("2026-07-17T12:30:00-07:00"))
    selected = db.missing_digest_exchanges(conn, limit=25, since=cutoff, operator_only=True)
    assert [row["id"] for row in selected] == ["cursor:recent-primary#1", "cursor:recent-quick#1"]

def test_cloud_session_id_is_idempotent():
    # Guards against the claude-cloud: prefix accumulating across re-ingests.
    base = "cse_abc123"
    once = cloud_claude.cloud_session_id(base)
    assert once == "claude-cloud:cse_abc123"
    assert cloud_claude.cloud_session_id(once) == once
    assert cloud_claude.cloud_session_id("claude-cloud:claude-cloud:" + base) == once

def test_cloud_import_ingest_is_stable_across_rebuilds(tmp_path):
    # Reproduces the duplication bug: importing the same export twice must not grow the
    # session count or double-prefix ids.
    from apps.holodeck.turns import db as turns_db
    from apps.holodeck.turns import ingest as turns_ingest
    export = {"sessions": [{
        "summary": {"id": "cse_dup1", "title": "Dup test", "status": "active", "updated_at": "2026-07-19T00:00:00Z"},
        "detail": {"response_shape": {"config": {"model": "claude-opus-4-8",
            "outcomes": [{"git_info": {"repo": "FocusOnFoundationsNonprofit/fof-mono", "branches": ["feature/x"]}}]}}},
        "events": [{"event_type": "user", "created_at": "2026-07-19T00:00:00Z", "sequence_num": "1",
                    "payload": {"message": {"content": "hello"}}}],
    }]}
    import_dir = tmp_path / "apps/holodeck/data/cloud_claude_import"
    import_dir.mkdir(parents=True)
    (import_dir / "export.json").write_text(json.dumps(export), encoding="utf-8")
    db_path = tmp_path / "turns.db"
    conn = turns_db.connect(db_path)
    turns_db.init_db(conn)
    worktrees = [{"path": str(tmp_path), "branch": "feature/x"}]
    for _ in range(2):
        turns_ingest.ingest_cloud_claude(conn, worktrees, root=str(tmp_path))
    rows = conn.execute("SELECT id FROM sessions WHERE platform = 'claude' AND host = 'cloud'").fetchall()
    ids = [row["id"] for row in rows]
    assert len(ids) == 1, ids
    assert ids[0] == "claude-cloud:cse_dup1"
    assert not any(i.startswith("claude-cloud:claude-cloud:") for i in ids)
    conn.close()

def test_codex_subagent_is_delegated():
    from apps.holodeck.turns import labels
    sub = {"platform": "codex", "entrypoint": "subagent", "originator": "Codex Desktop", "label": "Codex Subagent - Codex Auto Review low"}
    assert labels.codex_session_is_delegated(sub) is True
    assert labels.derive_session_origin(sub) == labels.DELEGATED_ORIGIN
    normal = {"platform": "codex", "entrypoint": "app", "originator": "Codex Desktop", "label": "Codex App - GPT 5.6 Sol xhigh"}
    cli = {"platform": "codex", "entrypoint": "cli", "originator": "Codex Desktop", "label": "Codex CLI - GPT 5.5"}
    claude_cli = {"platform": "claude", "entrypoint": "cli", "label": "Claude CLI - Fable 5"}
    assert labels.derive_session_origin(cli) == labels.DELEGATED_ORIGIN
    assert labels.derive_session_origin(normal) == labels.OPERATOR_ORIGIN
    assert labels.derive_session_origin(claude_cli) == labels.OPERATOR_ORIGIN

def test_list_subagents_matches_raw_parent_id(tmp_path):
    # The frontend passes the raw snapshot session id (no prefix); turns.db stores
    # parent_session_id prefixed (e.g. cursor:<uuid>). list_subagents must match both.
    from apps.holodeck.turns import db as turns_db
    conn = turns_db.connect(tmp_path / "turns.db")
    turns_db.init_db(conn)
    now = "2026-07-20T00:00:00Z"
    turns_db.upsert_session(conn, {"id": "cursor:parent1", "platform": "cursor", "entrypoint": "app", "host": "local", "source_path": None, "project": None, "worktree": "/w", "branch": "b", "label": "P", "model": None, "interface": None, "origin": "operator", "title": "Parent", "started": now, "last_activity": now, "ingested_at": now})
    turns_db.upsert_session(conn, {"id": "codex:child1", "platform": "codex", "entrypoint": "cli", "host": "local", "source_path": None, "project": None, "worktree": "/w", "branch": "b", "label": "Codex CLI (fable5-w-codex)", "model": None, "interface": None, "origin": "delegated", "parent_session_id": "cursor:parent1", "title": "Child", "started": now, "last_activity": now, "ingested_at": now})
    turns_db.upsert_exchange(conn, {"id": "codex:child1#0", "session_id": "codex:child1", "idx": 0, "kind": "primary", "user_ts": now, "user_text": "do the task", "response_text": "did it", "response_end_ts": now, "origin": "delegated", "follow_up_of": None})
    assert len(turns_db.list_subagents(conn, "cursor:parent1")) == 1
    assert len(turns_db.list_subagents(conn, "parent1")) == 1  # raw id (as the frontend sends)
    conn.close()

### History-purge hash map
def test_hash_map_load_resolve_and_remap(tmp_path):
    commit_tsv = "\n".join([
        "old_hash\tnew_hash\tstatus\tauthor_date\tauthor\tsubject\tbranches\tnew_exists\tnew_subject",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\tbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\trewritten\t2026-07-16T10:00:00-07:00\tRandy\tOld subject\tfeature/test\tyes\tNew subject",
        "cccccccccccccccccccccccccccccccccccccccc\t0000000000000000000000000000000000000000\tpruned\t2026-06-08T17:41:06+00:00\tClaude\tPruned\tmain\tn/a\t",
    ]) + "\n"
    tip_tsv = "\n".join([
        "branch\told_tip\tnew_tip\told_date\told_subject\tnew_exists\tnew_subject",
        "feature/test\taaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\tbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\t2026-07-16T10:00:00-07:00\tOld subject\tyes\tNew subject",
    ]) + "\n"
    commit_path = tmp_path / "commit-map.tsv"
    tip_path = tmp_path / "branch-tip-map.tsv"
    commit_path.write_text(commit_tsv, encoding="utf-8")
    tip_path.write_text(tip_tsv, encoding="utf-8")
    conn = init_tmp_db(tmp_path)
    db.upsert_session(conn, make_session("cursor:s1"))
    db.upsert_exchange(conn, {"id": "cursor:s1#1", "session_id": "cursor:s1", "idx": 1, "kind": "primary", "user_ts": "2026-07-16T10:00:00-07:00", "user_text": "Build", "response_text": "Done", "response_end_ts": "2026-07-16T10:20:00-07:00", "follow_up_of": None})
    db.upsert_commit(conn, {"sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "branch": "feature/test", "worktree": "/repo/main", "author": "Randy", "author_email": "randy@example.test", "author_date": "2026-07-16T10:30:00-07:00", "committer_date": "2026-07-16T10:30:00-07:00", "subject": "Old subject", "body": "", "is_agent_commit": 0})
    db.upsert_link(conn, {"exchange_id": "cursor:s1#1", "sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "method": "agent-window", "confidence": 0.9})
    summary = hash_map.load_maps_from_files(conn, commit_map_path=commit_path, branch_tip_map_path=tip_path, root=tmp_path)
    assert summary["commit_map_rows"] == 2
    assert summary["branch_tip_map_rows"] == 1
    assert hash_map.resolve_sha(conn, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa") == "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    assert hash_map.resolve_sha(conn, "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", direction="to_old") == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    assert hash_map.resolve_sha(conn, "cccccccccccccccccccccccccccccccccccccccc") is None
    remapped = hash_map.remap_commits_to_new_shas(conn)
    assert remapped["remapped_commits"] == 1
    assert remapped["links_moved"] == 1
    assert conn.execute("SELECT count(*) AS n FROM commits WHERE sha = ?", ("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",)).fetchone()["n"] == 0
    assert conn.execute("SELECT count(*) AS n FROM commits WHERE sha = ?", ("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",)).fetchone()["n"] == 1
    assert conn.execute("SELECT sha FROM links WHERE exchange_id = ?", ("cursor:s1#1",)).fetchone()["sha"] == "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    conn.close()
