#!/usr/bin/env python3
# Generate synthetic lesson data for dashboard development and testing.
# Creates realistic entries for two students (Zap and Fran) across ~4 months.
#
# Fran: 1–3 lessons most school days (occasional miss days), 5–45 min each.
# Zap:  ~2 sessions/week, plus a recurring 90-min weekly class for 6 weeks.
#
# Teachers: Randy, TL (sometimes both), plus some "self".
# Outputs JSON session files + SQLite DB.
#
# Usage:
#   python3 generate_synthetic_data.py                          # default output
#   python3 generate_synthetic_data.py --out-dir ./sample-data  # custom location
#   python3 generate_synthetic_data.py --db-name lessons_dev.db # custom DB name
import argparse
import os
import random
import sys
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import save_lesson
import lessons_db

PACIFIC = ZoneInfo("America/Los_Angeles")

### Subjects + weights (per-student, tuned below)
ALL_SUBJECTS = ["Math", "Reading", "Writing", "Science", "Art", "Music", "History", "Spanish"]
FRAN_SUBJECT_WEIGHTS = [0.25, 0.22, 0.15, 0.13, 0.08, 0.07, 0.05, 0.05]
ZAP_SUBJECT_WEIGHTS  = [0.20, 0.20, 0.10, 0.20, 0.10, 0.10, 0.05, 0.05]

### Curricula by subject
CURRICULA = {
    "Math": ["Beast Academy", "Column Arithmetic", "Synthesis", ""],
    "Reading": ["Charlotte's Web", "The Phantom Tollbooth", "Magic Tree House", "Frog and Toad", ""],
    "Writing": ["Writing Without Tears", ""],
    "Science": ["Magic School Bus", ""],
    "Art": [""],
    "Music": ["Piano Adventures Level 2", ""],
    "History": ["Story of the World Vol 2", ""],
    "Spanish": ["Duolingo", ""],
}

### Locations — more than half are "home"
LOCATIONS = ["home", "home", "home", "home", "kitchen table", "living room",
             "library", "co-op", "backyard"]

### Notes by subject
NOTES = {
    "Math": [
        "fractions — getting more confident with common denominators",
        "multiplication drills, 7s and 8s still tricky",
        "word problems, did 3 pages",
        "geometry intro — identifying shapes",
        "subtraction with regrouping, much improved",
        "skip counting by 4s and 6s",
        "division intro — sharing equally concept",
        "place value to thousands",
        "money and making change practice",
        "worked through challenge problems at end of chapter",
        "mental math warm-ups then worksheet",
        "reviewed last week's mistakes, all corrected",
        "",
    ],
    "Reading": [
        "read two chapters aloud, good expression",
        "silent reading, answered comprehension questions",
        "finished the book — loved it",
        "struggled with vocabulary but pushed through",
        "read aloud to younger sibling",
        "discussed character motivations",
        "paired reading — alternating paragraphs",
        "started a new book, very excited",
        "re-read favorite chapter",
        "",
    ],
    "Writing": [
        "journal entry about the weekend",
        "cursive practice — lowercase letters",
        "wrote a short story about a dragon",
        "thank-you letter to grandma",
        "paragraph structure — topic sentences",
        "creative writing prompt — space adventure",
        "practiced letter formation",
        "wrote a poem about the rain",
        "",
    ],
    "Science": [
        "baking soda volcano experiment",
        "plant growth observation — measured sprouts",
        "water cycle diagram",
        "magnetic vs non-magnetic materials sorting",
        "simple machines — levers and pulleys",
        "bug collection walk, identified 4 insects",
        "discussed states of matter with ice experiment",
        "solar system poster — labeled all planets",
        "",
    ],
    "Art": [
        "watercolors — painted the backyard",
        "clay sculpture — made an animal",
        "sketching practice — still life of fruit bowl",
        "collage with magazine cutouts",
        "color mixing — secondary colors",
        "drew comic strip panels",
        "",
    ],
    "Music": [
        "piano practice — scales and arpeggios",
        "learned a new piece, first page",
        "rhythm clapping exercises",
        "practiced recital piece — getting smoother",
        "sight reading simple melodies",
        "worked on dynamics — loud vs soft",
        "",
    ],
    "History": [
        "ancient Egypt — built a pyramid model",
        "read about Roman roads",
        "timeline activity — placed 10 events",
        "discussed the Middle Ages, castles and knights",
        "",
    ],
    "Spanish": [
        "colors and numbers review",
        "basic greetings dialogue practice",
        "food vocabulary unit",
        "family members vocabulary",
        "",
    ],
}

### Times of day
TIMES = ["", "", "9:00 AM", "9:30 AM", "10:00 AM", "10:30 AM",
         "11:00 AM", "1:00 PM", "1:30 PM", "2:00 PM", "2:30 PM", "3:00 PM"]

### Helpers
def _pick_teacher():
    r = random.random()
    if r < 0.35:
        return ["TL"]
    elif r < 0.60:
        return ["Randy"]
    elif r < 0.72:
        return ["Randy", "TL"]
    else:
        return ["self"]
def _pick_created_by():
    return random.choice(["Randy", "TL"])
def _make_entry(student, day, subject, duration, teacher=None, curricula=None,
                location=None, time_val=None, notes=None, created_by=None):
    teacher = teacher or _pick_teacher()
    curricula_opts = CURRICULA.get(subject, [""])
    curricula = curricula if curricula is not None else random.choice(curricula_opts)
    location = location if location is not None else random.choice(LOCATIONS)
    time_val = time_val if time_val is not None else random.choice(TIMES)
    notes_opts = NOTES.get(subject, [""])
    notes = notes if notes is not None else random.choice(notes_opts)
    created_by = created_by or _pick_created_by()
    now = datetime(day.year, day.month, day.day,
                   random.randint(8, 18), random.randint(0, 59), tzinfo=PACIFIC)
    students = [student]
    data = {
        "students": students,
        "teachers": teacher,
        "subject": subject,
        "curricula": curricula,
        "duration": duration,
        "location": location,
        "date": day.strftime("%Y-%m-%d"),
        "time": time_val,
        "notes": notes,
        "transcript": f"(synthetic) {student} did {duration} min of {subject.lower()}",
        "createdBy": created_by,
    }
    entry, _ = save_lesson.build_entry(data, now=now)
    return entry

def _school_days(start, end):
    days = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days

### Fran: 1–3 lessons most school days, 5–45 min, occasional miss
def _generate_fran(school_days):
    entries = []
    fran_durations = [5, 10, 10, 15, 15, 15, 20, 20, 25, 25, 30, 30, 30, 35, 40, 45]
    for day in school_days:
        if random.random() < 0.08:
            continue
        n_lessons = random.choices([1, 2, 3], weights=[0.25, 0.50, 0.25], k=1)[0]
        day_subjects = random.choices(ALL_SUBJECTS, weights=FRAN_SUBJECT_WEIGHTS, k=n_lessons)
        day_subjects = list(dict.fromkeys(day_subjects))
        for subj in day_subjects:
            dur = random.choice(fran_durations)
            entries.append(_make_entry("Fran", day, subj, dur))
    return entries

### Zap: ~2 sessions/week + recurring weekly 90-min class for 6 weeks
def _generate_zap(school_days):
    entries = []
    zap_durations = [10, 15, 15, 20, 20, 25, 30, 30, 35, 40, 45]
    weeks = {}
    for day in school_days:
        wk = day.isocalendar()[1]
        weeks.setdefault(wk, []).append(day)
    recurring_start_week = sorted(weeks.keys())[4]
    recurring_weeks = sorted(weeks.keys())[4:10]
    for wk, days in sorted(weeks.items()):
        if wk in recurring_weeks:
            wed_candidates = [d for d in days if d.weekday() == 2]
            recur_day = wed_candidates[0] if wed_candidates else days[len(days) // 2]
            entries.append(_make_entry(
                "Zap", recur_day, "Science", 90,
                teacher=["Ms. Rivera"], curricula="",
                location="co-op", time_val="1:00 PM",
                notes="weekly science co-op class — hands-on experiments",
            ))
        session_days = random.sample(days, min(2, len(days)))
        for day in session_days:
            subj = random.choices(ALL_SUBJECTS, weights=ZAP_SUBJECT_WEIGHTS, k=1)[0]
            dur = random.choice(zap_durations)
            entries.append(_make_entry("Zap", day, subj, dur))
    return entries

def generate(out_dir, db_name="lessons_dev.db"):
    os.makedirs(out_dir, exist_ok=True)
    db_path = os.path.join(out_dir, db_name)
    if os.path.exists(db_path):
        os.remove(db_path)
    for f in os.listdir(out_dir):
        if f.endswith(".json"):
            os.remove(os.path.join(out_dir, f))
    end_date = datetime.now(PACIFIC).date()
    start_date = end_date - timedelta(days=120)
    days = _school_days(start_date, end_date)
    random.shuffle(days)
    fran_entries = _generate_fran(days)
    zap_entries = _generate_zap(days)
    all_entries = fran_entries + zap_entries
    all_entries.sort(key=lambda e: (e["date"], e.get("time", ""), e["students"][0]))
    conn = lessons_db.connect(db_path)
    for entry in all_entries:
        path = save_lesson.save_entry(entry, log_dir=out_dir)
        lessons_db.upsert_entry(conn, entry, source_file=path)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()
    return all_entries, db_path

### CLI
def main():
    ap = argparse.ArgumentParser(description="Generate synthetic lesson data for testing.")
    ap.add_argument("--out-dir", default=os.path.join(_HERE, "..", "sample-data"),
                    help="Output directory for JSON files + DB.")
    ap.add_argument("--db-name", default="lessons_dev.db", help="DB filename (default: lessons_dev.db).")
    ap.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    args = ap.parse_args()
    random.seed(args.seed)
    out_dir = os.path.abspath(args.out_dir)
    entries, db_path = generate(out_dir, args.db_name)
    students = {}
    subjects = {}
    teachers = {}
    for e in entries:
        for s in e["students"]:
            students[s] = students.get(s, 0) + 1
        subjects[e["subject"]] = subjects.get(e["subject"], 0) + 1
        for t in e["teachers"]:
            teachers[t] = teachers.get(t, 0) + 1
    print(f"Generated {len(entries)} entries in {out_dir}")
    print(f"  DB: {db_path}")
    print(f"  Date range: {entries[0]['date']} to {entries[-1]['date']}")
    print(f"  Students: {', '.join(f'{k} ({v})' for k, v in sorted(students.items()))}")
    print(f"  Teachers: {', '.join(f'{k} ({v})' for k, v in sorted(teachers.items(), key=lambda x: -x[1]))}")
    print(f"  Subjects: {', '.join(f'{k} ({v})' for k, v in sorted(subjects.items(), key=lambda x: -x[1]))}")
if __name__ == "__main__":
    main()
