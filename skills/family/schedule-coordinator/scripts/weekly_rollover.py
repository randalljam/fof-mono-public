#!/usr/bin/env python3
"""Move exact-dated Horizon entries into the newly exposed Next Week.

The scheduler may invoke ``scheduled`` frequently in UTC. This module derives
the active boundary in America/Los_Angeles, serializes work with a schedule-
local lock, and records the last completed Pacific Monday. Bootstrap is
deliberately dry-run by default and requires an exact proposal digest to apply.

Explicit Horizon date spans are expanded deterministically into one ordinary
entry per target-week day. A separate digest-gated repair command converts a
legacy range entry that an older version already placed in a weekly file.
"""
import argparse
import difflib
import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
from schedule_files import (  # noqa: E402
    HORIZON_FILENAME,
    PACIFIC,
    format_day_heading,
    week_file_content,
    week_filename,
)

ROLLOVER_CONTRACT_ID = "family-schedule-weekly-rollover-v1"
STATE_FILENAME = ".family-schedule-rollover-state.json"
LOCK_FILENAME = ".family-schedule-rollover.lock"
ENTRY_PATTERN = re.compile(
    r"^- (?P<start>\d{4}-\d{2}-\d{2})"
    r"(?:\s+\([^)]+\))?"
    r"(?:"
    r"\s+(?:through|to)\s+(?P<word_end>\d{4}-\d{2}-\d{2})"
    r"|\s*(?:–|—)\s*(?P<dash_end>\d{4}-\d{2}-\d{2})"
    r")?"
    r"(?:\s+\([^)]+\))?\s*(?:·\s*)?(?P<body>.*)$",
    re.IGNORECASE,
)
LEGACY_DESTINATION_RANGE_PATTERN = re.compile(
    r"^- (?:(?P<start>\d{4}-\d{2}-\d{2})\s+)?"
    r"(?:through|to)\s+(?P<end>\d{4}-\d{2}-\d{2})"
    r"(?:\s+\([^)]+\))?\s*(?:·\s*)?(?P<body>.*)$",
    re.IGNORECASE,
)
SOURCE_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
WEEKDAY_RANGE = (
    r"(?:Mon(?:day)?|Tue(?:sday)?|Wed(?:nesday)?|"
    r"Thu(?:rsday)?|Fri(?:day)?|Sat(?:urday)?|Sun(?:day)?)"
)
REDUNDANT_RECURRENCE_PATTERN = re.compile(
    rf"(?ix)"
    rf"\b(?:daily|every\s+day|each\s+day)\b"
    rf"\s*\(?\s*{WEEKDAY_RANGE}\s*"
    rf"(?:through|to|[-–—])\s*{WEEKDAY_RANGE}\s*\)?"
)
STANDALONE_RECURRENCE_PATTERN = re.compile(
    r"(?i)^(?:daily|every\s+day|each\s+day)$")
TIME_RECURRENCE_PATTERN = re.compile(
    r"(?i)(?<=\*\*)\s+(?:daily|every\s+day|each\s+day)\b")
STATE_VERSION = 1

class BootstrapRequiredError(RuntimeError):
    """Raised when scheduled mode has not been explicitly initialized."""
class ProposalChangedError(RuntimeError):
    """Raised when bootstrap apply does not match the reviewed proposal."""
def parse_now(value=None):
    """Return an aware datetime, interpreting naive inputs as Pacific."""
    if value is None:
        return datetime.now(PACIFIC)
    if isinstance(value, datetime):
        parsed = value
    else:
        normalized = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=PACIFIC)
    return parsed.astimezone(PACIFIC)
def active_boundary_monday(now=None):
    """Return the Pacific Monday whose boundary has most recently begun."""
    pacific_now = parse_now(now)
    return pacific_now.date() - timedelta(days=pacific_now.weekday())
def _path(schedule_dir, filename):
    """Return one path below a schedule directory."""
    return Path(schedule_dir) / filename
def _read_required(path):
    """Read a required UTF-8 file without mutating the filesystem."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise FileNotFoundError(f"required schedule file does not exist: {path}") from error
def _read_destination(schedule_dir, monday):
    """Read a dated destination or return its in-memory skeleton."""
    path = _path(schedule_dir, week_filename(monday))
    if path.exists():
        return path, path.read_text(encoding="utf-8"), True
    return path, week_file_content(monday), False
def _source_sha256(raw_block):
    """Return the stable identity of one exact Horizon source block."""
    return hashlib.sha256(raw_block.encode("utf-8")).hexdigest()
def _entry_marker(source_sha256, occurrence_date=None):
    """Return a stable source marker, optionally scoped to one occurrence."""
    suffix = (
        f":date={occurrence_date.isoformat()}"
        if occurrence_date is not None else ""
    )
    return (
        f"<!-- family-schedule-source: horizon:{source_sha256}{suffix} -->"
    )
def _date_span(start, end):
    """Yield each calendar date in an inclusive span."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)
def _clean_range_body(body):
    """Strip only explicit daily/weekday recurrence prose from a range body."""
    segments = re.split(r"\s*·\s*", body.strip())
    cleaned_segments = []
    for segment in segments:
        cleaned = _strip_redundant_recurrence(segment)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ·")
        if cleaned and not STANDALONE_RECURRENCE_PATTERN.fullmatch(cleaned):
            cleaned_segments.append(cleaned)
    if not cleaned_segments:
        return ""
    if (
        len(cleaned_segments) >= 2
        and re.fullmatch(r"\*\*[^*]+\*\*", cleaned_segments[0])
    ):
        first = f"{cleaned_segments[0]} {cleaned_segments[1]}"
        cleaned_segments = [first, *cleaned_segments[2:]]
    return " · ".join(cleaned_segments)
def _strip_redundant_recurrence(text):
    """Remove only recurrence syntax made redundant by an explicit date span."""
    cleaned = REDUNDANT_RECURRENCE_PATTERN.sub("", text)
    return TIME_RECURRENCE_PATTERN.sub("", cleaned)
def _format_horizon_span(entry, start, end):
    """Render one residual Horizon source block with its metadata intact."""
    if start == end:
        date_prefix = start.isoformat()
        body = _clean_range_body(entry["body"])
        continuation_lines = [
            _strip_redundant_recurrence(line).rstrip()
            for line in entry["continuation_lines"]
            if _strip_redundant_recurrence(line).strip()
            and not STANDALONE_RECURRENCE_PATTERN.fullmatch(
                _strip_redundant_recurrence(line).strip())
        ]
    else:
        date_prefix = f"{start.isoformat()} through {end.isoformat()}"
        body = entry["body"].strip()
        continuation_lines = entry["continuation_lines"]
    first_line = f"- {date_prefix}"
    if body:
        first_line += f" · {body}"
    return [first_line, *continuation_lines]
def _parse_upcoming_entries(horizon_text):
    """Return exact-dated top-level list blocks in the Upcoming section."""
    lines = horizon_text.splitlines()
    upcoming_start = None
    upcoming_end = len(lines)
    for index, line in enumerate(lines):
        if line.strip() == "## Upcoming":
            upcoming_start = index + 1
            continue
        if upcoming_start is not None and line.startswith("## "):
            upcoming_end = index
            break
    if upcoming_start is None:
        return lines, []
    entries = []
    index = upcoming_start
    while index < upcoming_end:
        match = ENTRY_PATTERN.match(lines[index])
        if not match:
            index += 1
            continue
        try:
            start_date = date.fromisoformat(match.group("start"))
            end_text = match.group("word_end") or match.group("dash_end")
            end_date = date.fromisoformat(end_text) if end_text else start_date
        except ValueError:
            index += 1
            continue
        if end_date < start_date:
            index += 1
            continue
        end = index + 1
        while end < upcoming_end and (
                lines[end].startswith(" ") or lines[end].startswith("\t")):
            end += 1
        raw_lines = lines[index:end]
        raw_block = "\n".join(raw_lines)
        source_sha256 = _source_sha256(raw_block)
        entries.append({
            "start_date": start_date,
            "end_date": end_date,
            "body": match.group("body"),
            "continuation_lines": raw_lines[1:],
            "start": index,
            "end": end,
            "raw": raw_block,
            "source_line": lines[index],
            "source_sha256": source_sha256,
            "legacy_marker": _entry_marker(source_sha256),
        })
        index = end
    return lines, entries
def _expand_entry(entry, target_start, target_end):
    """Return target occurrences and any residual Horizon spans."""
    overlap_start = max(entry["start_date"], target_start)
    overlap_end = min(entry["end_date"], target_end)
    if overlap_start > overlap_end:
        return [], None
    is_range = entry["start_date"] != entry["end_date"]
    body = _clean_range_body(entry["body"]) if is_range else entry["body"].strip()
    continuation_lines = entry["continuation_lines"]
    if is_range:
        continuation_lines = [
            _strip_redundant_recurrence(line).rstrip()
            for line in continuation_lines
            if _strip_redundant_recurrence(line).strip()
            and not STANDALONE_RECURRENCE_PATTERN.fullmatch(
                _strip_redundant_recurrence(line).strip())
        ]
    occurrences = []
    for occurrence_date in _date_span(overlap_start, overlap_end):
        marker = _entry_marker(
            entry["source_sha256"],
            occurrence_date if is_range else None,
        )
        occurrences.append({
            "date": occurrence_date,
            "source_line": entry["source_line"],
            "source_sha256": entry["source_sha256"],
            "destination_lines": [
                f"- {body}",
                *continuation_lines,
            ],
            "marker": marker,
        })
    residual_spans = []
    if entry["start_date"] < overlap_start:
        residual_spans.append(
            (entry["start_date"], overlap_start - timedelta(days=1)))
    if overlap_end < entry["end_date"]:
        residual_spans.append(
            (overlap_end + timedelta(days=1), entry["end_date"]))
    replacement_lines = []
    for residual_start, residual_end in residual_spans:
        replacement_lines.extend(
            _format_horizon_span(entry, residual_start, residual_end))
    return occurrences, replacement_lines
def _rewrite_entries(horizon_text, entries):
    """Replace selected source blocks with zero or more residual spans."""
    lines = horizon_text.splitlines()
    replacements = {entry["start"]: entry for entry in entries}
    result_lines = []
    index = 0
    while index < len(lines):
        entry = replacements.get(index)
        if entry is None:
            result_lines.append(lines[index])
            index += 1
            continue
        result_lines.extend(entry["replacement_lines"])
        index = entry["end"]
    result = "\n".join(result_lines)
    if horizon_text.endswith("\n"):
        result += "\n"
    return result
def _find_day_section(lines, day):
    """Return the body bounds for one dated day heading."""
    heading = f"## {format_day_heading(day)}"
    try:
        heading_index = lines.index(heading)
    except ValueError as error:
        raise ValueError(f"destination week is missing heading: {heading}") from error
    end = len(lines)
    for index in range(heading_index + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    return heading_index + 1, end
def _remove_legacy_range_blocks(lines, entries):
    """Remove older one-entry range promotions before daily replacement."""
    source_sha256s = {
        entry["source_sha256"]
        for entry in entries
        if ":date=" in entry["marker"]
    }
    for source_sha256 in sorted(source_sha256s):
        marker = _entry_marker(source_sha256)
        marker_indexes = [
            index for index, line in enumerate(lines) if line == marker
        ]
        if not marker_indexes:
            continue
        if len(marker_indexes) != 1:
            raise ValueError(
                f"expected at most one legacy marker for {source_sha256}")
        marker_index = marker_indexes[0]
        entry_index = marker_index + 1
        while entry_index < len(lines) and not lines[entry_index].strip():
            entry_index += 1
        if (
            entry_index >= len(lines)
            or not LEGACY_DESTINATION_RANGE_PATTERN.match(lines[entry_index])
        ):
            raise ValueError(
                "legacy range marker is not followed by a supported range entry")
        block_end = entry_index + 1
        while block_end < len(lines) and (
                lines[block_end].startswith(" ")
                or lines[block_end].startswith("\t")):
            block_end += 1
        del lines[marker_index:block_end]
    return lines
def _insert_promoted_entries(destination_text, entries, boundary):
    """Insert promoted entries once and append one idempotent rollover log."""
    lines = destination_text.splitlines()
    lines = _remove_legacy_range_blocks(lines, entries)
    existing_text = "\n".join(lines)
    added = []
    for entry in entries:
        if entry["marker"] in existing_text:
            continue
        start, end = _find_day_section(lines, entry["date"])
        body = [
            line for line in lines[start:end]
            if line.strip() != "(nothing scheduled)"
        ]
        while body and not body[-1].strip():
            body.pop()
        if body:
            body.append("")
        body.append(entry["marker"])
        body.extend(entry["destination_lines"])
        body.append("")
        lines[start:end] = body
        existing_text = "\n".join(lines)
        added.append(entry)
    transaction_marker = (
        f"<!-- family-schedule-rollover: boundary={boundary.isoformat()} -->")
    if transaction_marker not in existing_text:
        try:
            log_index = lines.index("## Log")
        except ValueError as error:
            raise ValueError("destination week is missing heading: ## Log") from error
        log_end = len(lines)
        for index in range(log_index + 1, len(lines)):
            if lines[index].startswith("## "):
                log_end = index
                break
        log_body = lines[log_index + 1:log_end]
        while log_body and not log_body[-1].strip():
            log_body.pop()
        if log_body:
            log_body.append("")
        log_body.extend([
            transaction_marker,
            (
                f"- {boundary.isoformat()} · system — Weekly boundary prepared "
                f"Next Week; moved {len(entries)} exact-dated Horizon "
                f"{'occurrence' if len(entries) == 1 else 'occurrences'}."
            ),
            "",
        ])
        lines[log_index + 1:log_end] = log_body
    result = "\n".join(lines)
    if destination_text.endswith("\n") or result:
        result += "\n"
    return result, added
def build_proposal(schedule_dir, boundary):
    """Build a pure, reviewable transaction proposal for one boundary."""
    boundary = date.fromisoformat(str(boundary))
    if boundary.weekday() != 0:
        raise ValueError(f"rollover boundary is not a Monday: {boundary}")
    target_monday = boundary + timedelta(days=7)
    target_sunday = target_monday + timedelta(days=6)
    horizon_path = _path(schedule_dir, HORIZON_FILENAME)
    horizon_before = _read_required(horizon_path)
    _, parsed_entries = _parse_upcoming_entries(horizon_before)
    eligible = []
    source_rewrites = []
    for source_entry in parsed_entries:
        occurrences, replacement_lines = _expand_entry(
            source_entry, target_monday, target_sunday)
        if not occurrences:
            continue
        eligible.extend(occurrences)
        source_rewrites.append({
            **source_entry,
            "replacement_lines": replacement_lines,
        })
    destination_path, destination_before, destination_exists = (
        _read_destination(schedule_dir, target_monday))
    destination_after, added = _insert_promoted_entries(
        destination_before, eligible, boundary)
    horizon_after = _rewrite_entries(horizon_before, source_rewrites)
    proposal = {
        "contract": ROLLOVER_CONTRACT_ID,
        "boundary": boundary.isoformat(),
        "target_monday": target_monday.isoformat(),
        "target_sunday": target_sunday.isoformat(),
        "destination_path": str(destination_path),
        "destination_existed": destination_exists,
        "destination_before": destination_before,
        "destination_after": destination_after,
        "horizon_path": str(horizon_path),
        "horizon_before": horizon_before,
        "horizon_after": horizon_after,
        "inventory": [
            {
                "date": entry["date"].isoformat(),
                "source_line": entry["source_line"],
                "marker": entry["marker"],
                "already_in_destination": entry not in added,
            }
            for entry in eligible
        ],
    }
    digest_source = json.dumps(
        proposal, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    proposal["sha256"] = hashlib.sha256(
        digest_source.encode("utf-8")).hexdigest()
    return proposal
def _diff(path, before, after):
    """Return a unified diff for one proposed file change."""
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    return "".join(difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile=f"{path} (before)",
        tofile=f"{path} (proposed)",
    ))
def render_proposal(proposal):
    """Return the bootstrap proposal in an auditable text form."""
    lines = [
        f"contract: {proposal['contract']}",
        f"boundary: {proposal['boundary']}",
        (
            f"target-week: {proposal['target_monday']} to "
            f"{proposal['target_sunday']}"
        ),
        f"destination: {proposal['destination_path']}",
        f"proposal-sha256: {proposal['sha256']}",
        f"inventory-count: {len(proposal['inventory'])}",
        "inventory:",
    ]
    if proposal["inventory"]:
        for item in proposal["inventory"]:
            suffix = " (already present; will only prune source)" if (
                item["already_in_destination"]) else ""
            lines.append(f"- {item['source_line']}{suffix}")
    else:
        lines.append("- (no exact-dated Horizon items in target week)")
    lines.extend([
        "",
        _diff(
            proposal["destination_path"],
            (
                proposal["destination_before"]
                if proposal["destination_existed"] else ""
            ),
            proposal["destination_after"],
        ).rstrip(),
        "",
        _diff(
            proposal["horizon_path"],
            proposal["horizon_before"],
            proposal["horizon_after"],
        ).rstrip(),
    ])
    return "\n".join(lines).rstrip() + "\n"
def _weekly_day_date(lines, marker_index, week_monday):
    """Return the date owned by the day section containing a marker."""
    weekdays = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }
    for index in range(marker_index - 1, -1, -1):
        match = re.match(
            r"^## (Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
            lines[index],
        )
        if match:
            return week_monday + timedelta(days=weekdays[match.group(1)])
        if lines[index] == "## Log":
            break
    raise ValueError("legacy source marker is not inside a weekly day section")
def _weekly_entry_block(lines, marker_index):
    """Return the nonempty bullet block immediately following a source marker."""
    entry_index = marker_index + 1
    while entry_index < len(lines) and not lines[entry_index].strip():
        entry_index += 1
    if entry_index >= len(lines) or not lines[entry_index].startswith("- "):
        raise ValueError(
            "completed range marker is not followed by a weekly entry")
    block_end = entry_index + 1
    while block_end < len(lines) and (
            lines[block_end].startswith(" ")
            or lines[block_end].startswith("\t")):
        block_end += 1
    return lines[entry_index:block_end]
def _repair_occurrence_marker(source_sha256, occurrence_date):
    """Return the range-aware marker used by repaired and new occurrences."""
    return _entry_marker(source_sha256, occurrence_date)
def _build_repair_noop(path, before, week_monday, source_sha256, dates):
    """Return a stable no-op proposal for an already completed repair."""
    proposal = {
        "contract": ROLLOVER_CONTRACT_ID,
        "operation": "repair-range",
        "week_monday": week_monday.isoformat(),
        "destination_path": str(path),
        "destination_before": before,
        "destination_after": before,
        "source_sha256": source_sha256,
        "occurrence_dates": [day.isoformat() for day in dates],
        "already_applied": True,
    }
    return _with_digest(proposal)
def _with_digest(proposal):
    """Attach a SHA-256 over the complete proposal contents."""
    digest_source = json.dumps(
        proposal, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    proposal["sha256"] = hashlib.sha256(
        digest_source.encode("utf-8")).hexdigest()
    return proposal
def build_range_repair_proposal(schedule_dir, week_monday, source_sha256):
    """Preview conversion of one explicit legacy range entry in a weekly file."""
    week_monday = date.fromisoformat(str(week_monday))
    if week_monday.weekday() != 0:
        raise ValueError(f"repair week is not a Monday: {week_monday}")
    source_sha256 = str(source_sha256).lower()
    if not SOURCE_SHA256_PATTERN.fullmatch(source_sha256):
        raise ValueError("source SHA-256 must be exactly 64 lowercase hex characters")
    path = _path(schedule_dir, week_filename(week_monday))
    before = _read_required(path)
    lines = before.splitlines()
    legacy_marker = _entry_marker(source_sha256)
    marker_indexes = [
        index for index, line in enumerate(lines) if line == legacy_marker
    ]
    if not marker_indexes:
        occurrence_pattern = re.compile(
            rf"^<!-- family-schedule-source: horizon:{source_sha256}"
            rf":date=(\d{{4}}-\d{{2}}-\d{{2}}) -->$"
        )
        occurrence_markers = [
            (index, date.fromisoformat(match.group(1)))
            for index, line in enumerate(lines)
            if (match := occurrence_pattern.match(line))
        ]
        occurrence_dates = sorted(day for _, day in occurrence_markers)
        week_sunday = week_monday + timedelta(days=6)
        contiguous_dates = (
            list(_date_span(occurrence_dates[0], occurrence_dates[-1]))
            if occurrence_dates else []
        )
        if (
            len(occurrence_dates) < 2
            or occurrence_dates != contiguous_dates
            or len(set(occurrence_dates)) != len(occurrence_dates)
            or occurrence_dates[0] < week_monday
            or occurrence_dates[-1] > week_sunday
        ):
            raise ValueError(
                "legacy marker was not found and a completed range repair "
                "could not be verified"
            )
        occurrence_blocks = []
        for marker_index, occurrence_date in occurrence_markers:
            if _weekly_day_date(
                    lines, marker_index, week_monday) != occurrence_date:
                raise ValueError(
                    "completed range marker is under the wrong day section")
            occurrence_blocks.append(
                _weekly_entry_block(lines, marker_index))
        if any(
                block != occurrence_blocks[0]
                for block in occurrence_blocks[1:]):
            raise ValueError(
                "completed range occurrences do not contain identical entries")
        return _build_repair_noop(
            path, before, week_monday, source_sha256, occurrence_dates)
    if len(marker_indexes) != 1:
        raise ValueError(
            f"expected one legacy marker, found {len(marker_indexes)}")
    marker_index = marker_indexes[0]
    entry_index = marker_index + 1
    while entry_index < len(lines) and not lines[entry_index].strip():
        entry_index += 1
    if entry_index >= len(lines):
        raise ValueError("legacy marker is not followed by an entry")
    match = LEGACY_DESTINATION_RANGE_PATTERN.match(lines[entry_index])
    if not match:
        raise ValueError(
            "legacy marker is not followed by a supported range entry")
    section_date = _weekly_day_date(lines, marker_index, week_monday)
    start_date = (
        date.fromisoformat(match.group("start"))
        if match.group("start") else section_date
    )
    end_date = date.fromisoformat(match.group("end"))
    week_sunday = week_monday + timedelta(days=6)
    if (
        start_date != section_date
        or end_date <= start_date
        or start_date < week_monday
        or end_date > week_sunday
    ):
        raise ValueError(
            "legacy repair range must start in its day section and remain "
            "inside the selected Monday-Sunday file"
        )
    block_end = entry_index + 1
    while block_end < len(lines) and (
            lines[block_end].startswith(" ")
            or lines[block_end].startswith("\t")):
        block_end += 1
    body = _clean_range_body(match.group("body"))
    continuation_lines = [
        _strip_redundant_recurrence(line).rstrip()
        for line in lines[entry_index + 1:block_end]
        if _strip_redundant_recurrence(line).strip()
        and not STANDALONE_RECURRENCE_PATTERN.fullmatch(
            _strip_redundant_recurrence(line).strip())
    ]
    occurrences = [
        {
            "date": occurrence_date,
            "source_line": lines[entry_index],
            "source_sha256": source_sha256,
            "destination_lines": [f"- {body}", *continuation_lines],
            "marker": _repair_occurrence_marker(
                source_sha256, occurrence_date),
        }
        for occurrence_date in _date_span(start_date, end_date)
    ]
    without_legacy = [
        line for index, line in enumerate(lines)
        if index < marker_index or index >= block_end
    ]
    interim = "\n".join(without_legacy)
    if before.endswith("\n"):
        interim += "\n"
    after, _ = _insert_promoted_entries(
        interim, occurrences, week_monday - timedelta(days=7))
    proposal = {
        "contract": ROLLOVER_CONTRACT_ID,
        "operation": "repair-range",
        "week_monday": week_monday.isoformat(),
        "destination_path": str(path),
        "destination_before": before,
        "destination_after": after,
        "source_sha256": source_sha256,
        "occurrence_dates": [
            item["date"].isoformat() for item in occurrences
        ],
        "already_applied": False,
    }
    return _with_digest(proposal)
def render_range_repair_proposal(proposal):
    """Return a reviewable, digest-pinned legacy repair proposal."""
    return "\n".join([
        f"contract: {proposal['contract']}",
        "operation: repair-range",
        f"week-monday: {proposal['week_monday']}",
        f"destination: {proposal['destination_path']}",
        f"source-sha256: {proposal['source_sha256']}",
        f"proposal-sha256: {proposal['sha256']}",
        f"already-applied: {str(proposal['already_applied']).lower()}",
        f"occurrence-count: {len(proposal['occurrence_dates'])}",
        "occurrence-dates: " + ", ".join(proposal["occurrence_dates"]),
        "",
        _diff(
            proposal["destination_path"],
            proposal["destination_before"],
            proposal["destination_after"],
        ).rstrip(),
    ]).rstrip() + "\n"
def _atomic_write(path, content):
    """Durably replace one file with a same-directory temporary file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    prior_mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary_name, prior_mode)
        os.replace(temporary_name, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
def _state_content(boundary):
    """Return the durable state JSON for a completed boundary."""
    return json.dumps({
        "contract": ROLLOVER_CONTRACT_ID,
        "state_version": STATE_VERSION,
        "last_completed_boundary": boundary.isoformat(),
    }, indent=2, sort_keys=True) + "\n"
def _load_state(schedule_dir):
    """Read and validate rollover state, returning the completed Monday."""
    state_path = _path(schedule_dir, STATE_FILENAME)
    if not state_path.exists():
        raise BootstrapRequiredError(
            f"bootstrap required: state file is absent: {state_path}")
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        boundary = date.fromisoformat(state["last_completed_boundary"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid rollover state: {state_path}") from error
    if state.get("contract") != ROLLOVER_CONTRACT_ID:
        raise ValueError(
            f"unsupported rollover state contract: {state.get('contract')!r}")
    if state.get("state_version") != STATE_VERSION:
        raise ValueError(
            f"unsupported rollover state version: {state.get('state_version')!r}")
    if boundary.weekday() != 0:
        raise ValueError(
            f"last completed boundary is not a Monday: {boundary}")
    return boundary
def _locked(schedule_dir):
    """Open and exclusively lock the schedule-local transaction lock."""
    lock_path = _path(schedule_dir, LOCK_FILENAME)
    lock_file = open(lock_path, "a+", encoding="utf-8")
    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
    return lock_file
def apply_proposal(proposal):
    """Apply destination-first, then Horizon, leaving state to the caller."""
    if proposal["destination_after"] != proposal["destination_before"]:
        _atomic_write(proposal["destination_path"], proposal["destination_after"])
    if proposal["horizon_after"] != proposal["horizon_before"]:
        _atomic_write(proposal["horizon_path"], proposal["horizon_after"])
def bootstrap(schedule_dir, now=None, apply=False, proposal_sha256=None):
    """Preview or explicitly apply initialization for the active boundary."""
    boundary = active_boundary_monday(now)
    proposal = build_proposal(schedule_dir, boundary)
    if not apply:
        return proposal
    if not proposal_sha256:
        raise ProposalChangedError(
            "--proposal-sha256 is required with --apply")
    Path(schedule_dir).mkdir(parents=True, exist_ok=True)
    with _locked(schedule_dir):
        state_path = _path(schedule_dir, STATE_FILENAME)
        if state_path.exists():
            raise BootstrapRequiredError(
                f"bootstrap refused: state already exists: {state_path}")
        proposal = build_proposal(schedule_dir, boundary)
        if proposal["sha256"] != proposal_sha256:
            raise ProposalChangedError(
                "proposal changed; review a new dry-run before applying "
                f"(expected {proposal_sha256}, actual {proposal['sha256']})")
        apply_proposal(proposal)
        _atomic_write(state_path, _state_content(boundary))
    return proposal
def repair_range(
        schedule_dir,
        week_monday,
        source_sha256,
        apply=False,
        proposal_sha256=None):
    """Preview or digest-gated apply one legacy weekly range conversion."""
    proposal = build_range_repair_proposal(
        schedule_dir, week_monday, source_sha256)
    if not apply:
        return proposal
    if not proposal_sha256:
        raise ProposalChangedError(
            "--proposal-sha256 is required with --apply")
    Path(schedule_dir).mkdir(parents=True, exist_ok=True)
    with _locked(schedule_dir):
        proposal = build_range_repair_proposal(
            schedule_dir, week_monday, source_sha256)
        if proposal["sha256"] != proposal_sha256:
            raise ProposalChangedError(
                "proposal changed; review a new dry-run before applying "
                f"(expected {proposal_sha256}, actual {proposal['sha256']})")
        if proposal["destination_after"] != proposal["destination_before"]:
            _atomic_write(
                proposal["destination_path"],
                proposal["destination_after"],
            )
    return proposal
def run_scheduled(schedule_dir, now=None):
    """Catch up every uncompleted Pacific Monday boundary in order."""
    current_boundary = active_boundary_monday(now)
    last_completed = _load_state(schedule_dir)
    if last_completed > current_boundary:
        raise ValueError(
            f"rollover state is ahead of Pacific time: {last_completed}")
    if last_completed == current_boundary:
        return []
    completed = []
    with _locked(schedule_dir):
        last_completed = _load_state(schedule_dir)
        if last_completed > current_boundary:
            raise ValueError(
                f"rollover state is ahead of Pacific time: {last_completed}")
        boundary = last_completed + timedelta(days=7)
        while boundary <= current_boundary:
            proposal = build_proposal(schedule_dir, boundary)
            apply_proposal(proposal)
            _atomic_write(
                _path(schedule_dir, STATE_FILENAME),
                _state_content(boundary),
            )
            completed.append(proposal)
            boundary += timedelta(days=7)
    return completed
def _print_scheduled_result(completed):
    """Print only meaningful scheduled work; no-op ticks stay silent."""
    for proposal in completed:
        print(
            "weekly-rollover-complete: "
            f"boundary={proposal['boundary']} "
            f"next-week={proposal['target_monday']}..{proposal['target_sunday']} "
            f"moved={len(proposal['inventory'])} "
            f"proposal-sha256={proposal['sha256']}"
        )
def main():
    """Run scheduled catch-up or the guarded one-time bootstrap."""
    parser = argparse.ArgumentParser(
        description="Transactional Pacific family-schedule weekly rollover")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scheduled_parser = subparsers.add_parser(
        "scheduled", help="catch up completed Pacific Monday boundaries")
    scheduled_parser.add_argument("schedule_dir")
    scheduled_parser.add_argument(
        "--now", help="inject an ISO datetime for tests/diagnostics")
    bootstrap_parser = subparsers.add_parser(
        "bootstrap", help="preview current Next Week migration (dry-run default)")
    bootstrap_parser.add_argument("schedule_dir")
    bootstrap_parser.add_argument(
        "--now", help="inject an ISO datetime for tests/diagnostics")
    bootstrap_parser.add_argument("--apply", action="store_true")
    bootstrap_parser.add_argument("--proposal-sha256")
    repair_parser = subparsers.add_parser(
        "repair-range",
        help="preview one legacy weekly range conversion (dry-run default)",
    )
    repair_parser.add_argument("schedule_dir")
    repair_parser.add_argument(
        "week_monday", help="Monday date naming the destination weekly file")
    repair_parser.add_argument(
        "--source-sha256",
        required=True,
        help="exact SHA-256 from the legacy family-schedule-source marker",
    )
    repair_parser.add_argument("--apply", action="store_true")
    repair_parser.add_argument("--proposal-sha256")
    args = parser.parse_args()
    try:
        if args.command == "scheduled":
            _print_scheduled_result(
                run_scheduled(args.schedule_dir, now=args.now))
            return
        if args.command == "repair-range":
            proposal = repair_range(
                args.schedule_dir,
                args.week_monday,
                args.source_sha256,
                apply=args.apply,
                proposal_sha256=args.proposal_sha256,
            )
            print(render_range_repair_proposal(proposal), end="")
            if args.apply:
                print(
                    "range-repair-applied: "
                    f"week={proposal['week_monday']} "
                    f"source-sha256={proposal['source_sha256']}"
                )
            return
        proposal = bootstrap(
            args.schedule_dir,
            now=args.now,
            apply=args.apply,
            proposal_sha256=args.proposal_sha256,
        )
        print(render_proposal(proposal), end="")
        if args.apply:
            print(f"bootstrap-applied: {proposal['boundary']}")
    except (
        BootstrapRequiredError,
        FileNotFoundError,
        ProposalChangedError,
        TypeError,
        ValueError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(2)
if __name__ == "__main__":
    main()
