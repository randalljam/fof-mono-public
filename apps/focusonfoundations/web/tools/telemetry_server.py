#!/usr/bin/env python3
"""Localhost-only applet telemetry receiver.

Run from apps/focusonfoundations/web:
    ../../../.venv/bin/python3 tools/telemetry_server.py

The React applets POST full session buffers to http://localhost:8787/api/save-session.
Each request rebuilds one SQLite file under _data/applet-sessions/ atomically. This tool is
for local development only and should never be deployed.
"""
import http.server
import sqlite3
import json
import os
import re

### Config
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(APP_DIR, "_data", "applet-sessions")
PORT = int(os.environ.get("TELEMETRY_PORT", "8787"))
TOKEN_RE = re.compile(r"[^A-Za-z0-9_-]+")
APPLET_RE = re.compile(r"^[A-Za-z0-9_-]+$")
USER_RE = re.compile(r"^[A-Za-z0-9_-]+$")
STAMP_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})_(\d{2})(\d{2})(\d{2})$")
FILENAME_RE = re.compile(r"^[A-Za-z0-9_-]+_[A-Za-z0-9_-]+_\d{4}-\d{2}-\d{2}_\d{6}\.sqlite$")

### Validation
def has_path_separator(value):
    text = str(value or "")
    return "/" in text or "\\" in text or text in (".", "..")
def sanitize_token(value, fallback):
    if has_path_separator(value):
        raise ValueError("path separators are not allowed")
    clean = TOKEN_RE.sub("", str(value or ""))
    return clean or fallback
def is_leap_year(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
def month_days(year, month):
    if month == 2:
        return 29 if is_leap_year(year) else 28
    if month in (4, 6, 9, 11):
        return 30
    return 31
def validate_stamp(stamp):
    match = STAMP_RE.match(str(stamp or ""))
    if not match:
        raise ValueError("bad start_stamp")
    year, month, day, hour, minute, second = [int(part) for part in match.groups()]
    if month < 1 or month > 12:
        raise ValueError("bad start_stamp")
    if day < 1 or day > month_days(year, month):
        raise ValueError("bad start_stamp")
    if hour > 23 or minute > 59 or second > 59:
        raise ValueError("bad start_stamp")
    return stamp
def stamp_to_wall_time(stamp):
    validate_stamp(stamp)
    return stamp[:10] + " " + stamp[11:13] + ":" + stamp[13:15] + ":" + stamp[15:17]
def valid_wall_time(value):
    text = str(value or "")
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$", text)
    if not match:
        return False
    try:
        validate_stamp(text[:10] + "_" + text[11:13] + text[14:16] + text[17:19])
        return True
    except ValueError:
        return False
def session_identity(payload):
    applet = sanitize_token(payload.get("applet"), "applet")
    user = sanitize_token(payload.get("user"), "anon")
    stamp = validate_stamp(payload.get("start_stamp"))
    if not APPLET_RE.match(applet) or not USER_RE.match(user):
        raise ValueError("bad applet or user")
    filename = applet + "_" + user + "_" + stamp + ".sqlite"
    if not FILENAME_RE.match(filename):
        raise ValueError("bad session filename")
    session_id = payload.get("session_id") or filename[:-7]
    if has_path_separator(session_id):
        raise ValueError("bad session_id")
    session_id = sanitize_token(session_id, filename[:-7])
    if session_id != filename[:-7]:
        raise ValueError("session_id does not match filename")
    start_wall_time = payload.get("start_wall_time")
    if not valid_wall_time(start_wall_time):
        start_wall_time = stamp_to_wall_time(stamp)
    return {"applet": applet, "user": user, "stamp": stamp, "filename": filename, "session_id": session_id, "start_wall_time": start_wall_time}
def safe_session_filename(payload):
    return session_identity(payload)["filename"]

### Time
def add_days(year, month, day, extra_days):
    while extra_days > 0:
        days_this_month = month_days(year, month)
        if day + extra_days <= days_this_month:
            day += extra_days
            extra_days = 0
        else:
            extra_days -= days_this_month - day + 1
            day = 1
            month += 1
            if month > 12:
                month = 1
                year += 1
    return year, month, day
def wall_time_add_ms(start_wall_time, duration_ms):
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$", start_wall_time)
    if not match:
        return start_wall_time
    year, month, day, hour, minute, second = [int(part) for part in match.groups()]
    total_seconds = hour * 3600 + minute * 60 + second + max(0, int(duration_ms or 0)) // 1000
    extra_days = total_seconds // 86400
    rem = total_seconds % 86400
    hour = rem // 3600
    rem = rem % 3600
    minute = rem // 60
    second = rem % 60
    year, month, day = add_days(year, month, day, extra_days)
    return "%04d-%02d-%02d %02d:%02d:%02d" % (year, month, day, hour, minute, second)

### Event normalization
def to_int(value, default=None):
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default
def normalized_detail(detail):
    if isinstance(detail, dict):
        return detail
    return {}
def normalize_events(events):
    out = []
    if not isinstance(events, list):
        return out
    for event in events:
        if not isinstance(event, dict):
            continue
        out.append({
            "t_ms": max(0, to_int(event.get("t_ms"), 0)),
            "kind": str(event.get("kind") or ""),
            "step": to_int(event.get("step"), None),
            "target": None if event.get("target") is None else str(event.get("target")),
            "detail": normalized_detail(event.get("detail")),
        })
    return out
def detail_json(detail):
    try:
        return json.dumps(detail, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return json.dumps(str(detail))

### Derivations
def derive_step_visits(events):
    visits = []
    open_visit = None
    for event in events:
        if event.get("kind") == "step-enter":
            if open_visit is not None:
                visits.append(open_visit)
            open_visit = {"step": event.get("step"), "enter_t_ms": event.get("t_ms"), "leave_t_ms": None, "duration_ms": None}
        elif event.get("kind") == "step-leave" and open_visit is not None:
            if event.get("step") == open_visit.get("step"):
                leave_t_ms = event.get("t_ms")
                open_visit["leave_t_ms"] = leave_t_ms
                open_visit["duration_ms"] = leave_t_ms - open_visit["enter_t_ms"] if leave_t_ms is not None and open_visit.get("enter_t_ms") is not None else None
                visits.append(open_visit)
                open_visit = None
    if open_visit is not None:
        visits.append(open_visit)
    return visits
def quiz_key(detail):
    return (str(detail.get("quiz") or ""), str(detail.get("round") if detail.get("round") is not None else ""))
def detail_bool(value):
    if value is True or value == 1 or value == "1" or value == "true" or value == "True":
        return 1
    return 0
def derive_quiz_attempts(events):
    attempts = []
    round_start = {}
    attempt_counts = {}
    for event in events:
        detail = normalized_detail(event.get("detail"))
        key = quiz_key(detail)
        if event.get("kind") == "quiz-round":
            round_start[key] = event.get("t_ms")
            attempt_counts[key] = 0
        elif event.get("kind") == "quiz-attempt":
            attempt_counts[key] = attempt_counts.get(key, 0) + 1
            start_t_ms = round_start.get(key)
            response_time_ms = event.get("t_ms") - start_t_ms if start_t_ms is not None else None
            attempts.append({
                "quiz": detail.get("quiz"),
                "round": to_int(detail.get("round"), None),
                "attempt_index": attempt_counts[key],
                "prompt": detail.get("prompt"),
                "given": detail.get("given"),
                "is_correct": detail_bool(detail.get("isCorrect", detail.get("is_correct"))),
                "t_ms": event.get("t_ms"),
                "response_time_ms": response_time_ms,
            })
    return attempts

### SQLite
def create_tables(conn):
    conn.executescript("""
CREATE TABLE Users (
  name TEXT PRIMARY KEY
);
CREATE TABLE Sessions (
  session_id TEXT PRIMARY KEY,
  session_filename TEXT,
  applet TEXT,
  user_name TEXT,
  start_time TEXT,
  end_time TEXT,
  duration_ms INTEGER,
  user_agent TEXT,
  total_clicks INTEGER,
  total_quiz_attempts INTEGER,
  FOREIGN KEY (user_name) REFERENCES Users(name)
);
CREATE TABLE Events (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT,
  t_ms INTEGER,
  kind TEXT,
  step INTEGER,
  target TEXT,
  detail_json TEXT,
  FOREIGN KEY (session_id) REFERENCES Sessions(session_id)
);
CREATE TABLE StepVisits (
  visit_id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT,
  step INTEGER,
  enter_t_ms INTEGER,
  leave_t_ms INTEGER,
  duration_ms INTEGER,
  FOREIGN KEY (session_id) REFERENCES Sessions(session_id)
);
CREATE TABLE QuizAttempts (
  attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT,
  quiz TEXT,
  round INTEGER,
  attempt_index INTEGER,
  prompt TEXT,
  given TEXT,
  is_correct INTEGER,
  t_ms INTEGER,
  response_time_ms INTEGER,
  FOREIGN KEY (session_id) REFERENCES Sessions(session_id)
);
""")
def save_payload(payload, data_dir=None):
    identity = session_identity(payload)
    events = normalize_events(payload.get("events"))
    step_visits = derive_step_visits(events)
    quiz_attempts = derive_quiz_attempts(events)
    duration_ms = events[-1]["t_ms"] if events else 0
    end_time = wall_time_add_ms(identity["start_wall_time"], duration_ms)
    total_clicks = sum(1 for event in events if event.get("kind") == "click")
    total_quiz_attempts = sum(1 for event in events if event.get("kind") == "quiz-attempt")
    out_dir = data_dir or DATA_DIR
    os.makedirs(out_dir, exist_ok=True)
    final_path = os.path.join(out_dir, identity["filename"])
    tmp_path = final_path + ".tmp"
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    conn = sqlite3.connect(tmp_path)
    try:
        create_tables(conn)
        conn.execute("INSERT INTO Users (name) VALUES (?)", (identity["user"],))
        conn.execute("""INSERT INTO Sessions
          (session_id, session_filename, applet, user_name, start_time, end_time, duration_ms, user_agent, total_clicks, total_quiz_attempts)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
          (identity["session_id"], identity["filename"], identity["applet"], identity["user"], identity["start_wall_time"], end_time, duration_ms, str(payload.get("user_agent") or ""), total_clicks, total_quiz_attempts))
        for event in events:
            conn.execute("INSERT INTO Events (session_id, t_ms, kind, step, target, detail_json) VALUES (?, ?, ?, ?, ?, ?)",
                         (identity["session_id"], event["t_ms"], event["kind"], event["step"], event["target"], detail_json(event["detail"])))
        for visit in step_visits:
            conn.execute("INSERT INTO StepVisits (session_id, step, enter_t_ms, leave_t_ms, duration_ms) VALUES (?, ?, ?, ?, ?)",
                         (identity["session_id"], visit["step"], visit["enter_t_ms"], visit["leave_t_ms"], visit["duration_ms"]))
        for attempt in quiz_attempts:
            conn.execute("""INSERT INTO QuizAttempts
              (session_id, quiz, round, attempt_index, prompt, given, is_correct, t_ms, response_time_ms)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (identity["session_id"], attempt["quiz"], attempt["round"], attempt["attempt_index"], attempt["prompt"], attempt["given"], attempt["is_correct"], attempt["t_ms"], attempt["response_time_ms"]))
        conn.commit()
    finally:
        conn.close()
    os.replace(tmp_path, final_path)
    return {"ok": True, "file": identity["filename"], "events": len(events), "path": final_path}

### HTTP
class TelemetryHandler(http.server.BaseHTTPRequestHandler):
    def send_json(self, status, body):
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        origin = self.headers.get("Origin")
        self.send_header("Access-Control-Allow-Origin", origin if origin else "*")
        if origin:
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def do_OPTIONS(self):
        self.send_json(200, {"ok": True})
    def do_GET(self):
        if self.path.split("?", 1)[0] == "/api/health":
            self.send_json(200, {"ok": True})
        else:
            self.send_json(404, {"ok": False, "error": "not found"})
    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/save-session":
            self.send_json(404, {"ok": False, "error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = save_payload(payload)
            self.send_json(200, {"ok": True, "file": result["file"], "events": result["events"]})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
def run():
    server = http.server.HTTPServer(("127.0.0.1", PORT), TelemetryHandler)
    print("Telemetry server listening on http://localhost:%d" % PORT)
    server.serve_forever()
if __name__ == "__main__":
    run()
