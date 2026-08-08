#!/usr/bin/env python3
"""Ensure current and next authoritative weekly schedule skeletons.

Usage:
    python3 rollover_week.py SCHEDULE_DIR [--week YYYY-Www]

Creates the current and following Monday-dated weekly files with day
headings and empty log sections. Existing content is never overwritten.
The first output line retains the current week's legacy "created:" or
"exists:" gate status.

This is the manual/interactive skeleton gate, not the scheduled transaction
owner. ``weekly_rollover.py scheduled`` performs the guarded Horizon-to-Next-
Week move and advances durable Pacific boundary state.

The --week selector injects the active ISO week for development and tests.

Stdlib only — no dependencies beyond Python 3.9+.
"""
import argparse
import os
import sys
from datetime import timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
from schedule_files import (  # noqa: E402
    DAY_NAMES,
    MONTH_ABBREVS,
    PACIFIC,
    ensure_active_week_files,
    format_day_heading,
    iso_week_dates,
    pacific_today,
    week_file_content,
    week_filename,
)

def parse_week_arg(week_str):
    """Parse 'YYYY-Www' into (iso_year, iso_week)."""
    parts = week_str.split("-W")
    if len(parts) != 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None
def main():
    parser = argparse.ArgumentParser(
        description="Ensure current and next weekly schedule skeletons")
    parser.add_argument("schedule_dir",
                        help="Path to the schedule/ directory")
    parser.add_argument("--week",
                        help="Target week as YYYY-Www (default: current week in Pacific)")
    args = parser.parse_args()

    if args.week:
        parsed = parse_week_arg(args.week)
        if not parsed:
            print(f"error: invalid week format '{args.week}', expected YYYY-Www",
                  file=sys.stderr)
            sys.exit(1)
        iso_year, iso_week = parsed
        try:
            today, _ = iso_week_dates(iso_year, iso_week)
        except ValueError:
            print(f"error: invalid ISO week '{args.week}'", file=sys.stderr)
            sys.exit(1)
    else:
        today = pacific_today()
    results = ensure_active_week_files(args.schedule_dir, today=today)
    current = results["current"]
    next_week = results["next"]
    print(f"{current['status']}: {current['path']}")
    print(f"week: {current['monday']} to {current['sunday']}")
    current_dates = [
        str(current["monday"] + timedelta(days=offset))
        for offset in range(7)
    ]
    print(f"dates: {', '.join(current_dates)}")
    print(f"next-{next_week['status']}: {next_week['path']}")
    print(f"next-week: {next_week['monday']} to {next_week['sunday']}")
    next_dates = [
        str(next_week["monday"] + timedelta(days=offset))
        for offset in range(7)
    ]
    print(f"next-dates: {', '.join(next_dates)}")
if __name__ == "__main__":
    main()
