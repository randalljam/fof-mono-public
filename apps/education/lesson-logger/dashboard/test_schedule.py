#!/usr/bin/env python3
# Tests for the family-schedule tab: sync, markdown rendering, and the /schedule route.
# Run: cd apps/education/lesson-logger/dashboard && .venv/bin/pytest test_schedule.py -v
import base64
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module
from app import (
    app,
    _collapse_log_section,
    _decorate_past_week_days,
    _pacific_today,
    _render_markdown_file,
)
from httpx import ASGITransport, AsyncClient
import pytest
import sync_schedule

def _auth_header(user, password):
    creds = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {creds}"}

### Markdown rendering
def test_render_markdown_file_renders_html(tmp_path, monkeypatch):
    f = tmp_path / "current-week.md"
    f.write_text("## Monday Jun 15\n- **3:30p** gymnastics\n- ~~cancelled~~\n")
    monkeypatch.setattr(app_module, "SCHEDULE_DIR", tmp_path)
    html, exists, metadata = _render_markdown_file("current-week.md")
    assert exists is True
    assert metadata == {}
    assert "<h2>" in html
    assert "<strong>3:30p</strong>" in html
    assert "<ul>" in html
    assert "<del>cancelled</del>" in html
def test_render_current_week_extracts_source_metadata(tmp_path, monkeypatch):
    f = tmp_path / "current-week.md"
    f.write_text(
        "file: schedule/2026-07-27_week_family-schedule.md\n"
        "week: Mon 2026-07-27 — Sun 2026-08-02\n\n"
        "## Monday Jul 27\n(nothing scheduled)\n"
    )
    monkeypatch.setattr(app_module, "SCHEDULE_DIR", tmp_path)
    html, exists, metadata = _render_markdown_file("current-week.md")
    assert exists is True
    assert metadata == {
        "file": "schedule/2026-07-27_week_family-schedule.md",
        "week": "Mon 2026-07-27 — Sun 2026-08-02",
    }
    assert "file:" not in html
    assert "week:" not in html
    assert "Monday Jul 27" in html
def test_decorate_past_week_days_uses_strict_date_boundary():
    html = (
        "<h2>Monday Jul 27</h2><p>past</p>"
        "<h2>Tuesday Jul 28</h2><p>past</p>"
        "<h2>Wednesday Jul 29</h2><p>today</p>"
        "<h2>Thursday Jul 30</h2><p>future</p>"
    )
    metadata = {
        "file": "schedule/2026-07-27_week_family-schedule.md",
        "week": "Mon 2026-07-27 — Sun 2026-08-02",
    }
    decorated = _decorate_past_week_days(html, metadata, today=date(2026, 7, 29))
    assert '<h2 class="schedule-day-past">Monday Jul 27</h2>' in decorated
    assert '<h2 class="schedule-day-past">Tuesday Jul 28</h2>' in decorated
    assert '<h2 class="schedule-day-past">Wednesday Jul 29</h2>' not in decorated
    assert '<h2 class="schedule-day-past">Thursday Jul 30</h2>' not in decorated
    assert "<h2>Wednesday Jul 29</h2>" in decorated
    assert "<h2>Thursday Jul 30</h2>" in decorated
def test_decorate_past_week_days_without_metadata_is_unchanged():
    html = "<h2>Monday Jul 27</h2>"
    assert _decorate_past_week_days(html, {}, today=date(2026, 7, 29)) == html
def test_pacific_today_honors_midnight_boundary():
    assert _pacific_today(datetime(2026, 7, 30, 6, 59, tzinfo=timezone.utc)) == date(2026, 7, 29)
    assert _pacific_today(datetime(2026, 7, 30, 7, 0, tzinfo=timezone.utc)) == date(2026, 7, 30)
def test_render_next_week_never_applies_past_day_styling(tmp_path, monkeypatch):
    f = tmp_path / "next-week.md"
    f.write_text(
        "file: schedule/2026-07-27_week_family-schedule.md\n"
        "week: Mon 2026-07-27 — Sun 2026-08-02\n\n"
        "## Monday Jul 27\n(nothing scheduled)\n"
    )
    monkeypatch.setattr(app_module, "SCHEDULE_DIR", tmp_path)
    html, exists, metadata = _render_markdown_file("next-week.md")
    assert exists is True
    assert metadata["week"] == "Mon 2026-07-27 — Sun 2026-08-02"
    assert "schedule-day-past" not in html
def test_render_next_week_shows_expanded_daily_occurrences_without_range_prose(
        tmp_path, monkeypatch):
    f = tmp_path / "next-week.md"
    daily_entry = (
        "- **9:00a–12:00p** Kids soccer camp · pickup at noon"
    )
    f.write_text(
        "file: schedule/2026-08-03_week_family-schedule.md\n"
        "week: Mon 2026-08-03 — Sun 2026-08-09\n\n"
        f"## Monday Aug 3\n{daily_entry}\n\n"
        f"## Tuesday Aug 4\n{daily_entry}\n\n"
        f"## Wednesday Aug 5\n{daily_entry}\n\n"
        f"## Thursday Aug 6\n{daily_entry}\n\n"
        f"## Friday Aug 7\n{daily_entry}\n\n"
        "## Saturday Aug 8\n(nothing scheduled)\n\n"
        "## Sunday Aug 9\n(nothing scheduled)\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(app_module, "SCHEDULE_DIR", tmp_path)
    html, exists, metadata = _render_markdown_file("next-week.md")
    assert exists is True
    assert metadata["week"] == "Mon 2026-08-03 — Sun 2026-08-09"
    assert html.count("Kids soccer camp") == 5
    assert html.count("pickup at noon") == 5
    assert "through 2026-08-07" not in html
    assert "daily (Mon–Fri)" not in html
def test_render_horizon_moves_explanations_into_tooltips(tmp_path, monkeypatch):
    f = tmp_path / "horizon.md"
    f.write_text(
        "## Recurring\nWeekly/regular activities with defaults.\n\n"
        "## Upcoming\nItems with known dates, not yet in a week file.\n\n"
        "### Next 2 weeks\nDates within 14 days of the horizon start date (Aug 3).\n\n"
        "### This month\nSame calendar month, beyond 2 weeks out (August).\n\n"
        "(nothing else this month)\n\n"
        "### Later\nNext month and beyond. Dates can be approximate (September onward).\n\n"
        "(nothing scheduled later)\n\n"
        "## Notes\nGeneral scheduling notes, preferences, standing arrangements for fall.\n\n"
        "- Keep Tuesdays flexible.\n"
    )
    monkeypatch.setattr(app_module, "SCHEDULE_DIR", tmp_path)
    html, exists, metadata = _render_markdown_file("horizon.md")
    assert exists is True
    assert metadata == {}
    assert html.count('class="schedule-tooltip-heading"') == 6
    assert html.count('role="tooltip"') == 6
    assert html.count('tabindex="0"') == 6
    expected_tooltips = {
        "recurring": ("Recurring", "Weekly/regular activities with defaults."),
        "upcoming": ("Upcoming", "Items with known dates, not yet in a week file."),
        "next-two-weeks": (
            "Next Two Weeks",
            "Dates within 14 days of the horizon start date (Aug 3).",
        ),
        "this-month": (
            "This Month",
            "Same calendar month, beyond 2 weeks out (August).",
        ),
        "later": (
            "Later",
            "Next month and beyond. Dates can be approximate (September onward).",
        ),
        "notes": (
            "Notes",
            "General scheduling notes, preferences, standing arrangements for fall.",
        ),
    }
    for slug, (label, explanation) in expected_tooltips.items():
        assert f'aria-describedby="schedule-tooltip-{slug}"' in html
        assert label in html
        assert f'role="tooltip">{explanation}</span>' in html
        assert f"<p>{explanation}</p>" not in html
    assert "(nothing else this month)" in html
    assert "(nothing scheduled later)" in html
    assert "Keep Tuesdays flexible." in html
def test_render_markdown_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "SCHEDULE_DIR", tmp_path)
    html, exists, metadata = _render_markdown_file("nope.md")
    assert exists is False
    assert html is None
    assert metadata == {}
def test_collapse_log_section_defaults_closed():
    html = (
        "<h2>Sunday Jun 28</h2><p>(nothing scheduled)</p>"
        "<h2>Log</h2><ul><li>entry one</li><li>entry two</li></ul>"
    )
    collapsed = _collapse_log_section(html)
    assert '<details class="schedule-log">' in collapsed
    assert 'open' not in collapsed
    assert '<summary class="schedule-log-summary">Log</summary>' in collapsed
    assert '<div class="schedule-log-body"><ul><li>entry one</li><li>entry two</li></ul></div>' in collapsed
    assert "<h2>Log</h2>" not in collapsed
    assert "<h2>Sunday Jun 28</h2>" in collapsed
def test_collapse_log_section_stops_before_following_h2():
    html = "<h2>Log</h2><ul><li>a</li></ul><h2>Notes</h2><p>keep</p>"
    collapsed = _collapse_log_section(html)
    assert collapsed.endswith("<h2>Notes</h2><p>keep</p>")
    assert "<li>a</li>" in collapsed
def test_collapse_log_section_noop_without_log():
    html = "<h2>Monday</h2><p>hi</p>"
    assert _collapse_log_section(html) == html
def test_render_collapses_log_on_week_files(tmp_path, monkeypatch):
    f = tmp_path / "next-week.md"
    f.write_text(
        "## Sunday Jun 28\n(nothing scheduled)\n\n"
        "## Log\n- 2026-06-18 7:10p · TL — museum\n"
    )
    monkeypatch.setattr(app_module, "SCHEDULE_DIR", tmp_path)
    html, exists, metadata = _render_markdown_file("next-week.md")
    assert exists is True
    assert metadata == {}
    assert '<details class="schedule-log">' in html
    assert 'open=' not in html and " open>" not in html
    assert '<summary class="schedule-log-summary">Log</summary>' in html
    assert "museum" in html
    assert "<h2>Log</h2>" not in html

### Sync from Hermes
def test_sync_schedule_writes_files(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_SCHEDULE_BASE_URL", "http://hermes.test/family-schedule")
    monkeypatch.setenv("SCHEDULE_DIR", str(tmp_path))
    def fake_download(url):
        return f"# from {url}".encode()
    monkeypatch.setattr(sync_schedule, "_download", fake_download)
    assert sync_schedule.sync_schedule_from_hermes() is True
    assert (tmp_path / "current-week.md").read_text() == "# from http://hermes.test/family-schedule/current-week.md"
    assert (tmp_path / "next-week.md").read_text() == "# from http://hermes.test/family-schedule/next-week.md"
    assert (tmp_path / "horizon.md").read_text() == "# from http://hermes.test/family-schedule/horizon.md"
def test_sync_schedule_keeps_cache_on_404(tmp_path, monkeypatch):
    cached = tmp_path / "current-week.md"
    cached.write_text("CACHED WEEK")
    cached_next = tmp_path / "next-week.md"
    cached_next.write_text("CACHED NEXT WEEK")
    monkeypatch.setenv("HERMES_SCHEDULE_BASE_URL", "http://hermes.test/family-schedule")
    monkeypatch.setenv("SCHEDULE_DIR", str(tmp_path))
    def fake_download(url):
        if url.endswith("current-week.md") or url.endswith("next-week.md"):
            raise sync_schedule.FileNotFoundOnHermes(url)
        return b"# horizon"
    monkeypatch.setattr(sync_schedule, "_download", fake_download)
    # Horizon refreshes, so overall True; both weekly aliases keep their cached copies.
    assert sync_schedule.sync_schedule_from_hermes() is True
    assert cached.read_text() == "CACHED WEEK"
    assert cached_next.read_text() == "CACHED NEXT WEEK"
    assert (tmp_path / "horizon.md").read_text() == "# horizon"
def test_sync_schedule_is_best_effort_when_cache_directory_is_unwritable(
        tmp_path, monkeypatch, caplog):
    dest = tmp_path / "unwritable"
    monkeypatch.setenv(
        "HERMES_SCHEDULE_BASE_URL",
        "http://hermes.test/family-schedule",
    )
    monkeypatch.setenv("SCHEDULE_DIR", str(dest))
    def fail_makedirs(path, exist_ok):
        raise PermissionError("read-only filesystem")
    monkeypatch.setattr(sync_schedule.os, "makedirs", fail_makedirs)

    assert sync_schedule.sync_schedule_from_hermes() is False
    assert "cannot create cache directory" in caplog.text
def test_manual_pull_caches_current_next_and_horizon():
    script = (Path(__file__).parent / "sync_schedule_from_hermes.sh").read_text()
    assert 'pull_file "$REMOTE_WEEK" "current-week.md" 0' in script
    assert 'pull_file "$REMOTE_NEXT_WEEK" "next-week.md" 0' in script
    assert 'pull_file "$REMOTE_HORIZON" "horizon.md" 1' in script
    assert 'ZoneInfo("America/Los_Angeles")' in script
def test_local_runner_checks_new_runtime_dependencies():
    script = (Path(__file__).parent / "run_local.sh").read_text()
    assert ".venv/bin/python -c 'import markdown'" in script

def test_local_runner_disables_implicit_private_sync():
    script = (Path(__file__).parent / "run_local.sh").read_text()
    assert 'export HERMES_LESSON_DB_URL="${HERMES_LESSON_DB_URL:-}"' in script
    assert 'export HERMES_SCHEDULE_BASE_URL="${HERMES_SCHEDULE_BASE_URL:-}"' in script

### /schedule route
@pytest.mark.anyio
async def test_schedule_route_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/schedule")
        assert r.status_code == 401
@pytest.mark.anyio
async def test_schedule_route_renders_dev_files():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/schedule", headers=_auth_header("randy", "randy"))
        assert r.status_code == 200
        html = r.text
        assert "Family Schedule" in html
        assert "Lesson Logger" in html  # back button
        assert "gymnastics" in html     # rendered from schedule_dev/current-week.md
        assert "science museum" in html # rendered from schedule_dev/next-week.md
        assert "Recurring" in html       # rendered from schedule_dev/horizon.md
        this_week = html.index("<span>This Week</span>")
        next_week = html.index("<span>Next Week</span>")
        horizon = html.index("<span>Horizon</span>")
        assert this_week < next_week < horizon
        assert html.count("<span>This Week</span>") == 1
        assert "schedule-date-range" not in html
        assert "Mon 2026-06-15 — Sun 2026-06-21" not in html
        assert "Mon 2026-06-22 — Sun 2026-06-28" not in html
        assert "file: schedule/" not in html
        assert 'role="tooltip"' in html
        assert 'aria-describedby="schedule-tooltip-recurring"' in html
        assert "schedule-card-title" in html
        assert "<h2>" in html           # python-markdown headings rendered
        assert html.count('<details class="schedule-log">') == 2  # current + next week logs
        assert '<summary class="schedule-log-summary">Log</summary>' in html
        assert "grid-cols-1" in html     # one vertical column on phones
        assert "lg:grid-cols-3" in html  # three columns across on desktop
