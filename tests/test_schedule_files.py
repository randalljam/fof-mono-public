#!/usr/bin/env python3
import importlib.util
import os
import subprocess
import sys
from datetime import date, datetime, timezone

import pytest

_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills", "family", "schedule-coordinator", "scripts", "schedule_files.py",
)
def _load():
    spec = importlib.util.spec_from_file_location("schedule_files_contract", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
def test_contract_identifier_is_stable():
    module = _load()
    assert module.ROUTING_CONTRACT_ID == "family-schedule-routing-v1"
def test_ensure_active_weeks_creates_current_and_next_at_year_boundary(tmp_path):
    module = _load()
    results = module.ensure_active_week_files(tmp_path, today=date(2026, 12, 31))
    assert results["current"]["status"] == "created"
    assert results["current"]["monday"] == date(2026, 12, 28)
    assert results["current"]["sunday"] == date(2027, 1, 3)
    assert results["next"]["status"] == "created"
    assert results["next"]["monday"] == date(2027, 1, 4)
    assert results["next"]["sunday"] == date(2027, 1, 10)
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "2026-12-28_week_family-schedule.md",
        "2027-01-04_week_family-schedule.md",
    ]
    current_text = (tmp_path / "2026-12-28_week_family-schedule.md").read_text()
    next_text = (tmp_path / "2027-01-04_week_family-schedule.md").read_text()
    assert "week: Mon 2026-12-28 — Sun 2027-01-03" in current_text
    assert "## Sunday Jan 3" in current_text
    assert "week: Mon 2027-01-04 — Sun 2027-01-10" in next_text
    assert "## Monday Jan 4" in next_text
def test_ensure_active_weeks_is_idempotent_and_never_overwrites(tmp_path):
    module = _load()
    current_path = tmp_path / "2026-07-27_week_family-schedule.md"
    current_path.write_text("preserve this schedule\n")
    first = module.ensure_active_week_files(tmp_path, today="2026-07-29")
    assert first["current"]["status"] == "exists"
    assert first["next"]["status"] == "created"
    assert current_path.read_text() == "preserve this schedule\n"
    next_path = tmp_path / "2026-08-03_week_family-schedule.md"
    next_path.write_text("preserve next week too\n")
    second = module.ensure_active_week_files(tmp_path, today="2026-07-29")
    assert second["current"]["status"] == "exists"
    assert second["next"]["status"] == "exists"
    assert current_path.read_text() == "preserve this schedule\n"
    assert next_path.read_text() == "preserve next week too\n"
def test_route_current_and_next_dates_to_authoritative_week_files(tmp_path):
    module = _load()
    current = module.route_schedule_date(
        tmp_path, "2026-12-31", today="2026-12-31", for_write=True)
    next_week = module.route_schedule_date(
        tmp_path, "2027-01-10", today="2026-12-31", for_write=True)
    assert current["bucket"] == "current"
    assert current["path"].endswith("2026-12-28_week_family-schedule.md")
    assert next_week["bucket"] == "next"
    assert next_week["path"].endswith("2027-01-04_week_family-schedule.md")
    assert os.path.isfile(current["path"])
    assert os.path.isfile(next_week["path"])
def test_route_cli_sends_next_week_write_to_next_monday_file(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            _SCRIPT,
            "route",
            str(tmp_path),
            "2027-01-05",
            "--today",
            "2026-12-31",
            "--write",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == (
        f"next: {tmp_path}/2027-01-04_week_family-schedule.md")
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "2026-12-28_week_family-schedule.md",
        "2027-01-04_week_family-schedule.md",
    ]
def test_route_future_beyond_next_week_to_horizon_without_creating_it(tmp_path):
    module = _load()
    route = module.route_schedule_date(
        tmp_path, "2027-01-11", today="2026-12-31", for_write=True)
    assert route["bucket"] == "horizon"
    assert route["path"] == str(tmp_path / "horizon_family-schedule.md")
    assert list(tmp_path.iterdir()) == []
def test_past_write_is_rejected_by_default(tmp_path):
    module = _load()
    with pytest.raises(module.PastScheduleWriteError, match="refusing write"):
        module.route_schedule_date(
            tmp_path, "2026-07-28", today="2026-07-29", for_write=True)
    assert list(tmp_path.iterdir()) == []
def test_explicit_past_write_within_active_week_uses_current_file(tmp_path):
    module = _load()
    route = module.route_schedule_date(
        tmp_path,
        "2026-07-28",
        today="2026-07-29",
        for_write=True,
        allow_past=True,
    )
    assert route["bucket"] == "current"
    assert route["path"].endswith("2026-07-27_week_family-schedule.md")
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "2026-07-27_week_family-schedule.md",
        "2026-08-03_week_family-schedule.md",
    ]
def test_historical_read_resolves_existing_monday_file_without_creating(tmp_path):
    module = _load()
    historical_path = tmp_path / "2026-07-13_week_family-schedule.md"
    historical_path.write_text("historical schedule\n")
    route = module.route_schedule_date(
        tmp_path, "2026-07-19", today="2026-07-29")
    assert route["bucket"] == "historical"
    assert route["path"] == str(historical_path)
    assert [path.name for path in tmp_path.iterdir()] == [historical_path.name]
def test_explicit_historical_write_requires_and_uses_existing_file(tmp_path):
    module = _load()
    historical_path = tmp_path / "2026-07-13_week_family-schedule.md"
    historical_path.write_text("historical schedule\n")
    route = module.route_schedule_date(
        tmp_path,
        "2026-07-19",
        today="2026-07-29",
        for_write=True,
        allow_past=True,
    )
    assert route["bucket"] == "historical"
    assert route["path"] == str(historical_path)
    assert historical_path.read_text() == "historical schedule\n"
def test_missing_historical_read_fails_without_creating(tmp_path):
    module = _load()
    with pytest.raises(FileNotFoundError, match="historical schedule file"):
        module.resolve_schedule_file(
            tmp_path, "2026-07-19", today="2026-07-29")
    assert list(tmp_path.iterdir()) == []
def test_pacific_date_injection_converts_aware_datetimes():
    module = _load()
    utc_time = datetime(2027, 1, 4, 7, 30, tzinfo=timezone.utc)
    assert module.pacific_today(utc_time) == date(2027, 1, 3)
