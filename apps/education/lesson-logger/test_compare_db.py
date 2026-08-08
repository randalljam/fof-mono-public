#!/usr/bin/env python3
# Unit tests for compare_db.py — the Hermes/dashboard lessons-DB diff utility.
# Covers the pure logic (no Fly/network): student formatting, DB reads, the
# compare facts (including same-id-but-differing-rows), and short/long output.
# Run: .venv/bin/pytest apps/education/lesson-logger/test_compare_db.py -v
#   (or, stdlib only:) python3 apps/education/lesson-logger/test_compare_db.py
import importlib.util
import io
import json
import os
import sqlite3
import tempfile
from contextlib import redirect_stdout

_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "scripts", "compare_db.py",
)
def _load():
    spec = importlib.util.spec_from_file_location("compare_db", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
def _make_db(path, rows):
    """Create a minimal lessons DB (the columns compare_db reads) and insert rows.

    Each row is (id, date, students_list, duration, subject).
    """
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE entries (id TEXT PRIMARY KEY, date TEXT, students TEXT,"
        " duration INTEGER, subject TEXT)"
    )
    for entry_id, date, students, duration, subject in rows:
        conn.execute(
            "INSERT INTO entries (id, date, students, duration, subject) VALUES (?, ?, ?, ?, ?)",
            (entry_id, date, json.dumps(students), duration, subject),
        )
    conn.commit()
    conn.close()

### _format_students
def test_format_students():
    mod = _load()
    assert mod._format_students(json.dumps(["Kid1", "Mia"])) == "Kid1, Mia"
    assert mod._format_students(json.dumps([])) == "(none)"
    assert mod._format_students(None) == "(none)"
    assert mod._format_students("") == "(none)"
    # malformed JSON falls back to the raw string rather than crashing
    assert mod._format_students("not json") == "not json"
    # a non-list JSON value is stringified
    assert mod._format_students(json.dumps("Kid1")) == "Kid1"

### _load_entries
def test_load_entries_reads_rows():
    mod = _load()
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "lessons.db")
        _make_db(db, [
            ("b", "2026-06-02", ["Mia"], 20, "Art"),
            ("a", "2026-06-01", ["Kid1"], 30, "Math"),
        ])
        entries = mod._load_entries(db)
        assert set(entries) == {"a", "b"}, entries
        assert entries["a"]["subject"] == "Math"
        assert entries["a"]["duration"] == 30
def test_load_entries_no_table_raises():
    mod = _load()
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "empty.db")
        sqlite3.connect(db).close()  # valid DB, but no 'entries' table
        try:
            mod._load_entries(db)
        except SystemExit as exc:
            assert "no entries table" in str(exc), exc
        else:
            raise AssertionError("expected SystemExit for missing entries table")

### _compare
def test_compare_identical():
    mod = _load()
    a = {"x": {"id": "x", "duration": 30}, "y": {"id": "y", "duration": 15}}
    b = {"x": {"id": "x", "duration": 30}, "y": {"id": "y", "duration": 15}}
    result = mod._compare(a, b)
    assert result["same"] is True, result
    assert result["hermes_count"] == 2
    assert result["only_hermes"] == [] and result["only_dashboard"] == []
    assert result["differing"] == []
def test_compare_missing_on_each_side():
    mod = _load()
    hermes = {"a": {"id": "a"}, "b": {"id": "b"}}
    dashboard = {"a": {"id": "a"}, "c": {"id": "c"}}
    result = mod._compare(hermes, dashboard)
    assert result["same"] is False
    assert result["only_hermes"] == ["b"]
    assert result["only_dashboard"] == ["c"]
    assert result["differing"] == []
def test_compare_same_ids_differing_rows():
    # The key regression guard: matching id sets but a row edited on one side
    # must NOT be reported as SAME.
    mod = _load()
    hermes = {"a": {"id": "a", "duration": 30}}
    dashboard = {"a": {"id": "a", "duration": 45}}
    result = mod._compare(hermes, dashboard)
    assert result["same"] is False, result
    assert result["only_hermes"] == [] and result["only_dashboard"] == []
    assert result["differing"] == ["a"], result

### run_compare output
def _run_compare_output(mod, hermes_rows, dashboard_rows, long_mode=False):
    with tempfile.TemporaryDirectory() as d:
        h = os.path.join(d, "hermes.db")
        b = os.path.join(d, "dashboard.db")
        _make_db(h, hermes_rows)
        _make_db(b, dashboard_rows)
        buf = io.StringIO()
        with redirect_stdout(buf):
            mod.run_compare(h, b, long_mode=long_mode)
        return buf.getvalue()
def test_run_compare_same_prints_check():
    mod = _load()
    rows = [("a", "2026-06-01", ["Kid1"], 30, "Math")]
    out = _run_compare_output(mod, rows, rows)
    assert "✅ SAME" in out, out
    assert "1 entries on Hermes and dashboard" in out, out
def test_run_compare_differing_rows_flagged():
    mod = _load()
    hermes = [("a", "2026-06-01", ["Kid1"], 30, "Math")]
    dashboard = [("a", "2026-06-01", ["Kid1"], 45, "Math")]
    out = _run_compare_output(mod, hermes, dashboard)
    assert "❌ DIFFER" in out, out
    assert "Differing entries (1)" in out, out
    assert "hermes:" in out and "dashboard:" in out, out
def test_run_compare_long_lists_all_then_summary():
    mod = _load()
    rows = [
        ("a", "2026-06-01", ["Kid1"], 30, "Math"),
        ("b", "2026-06-02", ["Mia"], 20, "Art"),
    ]
    out = _run_compare_output(mod, rows, rows, long_mode=True)
    assert "Hermes entries (2)" in out, out
    assert "Dashboard entries (2)" in out, out
    # summary comes last in long mode
    assert out.index("=== Summary ===") > out.index("Hermes entries (2)"), out
    assert "✅ SAME" in out, out

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all ok")
