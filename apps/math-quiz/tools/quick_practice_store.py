#!/usr/bin/env python3
"""
file: apps/math-quiz/tools/quick_practice_store.py
title: Auto-generated "quick practice" problem sets in math-quiz SQLite files

Builds a fixed, machine-generated practice set per operation IN the per-user
.sqlite file (the same file the quiz appends to). Each operation (+, -, *) gets
exactly 7 problems, regenerated after every quiz from the learner's live fluency:
  - 3 problems the learner is FLUENT at  (green, or blue/permanent)
  - 3 problems the learner is ALMOST fluent at (yellow)
  - 1 problem the learner NEEDS PRACTICE on (red)
= 21 rows per user (3 operations x 7).

This is deliberately NOT part of the "Use internal" problem-list queue
(ProblemLists / ProblemListItems): that is a coach-authored queue consumed
one-at-a-time. These are immortal, fully-replaced-after-every-quiz, machine
sets read directly out of SQLite (e.g. by the Minecraft mod). It follows the
TargetedConfig precedent — special-purpose data, same file, own table + store
module — but uses rows (one per problem) so the mod can query plainly:
    SELECT problem_text FROM QuickPracticeItems
    WHERE user_name = ? AND operation = '+' ORDER BY item_order

Fluency rubric (ported verbatim from fluency_core.js evaluateFluencyStatus +
the combined/permanent roll-up in math_fluency.js prepareFluencyDatasets) so the
status here matches what the fluency dashboard shows. Fluency is NOT stored
anywhere in the file — it is recomputed from raw ProblemAttempts each time, here
and on the dashboard. So this regenerator is the write side; it recomputes the
same way the read side does.

Filling gaps (no data / highly incomplete): when a bucket does not have enough
real facts, the missing slots are filled by an escalating-difficulty algorithm
over the operation's fact universe (0-9 operands): easiest facts seed the FLUENT
slots, middle the ALMOST slots, hardest the NEEDS-PRACTICE slot. With zero data a
learner therefore still gets a sensible 7-problem ramp. Addition difficulty uses
the formal segmentation (single_digit_addition_categorization.md / SPEC §5);
multiplication and subtraction use documented heuristics pending their formal
"eventual x/- equivalents" (SPEC §5).
"""
import argparse
import json
import re
import sqlite3
from datetime import datetime

OPERATIONS = ('+', '-', '*')
OPERATION_NAMES = {'+': 'addition', '-': 'subtraction', '*': 'multiplication'}

# Slot plan for the 7-problem set (item_order 1..7): 3 fluent, 3 almost, 1 needs.
SLOT_PLAN = (('green', 3), ('yellow', 3), ('red', 1))
QUICK_PRACTICE_COUNT = sum(n for _, n in SLOT_PLAN)  # 7

# Rubric thresholds — mirror fluency_core.js defaultFluencyThresholds.
DEFAULT_THRESHOLDS = {
    'windowSize': 5,
    'minAccuracy': 0.8,
    'greenMs': 2000,
    'redMs': 4000,
    'retentionSessions': 3,
    'permanentSessions': 5,
}

_PROBLEM_RE = re.compile(r"(-?\d+)\s*([+\-*/xX×÷−])\s*(-?\d+)")

### Helpers: sqlite
def connect(path):
    """Open a math-quiz .sqlite with row access by column name."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
def _has_column(conn, table, column):
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)
def _session_type_exclusion_sql(conn, alias):
    # Visual-practice attempts count toward fluency (synced with analysis / dragon /
    # fluency_percent). Kept as a no-op for call-site compatibility.
    return ''
def ensure_quick_practice_schema(conn):
    """Create the QuickPracticeItems table if absent. One row per
    (user_name, operation, item_order); 7 per operation, 21 per user."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS QuickPracticeItems (
            user_name    TEXT NOT NULL,
            operation    TEXT NOT NULL,
            item_order   INTEGER NOT NULL,
            problem_text TEXT NOT NULL,
            num1         INTEGER NOT NULL,
            num2         INTEGER NOT NULL,
            slot_status  TEXT NOT NULL,
            fact_status  TEXT,
            origin       TEXT NOT NULL,
            computed_at  TEXT NOT NULL,
            PRIMARY KEY (user_name, operation, item_order),
            FOREIGN KEY (user_name) REFERENCES Users(name)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_quick_practice_user_op
        ON QuickPracticeItems (user_name, operation, item_order)
    """)
    conn.commit()

### Helpers: parsing
def _parse_problem_text(text):
    """(num1, op, num2) from a canonical/legacy problem string, or (None, None, None)."""
    m = _PROBLEM_RE.search(str(text or ''))
    if not m:
        return None, None, None
    op = m.group(2)
    if op in ('x', 'X', '×'):
        op = '*'
    elif op == '−':
        op = '-'
    elif op == '÷':
        op = '/'
    return int(m.group(1)), op, int(m.group(3))
def _normalize_commutative(num1, num2, operation):
    """Canonical orientation: + and * are commutative (smaller first); - is not."""
    if operation in ('+', '*'):
        return (min(num1, num2), max(num1, num2))
    return (num1, num2)
def _canonical_key(num1, num2, operation):
    n1, n2 = _normalize_commutative(num1, num2, operation)
    return f"{operation}|{n1}|{n2}"

### Helpers: fluency rubric (ported from fluency_core.js)
def _median(values):
    """Median of a list (None when empty) — matches math_utils.js computeMedian."""
    if not values:
        return None
    s = sorted(values)
    mid = len(s) // 2
    if len(s) % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2
    return s[mid]
def _evaluate_status(attempts, thresholds):
    """Per-fact status from a list of attempts (each {isCorrect, responseTime}),
    oldest-first. Verbatim port of evaluateFluencyStatus: window the last N, gray
    if accuracy < minAccuracy or no correct, else green/yellow/red by median ms."""
    window_size = thresholds.get('windowSize') or DEFAULT_THRESHOLDS['windowSize']
    min_accuracy = thresholds.get('minAccuracy', DEFAULT_THRESHOLDS['minAccuracy'])
    green_ms = thresholds.get('greenMs') or DEFAULT_THRESHOLDS['greenMs']
    red_ms = thresholds.get('redMs') or DEFAULT_THRESHOLDS['redMs']
    if not attempts:
        return 'nodata'
    window = attempts[-window_size:]
    considered = len(window)
    correct = [a for a in window if a['isCorrect']]
    correct_count = len(correct)
    accuracy = (correct_count / considered) if considered else 0
    if accuracy < min_accuracy or correct_count == 0:
        return 'gray'
    times = [a['responseTime'] for a in correct if isinstance(a['responseTime'], (int, float))]
    median_ms = _median(times)
    if median_ms is None:
        return 'nodata'
    if median_ms < green_ms:
        return 'green'
    if median_ms < red_ms:
        return 'yellow'
    return 'red'
def _is_permanent(status_history, permanent_threshold):
    """Blue (permanent) iff the last N per-session statuses are all green."""
    if not status_history or len(status_history) < permanent_threshold:
        return False
    return all(s == 'green' for s in status_history[-permanent_threshold:])
def compute_fact_statuses(conn, user_name, thresholds=None):
    """Return {operation: {(n1,n2): status}} for one user, where status is the
    'combined' per-fact status the dashboard shows: the latest session's status
    when that session has attempts for the fact (else the overall windowed status),
    upgraded green->blue when the fact has been green for permanentSessions in a row.
    n1/n2 are the canonical (commutative-normalized) operands."""
    thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    permanent_threshold = thresholds.get('permanentSessions') or DEFAULT_THRESHOLDS['permanentSessions']

    # Pull this user's attempts joined to their sessions, in chronological order.
    exclusion_sql = _session_type_exclusion_sql(conn, 's')
    rows = conn.execute(
        f"""
        SELECT s.session_id AS session_id,
               s.end_time AS end_time, s.start_time AS start_time,
               a.attempt_id AS attempt_id, a.problem_text AS problem_text,
               a.num1 AS num1, a.num2 AS num2, a.operation AS operation,
               a.is_correct AS is_correct, a.response_time_ms AS response_time_ms
        FROM ProblemAttempts a
        INNER JOIN Sessions s ON a.session_id = s.session_id
        WHERE s.user_name = ?{exclusion_sql}
        ORDER BY COALESCE(s.end_time, s.start_time, ''), a.attempt_id
        """,
        (user_name,),
    ).fetchall()

    # Latest session = the one with the greatest end_time (fallback start_time).
    session_sortkey = {}
    for r in rows:
        session_sortkey[r['session_id']] = r['end_time'] or r['start_time'] or ''
    latest_session_id = None
    latest_key = None
    for sid, key in session_sortkey.items():
        if latest_key is None or key > latest_key:
            latest_key, latest_session_id = key, sid

    # Group attempts per fact (overall) and per fact-per-session (for history/current).
    facts = {}  # key -> {operation, n1, n2, attempts: [...], by_session: {sid: [...]}}
    for r in rows:
        num1, op, num2 = r['num1'], r['operation'], r['num2']
        if num1 is None or num2 is None or not op:
            num1, op, num2 = _parse_problem_text(r['problem_text'])
        if num1 is None or num2 is None or op not in OPERATIONS:
            continue
        cn1, cn2 = _normalize_commutative(num1, num2, op)
        key = f"{op}|{cn1}|{cn2}"
        attempt = {
            'isCorrect': r['is_correct'] in (1, True),
            'responseTime': r['response_time_ms'] if isinstance(r['response_time_ms'], (int, float)) else None,
        }
        rec = facts.get(key)
        if rec is None:
            rec = {'operation': op, 'n1': cn1, 'n2': cn2, 'attempts': [], 'by_session': {}}
            facts[key] = rec
        rec['attempts'].append(attempt)
        rec['by_session'].setdefault(r['session_id'], []).append(attempt)

    # Per-session order, oldest first, for the permanent-status history.
    sessions_oldest_first = sorted(session_sortkey, key=lambda sid: session_sortkey[sid])

    out = {op: {} for op in OPERATIONS}
    for key, rec in facts.items():
        op = rec['operation']
        previous = _evaluate_status(rec['attempts'], thresholds)
        current_attempts = rec['by_session'].get(latest_session_id, [])
        current = _evaluate_status(current_attempts, thresholds)
        history = [
            _evaluate_status(rec['by_session'][sid], thresholds)
            for sid in sessions_oldest_first if sid in rec['by_session']
        ]
        combined = current if (current_attempts and current != 'nodata') else previous
        if combined == 'green' and _is_permanent(history, permanent_threshold):
            combined = 'blue'
        out[op][(rec['n1'], rec['n2'])] = combined
    return out

### Helpers: escalating-difficulty fact universe (for filling gaps)
_ADDITION_CATEGORY_RANK = {
    'add-zero': 0, 'add-one': 1, 'add-two': 2, 'doubles': 3, 'tough-21': 4, 'hardest-six': 5,
}
def _addition_difficulty(n1, n2):
    """Difficulty tuple for an addition fact (lower = easier). Uses the formal
    segmentation: Add-0 < Add-1 < Add-2 < Doubles < Tough-21 < Hardest-6, then sum."""
    lo, hi = min(n1, n2), max(n1, n2)
    if lo == 0:
        cat = 'add-zero'
    elif lo == 1:
        cat = 'add-one'
    elif lo == 2:
        cat = 'add-two'
    elif lo == hi:
        cat = 'doubles'
    elif lo >= 6:
        cat = 'hardest-six'
    else:
        cat = 'tough-21'
    return (_ADDITION_CATEGORY_RANK[cat], lo + hi, hi, lo)
def _multiplication_difficulty(n1, n2):
    """Difficulty tuple for a multiplication fact (heuristic, pending formal x
    segmentation): x0 < x1 < x2 < (x5 / squares) < general < both>=6, then product."""
    lo, hi = min(n1, n2), max(n1, n2)
    if lo == 0:
        rank = 0
    elif lo == 1:
        rank = 1
    elif lo == 2:
        rank = 2
    elif lo == 5 or hi == 5 or lo == hi:
        rank = 3   # x5 trick and squares are memorable anchors
    elif lo >= 6:
        rank = 5   # both operands 6-9 — the hardest
    else:
        rank = 4
    return (rank, lo * hi, hi, lo)
def _subtraction_difficulty(n1, n2):
    """Difficulty tuple for a subtraction fact (heuristic, pending formal -
    segmentation): -0 < (n-n=0) < -1 < general, then by minuend, then subtrahend."""
    if n2 == 0:
        rank = 0
    elif n1 == n2:
        rank = 1
    elif n2 == 1:
        rank = 2
    else:
        rank = 3
    return (rank, n1, n2)
def _difficulty_fn(operation):
    return {'+': _addition_difficulty, '*': _multiplication_difficulty,
            '-': _subtraction_difficulty}[operation]
def ordered_universe(operation):
    """All canonical facts for an operation (0-9 operands), easiest -> hardest.
    + and * are commutative (lo<=hi, 55 facts); - is non-negative single-digit
    (n1>=n2, 55 facts)."""
    diff = _difficulty_fn(operation)
    facts = []
    for lo in range(0, 10):
        for hi in range(lo, 10):
            if operation == '-':
                facts.append((hi, lo))   # minuend >= subtrahend, non-negative
            else:
                facts.append((lo, hi))
    facts.sort(key=lambda nm: diff(*nm))
    return facts

### Selection: build the 7-problem set for one operation
def _problem_text(n1, n2, operation):
    return f"{n1} {operation} {n2}"
def select_for_operation(operation, statuses, thresholds=None):
    """Build the ordered 7-item set for one operation. `statuses` is {(n1,n2): status}
    (canonical operands) from compute_fact_statuses. Returns a list of 7 dicts with
    num1/num2/problem_text/slot_status/fact_status/origin, ordered green,green,green,
    yellow,yellow,yellow,red. Real facts fill each bucket first (hardest within the
    bucket, so practice sits at the competence frontier); shortfalls are filled by the
    escalating-difficulty universe drawing from the band that matches the slot."""
    diff = _difficulty_fn(operation)
    # Pools of real facts per slot. Blue (permanent) counts as fluent (green slot).
    pools = {'green': [], 'yellow': [], 'red': []}
    for (n1, n2), status in statuses.items():
        if status in ('green', 'blue'):
            pools['green'].append((n1, n2))
        elif status == 'yellow':
            pools['yellow'].append((n1, n2))
        elif status == 'red':
            pools['red'].append((n1, n2))
    # Hardest-first within each pool (frontier of the band).
    for slot in pools:
        pools[slot].sort(key=lambda nm: diff(*nm), reverse=True)

    # Escalating-difficulty universe, split into thirds for the fallback bands.
    universe = ordered_universe(operation)
    third = len(universe) // 3
    bands = {
        'green': universe[:third],                 # easiest -> fluent slots
        'yellow': universe[third:2 * third],       # middle -> almost slots
        'red': universe[2 * third:],               # hardest -> needs-practice slot
    }

    chosen_keys = set()
    items = []
    for slot, count in SLOT_PLAN:
        picked = []
        # 1) real facts for this bucket
        for nm in pools[slot]:
            if len(picked) >= count:
                break
            k = _canonical_key(nm[0], nm[1], operation)
            if k in chosen_keys:
                continue
            picked.append((nm, statuses.get(nm, slot), 'data'))
            chosen_keys.add(k)
        # 2) fill shortfall from the matching difficulty band, then the whole universe
        if len(picked) < count:
            fill_order = bands[slot] + [f for f in universe if f not in bands[slot]]
            for nm in fill_order:
                if len(picked) >= count:
                    break
                k = _canonical_key(nm[0], nm[1], operation)
                if k in chosen_keys:
                    continue
                picked.append((nm, None, 'algorithm'))
                chosen_keys.add(k)
        # 3) order picks within the slot by ascending difficulty (tidy ramp)
        picked.sort(key=lambda p: diff(*p[0]))
        for nm, fact_status, origin in picked:
            items.append({
                'num1': nm[0], 'num2': nm[1],
                'problem_text': _problem_text(nm[0], nm[1], operation),
                'slot_status': slot,
                'fact_status': fact_status,
                'origin': origin,
            })
    return items

### Regenerate + read
def regenerate_for_user(conn, user_name, thresholds=None, computed_at=None):
    """Recompute and REPLACE all 21 quick-practice rows for a user (3 ops x 7).
    Returns a summary {user_name, computed_at, operations: {op: [items...]}}.
    Idempotent: always deletes the user's rows first, then inserts the fresh set."""
    if not user_name:
        raise ValueError('user_name is required')
    ensure_quick_practice_schema(conn)
    conn.execute("INSERT OR IGNORE INTO Users(name) VALUES(?)", (user_name,))
    stamp = computed_at or datetime.now().strftime('%Y-%m-%d_%H%M%S')
    statuses = compute_fact_statuses(conn, user_name, thresholds)
    conn.execute("DELETE FROM QuickPracticeItems WHERE user_name = ?", (user_name,))
    summary = {'user_name': user_name, 'computed_at': stamp, 'operations': {}}
    for operation in OPERATIONS:
        items = select_for_operation(operation, statuses.get(operation, {}), thresholds)
        for order, item in enumerate(items, start=1):
            conn.execute(
                "INSERT INTO QuickPracticeItems(user_name, operation, item_order, problem_text, "
                "num1, num2, slot_status, fact_status, origin, computed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_name, operation, order, item['problem_text'], item['num1'], item['num2'],
                 item['slot_status'], item['fact_status'], item['origin'], stamp),
            )
        summary['operations'][operation] = items
    conn.commit()
    return summary
def fetch_for_user(conn, user_name):
    """Return {operation: [item rows...]} for a user, item_order ascending. Empty
    dict-of-lists when the user has no rows yet."""
    ensure_quick_practice_schema(conn)
    rows = conn.execute(
        "SELECT operation, item_order, problem_text, num1, num2, slot_status, fact_status, origin, "
        "computed_at FROM QuickPracticeItems WHERE user_name = ? ORDER BY operation, item_order",
        (user_name,),
    ).fetchall()
    out = {op: [] for op in OPERATIONS}
    for r in rows:
        out.setdefault(r['operation'], []).append(dict(r))
    return out

### CLI
def _main():
    ap = argparse.ArgumentParser(description="Generate/show quick-practice sets in a math-quiz .sqlite")
    ap.add_argument("db", help="path to the per-user .sqlite file")
    ap.add_argument("user", help="learner name")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show", help="print the stored quick-practice sets")
    sub.add_parser("regenerate", help="recompute + replace the 21 rows for this user")
    args = ap.parse_args()
    conn = connect(args.db)
    try:
        if args.cmd == "regenerate":
            print(json.dumps(regenerate_for_user(conn, args.user), indent=2, default=str))
        else:
            print(json.dumps(fetch_for_user(conn, args.user), indent=2, default=str))
    finally:
        conn.close()

if __name__ == "__main__":
    _main()
