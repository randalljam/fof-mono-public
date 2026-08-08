import importlib.util
import inspect
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.holodeck import server as holodeck_server


BASE_URL = "http://127.0.0.1:8790"
BASE_HEADERS = {
    "Host": "127.0.0.1:8790",
    "Origin": BASE_URL,
    "Sec-Fetch-Site": "same-origin",
    "X-Holodeck-Action": "focus",
}


class FakeActivationResult:
    def to_dict(self):
        return {"ok": True, "target": "cursor", "status": "focused", "matched_by": "title"}


class FakeActivationError(Exception):
    def __init__(self, code, message="safe activation error"):
        self.code = code
        self.message = message
        super().__init__(message)


def api_client(peer="127.0.0.1"):
    return TestClient(
        holodeck_server.app,
        base_url=BASE_URL,
        client=(peer, 50000),
    )


def focus_body(path):
    return {"target": "cursor", "matcher": {"worktree_path": str(path)}}


def test_focus_cursor_success_uses_live_worktree_and_server_candidates(tmp_path, monkeypatch):
    worktree = tmp_path / "feature-demo"
    worktree.mkdir()
    workspace = worktree / "codex-feature-demo.code-workspace"
    workspace.write_text(json.dumps({"folders": [{"path": "."}]}), encoding="utf-8")
    monkeypatch.setattr(
        holodeck_server,
        "load_live_worktree_entries",
        lambda repo_root: [{"path": str(worktree), "branch": "feature/demo", "missing": False}],
    )
    called = {}

    def fake_focus(path, title_candidates, document_roots):
        called["path"] = path
        called["title_candidates"] = title_candidates
        called["document_roots"] = document_roots
        return FakeActivationResult()

    monkeypatch.setattr(holodeck_server, "invoke_cursor_focus", fake_focus)
    response = api_client().post("/api/focus", headers=BASE_HEADERS, json=focus_body(worktree))

    assert response.status_code == 200
    assert response.json() == {"ok": True, "target": "cursor", "status": "focused", "matched_by": "title"}
    assert called["path"] == worktree.resolve()
    assert called["title_candidates"] == ["codex-feature-demo"]
    assert called["document_roots"] == [worktree.resolve()]


def test_cursor_title_candidates_use_folder_without_workspace_file(tmp_path):
    worktree = tmp_path / "feature-demo"
    worktree.mkdir()

    assert holodeck_server.cursor_title_candidates(
        {"path": str(worktree), "branch": "feature/demo"}
    ) == ["feature-demo"]


def test_cursor_title_candidates_omit_repeated_basename(tmp_path, monkeypatch):
    main = tmp_path / "main" / "fof-mono"
    worktree = tmp_path / "worktrees" / "0013" / "fof-mono"
    main.mkdir(parents=True)
    worktree.mkdir(parents=True)
    entries = [
        {"path": str(main), "branch": "main", "missing": False},
        {"path": str(worktree), "branch": "feature/demo", "missing": False},
    ]
    monkeypatch.setattr(
        holodeck_server.worktrees_collector,
        "worktree_display_name",
        lambda path, branch: Path(path).name,
    )

    assert holodeck_server.cursor_title_candidates(entries[0], entries) == []
    assert holodeck_server.cursor_title_candidates(entries[1], entries) == []


def test_cursor_title_candidates_keep_unique_workspace_name(tmp_path, monkeypatch):
    main = tmp_path / "main" / "fof-mono"
    worktree = tmp_path / "worktrees" / "0013" / "fof-mono"
    main.mkdir(parents=True)
    worktree.mkdir(parents=True)
    entries = [
        {"path": str(main), "branch": "main", "missing": False},
        {"path": str(worktree), "branch": "feature/demo", "missing": False},
    ]
    monkeypatch.setattr(
        holodeck_server.worktrees_collector,
        "worktree_display_name",
        lambda path, branch: "codex-feature-demo" if branch == "feature/demo" else Path(path).name,
    )

    assert holodeck_server.cursor_title_candidates(entries[0], entries) == []
    assert holodeck_server.cursor_title_candidates(entries[1], entries) == ["codex-feature-demo"]


def test_cursor_document_roots_include_workspace_folders(tmp_path):
    worktree = tmp_path / "feature-demo"
    shared = tmp_path / "shared"
    worktree.mkdir()
    shared.mkdir()
    workspace = worktree / "codex-feature-demo.code-workspace"
    workspace.write_text(
        json.dumps({"folders": [{"path": "."}, {"path": "../shared"}]}),
        encoding="utf-8",
    )

    roots = holodeck_server.cursor_document_roots(
        {"path": str(worktree), "branch": "feature/demo", "missing": False}
    )

    assert roots == [worktree.resolve(), shared.resolve()]


def test_focus_rejects_path_outside_live_worktrees(tmp_path, monkeypatch):
    requested = tmp_path / "not-a-worktree"
    requested.mkdir()
    monkeypatch.setattr(holodeck_server, "load_live_worktree_entries", lambda repo_root: [])
    monkeypatch.setattr(
        holodeck_server,
        "invoke_cursor_focus",
        lambda *args, **kwargs: pytest.fail("automation must not run"),
    )

    response = api_client().post("/api/focus", headers=BASE_HEADERS, json=focus_body(requested))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden_client"


@pytest.mark.parametrize(
    ("code", "status"),
    [
        ("invalid_request", 400),
        ("app_not_running", 404),
        ("target_not_found", 404),
        ("ambiguous_match", 409),
        ("unsupported_platform", 501),
        ("automation_failed", 502),
        ("permission_required", 503),
        ("automation_timeout", 504),
    ],
)
def test_focus_maps_activation_errors(code, status, tmp_path, monkeypatch):
    def fail(requested_path):
        raise FakeActivationError(code)

    monkeypatch.setattr(holodeck_server, "execute_cursor_focus", fail)
    response = api_client().post("/api/focus", headers=BASE_HEADERS, json=focus_body(tmp_path))

    assert response.status_code == status
    assert response.json() == {"ok": False, "error": {"code": code, "message": "safe activation error"}}


@pytest.mark.parametrize(
    "body",
    [
        None,
        [],
        {},
        {"target": "chrome", "matcher": {"worktree_path": "/tmp/demo"}},
        {"target": "cursor", "matcher": {}},
        {"target": "cursor", "matcher": {"worktree_path": "relative/path"}},
        {"target": "cursor", "matcher": {"worktree_path": "/tmp/demo", "title": "demo"}},
        {"target": "cursor", "matcher": {"worktree_path": "/tmp/demo"}, "command": "open"},
    ],
)
def test_focus_rejects_invalid_schema(body, monkeypatch):
    monkeypatch.setattr(
        holodeck_server,
        "execute_cursor_focus",
        lambda path: pytest.fail("automation must not run"),
    )
    response = api_client().post("/api/focus", headers=BASE_HEADERS, json=body)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_focus_rejects_malformed_json():
    response = api_client().post(
        "/api/focus",
        headers={**BASE_HEADERS, "Content-Type": "application/json"},
        content="{",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


@pytest.mark.parametrize(
    "headers",
    [
        {key: value for key, value in BASE_HEADERS.items() if key != "X-Holodeck-Action"},
        {**BASE_HEADERS, "Content-Type": "text/plain"},
    ],
)
def test_focus_requires_json_and_custom_header(headers):
    response = api_client().post("/api/focus", headers=headers, content="{}")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


@pytest.mark.parametrize(
    "headers",
    [
        {**BASE_HEADERS, "Host": "example.test"},
        {**BASE_HEADERS, "Origin": "http://example.test"},
        {**BASE_HEADERS, "Sec-Fetch-Site": "cross-site"},
    ],
)
def test_focus_rejects_foreign_host_origin_and_fetch_site(headers):
    response = api_client().post("/api/focus", headers=headers, json=focus_body("/tmp/demo"))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden_client"


def test_focus_rejects_nonloopback_peer():
    response = api_client("192.0.2.10").post(
        "/api/focus",
        headers=BASE_HEADERS,
        json=focus_body("/tmp/demo"),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden_client"


def test_focus_returns_busy_without_running_automation(tmp_path, monkeypatch):
    monkeypatch.setattr(
        holodeck_server,
        "execute_cursor_focus",
        lambda path: pytest.fail("automation must not run"),
    )
    assert holodeck_server.FOCUS_LOCK.acquire(blocking=False)
    try:
        response = api_client().post("/api/focus", headers=BASE_HEADERS, json=focus_body(tmp_path))
    finally:
        holodeck_server.FOCUS_LOCK.release()

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "focus_busy"


def test_focus_maps_unexpected_adapter_exception_to_safe_error(tmp_path, monkeypatch):
    def fail(requested_path):
        raise RuntimeError("raw private automation output")

    monkeypatch.setattr(holodeck_server, "execute_cursor_focus", fail)
    response = api_client().post("/api/focus", headers=BASE_HEADERS, json=focus_body(tmp_path))

    assert response.status_code == 502
    assert response.json() == {
        "ok": False,
        "error": {"code": "automation_failed", "message": "macOS could not focus the Cursor window."},
    }


### Regression: server.py launch must still load macOS focus
def test_server_keeps_repo_root_on_sys_path():
    assert str(holodeck_server.ROOT.resolve()) in {str(Path(entry).resolve()) for entry in sys.path if entry}


def test_invoke_cursor_focus_source_loads_module_by_file_path():
    source = inspect.getsource(holodeck_server.invoke_cursor_focus)
    assert "from apps.mac import window_activation" not in source
    assert "spec_from_file_location" in source
    assert "apps/mac/window_activation.py" in source


def test_regression_apps_mac_attribute_import_fails_for_hollow_namespace(monkeypatch):
    """Old go-to-window code used `from apps.mac import window_activation`, which breaks
    when apps.mac is present as a hollow namespace (the server.py launch failure mode)."""
    hollow_apps = types.ModuleType("apps")
    hollow_apps.__path__ = []
    hollow_mac = types.ModuleType("apps.mac")
    hollow_mac.__path__ = []
    monkeypatch.setitem(sys.modules, "apps", hollow_apps)
    monkeypatch.setitem(sys.modules, "apps.mac", hollow_mac)
    monkeypatch.delitem(sys.modules, "apps.mac.window_activation", raising=False)

    with pytest.raises(ImportError):
        from apps.mac import window_activation  # noqa: F401


def test_invoke_cursor_focus_succeeds_when_apps_mac_package_import_is_broken(monkeypatch):
    """File-path loading must keep focus working even if the old package import cannot."""
    hollow_apps = types.ModuleType("apps")
    hollow_apps.__path__ = []
    hollow_mac = types.ModuleType("apps.mac")
    hollow_mac.__path__ = []
    monkeypatch.setitem(sys.modules, "apps", hollow_apps)
    monkeypatch.setitem(sys.modules, "apps.mac", hollow_mac)
    monkeypatch.delitem(sys.modules, "apps.mac.window_activation", raising=False)

    recorded = {}

    class FakeLoader:
        def exec_module(self, module):
            def focus_cursor_window(path, title_candidates=None, document_roots=None, timeout=15):
                recorded["call"] = {
                    "path": path,
                    "title_candidates": title_candidates,
                    "document_roots": document_roots,
                    "timeout": timeout,
                }
                return FakeActivationResult()

            module.focus_cursor_window = focus_cursor_window

    class FakeSpec:
        def __init__(self, name, location):
            self.name = name
            self.loader = FakeLoader()

    def fake_spec_from_file_location(name, location, *args, **kwargs):
        recorded["name"] = name
        recorded["location"] = Path(location).resolve()
        return FakeSpec(name, location)

    def fake_module_from_spec(spec):
        return types.ModuleType(spec.name)

    monkeypatch.setattr(importlib.util, "spec_from_file_location", fake_spec_from_file_location)
    monkeypatch.setattr(importlib.util, "module_from_spec", fake_module_from_spec)

    with pytest.raises(ImportError):
        from apps.mac import window_activation  # noqa: F401

    worktree = Path("/tmp/fof-website-focus-regression")
    result = holodeck_server.invoke_cursor_focus(worktree, ["fof-website"], [worktree])

    assert recorded["name"] == "holodeck_window_activation"
    assert recorded["location"] == (holodeck_server.ROOT / "apps/mac/window_activation.py").resolve()
    assert recorded["call"] == {
        "path": str(worktree),
        "title_candidates": ("fof-website",),
        "document_roots": (str(worktree),),
        "timeout": 15,
    }
    assert result.to_dict()["ok"] is True


def test_invoke_cursor_focus_loads_real_module_under_server_script_sys_path():
    """Simulate `python apps/holodeck/server.py` sys.path and ensure the focus module loads."""
    repo = holodeck_server.ROOT.resolve()
    script = r"""
import importlib.util
import sys
from pathlib import Path

repo = Path(%r)
script_dir = repo / "apps/holodeck"
# Match script launch: script dir first, repo root absent until server inserts it.
sys.path = [str(script_dir)] + [
    entry for entry in sys.path
    if entry and Path(entry).resolve() != repo and Path(entry).resolve() != script_dir
]
sys.path.insert(0, str(repo))
module_path = repo / "apps/mac/window_activation.py"
spec = importlib.util.spec_from_file_location("holodeck_window_activation", module_path)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert callable(module.focus_cursor_window)
# The old attribute import is unsafe under this launch shape; file load is required.
try:
    from apps.mac import window_activation as package_import
except ImportError:
    package_import = None
if package_import is not None:
    assert package_import.__file__ == str(module_path)
print("OK")
""" % (str(repo),)
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert completed.stdout.strip().endswith("OK")


def test_invoke_cursor_focus_errors_when_activation_module_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(holodeck_server, "ROOT", tmp_path)

    class FakeSpec:
        loader = None

    monkeypatch.setattr(
        importlib.util,
        "spec_from_file_location",
        lambda name, location, *args, **kwargs: FakeSpec(),
    )
    with pytest.raises(holodeck_server.FocusRequestError) as exc_info:
        holodeck_server.invoke_cursor_focus(tmp_path, [], [tmp_path])
    assert exc_info.value.code == "automation_failed"
    assert "could not be loaded" in exc_info.value.message
