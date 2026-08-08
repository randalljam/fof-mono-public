import io
import json
import urllib.error

import pytest
from fastapi.testclient import TestClient

from apps.holodeck import server as holodeck_server

### Fixtures
class FakeResponse:
    def __init__(self, status=200):
        self.status = status
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, traceback):
        return False
    def read(self):
        return b"{}"
@pytest.fixture(autouse=True)
def clear_cloud_status_cache():
    with holodeck_server.CLOUD_STATUS_LOCK:
        holodeck_server.CLOUD_STATUS_CACHE.clear()
    yield
    with holodeck_server.CLOUD_STATUS_LOCK:
        holodeck_server.CLOUD_STATUS_CACHE.clear()

### Helpers
def write_codex_auth(home, token="codex-secret"):
    auth_dir = home / ".codex"
    auth_dir.mkdir()
    (auth_dir / "auth.json").write_text(json.dumps({"tokens": {"access_token": token}}), encoding="utf-8")
def write_claude_export(root, name="2026-07-19_120000_claude-cloud.json"):
    # Use the per-root legacy import dir so pytest tmp_path siblings do not share exports.
    export_dir = root / "apps/holodeck/data/cloud_claude_import"
    export_dir.mkdir(parents=True)
    path = export_dir / name
    path.write_text(json.dumps({"sessions": []}), encoding="utf-8")
    return path
def request_header(request, name):
    for key, value in dict(request.header_items()).items():
        if key.lower() == name.lower():
            return value
    return request.get_header(name) or request.headers.get(name) or request.unredirected_hdrs.get(name)
def raise_http_status(status):
    raise urllib.error.HTTPError("https://example.test", status, "error", {}, io.BytesIO(b""))
def source_by_key(sources, key):
    return next(source for source in sources if source["key"] == key)

### Tests
def test_cloud_status_endpoint_returns_safe_sources(monkeypatch):
    monkeypatch.setattr(
        holodeck_server,
        "cloud_status_sources",
        lambda: [
            {"key": "codex-cloud", "state": "ok", "detail": "Codex cloud token is valid."},
            {"key": "claude-cloud", "state": "absent", "detail": holodeck_server.CLAUDE_EXPORT_GUIDANCE},
        ],
    )
    response = TestClient(holodeck_server.app).get("/api/cloud-status")
    assert response.status_code == 200
    assert response.json()["sources"][0]["key"] == "codex-cloud"
    assert response.json()["sources"][1]["state"] == "absent"
def test_cloud_status_absent_without_credentials(monkeypatch, tmp_path):
    monkeypatch.setattr(holodeck_server.turns_cloud_claude, "PLAYWRIGHT_PROFILE", tmp_path / "missing-profile")
    sources = holodeck_server.cloud_status_sources(home=tmp_path, root=tmp_path, env={}, now=1000)
    assert source_by_key(sources, "codex-cloud")["state"] == "absent"
    assert source_by_key(sources, "claude-cloud")["state"] == "absent"
    assert "browser export" in source_by_key(sources, "claude-cloud")["detail"].lower()
def test_codex_cloud_status_ok_uses_bearer_without_echoing_secret(tmp_path):
    write_codex_auth(tmp_path)
    requests = []
    def fake_urlopen(request, timeout=20):
        requests.append(request)
        return FakeResponse(200)
    source = holodeck_server.codex_cloud_status(urlopen=fake_urlopen, home=tmp_path)
    assert source["state"] == "ok"
    assert request_header(requests[0], "Authorization") == "Bearer codex-secret"
    assert "codex-secret" not in json.dumps(source)
def test_codex_cloud_status_expired_on_401(tmp_path):
    write_codex_auth(tmp_path)
    source = holodeck_server.codex_cloud_status(urlopen=lambda request, timeout=20: raise_http_status(401), home=tmp_path)
    assert source["state"] == "expired"
    assert "codex login" in source["detail"]
def test_claude_cloud_status_ok_when_export_present(tmp_path):
    path = write_claude_export(tmp_path)
    source = holodeck_server.claude_cloud_status(root=tmp_path, env={})
    assert source["state"] == "ok"
    assert path.name in source["detail"]
    assert "export ready" in source["detail"].lower()
def test_claude_cloud_status_ok_reads_dotenv_without_echoing_secret(tmp_path):
    (tmp_path / ".env").write_text('CLAUDE_AI_SESSION_KEY="sessionKey=claude-secret"\n', encoding="utf-8")
    requests = []
    def fake_urlopen(request, timeout=20):
        requests.append(request)
        return FakeResponse(200)
    source = holodeck_server.claude_cloud_status(urlopen=fake_urlopen, root=tmp_path, env={})
    assert source["state"] == "ok"
    assert request_header(requests[0], "Cookie") == "sessionKey=claude-secret"
    assert request_header(requests[0], "anthropic-version") == holodeck_server.CLAUDE_CLOUD_API_VERSION
    assert "claude-secret" not in json.dumps(source)
def test_claude_cloud_status_export_guidance_on_401(tmp_path):
    (tmp_path / ".env").write_text("CLAUDE_AI_SESSION_KEY=claude-secret\n", encoding="utf-8")
    source = holodeck_server.claude_cloud_status(urlopen=lambda request, timeout=20: raise_http_status(401), root=tmp_path, env={})
    assert source["state"] == "expired"
    assert "browser export" in source["detail"].lower()
    assert "claude.ai/code" in source["detail"]
def test_claude_cloud_status_uses_playwright_profile(monkeypatch, tmp_path):
    profile = tmp_path / "profile"
    profile.mkdir()
    calls = []
    def fake_playwright_get(path, params=None):
        calls.append((path, tuple(params or [])))
        return {"data": []}
    monkeypatch.setattr(holodeck_server.turns_cloud_claude, "PLAYWRIGHT_PROFILE", profile)
    monkeypatch.setattr(holodeck_server.turns_cloud_claude, "playwright_available", lambda: True)
    monkeypatch.setattr(holodeck_server.turns_cloud_claude, "playwright_api_get", fake_playwright_get)
    source = holodeck_server.claude_cloud_status(root=tmp_path, env={})
    assert source["state"] == "ok"
    assert calls == [("/v1/code/sessions", (("statuses", "active"), ("limit", "1")))]
def test_claude_cloud_status_export_guidance_when_playwright_needs_login(monkeypatch, tmp_path):
    profile = tmp_path / "profile"
    profile.mkdir()
    def fake_playwright_get(path, params=None):
        raise holodeck_server.turns_cloud_claude.CloudClaudeAuthError(holodeck_server.turns_cloud_claude.AUTH_LOGIN_NOTE)
    monkeypatch.setattr(holodeck_server.turns_cloud_claude, "PLAYWRIGHT_PROFILE", profile)
    monkeypatch.setattr(holodeck_server.turns_cloud_claude, "playwright_available", lambda: True)
    monkeypatch.setattr(holodeck_server.turns_cloud_claude, "playwright_api_get", fake_playwright_get)
    source = holodeck_server.claude_cloud_status(root=tmp_path, env={})
    assert source["state"] == "absent"
    assert "browser export" in source["detail"].lower()
def test_cloud_status_cache_avoids_repeated_probe(tmp_path):
    write_codex_auth(tmp_path)
    calls = []
    def fake_urlopen(request, timeout=20):
        calls.append(request)
        return FakeResponse(200)
    first = holodeck_server.cloud_status_sources(urlopen=fake_urlopen, home=tmp_path, root=tmp_path, env={}, now=1000)
    second = holodeck_server.cloud_status_sources(urlopen=fake_urlopen, home=tmp_path, root=tmp_path, env={}, now=1020)
    assert source_by_key(first, "codex-cloud")["state"] == "ok"
    assert source_by_key(second, "codex-cloud")["state"] == "ok"
    assert len(calls) == 1
def test_claude_export_snippet_file_exists():
    assert holodeck_server.CLAUDE_EXPORT_SNIPPET_PATH.is_file()
    text = holodeck_server.CLAUDE_EXPORT_SNIPPET_PATH.read_text(encoding="utf-8")
    assert "holodeck-claude-cloud-export.json" in text
    assert "claude.ai" in text
