#!/usr/bin/env python3
import importlib.util
import os
import subprocess
import sys
import tempfile
from datetime import date

_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills", "family", "schedule-coordinator", "scripts", "rollover_week.py",
)
def _load():
    spec = importlib.util.spec_from_file_location("rollover_week", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
def test_iso_week_dates():
    mod = _load()
    mon, sun = mod.iso_week_dates(2026, 25)
    assert str(mon) == "2026-06-15", f"W25 Monday: {mon}"
    assert str(sun) == "2026-06-21", f"W25 Sunday: {sun}"
    mon, sun = mod.iso_week_dates(2026, 24)
    assert str(mon) == "2026-06-08", f"W24 Monday: {mon}"
    assert str(sun) == "2026-06-14", f"W24 Sunday: {sun}"
    mon, sun = mod.iso_week_dates(2026, 1)
    assert str(mon) == "2025-12-29", f"W1 Monday: {mon}"
    assert str(sun) == "2026-01-04", f"W1 Sunday: {sun}"
def test_format_day_heading():
    mod = _load()
    assert mod.format_day_heading(date(2026, 6, 15)) == "Monday Jun 15"
    assert mod.format_day_heading(date(2026, 6, 20)) == "Saturday Jun 20"
    assert mod.format_day_heading(date(2026, 1, 1)) == "Thursday Jan 1"
def test_week_filename():
    mod = _load()
    assert mod.week_filename(date(2026, 6, 15)) == "2026-06-15_week_family-schedule.md"
    assert mod.week_filename(date(2026, 6, 8)) == "2026-06-08_week_family-schedule.md"
def test_week_file_content_structure():
    mod = _load()
    content = mod.week_file_content(date(2026, 6, 15), date(2026, 6, 21))
    assert "file: schedule/2026-06-15_week_family-schedule.md" in content
    assert "week: Mon 2026-06-15 — Sun 2026-06-21" in content
    assert "## Monday Jun 15" in content
    assert "## Sunday Jun 21" in content
    assert "## Log" in content
    assert content.count("(nothing scheduled)") == 7
    lines = content.strip().split("\n")
    for i, line in enumerate(lines):
        if line.startswith("## ") and i > 0:
            assert lines[i - 1] == "", f"expected blank line before '{line}' (line {i})"
def test_cli_ensures_current_and_next_with_legacy_first_line_status():
    with tempfile.TemporaryDirectory() as tmpdir:
        schedule_dir = os.path.join(tmpdir, "schedule")
        command = [sys.executable, _SCRIPT, schedule_dir, "--week", "2026-W25"]
        created = subprocess.run(
            command, check=True, capture_output=True, text=True)
        created_lines = created.stdout.splitlines()
        assert created_lines[0].startswith(
            f"created: {schedule_dir}/2026-06-15_week_family-schedule.md")
        assert (
            f"next-created: {schedule_dir}/2026-06-22_week_family-schedule.md"
            in created_lines
        )
        current_path = os.path.join(
            schedule_dir, "2026-06-15_week_family-schedule.md")
        next_path = os.path.join(
            schedule_dir, "2026-06-22_week_family-schedule.md")
        assert os.path.isfile(current_path)
        assert os.path.isfile(next_path)
        with open(current_path, "w", encoding="utf-8") as schedule_file:
            schedule_file.write("custom content\n")
        existing = subprocess.run(
            command, check=True, capture_output=True, text=True)
        existing_lines = existing.stdout.splitlines()
        assert existing_lines[0].startswith(f"exists: {current_path}")
        assert f"next-exists: {next_path}" in existing_lines
        with open(current_path, encoding="utf-8") as schedule_file:
            assert schedule_file.read() == "custom content\n"
def test_parse_week_arg():
    mod = _load()
    assert mod.parse_week_arg("2026-W25") == (2026, 25)
    assert mod.parse_week_arg("2026-W01") == (2026, 1)
    assert mod.parse_week_arg("bad") is None
    assert mod.parse_week_arg("2026-25") is None
if __name__ == "__main__":
    test_iso_week_dates()
    test_format_day_heading()
    test_week_filename()
    test_week_file_content_structure()
    test_cli_ensures_current_and_next_with_legacy_first_line_status()
    test_parse_week_arg()
    print("ok — all tests passed")
