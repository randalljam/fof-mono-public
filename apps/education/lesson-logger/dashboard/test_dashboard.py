#!/usr/bin/env python3
# Tests for the lesson-logger dashboard.
# Run: cd apps/education/lesson-logger/dashboard && .venv/bin/pytest test_dashboard.py -v
import base64
import os
import shutil
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.pop("LESSONS_DB", None)
os.environ.pop("HERMES_LESSON_DB_URL", None)

from app import (
    week_range, month_range, learning_year_range, format_range_label,
    prev_range, next_range,
    compute_summary, compute_subject_breakdown, compute_consistency,
    compute_curricula_breakdown,
    query_entries, get_all_students, get_all_subjects,
    app, SUBJECT_COLORS, USERS, _load_users, get_db,
    DATA_DIR, PREFS_DB,
)
from httpx import ASGITransport, AsyncClient
import pytest
import sync_db

### Date helpers
def test_week_range_monday_start():
    start, end = week_range(date(2026, 6, 4))  # Wednesday
    assert start == date(2026, 6, 1)  # Monday
    assert end == date(2026, 6, 7)    # Sunday
def test_week_range_monday():
    start, end = week_range(date(2026, 6, 1))  # Monday
    assert start == date(2026, 6, 1)
    assert end == date(2026, 6, 7)
def test_week_range_sunday():
    start, end = week_range(date(2026, 6, 7))  # Sunday
    assert start == date(2026, 6, 1)
    assert end == date(2026, 6, 7)
def test_month_range():
    start, end = month_range(date(2026, 5, 15))
    assert start == date(2026, 5, 1)
    assert end == date(2026, 5, 31)
def test_month_range_feb():
    start, end = month_range(date(2026, 2, 10))
    assert start == date(2026, 2, 1)
    assert end == date(2026, 2, 28)
def test_month_range_december():
    start, end = month_range(date(2026, 12, 25))
    assert start == date(2026, 12, 1)
    assert end == date(2026, 12, 31)
def test_learning_year_sept_onwards():
    start, end = learning_year_range(date(2026, 10, 15))
    assert start == date(2026, 9, 1)
    assert end == date(2027, 8, 30)
def test_learning_year_before_sept():
    start, end = learning_year_range(date(2026, 3, 15))
    assert start == date(2025, 9, 1)
    assert end == date(2026, 8, 30)
def test_format_range_week():
    label = format_range_label("week", date(2026, 6, 1), date(2026, 6, 7))
    assert "Jun" in label and "2026" in label
def test_format_range_month():
    label = format_range_label("month", date(2026, 5, 1), date(2026, 5, 31))
    assert label == "May 2026"
def test_format_range_year():
    label = format_range_label("year", date(2025, 9, 1), date(2026, 8, 30))
    assert "2025" in label
def test_prev_next_week():
    ref = date(2026, 6, 1)
    assert prev_range("week", ref) == date(2026, 5, 25)
    assert next_range("week", ref) == date(2026, 6, 8)
def test_prev_next_month():
    ref = date(2026, 5, 1)
    assert prev_range("month", ref) == date(2026, 4, 1)
    assert next_range("month", ref) == date(2026, 6, 1)

### Aggregation
SAMPLE_ENTRIES = [
    {"date": "2026-06-02", "subject": "Math", "duration": 30, "curricula": "Beast Academy", "notes": "fractions"},
    {"date": "2026-06-02", "subject": "Reading", "duration": 20, "curricula": "Charlotte's Web", "notes": ""},
    {"date": "2026-06-03", "subject": "Math", "duration": 25, "curricula": "Beast Academy", "notes": "geometry"},
    {"date": "2026-06-04", "subject": "Art", "duration": 45, "curricula": "", "notes": "painting"},
    {"date": "2026-06-04", "subject": "Science", "duration": 30, "curricula": "Magic School Bus", "notes": "volcanoes"},
]
def test_compute_summary():
    s = compute_summary(SAMPLE_ENTRIES)
    assert s["total_minutes"] == 150
    assert s["total_sessions"] == 5
    assert s["subjects_covered"] == 4
    assert s["active_days"] == 3
    assert s["avg_per_active_day"] == 50
    assert s["time_display"] == "2h 30m"
def test_compute_summary_empty():
    s = compute_summary([])
    assert s["total_minutes"] == 0
    assert s["total_sessions"] == 0
    assert s["time_display"] == "0m"
    assert s["avg_per_active_day"] == 0
def test_compute_summary_under_hour():
    s = compute_summary([{"date": "2026-06-02", "subject": "Math", "duration": 45, "curricula": "", "notes": ""}])
    assert s["time_display"] == "45m"
def test_subject_breakdown_order():
    breakdown = compute_subject_breakdown(SAMPLE_ENTRIES)
    subjects = [b["subject"] for b in breakdown]
    assert subjects[0] == "Math"
    assert subjects[1] == "Reading"
    assert "Art" in subjects
    assert "Science" in subjects
def test_subject_breakdown_minutes():
    breakdown = compute_subject_breakdown(SAMPLE_ENTRIES)
    math = next(b for b in breakdown if b["subject"] == "Math")
    assert math["minutes"] == 55
    assert math["color"] == SUBJECT_COLORS["Math"]
def test_subject_breakdown_custom_subject():
    entries = SAMPLE_ENTRIES + [{"date": "2026-06-05", "subject": "Woodworking", "duration": 60, "curricula": "", "notes": ""}]
    breakdown = compute_subject_breakdown(entries)
    subjects = [b["subject"] for b in breakdown]
    assert "Woodworking" in subjects
    assert subjects.index("Woodworking") > subjects.index("Math")
def test_consistency_week():
    start = date(2026, 6, 1)
    end = date(2026, 6, 7)
    days = compute_consistency(SAMPLE_ENTRIES, "week", start, end)
    assert len(days) == 7
    assert days[0]["label"] == "Mon"
    assert days[6]["label"] == "Sun"
    assert days[0]["minutes"] == 0    # Monday Jun 1 - no entries
    assert days[1]["minutes"] == 50   # Tuesday Jun 2 - Math 30 + Reading 20
    assert days[2]["minutes"] == 25   # Wednesday Jun 3 - Math 25
    assert days[3]["minutes"] == 75   # Thursday Jun 4 - Art 45 + Science 30
def test_consistency_month():
    start = date(2026, 6, 1)
    end = date(2026, 6, 30)
    days = compute_consistency(SAMPLE_ENTRIES, "month", start, end)
    assert len(days) == 30
    assert days[0]["label"] == "1"
    assert days[1]["minutes"] == 50
def test_curricula_breakdown():
    breakdown = compute_curricula_breakdown(SAMPLE_ENTRIES)
    assert "Math" in breakdown
    math_items = breakdown["Math"]
    beast = next(c for c in math_items if c["curricula"] == "Beast Academy")
    assert beast["minutes"] == 55
    assert beast["sessions"] == 2
def test_curricula_breakdown_empty_curricula():
    breakdown = compute_curricula_breakdown(SAMPLE_ENTRIES)
    assert "Art" in breakdown
    art_items = breakdown["Art"]
    assert art_items[0]["curricula"] == "Not specified"

### Database queries (against the dev DB)
def test_get_all_students():
    students = get_all_students()
    assert "Fran" in students
    assert "Zap" in students
def test_get_all_subjects():
    subjects = get_all_subjects()
    assert "Math" in subjects
    assert "Reading" in subjects
    assert len(subjects) >= 6
def test_query_entries_fran_month():
    entries = query_entries("Fran", date(2026, 5, 1), date(2026, 5, 31))
    assert len(entries) > 0
    for e in entries:
        assert "Fran" in e["students"]
        assert e["date"] >= "2026-05-01"
        assert e["date"] <= "2026-05-31"
def test_query_entries_with_subject_filter():
    entries = query_entries("Fran", date(2026, 2, 1), date(2026, 6, 30), subject="Math")
    assert len(entries) > 0
    for e in entries:
        assert e["subject"] == "Math"
def test_query_entries_empty_range():
    entries = query_entries("Fran", date(2027, 1, 1), date(2027, 1, 7))
    assert entries == []

### Direct DB sync
def _create_test_db(path, value):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE marker (value TEXT)")
    conn.execute("CREATE TABLE entries (id TEXT PRIMARY KEY, students TEXT)")
    conn.execute("INSERT INTO marker VALUES (?)", (value,))
    conn.commit()
    conn.close()
def _read_marker(path):
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT value FROM marker").fetchone()[0]
    finally:
        conn.close()
def test_sync_from_hermes_replaces_with_valid_db(tmp_path, monkeypatch):
    source = tmp_path / "source.db"
    dest = tmp_path / "dest.db"
    _create_test_db(source, "fresh")
    monkeypatch.setenv("HERMES_LESSON_DB_URL", "http://hermes.test/lessons.db")
    monkeypatch.setenv("LESSONS_DB", str(dest))
    def fake_download(url, tmp):
        assert url == "http://hermes.test/lessons.db"
        shutil.copyfile(source, tmp)
    monkeypatch.setattr(sync_db, "_download_db", fake_download)
    assert sync_db.sync_from_hermes() is True
    assert _read_marker(dest) == "fresh"
def test_sync_from_hermes_preserves_cache_on_invalid_download(tmp_path, monkeypatch):
    dest = tmp_path / "dest.db"
    _create_test_db(dest, "cached")
    monkeypatch.setenv("HERMES_LESSON_DB_URL", "http://hermes.test/lessons.db")
    monkeypatch.setenv("LESSONS_DB", str(dest))
    def fake_download(url, tmp):
        with open(tmp, "wb") as f:
            f.write(b"not a sqlite db")
    monkeypatch.setattr(sync_db, "_download_db", fake_download)
    assert sync_db.sync_from_hermes() is False
    assert _read_marker(dest) == "cached"
def test_sync_from_hermes_rejects_db_without_entries_table(tmp_path, monkeypatch):
    source = tmp_path / "source.db"
    dest = tmp_path / "dest.db"
    _create_test_db(dest, "cached")
    conn = sqlite3.connect(source)
    conn.execute("CREATE TABLE other (value TEXT)")
    conn.commit()
    conn.close()
    monkeypatch.setenv("HERMES_LESSON_DB_URL", "http://hermes.test/lessons.db")
    monkeypatch.setenv("LESSONS_DB", str(dest))
    def fake_download(url, tmp):
        shutil.copyfile(source, tmp)
    monkeypatch.setattr(sync_db, "_download_db", fake_download)
    assert sync_db.sync_from_hermes() is False
    assert _read_marker(dest) == "cached"
def test_get_db_falls_back_when_configured_db_missing_entries(tmp_path, monkeypatch):
    bad_db = tmp_path / "bad.db"
    conn = sqlite3.connect(bad_db)
    conn.execute("CREATE TABLE other (value TEXT)")
    conn.commit()
    conn.close()
    monkeypatch.setenv("LESSONS_DB", str(bad_db))
    conn = get_db()
    try:
        rows = conn.execute("SELECT COUNT(*) FROM entries").fetchone()
        assert rows[0] > 0
    finally:
        conn.close()

### Auth config
def test_dev_password_flag_allows_username_password(monkeypatch):
    USERS.clear()
    monkeypatch.setenv("DASH_USER1", "randy")
    monkeypatch.setenv("DASH_PASS1", "not-randy")
    monkeypatch.setenv("DASH_USER2", "tl")
    monkeypatch.setenv("DASH_PASS2", "not-tl")
    monkeypatch.setenv("DASH_DEV_PASSWORDS", "true")
    _load_users()
    assert USERS["randy"] == "randy"
    assert USERS["tl"] == "tl"

### HTTP / Auth (end-to-end against dev DB)
def _auth_header(user, password):
    creds = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {creds}"}

@pytest.mark.anyio
async def test_unauthenticated_returns_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/")
        assert r.status_code == 401

@pytest.mark.anyio
async def test_authenticated_returns_200():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/", headers=_auth_header("randy", "randy"))
        assert r.status_code == 200
@pytest.mark.anyio
async def test_internal_sync_endpoint_triggers_sync(monkeypatch):
    calls = []
    monkeypatch.setattr(sync_db, "sync_from_hermes", lambda: calls.append("sync") or True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/internal/sync", headers=_auth_header("randy", "randy"))
        assert r.status_code == 200
        assert r.json() == {"ok": True}
        assert calls == ["sync"]
@pytest.mark.anyio
async def test_internal_sync_endpoint_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/internal/sync")
        assert r.status_code == 401
@pytest.mark.anyio
async def test_internal_sync_endpoint_reports_failure(monkeypatch):
    monkeypatch.setattr(sync_db, "sync_from_hermes", lambda: False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/internal/sync", headers=_auth_header("randy", "randy"))
        assert r.status_code == 503

@pytest.mark.anyio
async def test_wrong_password_returns_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/", headers=_auth_header("randy", "wrong"))
        assert r.status_code == 401

@pytest.mark.anyio
async def test_dashboard_renders_student_data():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(
            "/?mode=month&student=Fran&ref=2026-05-15",
            headers=_auth_header("randy", "randy"),
        )
        assert r.status_code == 200
        html = r.text
        assert "Fran" in html
        assert "Minutes by Subject" in html
        assert "Recent Lessons" in html
        assert "13h 20m" in html  # Fran's May total from dev DB

@pytest.mark.anyio
async def test_dashboard_week_mode():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(
            "/?mode=week&student=Fran&ref=2026-06-02",
            headers=_auth_header("randy", "randy"),
        )
        assert r.status_code == 200
        assert "Week of" in r.text
        assert "Daily Consistency" in r.text

@pytest.mark.anyio
async def test_dashboard_year_mode():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(
            "/?mode=year&student=Fran&ref=2026-03-15",
            headers=_auth_header("randy", "randy"),
        )
        assert r.status_code == 200
        assert "Learning Year" in r.text
        assert "Monthly Activity" in r.text

@pytest.mark.anyio
async def test_dashboard_empty_range():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(
            "/?mode=week&student=Fran&ref=2027-01-15",
            headers=_auth_header("randy", "randy"),
        )
        assert r.status_code == 200
        assert "No lessons found" in r.text

@pytest.mark.anyio
async def test_dashboard_zap_student():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(
            "/?mode=month&student=Zap&ref=2026-05-15",
            headers=_auth_header("tl", "tl"),
        )
        assert r.status_code == 200
        assert "Zap" in html if (html := r.text) else False

@pytest.mark.anyio
async def test_preferences_save():
    assert PREFS_DB == Path(os.environ["PREFS_DB"])
    assert PREFS_DB != DATA_DIR / "dashboard_state.sqlite"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/preferences",
            data={"default_student": "Zap", "default_time_mode": "month"},
            headers=_auth_header("randy", "randy"),
            follow_redirects=False,
        )
        assert r.status_code == 303
    conn = sqlite3.connect(PREFS_DB)
    try:
        saved = conn.execute(
            "SELECT default_student, default_time_mode "
            "FROM preferences WHERE username = ?",
            ("randy",),
        ).fetchone()
    finally:
        conn.close()
    assert saved == ("Zap", "month")

@pytest.mark.anyio
async def test_filter_subject():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(
            "/?mode=month&student=Fran&ref=2026-05-15&subject=Math",
            headers=_auth_header("randy", "randy"),
        )
        assert r.status_code == 200
        assert "3h 55m" in r.text
