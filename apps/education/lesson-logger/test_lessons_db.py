#!/usr/bin/env python3
# Unit tests for the lessons SQLite store (ingestion + queryable layer).
# Run: .venv/bin/pytest apps/education/lesson-logger/test_lessons_db.py -v
#   (or any venv with pytest installed)
import importlib.util
import json
import os
import tempfile

_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "scripts", "lessons_db.py",
)
def _load():
    spec = importlib.util.spec_from_file_location("lessons_db", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
def _entry(id_, subject, duration, students, date="2026-06-06"):
    return {
        "id": id_, "date": date, "students": students, "subject": subject,
        "duration": duration, "notes": "", "transcript": "test transcript",
        "createdAt": "2026-06-06T18:00:00-07:00",
    }
def test_upsert_and_json_students():
    mod = _load()
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "lessons.db")
        conn = mod.connect(db)
        mod.upsert_entry(conn, _entry("a", "Math", 30, ["Kid1", "Mia"]))
        rows = conn.execute("SELECT subject, duration FROM entries WHERE id='a'").fetchall()
        assert rows == [("Math", 30)], rows
        studs = [r[0] for r in conn.execute(
            "SELECT j.value FROM entries e, json_each(e.students) j WHERE e.id='a'"
        )]
        assert set(studs) == {"Kid1", "Mia"}, studs
        conn.close()
def test_upsert_idempotent():
    mod = _load()
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "lessons.db")
        conn = mod.connect(db)
        mod.upsert_entry(conn, _entry("a", "Math", 30, ["Kid1", "Mia"]))
        mod.upsert_entry(conn, _entry("a", "Math", 45, ["Kid1"]))
        n = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        assert n == 1, n
        dur = conn.execute("SELECT duration FROM entries WHERE id='a'").fetchone()[0]
        assert dur == 45, dur
        studs = [r[0] for r in conn.execute(
            "SELECT j.value FROM entries e, json_each(e.students) j WHERE e.id='a'"
        )]
        assert studs == ["Kid1"], studs
        conn.close()
def test_ingest_dir_and_summary():
    mod = _load()
    with tempfile.TemporaryDirectory() as d:
        logs = os.path.join(d, "lesson-logs")
        os.makedirs(logs)
        json.dump(_entry("a", "Math", 30, ["Kid1"]), open(os.path.join(logs, "a.json"), "w"))
        json.dump(_entry("b", "Math", 20, ["Kid1"]), open(os.path.join(logs, "b.json"), "w"))
        json.dump(_entry("c", "Art", 60, ["Mia"]), open(os.path.join(logs, "c.json"), "w"))
        db = os.path.join(d, "lessons.db")
        assert mod.ingest_dir(logs, db) == 3
        assert mod.ingest_dir(logs, db) == 3
        conn = mod.connect(db)
        assert conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 3
        conn.close()
        rollup = {(s, subj): mins for s, subj, mins, n in mod.summary(db)}
        assert rollup[("Kid1", "Math")] == 50, rollup
        assert rollup[("Mia", "Art")] == 60, rollup
if __name__ == "__main__":
    test_upsert_and_json_students()
    test_upsert_idempotent()
    test_ingest_dir_and_summary()
    print("ok")
