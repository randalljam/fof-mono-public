#!/usr/bin/env python3
"""Canonical active-week storage and date-routing helpers for family schedules."""
import argparse
import os
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTH_ABBREVS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                 "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
HORIZON_FILENAME = "horizon_family-schedule.md"
ROUTING_CONTRACT_ID = "family-schedule-routing-v1"

class PastScheduleWriteError(ValueError):
    """Raised when a write targets a date before the current Pacific date."""
def normalize_date(value):
    """Return a date from a date, datetime, or ISO YYYY-MM-DD string."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=PACIFIC).date()
        return value.astimezone(PACIFIC).date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError("expected a date, datetime, or ISO YYYY-MM-DD string")
def pacific_today(now=None):
    """Return the current Pacific date, with an injectable value for tests."""
    if now is None:
        return datetime.now(PACIFIC).date()
    return normalize_date(now)
def week_bounds(day):
    """Return the Monday and Sunday containing day."""
    day = normalize_date(day)
    monday = day - timedelta(days=day.weekday())
    return monday, monday + timedelta(days=6)
def active_week_bounds(today=None):
    """Return current and following Monday-Sunday bounds."""
    current_monday, current_sunday = week_bounds(pacific_today(today))
    next_monday = current_monday + timedelta(days=7)
    return current_monday, current_sunday, next_monday, next_monday + timedelta(days=6)
def iso_week_dates(iso_year, iso_week):
    """Return Monday and Sunday for an ISO year and week."""
    monday = date.fromisocalendar(iso_year, iso_week, 1)
    return monday, monday + timedelta(days=6)
def format_day_heading(date):
    """Return a schedule heading such as 'Monday Jun 16'."""
    date = normalize_date(date)
    return f"{DAY_NAMES[date.weekday()]} {MONTH_ABBREVS[date.month - 1]} {date.day}"
def week_filename(monday):
    """Return a Monday-dated authoritative weekly schedule filename."""
    monday = normalize_date(monday)
    return f"{monday.isoformat()}_week_family-schedule.md"
def week_file_content(monday, sunday=None):
    """Generate an empty authoritative weekly schedule skeleton."""
    monday = normalize_date(monday)
    if sunday is None:
        sunday = monday + timedelta(days=6)
    else:
        sunday = normalize_date(sunday)
    lines = [
        f"file: schedule/{week_filename(monday)}",
        f"week: Mon {monday.isoformat()} — Sun {sunday.isoformat()}",
        "",
    ]
    for offset in range(7):
        day = monday + timedelta(days=offset)
        lines.append(f"## {format_day_heading(day)}")
        lines.append("(nothing scheduled)")
        lines.append("")
    lines.append("## Log")
    lines.append("")
    return "\n".join(lines)
def _ensure_week_file(schedule_dir, monday):
    """Create one week exclusively, preserving any existing contents."""
    monday, sunday = week_bounds(monday)
    path = os.path.join(os.fspath(schedule_dir), week_filename(monday))
    os.makedirs(os.fspath(schedule_dir), exist_ok=True)
    try:
        with open(path, "x", encoding="utf-8") as schedule_file:
            schedule_file.write(week_file_content(monday, sunday))
        status = "created"
    except FileExistsError:
        status = "exists"
    return {
        "status": status,
        "path": path,
        "monday": monday,
        "sunday": sunday,
    }
def ensure_active_week_files(schedule_dir, today=None):
    """Idempotently ensure only the current and following Pacific week files."""
    current_monday, _, next_monday, _ = active_week_bounds(today)
    return {
        "current": _ensure_week_file(schedule_dir, current_monday),
        "next": _ensure_week_file(schedule_dir, next_monday),
    }
def route_schedule_date(schedule_dir, target_date, today=None,
                        for_write=False, allow_past=False):
    """Return canonical storage metadata for one schedule date.

    Current and following-week routes ensure both active week skeletons. Future
    dates beyond the following Sunday route to Horizon. Historical dates never
    create files and resolve only when their Monday-dated file already exists.
    """
    target_date = normalize_date(target_date)
    today = pacific_today(today)
    current_monday, current_sunday, next_monday, next_sunday = active_week_bounds(today)
    if for_write and target_date < today and not allow_past:
        raise PastScheduleWriteError(
            f"refusing write for past date {target_date}; "
            "set allow_past=True only for an intentional correction")
    if target_date < current_monday:
        historical_monday, historical_sunday = week_bounds(target_date)
        path = os.path.join(os.fspath(schedule_dir), week_filename(historical_monday))
        if not os.path.isfile(path):
            raise FileNotFoundError(
                f"historical schedule file does not exist: {path}")
        return {
            "bucket": "historical",
            "path": path,
            "target_date": target_date,
            "monday": historical_monday,
            "sunday": historical_sunday,
        }
    if target_date <= next_sunday:
        active = ensure_active_week_files(schedule_dir, today)
        bucket = "current" if target_date <= current_sunday else "next"
        result = active[bucket]
        return {
            "bucket": bucket,
            "path": result["path"],
            "target_date": target_date,
            "monday": result["monday"],
            "sunday": result["sunday"],
        }
    return {
        "bucket": "horizon",
        "path": os.path.join(os.fspath(schedule_dir), HORIZON_FILENAME),
        "target_date": target_date,
        "monday": None,
        "sunday": None,
    }
def resolve_schedule_file(schedule_dir, target_date, today=None,
                          for_write=False, allow_past=False):
    """Return the canonical file path for one schedule date."""
    route = route_schedule_date(
        schedule_dir,
        target_date,
        today=today,
        for_write=for_write,
        allow_past=allow_past,
    )
    return route["path"]
def _print_status(label, result):
    """Print one active-week creation status for command-line callers."""
    print(f"{label}-{result['status']}: {result['path']}")
    print(f"{label}-week: {result['monday']} to {result['sunday']}")
def main():
    """Run the canonical ensure or route operation."""
    parser = argparse.ArgumentParser(
        description="Ensure and route authoritative family schedule files")
    subparsers = parser.add_subparsers(dest="command", required=True)
    ensure_parser = subparsers.add_parser(
        "ensure", help="ensure current and next weekly skeletons")
    ensure_parser.add_argument("schedule_dir")
    ensure_parser.add_argument("--today", help="injected Pacific date as YYYY-MM-DD")
    route_parser = subparsers.add_parser(
        "route", help="resolve the authoritative file for a target date")
    route_parser.add_argument("schedule_dir")
    route_parser.add_argument("target_date", help="target date as YYYY-MM-DD")
    route_parser.add_argument("--today", help="injected Pacific date as YYYY-MM-DD")
    route_parser.add_argument("--write", action="store_true")
    route_parser.add_argument("--allow-past", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "ensure":
            results = ensure_active_week_files(args.schedule_dir, args.today)
            _print_status("current", results["current"])
            _print_status("next", results["next"])
            return
        route = route_schedule_date(
            args.schedule_dir,
            args.target_date,
            today=args.today,
            for_write=args.write,
            allow_past=args.allow_past,
        )
        print(f"{route['bucket']}: {route['path']}")
    except (FileNotFoundError, PastScheduleWriteError, TypeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)
if __name__ == "__main__":
    main()
