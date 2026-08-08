#!/usr/bin/env python3
"""Tests for quick_practice_store (auto-generated per-operation quick-practice sets in the
.sqlite) plus the dev-server save_run regeneration + latest-user-db exposure. Stdlib
sqlite3 only; mirrors the fluency rubric ported from fluency_core.js."""
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(__file__))
import quick_practice_store as Q  # noqa: E402
import dev_server as D  # noqa: E402
from test_anchor_store import SCHEMA, make_db  # noqa: E402


def _make_db(path, user, sessions):
    """sessions: list of (session_id, end_time, attempts) where each attempt is
    (num1, num2, op, is_correct, response_time_ms). Builds a raw per-user .sqlite."""
    c = sqlite3.connect(path)
    c.executescript(SCHEMA)
    c.execute("INSERT INTO Users(name) VALUES(?)", (user,))
    for sid, end_time, attempts in sessions:
        c.execute("INSERT INTO Sessions(session_id, user_name, start_time, end_time, total_problems) "
                  "VALUES(?,?,?,?,?)", (sid, user, end_time, end_time, len(attempts)))
        for i, (n1, n2, op, ok, rt) in enumerate(attempts):
            c.execute("INSERT INTO ProblemAttempts(session_id, problem_id, problem_text, num1, num2, "
                      "operation, correct_answer, is_correct, response_time_ms) VALUES(?,?,?,?,?,?,?,?,?)",
                      (sid, f"{sid}-{i}", f"{n1} {op} {n2}", n1, n2, op, 0, 1 if ok else 0, rt))
    c.commit()
    c.close()


class RubricTests(unittest.TestCase):
    def _atts(self, specs):
        return [{'isCorrect': ok, 'responseTime': rt} for ok, rt in specs]

    def test_evaluate_status_bands(self):
        T = Q.DEFAULT_THRESHOLDS
        self.assertEqual(Q._evaluate_status([], T), 'nodata')
        self.assertEqual(Q._evaluate_status(self._atts([(True, 1000)] * 5), T), 'green')
        self.assertEqual(Q._evaluate_status(self._atts([(True, 3000)] * 5), T), 'yellow')
        self.assertEqual(Q._evaluate_status(self._atts([(True, 5000)] * 5), T), 'red')

    def test_evaluate_status_low_accuracy_is_gray(self):
        T = Q.DEFAULT_THRESHOLDS
        # 2/5 correct -> accuracy 0.4 < 0.8 -> gray (even if the correct ones were fast)
        specs = [(True, 800), (True, 800), (False, 800), (False, 800), (False, 800)]
        self.assertEqual(Q._evaluate_status(self._atts(specs), T), 'gray')
        # all wrong -> gray
        self.assertEqual(Q._evaluate_status(self._atts([(False, 500)] * 5), T), 'gray')

    def test_evaluate_status_windows_last_n(self):
        T = Q.DEFAULT_THRESHOLDS
        # old slow attempts fall out of the window of 5; last 5 are fast -> green
        specs = [(True, 9000), (True, 9000), (True, 800), (True, 800), (True, 800), (True, 800), (True, 800)]
        self.assertEqual(Q._evaluate_status(self._atts(specs), T), 'green')


class UniverseTests(unittest.TestCase):
    def test_universe_sizes(self):
        for op in ('+', '-', '*'):
            self.assertEqual(len(Q.ordered_universe(op)), 55, op)

    def test_addition_easiest_first_hardest_last(self):
        u = Q.ordered_universe('+')
        self.assertEqual(u[0], (0, 0))            # add-zero is easiest
        self.assertEqual(u[-1], (8, 9))           # hardest-six, biggest sum is last
        # add-zero facts all precede the hardest-six facts
        self.assertLess(u.index((0, 9)), u.index((6, 7)))

    def test_subtraction_non_negative_minuend_first(self):
        u = Q.ordered_universe('-')
        self.assertTrue(all(n1 >= n2 for n1, n2 in u))
        # "n - 0" is the easiest band
        self.assertEqual(Q._subtraction_difficulty(5, 0)[0], 0)
        self.assertLess(Q._subtraction_difficulty(5, 0), Q._subtraction_difficulty(9, 6))

    def test_multiplication_zero_and_one_easy(self):
        self.assertLess(Q._multiplication_difficulty(0, 7), Q._multiplication_difficulty(7, 8))
        self.assertLess(Q._multiplication_difficulty(1, 9), Q._multiplication_difficulty(7, 8))


class SelectionTests(unittest.TestCase):
    def test_full_data_picks_three_three_one_from_pools(self):
        statuses = {
            (3, 4): 'green', (2, 5): 'green', (1, 6): 'green', (0, 9): 'green',
            (5, 6): 'yellow', (4, 7): 'yellow', (3, 8): 'yellow',
            (8, 9): 'red', (7, 9): 'red',
        }
        items = Q.select_for_operation('+', statuses)
        self.assertEqual(len(items), 7)
        self.assertEqual([it['slot_status'] for it in items],
                         ['green', 'green', 'green', 'yellow', 'yellow', 'yellow', 'red'])
        self.assertTrue(all(it['origin'] == 'data' for it in items))
        # no duplicate facts across the set
        keys = {(it['num1'], it['num2']) for it in items}
        self.assertEqual(len(keys), 7)

    def test_no_data_fills_by_escalating_difficulty(self):
        items = Q.select_for_operation('+', {})
        self.assertEqual(len(items), 7)
        self.assertTrue(all(it['origin'] == 'algorithm' for it in items))
        diff = Q._addition_difficulty
        green_items = [it for it in items if it['slot_status'] == 'green']
        red_item = [it for it in items if it['slot_status'] == 'red'][0]
        # every fluent (green) slot is easier than the needs-practice (red) slot
        for g in green_items:
            self.assertLess(diff(g['num1'], g['num2']), diff(red_item['num1'], red_item['num2']))

    def test_partial_data_mixes_data_and_algorithm_without_dupes(self):
        items = Q.select_for_operation('*', {(3, 4): 'green'})
        self.assertEqual(len(items), 7)
        data_items = [it for it in items if it['origin'] == 'data']
        self.assertEqual(len(data_items), 1)
        self.assertEqual((data_items[0]['num1'], data_items[0]['num2']), (3, 4))
        self.assertEqual(data_items[0]['slot_status'], 'green')
        keys = {(it['num1'], it['num2']) for it in items}
        self.assertEqual(len(keys), 7)   # no duplicates

    def test_blue_counts_as_fluent(self):
        items = Q.select_for_operation('+', {(8, 9): 'blue'})
        green = [it for it in items if it['slot_status'] == 'green' and it['origin'] == 'data']
        self.assertEqual(len(green), 1)
        self.assertEqual((green[0]['num1'], green[0]['num2']), (8, 9))


class ComputeStatusTests(unittest.TestCase):
    def _db(self):
        return os.path.join(tempfile.mkdtemp(), "s.sqlite")

    def test_combined_status_from_single_session(self):
        p = self._db()
        _make_db(p, "Kid1", [("s1", "2026-06-20_120000", [
            (3, 4, '+', True, 900), (3, 4, '+', True, 1100),     # green
            (5, 6, '+', True, 3000), (5, 6, '+', True, 3200),    # yellow
            (7, 8, '+', True, 5000), (7, 8, '+', True, 5200),    # red
            (8, 2, '*', True, 800),                               # green (mult)
        ])])
        conn = Q.connect(p)
        try:
            st = Q.compute_fact_statuses(conn, "Kid1")
        finally:
            conn.close()
        self.assertEqual(st['+'][(3, 4)], 'green')
        self.assertEqual(st['+'][(5, 6)], 'yellow')
        self.assertEqual(st['+'][(7, 8)], 'red')
        self.assertEqual(st['*'][(2, 8)], 'green')   # canonical orientation lo,hi

    def test_green_for_five_sessions_becomes_permanent_blue(self):
        p = self._db()
        sessions = [(f"s{i}", f"2026-06-2{i}_120000", [(3, 4, '+', True, 800), (3, 4, '+', True, 900)])
                    for i in range(5)]
        _make_db(p, "Kid1", sessions)
        conn = Q.connect(p)
        try:
            st = Q.compute_fact_statuses(conn, "Kid1")
        finally:
            conn.close()
        self.assertEqual(st['+'][(3, 4)], 'blue')

    def test_visual_practice_sessions_count_toward_status(self):
        p = self._db()
        _make_db(p, "Kid1", [
            ("s1", "2026-06-20_120000", [(3, 4, '+', True, 800), (3, 4, '+', True, 900)]),
            ("s2", "2026-06-21_120000", [(3, 4, '+', True, 6000)] * 5),
        ])
        setup = sqlite3.connect(p)
        try:
            setup.execute("ALTER TABLE Sessions ADD COLUMN session_type TEXT")
            setup.execute("UPDATE Sessions SET session_type='visual-practice' WHERE session_id='s2'")
            setup.commit()
        finally:
            setup.close()
        conn = Q.connect(p)
        try:
            st = Q.compute_fact_statuses(conn, "Kid1")
        finally:
            conn.close()
        # Recent visual-practice slow corrects dominate the window → not green.
        self.assertEqual(st['+'][(3, 4)], 'red')

    def test_old_db_without_session_type_column_still_loads(self):
        p = self._db()
        _make_db(p, "Kid1", [("s1", "2026-06-20_120000", [(3, 4, '+', True, 800)])])
        conn = Q.connect(p)
        try:
            st = Q.compute_fact_statuses(conn, "Kid1")
        finally:
            conn.close()
        self.assertEqual(st['+'][(3, 4)], 'green')


class RegenerateTests(unittest.TestCase):
    def _db(self):
        return os.path.join(tempfile.mkdtemp(), "s.sqlite")

    def test_regenerate_writes_21_rows(self):
        p = self._db()
        _make_db(p, "Kid1", [("s1", "2026-06-20_120000", [(3, 4, '+', True, 900)])])
        conn = Q.connect(p)
        try:
            summary = Q.regenerate_for_user(conn, "Kid1")
            total = conn.execute("SELECT COUNT(*) FROM QuickPracticeItems WHERE user_name='Kid1'").fetchone()[0]
            per_op = conn.execute("SELECT operation, COUNT(*) FROM QuickPracticeItems "
                                  "WHERE user_name='Kid1' GROUP BY operation").fetchall()
        finally:
            conn.close()
        self.assertEqual(total, 21)
        self.assertEqual(sorted((r[0], r[1]) for r in per_op), [('*', 7), ('+', 7), ('-', 7)])
        self.assertEqual(set(summary['operations'].keys()), {'+', '-', '*'})

    def test_regenerate_is_idempotent_replace(self):
        p = self._db()
        _make_db(p, "Kid1", [("s1", "2026-06-20_120000", [(3, 4, '+', True, 900)])])
        conn = Q.connect(p)
        try:
            Q.regenerate_for_user(conn, "Kid1")
            Q.regenerate_for_user(conn, "Kid1")   # second run must replace, not duplicate
            total = conn.execute("SELECT COUNT(*) FROM QuickPracticeItems WHERE user_name='Kid1'").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(total, 21)

    def test_fetch_for_user_groups_by_operation_in_order(self):
        p = self._db()
        _make_db(p, "Kid1", [("s1", "2026-06-20_120000", [(3, 4, '+', True, 900)])])
        conn = Q.connect(p)
        try:
            Q.regenerate_for_user(conn, "Kid1")
            fetched = Q.fetch_for_user(conn, "Kid1")
        finally:
            conn.close()
        self.assertEqual(len(fetched['+']), 7)
        self.assertEqual([r['item_order'] for r in fetched['+']], [1, 2, 3, 4, 5, 6, 7])
        # the one real green fact (3+4, fast) lands in a green slot from data
        plus_data = [r for r in fetched['+'] if r['origin'] == 'data']
        self.assertTrue(any(r['problem_text'] == '3 + 4' and r['slot_status'] == 'green' for r in plus_data))


class DevServerQuickPractice(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        D.DATA_DIR = self.tmp
        D._s3 = lambda: (_ for _ in ()).throw(RuntimeError("no s3 in test"))
        self._display_names_file = D.dragon_display_names.DISPLAY_NAMES_FILE
        self._display_names_cache = D.dragon_display_names._cache
        D.dragon_display_names.DISPLAY_NAMES_FILE = self.tmp / "display_names.json"
        D.dragon_display_names._cache = None
    def tearDown(self):
        D.dragon_display_names.DISPLAY_NAMES_FILE = self._display_names_file
        D.dragon_display_names._cache = self._display_names_cache

    def test_save_run_regenerates_and_latest_user_db_exposes_it(self):
        user = "Kid1"
        d = tempfile.mkdtemp()
        p = os.path.join(d, "s.sqlite")
        make_db(p, user, "s1", [(1, 1), (2, 2)])   # addition facts, fast+correct
        raw = Path(p).read_bytes()
        r = D.save_run("real", "source", user, "2026-06-20_090000", "", raw, force_new=True)
        self.assertTrue(r["ok"])
        # save_run returns the regenerated summary with all three operations
        self.assertEqual(set(r["quickPractice"]["operations"].keys()), {'+', '-', '*'})
        # and the next load carries the 21 rows grouped by operation
        latest = D.latest_user_db("real", user)
        qp = latest["quickPractice"]
        self.assertEqual(len(qp['+']), 7)
        self.assertEqual(len(qp['-']), 7)
        self.assertEqual(len(qp['*']), 7)
    def test_regeneration_uses_the_file_profile_thresholds(self):
        path = self.tmp / "profile.sqlite"
        make_db(str(path), "Kid1", "s1", [(1, 1)])
        conn = D.profile_store.connect(str(path))
        try:
            expected = {"greenMs": 700, "redMs": 2500, "windowSize": 3, "minAccuracy": 0.9}
            D.profile_store.set_config(conn, "Kid1", thresholds=expected)
        finally:
            conn.close()
        with mock.patch.object(
                D.quick_practice_store, "regenerate_for_user",
                return_value={"operations": {}}) as regenerate:
            D._regenerate_quick_practice(path, "Kid1")
        self.assertEqual(regenerate.call_args.kwargs["thresholds"], expected)


if __name__ == "__main__":
    unittest.main()
