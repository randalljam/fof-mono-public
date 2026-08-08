#!/usr/bin/env python3
# Unit tests for combine_sqlite.py / combine_schema.py
# Run: .venv/bin/pytest apps/math-quiz/tools/test_combine_sqlite.py -v
import importlib.util
import os
import sqlite3
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(TOOLS, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
schema = _load('combine_schema', 'combine_schema.py')
combine = _load('combine_sqlite', 'combine_sqlite.py')

### Fixture helpers (test-only DDL)
BASE_SESSION_COLS = (
    'session_id', 'session_filename', 'user_name', 'start_time', 'end_time',
    'num_problems', 'number_range_start', 'number_range_end', 'numbers_include',
    'numbers_exclude', 'num_numbers', 'operations', 'total_problems',
    'correct_answers', 'average_response_time_ms',
)
def _sessions_ddl(extra_cols=()):
    cols = list(BASE_SESSION_COLS) + list(extra_cols)
    body = ', '.join(f'{c} TEXT' if c in ('session_id', 'session_filename', 'user_name', 'start_time', 'end_time', 'numbers_include', 'numbers_exclude', 'operations') else f'{c} INTEGER' for c in cols)
    return f'CREATE TABLE Sessions ({body}, PRIMARY KEY (session_id))'
def _problems_ddl(*, include_flags=True):
    cols = [
        'attempt_id INTEGER PRIMARY KEY AUTOINCREMENT', 'session_id TEXT', 'problem_id TEXT',
        'problem_text TEXT', 'num1 INTEGER', 'num2 INTEGER', 'operation TEXT',
        'correct_answer REAL', 'user_answer_string TEXT', 'user_answer REAL',
        'is_correct INTEGER', 'response_time_ms INTEGER',
    ]
    if include_flags:
        cols.append('flags_json TEXT')
    return f"CREATE TABLE ProblemAttempts ({', '.join(cols)})"
def _warmup_ddl():
    return """CREATE TABLE WarmupAttempts (
        warmup_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT, session_id TEXT, round INTEGER, target INTEGER,
        entered TEXT, is_correct INTEGER, response_time_ms INTEGER, timestamp TEXT
    )"""
def _make_anchor_db(path, *, start_time, session_id, user_name, problems, include_flags=True,
                    include_warmup=False, problem_ddl_override=None):
    conn = sqlite3.connect(path)
    has_flags = include_flags and problem_ddl_override is None
    conn.execute('CREATE TABLE Users (name TEXT PRIMARY KEY)')
    conn.execute(_sessions_ddl())
    conn.execute(problem_ddl_override or _problems_ddl(include_flags=include_flags))
    if include_warmup:
        conn.execute(_warmup_ddl())
        conn.execute(
            'INSERT INTO WarmupAttempts (user_name, session_id, round, target, entered, is_correct, response_time_ms, timestamp) '
            'VALUES (?, ?, 1, 3, "3", 1, 100, "t")',
            (user_name, session_id),
        )
    conn.execute('INSERT INTO Users (name) VALUES (?)', (user_name,))
    total = len(problems)
    correct = sum(1 for p in problems if p.get('is_correct', 1))
    avg = round(sum(p.get('response_time_ms', 1000) for p in problems) / total) if total else 0
    conn.execute(
        'INSERT INTO Sessions (session_id, session_filename, user_name, start_time, end_time, '
        'num_problems, total_problems, correct_answers, average_response_time_ms) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (session_id, os.path.basename(path), user_name, start_time, start_time + '_end',
         total, total, correct, avg),
    )
    for i, p in enumerate(problems):
        if has_flags:
            conn.execute(
                'INSERT INTO ProblemAttempts (session_id, problem_id, problem_text, is_correct, response_time_ms, flags_json) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                (session_id, f'{start_time}-{i}', p.get('text', f'1 + {i}'), p.get('is_correct', 1),
                 p.get('response_time_ms', 1000), p.get('flags_json')),
            )
        else:
            conn.execute(
                'INSERT INTO ProblemAttempts (session_id, problem_id, problem_text, is_correct, response_time_ms) '
                'VALUES (?, ?, ?, ?, ?)',
                (session_id, f'{start_time}-{i}', p.get('text', f'1 + {i}'), p.get('is_correct', 1),
                 p.get('response_time_ms', 1000)),
            )
    conn.commit()
    conn.close()

def _problems_ddl_no_response_time():
    return """CREATE TABLE ProblemAttempts (
        attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT, problem_id TEXT, problem_text TEXT, is_correct INTEGER
    )"""

### Tests: schema layer
def test_canonical_picks_latest_start_time():
    with tempfile.TemporaryDirectory() as d:
        old = os.path.join(d, 'old.sqlite')
        new = os.path.join(d, 'new.sqlite')
        _make_anchor_db(old, start_time='2026-06-15_100000', session_id='s-old', user_name='A',
                        problems=[{'text': '1 + 1'}], include_flags=False)
        _make_anchor_db(new, start_time='2026-06-15_200000', session_id='s-new', user_name='B',
                        problems=[{'text': '2 + 2'}], include_flags=True)
        snaps = [schema.introspect_file(old), schema.introspect_file(new)]
        canonical = schema.pick_canonical(snaps)
        assert canonical.basename == 'new.sqlite'
        assert 'flags_json' in canonical.column_names('ProblemAttempts')
        schema.check_all_compatible(snaps, canonical)

def test_schema_error_missing_required_column():
    with tempfile.TemporaryDirectory() as d:
        old = os.path.join(d, 'old.sqlite')
        new = os.path.join(d, 'new.sqlite')
        conn = sqlite3.connect(old)
        conn.execute('CREATE TABLE Users (name TEXT PRIMARY KEY)')
        conn.execute(_sessions_ddl())
        conn.execute(_problems_ddl_no_response_time())
        conn.execute("INSERT INTO Users VALUES ('A')")
        conn.execute(
            "INSERT INTO Sessions (session_id, session_filename, user_name, start_time, end_time, "
            "total_problems, correct_answers, average_response_time_ms) "
            "VALUES ('s1', 'old.sqlite', 'A', '2026-06-15_100000', 'end', 1, 1, 100)"
        )
        conn.execute(
            "INSERT INTO ProblemAttempts (session_id, problem_id, problem_text, is_correct) "
            "VALUES ('s1', 'p0', '1+1', 1)"
        )
        conn.commit()
        conn.close()
        _make_anchor_db(new, start_time='2026-06-15_200000', session_id='s-new', user_name='B',
                        problems=[{'text': '2 + 2'}])
        snaps = [schema.introspect_file(old), schema.introspect_file(new)]
        canonical = schema.pick_canonical(snaps)
        try:
            schema.check_compatible(snaps[0], canonical)
        except schema.SchemaError as e:
            assert 'response_time_ms' in str(e)
        else:
            raise AssertionError('expected SchemaError for missing response_time_ms')

def test_schema_error_missing_required_table():
    with tempfile.TemporaryDirectory() as d:
        bad = os.path.join(d, 'bad.sqlite')
        conn = sqlite3.connect(bad)
        conn.execute('CREATE TABLE Users (name TEXT PRIMARY KEY)')
        conn.execute(_sessions_ddl())
        conn.execute("INSERT INTO Users VALUES ('A')")
        conn.execute(
            "INSERT INTO Sessions (session_id, session_filename, user_name, start_time, end_time, "
            "total_problems, correct_answers, average_response_time_ms) "
            "VALUES ('s1', 'bad.sqlite', 'A', '2026-06-15_100000', 'end', 0, 0, 0)"
        )
        conn.commit()
        conn.close()
        try:
            schema.introspect_file(bad)
            schema.pick_canonical([schema.introspect_file(bad)])
        except schema.SchemaError as e:
            assert 'ProblemAttempts' in str(e)
        else:
            raise AssertionError('expected SchemaError for missing ProblemAttempts')

### Tests: combine merges
def test_identical_schemas_single_merge():
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, 'a.sqlite')
        b = os.path.join(d, 'b.sqlite')
        out = os.path.join(d, 'out.sqlite')
        _make_anchor_db(a, start_time='2026-06-15_100000', session_id='s-a', user_name='Kid',
                        problems=[{'text': '1 + 1', 'response_time_ms': 100}])
        _make_anchor_db(b, start_time='2026-06-15_200000', session_id='s-b', user_name='Kid',
                        problems=[{'text': '2 + 2', 'response_time_ms': 200}, {'text': '3 + 3', 'response_time_ms': 300}])
        snaps = [schema.introspect_file(p) for p in (a, b)]
        canonical = schema.pick_canonical(snaps)
        schema.check_all_compatible(snaps, canonical)
        bundles = [combine.load_source_bundle(p, canonical) for p in (a, b)]
        bundles = combine.sort_bundles(bundles)
        combine.combine_single(bundles, canonical, 'Canonical', 's-b', out)
        conn = sqlite3.connect(out)
        n = conn.execute('SELECT COUNT(*) FROM ProblemAttempts').fetchone()[0]
        user = conn.execute('SELECT user_name FROM Sessions').fetchone()[0]
        first = conn.execute('SELECT problem_text FROM ProblemAttempts ORDER BY attempt_id LIMIT 1').fetchone()[0]
        conn.close()
        assert n == 3
        assert user == 'Canonical'
        assert first == '1 + 1'

def test_older_missing_optional_column():
    with tempfile.TemporaryDirectory() as d:
        old = os.path.join(d, 'old.sqlite')
        new = os.path.join(d, 'new.sqlite')
        out = os.path.join(d, 'out.sqlite')
        _make_anchor_db(old, start_time='2026-06-15_100000', session_id='s-old', user_name='K',
                        problems=[{'text': '1 + 1'}], include_flags=False)
        _make_anchor_db(new, start_time='2026-06-15_200000', session_id='s-new', user_name='K',
                        problems=[{'text': '2 + 2', 'flags_json': '[]'}], include_flags=True)
        snaps = [schema.introspect_file(p) for p in (old, new)]
        canonical = schema.pick_canonical(snaps)
        bundles = combine.sort_bundles([combine.load_source_bundle(p, canonical) for p in (old, new)])
        combine.combine_multi(bundles, canonical, 'K', out)
        conn = sqlite3.connect(out)
        old_flags = conn.execute(
            "SELECT flags_json FROM ProblemAttempts WHERE session_id='s-old'"
        ).fetchone()[0]
        new_flags = conn.execute(
            "SELECT flags_json FROM ProblemAttempts WHERE session_id='s-new'"
        ).fetchone()[0]
        conn.close()
        assert old_flags is None
        assert new_flags == '[]'

def test_older_missing_optional_table():
    with tempfile.TemporaryDirectory() as d:
        old = os.path.join(d, 'old.sqlite')
        new = os.path.join(d, 'new.sqlite')
        out = os.path.join(d, 'out.sqlite')
        _make_anchor_db(old, start_time='2026-06-15_100000', session_id='s-old', user_name='K',
                        problems=[{'text': '1 + 1'}], include_warmup=False)
        _make_anchor_db(new, start_time='2026-06-15_200000', session_id='s-new', user_name='K',
                        problems=[{'text': '2 + 2'}], include_warmup=True)
        snaps = [schema.introspect_file(p) for p in (old, new)]
        canonical = schema.pick_canonical(snaps)
        bundles = combine.sort_bundles([combine.load_source_bundle(p, canonical) for p in (old, new)])
        combine.combine_single(bundles, canonical, 'K', 's-new', out)
        conn = sqlite3.connect(out)
        n = conn.execute('SELECT COUNT(*) FROM WarmupAttempts').fetchone()[0]
        conn.close()
        assert n == 1

def test_multi_duplicate_session_id():
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, 'a.sqlite')
        b = os.path.join(d, 'b.sqlite')
        out = os.path.join(d, 'out.sqlite')
        _make_anchor_db(a, start_time='2026-06-15_100000', session_id='same-id', user_name='K',
                        problems=[{'text': '1 + 1'}])
        _make_anchor_db(b, start_time='2026-06-15_200000', session_id='same-id', user_name='K',
                        problems=[{'text': '2 + 2'}])
        snaps = [schema.introspect_file(p) for p in (a, b)]
        canonical = schema.pick_canonical(snaps)
        bundles = [combine.load_source_bundle(p, canonical) for p in (a, b)]
        try:
            combine.combine_multi(bundles, canonical, 'K', out)
        except ValueError as e:
            assert 'Duplicate session_id' in str(e)
        else:
            raise AssertionError('expected ValueError for duplicate session_id')

def test_session_summary_excludes_null_response_time():
    # A NULL/missing response_time_ms must be dropped from the average, not counted as 0.
    problems = [
        {'is_correct': 1, 'response_time_ms': 100},
        {'is_correct': 0, 'response_time_ms': 300},
        {'is_correct': 1, 'response_time_ms': None},
    ]
    total, correct, avg = combine.session_summary(problems)
    assert total == 3            # count still reflects every problem
    assert correct == 2
    assert avg == 200            # (100 + 300) / 2, NOT (100 + 300 + 0) / 3 == 133

def test_run_merge_removes_partial_output_on_error():
    # A mid-merge failure (duplicate session_id in multi mode) must not leave a half-written
    # output file behind — run_merge builds into <out>.partial and only renames on success.
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, 'a.sqlite')
        b = os.path.join(d, 'b.sqlite')
        out = os.path.join(d, 'out.sqlite')
        _make_anchor_db(a, start_time='2026-06-15_100000', session_id='dup', user_name='K',
                        problems=[{'text': '1 + 1'}])
        _make_anchor_db(b, start_time='2026-06-15_200000', session_id='dup', user_name='K',
                        problems=[{'text': '2 + 2'}])
        snaps = [schema.introspect_file(p) for p in (a, b)]
        canonical = schema.pick_canonical(snaps)
        bundles = [combine.load_source_bundle(p, canonical) for p in (a, b)]
        try:
            combine.run_merge('multi', bundles, canonical, 'K', out)
        except ValueError as e:
            assert 'Duplicate session_id' in str(e)
        else:
            raise AssertionError('expected ValueError for duplicate session_id')
        assert not os.path.exists(out), 'output file should not exist after a failed merge'
        assert not os.path.exists(out + '.partial'), 'partial file should be cleaned up'

def test_recombine_rebuilds_fresh_provenance():
    # Re-combining a source that already carries a CombineProvenance table must skip the old
    # provenance on read and write exactly one fresh provenance row set for this combine.
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, 'a.sqlite')
        b = os.path.join(d, 'b.sqlite')
        first = os.path.join(d, 'first.sqlite')
        second = os.path.join(d, 'second.sqlite')
        _make_anchor_db(a, start_time='2026-06-15_100000', session_id='s-a', user_name='K',
                        problems=[{'text': '1 + 1'}])
        _make_anchor_db(b, start_time='2026-06-15_200000', session_id='s-b', user_name='K',
                        problems=[{'text': '2 + 2'}])
        snaps = [schema.introspect_file(p) for p in (a, b)]
        canonical = schema.pick_canonical(snaps)
        bundles = combine.sort_bundles([combine.load_source_bundle(p, canonical) for p in (a, b)])
        combine.run_merge('multi', bundles, canonical, 'K', first)
        conn = sqlite3.connect(first)
        assert conn.execute('SELECT COUNT(*) FROM CombineProvenance').fetchone()[0] == 2
        conn.close()
        # Now combine the already-combined file with a fresh source.
        c = os.path.join(d, 'c.sqlite')
        _make_anchor_db(c, start_time='2026-06-15_300000', session_id='s-c', user_name='K',
                        problems=[{'text': '3 + 3'}])
        snaps2 = [schema.introspect_file(p) for p in (first, c)]
        canonical2 = schema.pick_canonical(snaps2)
        # The prior combine's CombineProvenance table is not a mergeable app table.
        assert 'CombineProvenance' not in canonical2.tables
        bundles2 = combine.sort_bundles([combine.load_source_bundle(p, canonical2) for p in (first, c)])
        combine.run_merge('multi', bundles2, canonical2, 'K', second)
        conn = sqlite3.connect(second)
        prov = conn.execute('SELECT source_filename FROM CombineProvenance ORDER BY combine_id').fetchall()
        nprob = conn.execute('SELECT COUNT(*) FROM ProblemAttempts').fetchone()[0]
        conn.close()
        # Fresh provenance for THIS combine only (per source session): first.sqlite carries
        # two sessions (s-a, s-b) so two rows, plus one for c.sqlite — the old combine's
        # provenance rows are not carried forward.
        assert [r[0] for r in prov] == ['first.sqlite', 'first.sqlite', 'c.sqlite']
        assert nprob == 3  # 2 carried in first.sqlite + 1 from c.sqlite
