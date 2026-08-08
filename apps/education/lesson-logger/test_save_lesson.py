#!/usr/bin/env python3
# Unit tests for the lesson-logger save script (the deterministic persist step).
# Run: .venv/bin/pytest apps/education/lesson-logger/test_save_lesson.py -v
#   (or any venv with pytest installed — openai is NOT required)
import importlib.util
import base64
import json
import os
import sys
import tempfile
import types
from datetime import datetime
from zoneinfo import ZoneInfo

_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "scripts", "save_lesson.py",
)
def _load():
    fake_extract = types.ModuleType("extract_lesson")
    fake_extract.EXTRACTOR_VERSION = "test-1.0.0"
    sys.modules["extract_lesson"] = fake_extract
    spec = importlib.util.spec_from_file_location("save_lesson", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
def test_defaults_student_to_k1():
    mod = _load()
    now = datetime(2026, 6, 6, 18, 0, tzinfo=ZoneInfo("America/Los_Angeles"))
    entry, warns = mod.build_entry({"subject": "math", "duration": 32, "notes": "fractions", "transcript": "test"}, now=now)
    assert entry["students"] == ["Kid1"], entry
    assert entry["subject"] == "Math", entry
    assert entry["duration"] == 32, entry
    assert entry["date"] == "2026-06-06", entry
    assert any("defaulted to Kid1" in w for w in warns), warns
def test_explicit_students_and_long_duration():
    mod = _load()
    entry, warns = mod.build_entry({"students": ["Kid1", "Mia", "Kid1"], "subject": "Science", "duration": 120, "transcript": "test"})
    assert entry["students"] == ["Kid1", "Mia"], entry
    assert entry["duration"] == 120, entry
    assert not any("defaulted" in w for w in warns)
def test_duration_floor_and_ceiling():
    mod = _load()
    try:
        mod.build_entry({"subject": "Math", "duration": 0, "transcript": "test"})
        assert False, "expected ValueError for duration 0"
    except ValueError:
        pass
    entry, warns = mod.build_entry({"subject": "Math", "duration": 5000, "transcript": "test"})
    assert entry["duration"] == 1440, entry
    assert any("clamped" in w for w in warns), warns
def test_custom_subject_warns():
    mod = _load()
    entry, warns = mod.build_entry({"subject": "History", "duration": 45, "transcript": "test"})
    assert entry["subject"] == "History"
    assert any("custom subject" in w for w in warns), warns
def test_requires_subject_and_duration():
    mod = _load()
    for bad in ({"duration": 30, "transcript": "t"}, {"subject": "Math", "transcript": "t"}, {"subject": "Math", "duration": "", "transcript": "t"}):
        try:
            mod.build_entry(bad)
            assert False, f"expected ValueError for {bad}"
        except ValueError:
            pass
def test_save_writes_matching_file():
    mod = _load()
    entry, _ = mod.build_entry({"students": ["Kid1"], "subject": "Reading", "duration": 15, "date": "2026-06-06", "transcript": "test"})
    with tempfile.TemporaryDirectory() as d:
        path = mod.save_entry(entry, d)
        assert os.path.isfile(path) and path.endswith(".json")
        loaded = json.load(open(path))
        assert loaded["subject"] == "Reading" and loaded["duration"] == 15
        assert loaded["students"] == ["Kid1"]
        assert set(loaded) >= {"id", "date", "students", "subject", "duration", "notes", "createdAt"}
def test_notify_dashboard_sync_skips_when_unconfigured(monkeypatch):
    mod = _load()
    monkeypatch.delenv("LESSON_DASH_SYNC_URL", raising=False)
    assert mod.notify_dashboard_sync() is None
def test_notify_dashboard_sync_posts_with_basic_auth(monkeypatch):
    mod = _load()
    seen = {}
    class FakeResponse:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def getcode(self):
            return self.status
    def fake_urlopen(req, timeout):
        seen["url"] = req.full_url
        seen["method"] = req.get_method()
        seen["auth"] = req.get_header("Authorization")
        seen["timeout"] = timeout
        return FakeResponse()
    monkeypatch.setenv("LESSON_DASH_SYNC_URL", "https://example.test/internal/sync")
    monkeypatch.setenv("LESSON_DASH_SYNC_USER", "randy")
    monkeypatch.setenv("LESSON_DASH_SYNC_PASSWORD", "secret")
    monkeypatch.setenv("LESSON_DASH_SYNC_TIMEOUT", "3")
    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    assert mod.notify_dashboard_sync() == "dashboard sync requested"
    assert seen["url"] == "https://example.test/internal/sync"
    assert seen["method"] == "POST"
    assert seen["timeout"] == 3.0
    expected = base64.b64encode(b"randy:secret").decode("ascii")
    assert seen["auth"] == f"Basic {expected}"
if __name__ == "__main__":
    test_defaults_student_to_k1()
    test_explicit_students_and_long_duration()
    test_duration_floor_and_ceiling()
    test_custom_subject_warns()
    test_requires_subject_and_duration()
    test_save_writes_matching_file()
    print("ok")
