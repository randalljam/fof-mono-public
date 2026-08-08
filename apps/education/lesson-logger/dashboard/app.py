import json
import logging
import os
import re
import secrets
import sqlite3
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from html import escape, unescape
from pathlib import Path
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import base64
import markdown

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dashboard")

DASHBOARD_DIR = Path(__file__).resolve().parent
# Local durable files live on the lesson-logger data mount (../data), not a
# per-worktree dashboard/data folder — see scripts/local_files_mounts.txt.
DATA_DIR = DASHBOARD_DIR.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DB = DATA_DIR / "lessons_dev.db"
PREFS_DB = Path(os.environ.get("PREFS_DB", str(DATA_DIR / "dashboard_state.sqlite")))
SCHEDULE_DIR = Path(os.environ.get("SCHEDULE_DIR", str(DASHBOARD_DIR / "schedule_dev")))
PACIFIC = ZoneInfo("America/Los_Angeles")

STANDARD_SUBJECTS = ["Math", "Reading", "Writing", "Art", "Science", "Music"]
SUBJECT_COLORS = {
    "Math": "#6366f1",
    "Reading": "#f59e0b",
    "Writing": "#10b981",
    "Art": "#ec4899",
    "Science": "#3b82f6",
    "Music": "#8b5cf6",
    "History": "#ef4444",
    "Spanish": "#14b8a6",
}
DEFAULT_COLOR = "#94a3b8"

@asynccontextmanager
async def lifespan(app):
    from sync_db import sync_from_hermes
    from sync_schedule import sync_schedule_from_hermes
    sync_from_hermes()
    sync_schedule_from_hermes()
    yield

app = FastAPI(title="Lesson Logger Dashboard", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=DASHBOARD_DIR / "static"), name="static")
templates = Jinja2Templates(directory=DASHBOARD_DIR / "templates")

### Auth
USERS = {}
def _load_users():
    u1 = os.environ.get("DASH_USER1", "randy")
    p1 = os.environ.get("DASH_PASS1", "randy")
    u2 = os.environ.get("DASH_USER2", "tl")
    p2 = os.environ.get("DASH_PASS2", "tl")
    USERS[u1] = p1
    USERS[u2] = p2
    if os.environ.get("DASH_DEV_PASSWORDS", "").lower() in ("1", "true", "yes"):
        USERS["randy"] = "randy"
        USERS["tl"] = "tl"
_load_users()

class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/static"):
            return await call_next(request)
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth[6:]).decode("utf-8")
                username, password = decoded.split(":", 1)
            except Exception:
                username, password = "", ""
            username = username.strip()
            password = password.strip()
            dev_passwords = os.environ.get("DASH_DEV_PASSWORDS", "").lower() in ("1", "true", "yes")
            if dev_passwords and username in ("randy", "tl") and password == username:
                request.state.user = username
                return await call_next(request)
            if username in USERS and secrets.compare_digest(str(USERS[username]).strip(), password):
                request.state.user = username
                return await call_next(request)
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Lesson Logger Dashboard"'},
            content="Unauthorized",
        )

app.add_middleware(BasicAuthMiddleware)

### Preferences DB
def _init_prefs_db():
    conn = sqlite3.connect(str(PREFS_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            username TEXT PRIMARY KEY,
            default_student TEXT DEFAULT '',
            default_time_mode TEXT DEFAULT 'week',
            last_subject_filter TEXT DEFAULT '',
            filters_expanded INTEGER DEFAULT 0,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()
_init_prefs_db()
def get_prefs(username):
    conn = sqlite3.connect(str(PREFS_DB))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM preferences WHERE username = ?", (username,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        "username": username,
        "default_student": "",
        "default_time_mode": "week",
        "last_subject_filter": "",
        "filters_expanded": 0,
    }
def save_prefs(username, prefs):
    conn = sqlite3.connect(str(PREFS_DB))
    conn.execute(
        "INSERT OR REPLACE INTO preferences (username, default_student, default_time_mode, last_subject_filter, filters_expanded, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (username, prefs.get("default_student", ""), prefs.get("default_time_mode", "week"), prefs.get("last_subject_filter", ""), prefs.get("filters_expanded", 0), datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

### Lessons DB
def _has_entries_table(db_path):
    if not os.path.exists(db_path):
        return False
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'entries'").fetchone()
        return row is not None
    finally:
        conn.close()
def get_db():
    db_path = os.environ.get("LESSONS_DB", str(DEFAULT_DB))
    if not _has_entries_table(db_path):
        logger.warning(f"Lessons DB {db_path} is missing entries table; falling back to {DEFAULT_DB}")
        db_path = str(DEFAULT_DB)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_all_students():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT j.value AS student FROM entries e, json_each(e.students) j ORDER BY j.value").fetchall()
    conn.close()
    return [r["student"] for r in rows]

def get_all_subjects():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT subject FROM entries ORDER BY subject").fetchall()
    conn.close()
    return [r["subject"] for r in rows]

def get_all_teachers():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT j.value AS teacher FROM entries e, json_each(e.teachers) j ORDER BY j.value").fetchall()
    conn.close()
    return [r["teacher"] for r in rows]

def get_all_curricula():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT curricula FROM entries WHERE curricula != '' ORDER BY curricula").fetchall()
    conn.close()
    return [r["curricula"] for r in rows]

def get_all_locations():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT location FROM entries WHERE location != '' ORDER BY location").fetchall()
    conn.close()
    return [r["location"] for r in rows]

def get_all_created_by():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT created_by FROM entries WHERE created_by != '' ORDER BY created_by").fetchall()
    conn.close()
    return [r["created_by"] for r in rows]

### Date helpers
def week_range(ref_date):
    monday = ref_date - timedelta(days=ref_date.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday
def month_range(ref_date):
    first = ref_date.replace(day=1)
    if ref_date.month == 12:
        last = date(ref_date.year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(ref_date.year, ref_date.month + 1, 1) - timedelta(days=1)
    return first, last
def learning_year_range(ref_date):
    if ref_date.month >= 9:
        start = date(ref_date.year, 9, 1)
        end = date(ref_date.year + 1, 8, 30)
    else:
        start = date(ref_date.year - 1, 9, 1)
        end = date(ref_date.year, 8, 30)
    return start, end
def format_range_label(mode, start, end):
    if mode == "week":
        return f"Week of {start.strftime('%b %-d')} – {end.strftime('%b %-d, %Y')}"
    elif mode == "month":
        return start.strftime("%B %Y")
    else:
        return f"Learning Year {start.strftime('%Y')}–{end.strftime('%y')}"
def prev_range(mode, start):
    if mode == "week":
        return start - timedelta(days=7)
    elif mode == "month":
        first = start.replace(day=1)
        return (first - timedelta(days=1)).replace(day=1)
    else:
        return date(start.year - 1, 9, 1)
def next_range(mode, start):
    if mode == "week":
        return start + timedelta(days=7)
    elif mode == "month":
        if start.month == 12:
            return date(start.year + 1, 1, 1)
        return date(start.year, start.month + 1, 1)
    else:
        return date(start.year + 1, 9, 1)

### Query
def query_entries(student, start_date, end_date, subject=None, curricula=None, teacher=None, location=None, created_by=None):
    conn = get_db()
    sql = """
        SELECT e.* FROM entries e, json_each(e.students) j
        WHERE j.value = ? AND e.date >= ? AND e.date <= ?
    """
    params = [student, start_date.isoformat(), end_date.isoformat()]
    if subject:
        sql += " AND e.subject = ?"
        params.append(subject)
    if curricula:
        sql += " AND e.curricula = ?"
        params.append(curricula)
    if teacher:
        sql += " AND EXISTS (SELECT 1 FROM json_each(e.teachers) t WHERE t.value = ?)"
        params.append(teacher)
    if location:
        sql += " AND e.location = ?"
        params.append(location)
    if created_by:
        sql += " AND e.created_by = ?"
        params.append(created_by)
    sql += " ORDER BY e.date DESC, e.created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

### Aggregation helpers
def compute_summary(entries):
    total_minutes = sum(e["duration"] or 0 for e in entries)
    total_sessions = len(entries)
    subjects_covered = len(set(e["subject"] for e in entries if e["subject"]))
    active_days = len(set(e["date"] for e in entries))
    avg_per_active_day = round(total_minutes / active_days) if active_days > 0 else 0
    hours = total_minutes // 60
    mins = total_minutes % 60
    if hours > 0:
        time_display = f"{hours}h {mins}m"
    else:
        time_display = f"{mins}m"
    return {
        "total_minutes": total_minutes,
        "time_display": time_display,
        "total_sessions": total_sessions,
        "subjects_covered": subjects_covered,
        "active_days": active_days,
        "avg_per_active_day": avg_per_active_day,
    }
def compute_subject_breakdown(entries):
    by_subject = {}
    for e in entries:
        subj = e["subject"] or "Other"
        by_subject.setdefault(subj, 0)
        by_subject[subj] += e["duration"] or 0
    ordered = []
    for s in STANDARD_SUBJECTS:
        if s in by_subject:
            ordered.append({"subject": s, "minutes": by_subject.pop(s), "color": SUBJECT_COLORS.get(s, DEFAULT_COLOR)})
    for s in sorted(by_subject.keys()):
        ordered.append({"subject": s, "minutes": by_subject[s], "color": SUBJECT_COLORS.get(s, DEFAULT_COLOR)})
    return ordered
def compute_consistency(entries, mode, start_date, end_date):
    daily = {}
    for e in entries:
        daily.setdefault(e["date"], 0)
        daily[e["date"]] += e["duration"] or 0
    if mode == "week":
        days = []
        current = start_date
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i in range(7):
            d = current + timedelta(days=i)
            days.append({"label": day_names[i], "date": d.isoformat(), "minutes": daily.get(d.isoformat(), 0)})
        return days
    elif mode == "month":
        days = []
        current = start_date
        while current <= end_date:
            days.append({"label": str(current.day), "date": current.isoformat(), "minutes": daily.get(current.isoformat(), 0)})
            current += timedelta(days=1)
        return days
    else:
        months = []
        current = start_date
        while current <= end_date:
            month_start = current
            if current.month == 12:
                month_end = date(current.year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(current.year, current.month + 1, 1) - timedelta(days=1)
            month_end = min(month_end, end_date)
            total = sum(v for k, v in daily.items() if month_start.isoformat() <= k <= month_end.isoformat())
            months.append({"label": current.strftime("%b"), "date": current.isoformat(), "minutes": total})
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)
        return months
def compute_curricula_breakdown(entries):
    groups = {}
    for e in entries:
        subj = e["subject"] or "Other"
        curr = e["curricula"] or "Not specified"
        key = (subj, curr)
        if key not in groups:
            groups[key] = {"subject": subj, "curricula": curr, "minutes": 0, "sessions": 0, "color": SUBJECT_COLORS.get(subj, DEFAULT_COLOR)}
        groups[key]["minutes"] += e["duration"] or 0
        groups[key]["sessions"] += 1
    by_subject = {}
    for item in groups.values():
        by_subject.setdefault(item["subject"], []).append(item)
    ordered = {}
    for s in STANDARD_SUBJECTS:
        if s in by_subject:
            ordered[s] = sorted(by_subject.pop(s), key=lambda x: -x["minutes"])
    for s in sorted(by_subject.keys()):
        ordered[s] = sorted(by_subject[s], key=lambda x: -x["minutes"])
    return ordered

### Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    mode: str = None,
    student: str = None,
    ref: str = None,
    subject: str = None,
    curricula: str = None,
    teacher: str = None,
    location: str = None,
    created_by: str = None,
):
    username = request.state.user
    prefs = get_prefs(username)
    all_students = get_all_students()
    if not mode:
        mode = prefs.get("default_time_mode", "week")
    if mode not in ("week", "month", "year"):
        mode = "week"
    if not student:
        student = prefs.get("default_student") or (all_students[0] if all_students else "")
    if ref:
        try:
            ref_date = date.fromisoformat(ref)
        except ValueError:
            ref_date = date.today()
    else:
        ref_date = date.today()
    if mode == "week":
        start_date, end_date = week_range(ref_date)
    elif mode == "month":
        start_date, end_date = month_range(ref_date)
    else:
        start_date, end_date = learning_year_range(ref_date)
    range_label = format_range_label(mode, start_date, end_date)
    prev_ref = prev_range(mode, start_date).isoformat()
    next_ref = next_range(mode, start_date).isoformat()
    entries = query_entries(student, start_date, end_date, subject=subject, curricula=curricula, teacher=teacher, location=location, created_by=created_by)
    summary = compute_summary(entries)
    subject_breakdown = compute_subject_breakdown(entries)
    consistency = compute_consistency(entries, mode, start_date, end_date)
    curricula_breakdown = compute_curricula_breakdown(entries)
    recent = entries[:15]
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "username": username,
        "student": student,
        "mode": mode,
        "ref": ref_date.isoformat(),
        "range_label": range_label,
        "prev_ref": prev_ref,
        "next_ref": next_ref,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "summary": summary,
        "subject_breakdown": subject_breakdown,
        "subject_breakdown_json": json.dumps(subject_breakdown),
        "consistency": consistency,
        "consistency_json": json.dumps(consistency),
        "curricula_breakdown": curricula_breakdown,
        "recent": recent,
        "all_students": all_students,
        "all_subjects": get_all_subjects(),
        "all_teachers": get_all_teachers(),
        "all_curricula": get_all_curricula(),
        "all_locations": get_all_locations(),
        "all_created_by": get_all_created_by(),
        "filter_subject": subject or "",
        "filter_curricula": curricula or "",
        "filter_teacher": teacher or "",
        "filter_location": location or "",
        "filter_created_by": created_by or "",
        "subject_colors": SUBJECT_COLORS,
        "prefs": prefs,
    })
### Schedule
SCHEDULE_FILES = {
    "current-week.md": "This Week",
    "next-week.md": "Next Week",
    "horizon.md": "Horizon",
}
SCHEDULE_TOOLTIPS = (
    {
        "heading_pattern": r"Recurring",
        "label": "Recurring",
        "slug": "recurring",
        "description": "Weekly/regular activities with defaults.",
        "copy_prefix": "weekly/regular activities",
    },
    {
        "heading_pattern": r"Upcoming",
        "label": "Upcoming",
        "slug": "upcoming",
        "description": "Items with known dates, not yet in a week file.",
        "copy_prefix": "items with known dates",
    },
    {
        "heading_pattern": r"Next (?:2|Two) Weeks",
        "label": "Next Two Weeks",
        "slug": "next-two-weeks",
        "description": "Dates within 14 days of the horizon start date.",
        "copy_prefix": "dates within 14 days",
    },
    {
        "heading_pattern": r"This Month",
        "label": "This Month",
        "slug": "this-month",
        "description": "Same calendar month, beyond 2 weeks out.",
        "copy_prefix": "same calendar month",
    },
    {
        "heading_pattern": r"Later",
        "label": "Later",
        "slug": "later",
        "description": "Next month and beyond. Dates can be approximate.",
        "copy_prefix": "next month and beyond",
    },
    {
        "heading_pattern": r"Notes",
        "label": "Notes",
        "slug": "notes",
        "description": "General scheduling notes, preferences, standing arrangements.",
        "copy_prefix": "general scheduling notes",
    },
)
def _extract_schedule_metadata(text):
    """Remove leading file/week metadata from Markdown and return it separately."""
    metadata = {}
    body = []
    reading_metadata = True
    for line in text.splitlines():
        if reading_metadata:
            match = re.fullmatch(r"(file|week):\s*(.*)", line.strip(), flags=re.IGNORECASE)
            if match:
                metadata[match.group(1).lower()] = match.group(2).strip()
                continue
            if not line.strip():
                continue
            reading_metadata = False
        body.append(line)
    return "\n".join(body), metadata
def _decorate_horizon_headings(html):
    """Move Horizon subsection help text into accessible hover/focus tooltips."""
    for tooltip in SCHEDULE_TOOLTIPS:
        heading_pattern = re.compile(
            rf"<h(?P<level>[2-6])>\s*{tooltip['heading_pattern']}\s*</h(?P=level)>",
            flags=re.IGNORECASE,
        )
        match = heading_pattern.search(html)
        if not match:
            continue
        tooltip_html = escape(tooltip["description"])
        content_end = match.end()
        following = html[match.end():]
        paragraph = re.match(r"\s*<p>(?P<copy>.*?)</p>", following, flags=re.DOTALL)
        if paragraph:
            copy_html = paragraph.group("copy")
            copy_text = unescape(re.sub(r"<[^>]+>", "", copy_html)).strip().casefold()
            if copy_text.startswith(tooltip["copy_prefix"]):
                tooltip_html = copy_html
                content_end = match.end() + paragraph.end()
        level = match.group("level")
        tooltip_id = f"schedule-tooltip-{tooltip['slug']}"
        heading = (
            f'<h{level} class="schedule-tooltip-heading" tabindex="0" '
            f'aria-describedby="{tooltip_id}">'
            f'{escape(tooltip["label"])}'
            f'<span class="schedule-tooltip-icon" aria-hidden="true">i</span>'
            f'<span class="schedule-tooltip" id="{tooltip_id}" role="tooltip">'
            f"{tooltip_html}</span>"
            f"</h{level}>"
        )
        html = html[:match.start()] + heading + html[content_end:]
    return html
def _pacific_today(now=None):
    """Return the Pacific calendar date, with deterministic injection for tests."""
    if now is None:
        return datetime.now(PACIFIC).date()
    if now.tzinfo is None:
        now = now.replace(tzinfo=PACIFIC)
    return now.astimezone(PACIFIC).date()

def _decorate_past_week_days(html, metadata, today=None):
    """Mark current-week day headings before today's Pacific date as past."""
    file_metadata = metadata.get("file", "")
    start_match = re.search(r"(\d{4}-\d{2}-\d{2})_week_family-schedule\.md", file_metadata)
    if not start_match:
        week_metadata = metadata.get("week", "")
        start_match = re.match(r"Mon\s+(\d{4}-\d{2}-\d{2})\b", week_metadata)
    if not start_match:
        return html
    try:
        week_start = date.fromisoformat(start_match.group(1))
    except ValueError:
        return html
    today = today or _pacific_today()
    weekday_offsets = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }
    heading_pattern = re.compile(
        r"<h2>(?P<weekday>Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
        r"\s+[^<]+</h2>"
    )
    def decorate(match):
        heading_date = week_start + timedelta(days=weekday_offsets[match.group("weekday")])
        if heading_date < today:
            return match.group(0).replace("<h2>", '<h2 class="schedule-day-past">', 1)
        return match.group(0)
    return heading_pattern.sub(decorate, html)
def _collapse_log_section(html):
    """Wrap the Log heading and its entries in a closed disclosure toggle."""
    match = re.search(r"<h2>\s*Log\s*</h2>", html, flags=re.IGNORECASE)
    if not match:
        return html
    after = html[match.end():]
    next_h2 = re.search(r"<h2\b", after, flags=re.IGNORECASE)
    if next_h2:
        body = after[:next_h2.start()]
        rest = after[next_h2.start():]
    else:
        body = after
        rest = ""
    collapsed = (
        '<details class="schedule-log">'
        '<summary class="schedule-log-summary">Log</summary>'
        f'<div class="schedule-log-body">{body}</div>'
        "</details>"
    )
    return html[:match.start()] + collapsed + rest

def _render_markdown_file(filename):
    """Read a schedule markdown file from SCHEDULE_DIR and render it to HTML.

    Returns (html, exists, metadata). Missing file → a friendly placeholder."""
    path = SCHEDULE_DIR / filename
    if not path.exists():
        return None, False, {}
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to read schedule file {path}: {e}")
        return None, False, {}
    text, metadata = _extract_schedule_metadata(text)
    # Stock python-markdown has no ~~strikethrough~~; normalize before convert.
    text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)
    html = markdown.markdown(
        text,
        extensions=["tables", "sane_lists", "nl2br", "fenced_code", "smarty"],
    )
    if filename == "horizon.md":
        html = _decorate_horizon_headings(html)
    elif filename == "current-week.md":
        html = _decorate_past_week_days(html, metadata)
    html = _collapse_log_section(html)
    return html, True, metadata
@app.get("/schedule", response_class=HTMLResponse)
async def schedule(request: Request):
    username = request.state.user
    sections = []
    for filename, label in SCHEDULE_FILES.items():
        html, exists, metadata = _render_markdown_file(filename)
        sections.append({
            "filename": filename,
            "label": label,
            "html": html,
            "exists": exists,
        })
    return templates.TemplateResponse("schedule.html", {
        "request": request,
        "username": username,
        "sections": sections,
    })
@app.post("/internal/sync")
async def internal_sync():
    """Pull the latest Hermes lesson DB snapshot and schedule files after Hermes writes."""
    from sync_db import sync_from_hermes
    from sync_schedule import sync_schedule_from_hermes
    ok = sync_from_hermes()
    # Schedule sync is best-effort: a missing/empty schedule must not fail the lesson sync.
    sync_schedule_from_hermes()
    if not ok:
        raise HTTPException(status_code=503, detail="Hermes DB sync failed")
    return JSONResponse({"ok": True})

@app.post("/preferences")
async def update_preferences(request: Request):
    username = request.state.user
    form = await request.form()
    prefs = get_prefs(username)
    if "default_student" in form:
        prefs["default_student"] = form["default_student"]
    if "default_time_mode" in form:
        prefs["default_time_mode"] = form["default_time_mode"]
    save_prefs(username, prefs)
    return RedirectResponse(url="/", status_code=303)
