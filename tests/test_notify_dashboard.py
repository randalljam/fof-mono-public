#!/usr/bin/env python3
import importlib.util
import os

_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills", "family", "schedule-coordinator", "scripts", "notify_dashboard.py",
)
def _load():
    spec = importlib.util.spec_from_file_location("notify_dashboard", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def _clear_env(monkeypatch):
    for v in ("DASH_SYNC_URL", "LESSON_DASH_SYNC_URL", "DASH_SYNC_USER",
              "LESSON_DASH_SYNC_USER", "DASH_SYNC_PASSWORD", "LESSON_DASH_SYNC_PASSWORD",
              "DASH_SYNC_TIMEOUT", "LESSON_DASH_SYNC_TIMEOUT"):
        monkeypatch.delenv(v, raising=False)

def test_noop_without_url(monkeypatch):
    mod = _load()
    _clear_env(monkeypatch)
    called = []
    monkeypatch.setattr(mod.urllib.request, "urlopen", lambda *a, **k: called.append(a))
    assert mod.main() == 0
    assert called == []  # never tried to POST

def test_posts_with_basic_auth(monkeypatch):
    mod = _load()
    _clear_env(monkeypatch)
    monkeypatch.setenv("DASH_SYNC_URL", "http://dash.test/internal/sync")
    monkeypatch.setenv("DASH_SYNC_USER", "randy")
    monkeypatch.setenv("DASH_SYNC_PASSWORD", "pw")
    captured = {}
    class FakeResp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["auth"] = req.get_header("Authorization")
        return FakeResp()
    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    assert mod.main() == 0
    assert captured["url"] == "http://dash.test/internal/sync"
    assert captured["method"] == "POST"
    assert captured["auth"].startswith("Basic ")

def test_falls_back_to_lesson_env(monkeypatch):
    mod = _load()
    _clear_env(monkeypatch)
    monkeypatch.setenv("LESSON_DASH_SYNC_URL", "http://dash.test/internal/sync")
    captured = {}
    class FakeResp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        return FakeResp()
    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    assert mod.main() == 0
    assert captured["url"] == "http://dash.test/internal/sync"

def test_swallows_errors(monkeypatch):
    mod = _load()
    _clear_env(monkeypatch)
    monkeypatch.setenv("DASH_SYNC_URL", "http://dash.test/internal/sync")
    def boom(*a, **k):
        raise OSError("connection refused")
    monkeypatch.setattr(mod.urllib.request, "urlopen", boom)
    assert mod.main() == 0  # best-effort: errors never propagate
