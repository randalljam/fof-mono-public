#!/usr/bin/env python3
"""Tests for tools/problem_list_store.py."""
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import problem_list_store as P  # noqa: E402

def _make_db(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE Users (name TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()
class ParseTests(unittest.TestCase):
    def test_parse_standard_line(self):
        parsed = P.parse_problem_line("8 + 2")
        self.assertEqual(parsed["problem_text"], "8 + 2")
        self.assertEqual(parsed["category"], None)
        self.assertEqual(parsed["notes"], None)
    def test_parse_line_with_category_and_notes(self):
        parsed = P.parse_problem_line("11. 8 + 2 | Add Two | turn-around")
        self.assertEqual(parsed["problem_text"], "8 + 2")
        self.assertEqual(parsed["category"], "Add Two")
        self.assertEqual(parsed["notes"], "turn-around")
    def test_parse_text_skips_comments(self):
        text = "# heading\n\n1 + 1\n2 + 3, Add Two\n"
        rows = P.parse_problem_list_text(text)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]["category"], "Add Two")
class StorageTests(unittest.TestCase):
    def test_add_problem_list_orders_lists_and_items(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "sample.sqlite")
            _make_db(db)
            conn = P.connect(db)
            try:
                first = P.add_problem_list(
                    conn,
                    user_name="K2",
                    list_name="List A",
                    source="manual",
                    problems=P.parse_problem_list_text("1 + 1\n2 + 2\n"),
                    added_at="2026-06-19T11:11:11",
                )
                second = P.add_problem_list(
                    conn,
                    user_name="K2",
                    list_name="List B",
                    source="manual",
                    problems=P.parse_problem_list_text("3 + 3\n"),
                    added_at="2026-06-19T11:22:22",
                )
                self.assertEqual(first["list_order"], 1)
                self.assertEqual(second["list_order"], 2)
                rows = conn.execute(
                    "SELECT item_order, problem_text FROM ProblemListItems WHERE problem_list_id = ? ORDER BY item_order",
                    (first["problem_list_id"],),
                ).fetchall()
                rows = [(row[0], row[1]) for row in rows]
                self.assertEqual(rows, [(1, "1 + 1"), (2, "2 + 2")])
            finally:
                conn.close()
    def test_retain_defaults_to_keep_and_fetch_exposes_fields(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "s.sqlite")
            _make_db(db)
            conn = P.connect(db)
            try:
                P.add_problem_list(conn, user_name="K2", list_name="A", source="m",
                                   problems=P.parse_problem_list_text("8 + 2\n3 + 4\n"), added_at="t1")
                lists = P.fetch_problem_lists(conn, user_name="K2")
                self.assertEqual(len(lists), 1)
                self.assertEqual(lists[0]["retain"], 1)            # keep by default
                self.assertEqual(lists[0]["times_used"], 0)
                self.assertEqual(lists[0]["item_count"], 2)
                # items now carry the parsed num1/operation/num2 (for the browser to run them)
                first = lists[0]["items"][0]
                self.assertEqual((first["num1"], first["operation"], first["num2"]), (8, "+", 2))
            finally:
                conn.close()

    def test_consume_keeps_retained_and_bumps_usage(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "s.sqlite")
            _make_db(db)
            conn = P.connect(db)
            try:
                out = P.add_problem_list(conn, user_name="K2", list_name="A", source="m",
                                         problems=P.parse_problem_list_text("1 + 1\n"), added_at="t1")
                res = P.consume_problem_list(conn, out["problem_list_id"], used_at="2026-06-21T09:00:00")
                self.assertEqual(res["action"], "retained")
                self.assertEqual(res["times_used"], 1)
                lists = P.fetch_problem_lists(conn, user_name="K2")
                self.assertEqual(len(lists), 1)                    # still there
                self.assertEqual(lists[0]["times_used"], 1)
                self.assertEqual(lists[0]["last_used_at"], "2026-06-21T09:00:00")
            finally:
                conn.close()

    def test_consume_deletes_nonretained_and_reindexes(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "s.sqlite")
            _make_db(db)
            conn = P.connect(db)
            try:
                a = P.add_problem_list(conn, user_name="K2", list_name="A", source="m",
                                       problems=P.parse_problem_list_text("1 + 1\n"), added_at="t1", retain=False)
                P.add_problem_list(conn, user_name="K2", list_name="B", source="m",
                                   problems=P.parse_problem_list_text("2 + 2\n"), added_at="t2")
                P.add_problem_list(conn, user_name="K2", list_name="C", source="m",
                                   problems=P.parse_problem_list_text("3 + 3\n"), added_at="t3")
                res = P.consume_problem_list(conn, a["problem_list_id"])
                self.assertEqual(res["action"], "deleted")
                lists = P.fetch_problem_lists(conn, user_name="K2")
                # A is gone; B and C remain and are renumbered to a contiguous 1, 2 (no gaps).
                self.assertEqual([(p["list_order"], p["list_name"]) for p in lists], [(1, "B"), (2, "C")])
                # The deleted list's items are gone too.
                self.assertEqual(
                    conn.execute("SELECT COUNT(*) FROM ProblemListItems WHERE problem_list_id = ?",
                                 (a["problem_list_id"],)).fetchone()[0], 0)
                # next_problem_list returns the new top of the queue (B).
                self.assertEqual(P.next_problem_list(conn, "K2")["list_name"], "B")
            finally:
                conn.close()

    def test_consume_missing_id_is_noop(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "s.sqlite")
            _make_db(db)
            conn = P.connect(db)
            try:
                self.assertEqual(P.consume_problem_list(conn, 999)["action"], "missing")
            finally:
                conn.close()

    def test_set_retain_then_consume_deletes(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "s.sqlite")
            _make_db(db)
            conn = P.connect(db)
            try:
                out = P.add_problem_list(conn, user_name="K2", list_name="A", source="m",
                                         problems=P.parse_problem_list_text("1 + 1\n"), added_at="t1")
                P.set_retain(conn, out["problem_list_id"], retain=False)  # flip keep -> consume
                self.assertEqual(P.consume_problem_list(conn, out["problem_list_id"])["action"], "deleted")
                self.assertEqual(P.fetch_problem_lists(conn, user_name="K2"), [])
            finally:
                conn.close()

    def test_replace_list_items_swaps_contents(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "s.sqlite")
            _make_db(db)
            conn = P.connect(db)
            try:
                out = P.add_problem_list(conn, user_name="K2", list_name="A", source="m",
                                         problems=P.parse_problem_list_text("1 + 1\n2 + 2\n"), added_at="t1")
                P.replace_list_items(conn, out["problem_list_id"], P.parse_problem_list_text("5 + 5\n6 + 6\n7 + 7\n"))
                lists = P.fetch_problem_lists(conn, user_name="K2")
                self.assertEqual([it["problem_text"] for it in lists[0]["items"]], ["5 + 5", "6 + 6", "7 + 7"])
                self.assertEqual([it["item_order"] for it in lists[0]["items"]], [1, 2, 3])
                with self.assertRaises(ValueError):
                    P.replace_list_items(conn, 999, [])
            finally:
                conn.close()

    def test_create_list_allows_empty_then_fill(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "s.sqlite")
            _make_db(db)
            conn = P.connect(db)
            try:
                out = P.create_list(conn, "K2", "Blank")            # empty card
                self.assertEqual(out["item_count"], 0)
                self.assertEqual(out["list_order"], 1)
                lists = P.fetch_problem_lists(conn, user_name="K2")
                self.assertEqual((lists[0]["list_name"], lists[0]["item_count"], lists[0]["retain"]), ("Blank", 0, 1))
                # A second create appends at the end of the queue.
                out2 = P.create_list(conn, "K2", "Seeded", problems=P.parse_problem_list_text("4 + 5\n"), retain=False)
                self.assertEqual(out2["list_order"], 2)
                lists = P.fetch_problem_lists(conn, user_name="K2")
                self.assertEqual(lists[1]["items"][0]["problem_text"], "4 + 5")
                self.assertEqual(lists[1]["retain"], 0)
            finally:
                conn.close()

    def test_rename_list(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "s.sqlite")
            _make_db(db)
            conn = P.connect(db)
            try:
                out = P.add_problem_list(conn, user_name="K2", list_name="Old", source="m",
                                         problems=P.parse_problem_list_text("1 + 1\n"), added_at="t1")
                self.assertEqual(P.rename_list(conn, out["problem_list_id"], "New name"), 1)
                self.assertEqual(P.fetch_problem_lists(conn, user_name="K2")[0]["list_name"], "New name")
                self.assertEqual(P.rename_list(conn, out["problem_list_id"], "   "), 1)  # blank -> Untitled
                self.assertEqual(P.fetch_problem_lists(conn, user_name="K2")[0]["list_name"], "Untitled")
            finally:
                conn.close()

    def test_reorder_lists_sets_queue_order(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "s.sqlite")
            _make_db(db)
            conn = P.connect(db)
            try:
                a = P.add_problem_list(conn, "K2", "A", "m", P.parse_problem_list_text("1 + 1\n"), added_at="t1")
                b = P.add_problem_list(conn, "K2", "B", "m", P.parse_problem_list_text("2 + 2\n"), added_at="t2")
                c = P.add_problem_list(conn, "K2", "C", "m", P.parse_problem_list_text("3 + 3\n"), added_at="t3")
                # Reverse the queue: C, B, A
                P.reorder_lists(conn, "K2", [c["problem_list_id"], b["problem_list_id"], a["problem_list_id"]])
                lists = P.fetch_problem_lists(conn, user_name="K2")
                self.assertEqual([(p["list_order"], p["list_name"]) for p in lists], [(1, "C"), (2, "B"), (3, "A")])
                # A partial order still yields a contiguous 1..N (unlisted appended after).
                P.reorder_lists(conn, "K2", [b["problem_list_id"]])
                lists = P.fetch_problem_lists(conn, user_name="K2")
                self.assertEqual(lists[0]["list_name"], "B")
                self.assertEqual([p["list_order"] for p in lists], [1, 2, 3])
            finally:
                conn.close()

    def test_delete_list_ignores_retain_and_reindexes(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "s.sqlite")
            _make_db(db)
            conn = P.connect(db)
            try:
                a = P.add_problem_list(conn, "K2", "A", "m", P.parse_problem_list_text("1 + 1\n"), added_at="t1")  # retain=keep
                P.add_problem_list(conn, "K2", "B", "m", P.parse_problem_list_text("2 + 2\n"), added_at="t2")
                res = P.delete_list(conn, a["problem_list_id"])   # delete a retained list anyway
                self.assertEqual(res["action"], "deleted")
                lists = P.fetch_problem_lists(conn, user_name="K2")
                self.assertEqual([(p["list_order"], p["list_name"]) for p in lists], [(1, "B")])
                self.assertEqual(P.delete_list(conn, 999)["action"], "missing")
            finally:
                conn.close()

    def test_markdown_render_includes_metadata(self):
        sample = [{
            "problem_list_id": 1,
            "user_name": "K2",
            "list_order": 1,
            "list_name": "Session 20",
            "added_at": "2026-06-19T12:00:00",
            "source": "coach-note",
            "items": [
                {"item_order": 1, "problem_text": "0 + 6", "category": "Add Zero", "notes": None},
                {"item_order": 2, "problem_text": "8 + 2", "category": "Add Two", "notes": "turn-around"},
            ],
        }]
        md = P.render_problem_lists_markdown(sample, title="K2 Lists")
        self.assertIn("# K2 Lists", md)
        self.assertIn("list #1: Session 20", md)
        self.assertIn("| 2 | 8 + 2 | Add Two | turn-around |", md)
if __name__ == "__main__":
    unittest.main()
