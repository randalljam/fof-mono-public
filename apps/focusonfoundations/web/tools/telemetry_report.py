#!/usr/bin/env python3
"""Developer report for applet telemetry SQLite session files.

Usage from apps/focusonfoundations/web:
    ../../../.venv/bin/python3 tools/telemetry_report.py <path> [--events]

The path may be a single .sqlite file or a directory containing telemetry session files.
Directory input picks the newest .sqlite file by filename sort.
"""
import argparse
import json
import os
import sqlite3
import sys

### Path selection
def select_session_path(path):
    if os.path.isdir(path):
        names = []
        for name in os.listdir(path):
            full_path = os.path.join(path, name)
            if name.endswith(".sqlite") and os.path.isfile(full_path):
                names.append(name)
        names.sort()
        if not names:
            raise ValueError("no .sqlite files found in directory: " + path)
        return os.path.join(path, names[-1])
    if not os.path.exists(path):
        raise ValueError("session path not found: " + path)
    if not os.path.isfile(path):
        raise ValueError("session path is not a file or directory: " + path)
    if not path.endswith(".sqlite"):
        raise ValueError("session file must end with .sqlite: " + path)
    return path
### Loading
def row_dicts(rows):
    return [dict(row) for row in rows]
def parse_detail_json(text):
    if text is None or text == "":
        return {}
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return {}
    if isinstance(value, dict):
        return value
    return {}
def load_report(path):
    session_path = select_session_path(path)
    conn = sqlite3.connect(session_path)
    conn.row_factory = sqlite3.Row
    try:
        session_row = conn.execute("""SELECT session_id, session_filename, applet, user_name, start_time, end_time,
          duration_ms, total_clicks, total_quiz_attempts
          FROM Sessions ORDER BY session_id LIMIT 1""").fetchone()
        if session_row is None:
            raise ValueError("no Sessions row found in: " + session_path)
        session = dict(session_row)
        session["event_count"] = conn.execute("SELECT COUNT(*) FROM Events").fetchone()[0]
        events = row_dicts(conn.execute("""SELECT event_id, session_id, t_ms, kind, step, target, detail_json
          FROM Events ORDER BY event_id""").fetchall())
        for event in events:
            event["detail"] = parse_detail_json(event.get("detail_json"))
        step_visits = row_dicts(conn.execute("""SELECT visit_id, session_id, step, enter_t_ms, leave_t_ms, duration_ms
          FROM StepVisits ORDER BY visit_id""").fetchall())
        quiz_attempts = row_dicts(conn.execute("""SELECT attempt_id, session_id, quiz, round, attempt_index, prompt, given,
          is_correct, t_ms, response_time_ms
          FROM QuizAttempts ORDER BY attempt_id""").fetchall())
    finally:
        conn.close()
    return {
        "path": session_path,
        "session": session,
        "events": events,
        "step_visits": step_visits,
        "quiz_attempts": quiz_attempts,
        "step_titles": derive_step_titles(events),
    }
### Time formatting
def to_int(value, default=0):
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default
def format_m_ss(value):
    total_seconds = max(0, to_int(value, 0)) // 1000
    return "%d:%02d" % (total_seconds // 60, total_seconds % 60)
def format_m_ss_mmm(value):
    ms = max(0, to_int(value, 0))
    total_seconds = ms // 1000
    return "%d:%02d.%03d" % (total_seconds // 60, total_seconds % 60, ms % 1000)
def format_seconds(value):
    if value is None:
        return "open"
    ms = to_int(value, 0)
    if ms % 1000 == 0:
        return str(ms // 1000)
    return ("%.3f" % (ms / 1000.0)).rstrip("0").rstrip(".")
def format_percent(part_ms, total_ms):
    total = to_int(total_ms, 0)
    if total <= 0:
        return "0.0%"
    return "%.1f%%" % (to_int(part_ms, 0) * 100.0 / total)
def format_rate_per_minute(count, duration_ms):
    duration = to_int(duration_ms, 0)
    if duration <= 0:
        return "n/a"
    return "%.2f" % (count * 60000.0 / duration)
def format_ms(value):
    if value is None:
        return "-"
    return str(value)
def format_avg_ms(value):
    if value is None:
        return "-"
    if int(value) == value:
        return str(int(value))
    return ("%.1f" % value).rstrip("0").rstrip(".")
### Step titles
def title_text(value):
    if value is None:
        return None
    text = str(value)
    if text == "":
        return None
    return text
def title_from_step_item(item):
    if isinstance(item, dict):
        for key in ("title", "name", "label"):
            text = title_text(item.get(key))
            if text:
                return text
        return None
    return title_text(item)
def derive_step_titles(events):
    start_titles = {}
    enter_titles = {}
    for event in events:
        if event.get("kind") == "applet-start":
            steps = event.get("detail", {}).get("steps")
            if isinstance(steps, list):
                for index, item in enumerate(steps):
                    title = title_from_step_item(item)
                    if title and index not in start_titles:
                        start_titles[index] = title
    for event in events:
        if event.get("kind") == "step-enter":
            step = event.get("step")
            title = title_text(event.get("detail", {}).get("title"))
            if step is not None and title and step not in enter_titles:
                enter_titles[step] = title
    titles = {}
    for step in start_titles:
        titles[step] = start_titles[step]
    for step in enter_titles:
        titles[step] = enter_titles[step]
    return titles
def display_step(step):
    if step is None:
        return "-"
    return str(step)
def resolve_step_title(titles, step):
    if step in titles:
        return titles[step]
    return "step " + display_step(step)
### Aggregation
def step_sort_key(item):
    step = item.get("step")
    if step is None:
        return (1, 0)
    return (0, step)
def aggregate_steps(step_visits, titles):
    grouped = {}
    for visit in step_visits:
        step = visit.get("step")
        if step not in grouped:
            grouped[step] = {"step": step, "title": resolve_step_title(titles, step), "visit_count": 0, "duration_ms": 0}
        grouped[step]["visit_count"] += 1
        if visit.get("duration_ms") is not None:
            grouped[step]["duration_ms"] += to_int(visit.get("duration_ms"), 0)
    values = list(grouped.values())
    values.sort(key=step_sort_key)
    return values
def aggregate_counts(events, key_name, predicate):
    counts = {}
    for event in events:
        if predicate(event):
            key = event.get(key_name)
            if key is None or key == "":
                key = "(none)"
            counts[key] = counts.get(key, 0) + 1
    values = [{"name": key, "count": counts[key]} for key in counts]
    values.sort(key=lambda item: (-item["count"], str(item["name"])))
    return values
def is_correct_attempt(attempt):
    return to_int(attempt.get("is_correct"), 0) == 1
def build_round_summary(round_value, attempts):
    prompt = ""
    for attempt in attempts:
        if attempt.get("prompt") is not None:
            prompt = str(attempt.get("prompt"))
            break
    outcomes = ["ok" if is_correct_attempt(attempt) else "x" for attempt in attempts]
    times = [attempt.get("response_time_ms") for attempt in attempts]
    return {
        "round": round_value,
        "prompt": prompt,
        "tries": len(attempts),
        "outcomes": outcomes,
        "outcome_sequence": " ".join(outcomes),
        "response_times": times,
        "response_time_sequence": " ".join(format_ms(value) for value in times),
    }
def build_quiz_summary(quiz, attempts, round_order, round_map):
    correct = sum(1 for attempt in attempts if is_correct_attempt(attempt))
    response_times = [attempt.get("response_time_ms") for attempt in attempts if attempt.get("response_time_ms") is not None]
    avg_response = None
    max_response = None
    if response_times:
        avg_response = sum(response_times) * 1.0 / len(response_times)
        max_response = max(response_times)
    rounds = [build_round_summary(round_value, round_map[round_value]) for round_value in round_order]
    return {
        "quiz": quiz,
        "round_count": len(round_order),
        "total_attempts": len(attempts),
        "correct": correct,
        "wrong": len(attempts) - correct,
        "avg_response_time_ms": avg_response,
        "max_response_time_ms": max_response,
        "rounds": rounds,
    }
def aggregate_quizzes(quiz_attempts):
    quiz_order = []
    quiz_map = {}
    for attempt in quiz_attempts:
        quiz = attempt.get("quiz")
        if quiz is None or quiz == "":
            quiz = "(none)"
        if quiz not in quiz_map:
            quiz_order.append(quiz)
            quiz_map[quiz] = {"attempts": [], "round_order": [], "round_map": {}}
        entry = quiz_map[quiz]
        entry["attempts"].append(attempt)
        round_value = attempt.get("round")
        if round_value not in entry["round_map"]:
            entry["round_order"].append(round_value)
            entry["round_map"][round_value] = []
        entry["round_map"][round_value].append(attempt)
    return [build_quiz_summary(quiz, quiz_map[quiz]["attempts"], quiz_map[quiz]["round_order"], quiz_map[quiz]["round_map"]) for quiz in quiz_order]
### JSON formatting
def omit_nulls(value):
    if isinstance(value, dict):
        clean = {}
        for key in value:
            if value[key] is not None:
                clean[key] = omit_nulls(value[key])
        return clean
    if isinstance(value, list):
        return [omit_nulls(item) for item in value if item is not None]
    return value
def compact_json(value):
    return json.dumps(omit_nulls(value), sort_keys=True, separators=(",", ":"))
### Table formatting
def table_widths(headers, rows):
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(str(value)))
    return widths
def format_table(headers, rows, indent="  "):
    if not rows:
        return [indent + "(none)"]
    widths = table_widths(headers, rows)
    lines = []
    lines.append(indent + "  ".join(str(headers[index]).ljust(widths[index]) for index in range(len(headers))))
    lines.append(indent + "  ".join("-" * widths[index] for index in range(len(headers))))
    for row in rows:
        lines.append(indent + "  ".join(str(row[index]).ljust(widths[index]) for index in range(len(row))))
    return lines
def section_gap(lines):
    if lines:
        lines.append("")
### Report formatting
def format_session_section(report):
    session = report["session"]
    fields = [
        ("filename", os.path.basename(report["path"])),
        ("applet", session.get("applet") or ""),
        ("user", session.get("user_name") or ""),
        ("start_time", session.get("start_time") or ""),
        ("end_time", session.get("end_time") or ""),
        ("duration", format_m_ss(session.get("duration_ms"))),
        ("event_count", session.get("event_count")),
        ("total_clicks", session.get("total_clicks")),
        ("total_quiz_attempts", session.get("total_quiz_attempts")),
    ]
    width = max(len(field[0]) for field in fields)
    lines = ["SESSION"]
    for label, value in fields:
        lines.append("  " + label.ljust(width) + "  " + str(value))
    return lines
def format_step_timeline_section(report):
    titles = report["step_titles"]
    rows = []
    for visit in report["step_visits"]:
        rows.append([
            display_step(visit.get("step")),
            resolve_step_title(titles, visit.get("step")),
            format_m_ss(visit.get("enter_t_ms")),
            format_seconds(visit.get("duration_ms")),
        ])
    lines = ["STEP TIMELINE"]
    lines.extend(format_table(["step", "title", "enter", "duration_s"], rows))
    return lines
def format_time_per_step_section(report):
    total_ms = report["session"].get("duration_ms")
    rows = []
    for item in aggregate_steps(report["step_visits"], report["step_titles"]):
        rows.append([
            display_step(item.get("step")),
            item.get("title"),
            item.get("visit_count"),
            format_seconds(item.get("duration_ms")),
            format_percent(item.get("duration_ms"), total_ms),
        ])
    lines = ["TIME PER STEP"]
    lines.extend(format_table(["step", "title", "visits", "total_s", "pct"], rows))
    return lines
def format_quizzes_section(report):
    lines = ["QUIZZES"]
    quizzes = aggregate_quizzes(report["quiz_attempts"])
    if not quizzes:
        lines.append("  (none)")
        return lines
    for index, quiz in enumerate(quizzes):
        if index > 0:
            lines.append("")
        lines.append("  quiz %-20s rounds=%s attempts=%s correct=%s wrong=%s avg_ms=%s max_ms=%s" % (
            quiz["quiz"],
            quiz["round_count"],
            quiz["total_attempts"],
            quiz["correct"],
            quiz["wrong"],
            format_avg_ms(quiz["avg_response_time_ms"]),
            format_ms(quiz["max_response_time_ms"]),
        ))
        rows = []
        for round_item in quiz["rounds"]:
            rows.append([
                display_step(round_item.get("round")),
                round_item.get("prompt"),
                round_item.get("tries"),
                round_item.get("outcome_sequence"),
                round_item.get("response_time_sequence"),
            ])
        lines.extend(format_table(["round", "prompt", "tries", "outcomes", "response_ms"], rows, indent="    "))
    return lines
def format_activity_section(report):
    session = report["session"]
    events = report["events"]
    lines = ["ACTIVITY"]
    lines.append("  events_per_minute  " + format_rate_per_minute(session.get("event_count"), session.get("duration_ms")))
    lines.append("  count by kind")
    kind_rows = [[item["name"], item["count"]] for item in aggregate_counts(events, "kind", lambda event: True)]
    lines.extend(format_table(["kind", "count"], kind_rows, indent="    "))
    lines.append("  top click targets")
    click_rows = [[item["name"], item["count"]] for item in aggregate_counts(events, "target", lambda event: event.get("kind") == "click")[:10]]
    lines.extend(format_table(["target", "count"], click_rows, indent="    "))
    return lines
def format_events_section(report):
    rows = []
    for event in report["events"]:
        rows.append([
            format_m_ss_mmm(event.get("t_ms")),
            event.get("kind") or "",
            display_step(event.get("step")),
            event.get("target") if event.get("target") is not None else "-",
            compact_json(event.get("detail", {})),
        ])
    lines = ["EVENTS"]
    lines.extend(format_table(["time", "kind", "step", "target", "detail_json"], rows))
    return lines
def format_report(report, include_events=False):
    lines = []
    for section in (
        format_session_section(report),
        format_step_timeline_section(report),
        format_time_per_step_section(report),
        format_quizzes_section(report),
        format_activity_section(report),
    ):
        section_gap(lines)
        lines.extend(section)
    if include_events:
        section_gap(lines)
        lines.extend(format_events_section(report))
    return "\n".join(lines)
### CLI
def build_parser():
    parser = argparse.ArgumentParser(description="Print a developer report for an applet telemetry SQLite session file.")
    parser.add_argument("path", help="A .sqlite telemetry session file, or a directory containing session files.")
    parser.add_argument("--events", action="store_true", help="Append the full raw event timeline.")
    return parser
def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        print(format_report(load_report(args.path), include_events=args.events))
        return 0
    except Exception as exc:
        print("telemetry_report: error: " + str(exc), file=sys.stderr)
        return 1
if __name__ == "__main__":
    sys.exit(main())
