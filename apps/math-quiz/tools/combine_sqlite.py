#!/usr/bin/env python3
"""Combine one or more anchor per-run SQLite files.

Two merge modes:
  multi   — keep each source as its own Sessions row (multiple sessions, one file).
  single  — merge all ProblemAttempts (and warm-ups / mode events) into one session.

Schema is read from source files (not hard-coded). The canonical schema comes from the
file with the latest Sessions.start_time; older sources are mapped into it.
Adds a CombineProvenance table (not used by the live app) so merged files stay auditable.
Combined output replaces the per-run timestamp suffix with _session: anchor_<user>_session.sqlite

Usage (from apps/math-quiz/):
  python3 tools/combine_sqlite.py single --canonical-user G1 \\
    --target anchor_G1_2026-06-15_135413.sqlite \\
    --sources anchor_Guinea1_2026-06-15_135306.sqlite anchor_G1_2026-06-15_135413.sqlite \\
    --archive-sources

----------------------------------------------------------------------------------------
Design (kept here in code on purpose — no separate plan markdown to drift out of sync)
----------------------------------------------------------------------------------------
Split into two modules so the merge orchestration never hard-codes the app's DDL:
  - combine_schema.py — introspect each source via sqlite_master + PRAGMA table_info into a
    SchemaSnapshot; pick the canonical schema (latest Sessions.start_time, mtime tie-break);
    validate required tables/columns; map older rows into the canonical column order
    (absent columns -> NULL); raise SchemaError on incompatible drift (missing required
    column, or an unrecognized column that looks like a rename). create_output_db copies the
    canonical CREATE TABLE DDL and adds the output-only CombineProvenance table.
  - this module — load each source into a bundle of column-driven rows, sort by start_time,
    and merge. All reads/writes are driven by the introspected columns; there are no fixed
    SESSION_COLS / PROBLEM_COLS tuples.

Required tables: Users, Sessions, ProblemAttempts. Optional tables: ModeEvents,
WarmupAttempts (absent in a source -> treated as empty; absent in canonical -> not written).
Optional columns (e.g. flags_json) absent in an older source -> NULL on insert.

Behavior notes / known wrinkles (documented rather than coded around):
  - Re-combining is supported: a source that is itself a prior combined file already carries
    a CombineProvenance table; introspection skips it, so the output always gets a fresh
    provenance table describing only this combine (old provenance is intentionally dropped).
  - A single-merged file stamps its Sessions.start_time with the EARLIEST source start, so
    its recorded recency understates its true latest activity. If you re-combine such a file
    with a genuinely older raw file that happens to have an equal-or-later start_time, the
    canonical pick can go to the older file. In practice schemas are identical across runs so
    the schema choice is unaffected; only matters if you later evolve the schema mid-flight.
  - single mode loses per-problem merged-from markers if the canonical schema has no
    flags_json column (map_row drops the unknown key); session-level provenance in
    CombineProvenance is always preserved regardless.

Review notes — 2026-06-16:
  - Output is now written atomically (build into <output>.partial, os.replace into place
    only on success; the partial is removed on any error) so a mid-merge failure — e.g. a
    duplicate session_id in multi mode — can never leave a half-written file that looks like
    valid combined data. See run_merge().
  - Dropped a dead second connection to the canonical file in create_output_db (DDL already
    lives on the introspected snapshot).
  - session_summary (single mode recomputes Sessions.average_response_time_ms across the
    merged problem set) now averages only over problems that actually carry a timing; a
    NULL/missing response_time_ms is excluded from numerator AND denominator instead of
    counting as 0 and pulling the average down. This matters here specifically because the
    combiner re-aggregates STORED rows from arbitrary/older/merged files, where the column
    can legitimately be NULL — unlike the live capture-time summary (anchor.js / math_quiz),
    which always averages freshly-measured in-memory attempts that are never NULL, so the
    same dilution pattern there is dormant and was intentionally left untouched.
"""
import argparse
import json
import os
import shutil
from datetime import datetime, timezone

from combine_schema import (
    SchemaError,
    check_all_compatible,
    connect,
    create_output_db,
    fetch_table_rows,
    insert_row,
    introspect_file,
    map_row,
    pick_canonical,
    source_select_columns,
)

### Helpers: paths
def repo_math_quiz_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def default_data_dir():
    return os.path.join(repo_math_quiz_dir(), 'math-quiz_data')
def resolve_path(data_dir, name):
    if os.path.isabs(name):
        return name
    return os.path.join(data_dir, name)
def table_exists(conn, name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None
def session_summary(problems):
    total = len(problems)
    correct = sum(1 for p in problems if p['is_correct'])
    # Average only over problems that actually have a timing. A missing/NULL
    # response_time_ms (e.g. an attempt captured without a timer) is excluded from both
    # the numerator and the denominator so it can't dilute the average toward zero.
    timed = [p['response_time_ms'] for p in problems if p.get('response_time_ms') is not None]
    avg = round(sum(timed) / len(timed)) if timed else 0
    return total, correct, avg
def earliest_start(sessions):
    return min(s['start_time'] for s in sessions if s.get('start_time'))
def latest_end(sessions):
    return max(s['end_time'] for s in sessions if s.get('end_time'))
def output_filename(canonical_user):
    return f"anchor_{canonical_user}_session.sqlite"
def _row_dict(row, columns):
    return {col: row[i] for i, col in enumerate(columns)}
def load_source_bundle(path, canonical):
    snapshot = introspect_file(path)
    conn = connect(path)
    session_cols = source_select_columns(snapshot, canonical, 'Sessions')
    problem_cols = source_select_columns(snapshot, canonical, 'ProblemAttempts')
    sessions = [
        _row_dict(r, session_cols)
        for r in fetch_table_rows(conn, 'Sessions', session_cols, '1=1 ORDER BY start_time')
    ] if session_cols else []
    if not sessions:
        conn.close()
        raise ValueError(f"No Sessions row in {path}")
    problems_by_session = {}
    for sess in sessions:
        sid = sess['session_id']
        rows = fetch_table_rows(
            conn, 'ProblemAttempts', problem_cols,
            'session_id=? ORDER BY attempt_id', (sid,),
        )
        problems_by_session[sid] = [_row_dict(r, problem_cols) for r in rows]
    warmups = []
    if snapshot.has_table('WarmupAttempts'):
        wcols = source_select_columns(snapshot, canonical, 'WarmupAttempts')
        if wcols:
            warmups = [
                _row_dict(r, wcols)
                for r in fetch_table_rows(conn, 'WarmupAttempts', wcols, '1=1 ORDER BY warmup_id')
            ]
    mode_events = []
    if snapshot.has_table('ModeEvents'):
        ecols = source_select_columns(snapshot, canonical, 'ModeEvents')
        if ecols:
            mode_events = [
                _row_dict(r, ecols)
                for r in fetch_table_rows(conn, 'ModeEvents', ecols, '1=1 ORDER BY event_id')
            ]
    conn.close()
    return {
        'path': path,
        'basename': os.path.basename(path),
        'snapshot': snapshot,
        'sessions': sessions,
        'problems_by_session': problems_by_session,
        'warmups': warmups,
        'mode_events': mode_events,
    }
def sort_bundles(bundles):
    return sorted(bundles, key=lambda b: earliest_start(b['sessions']))
def record_provenance(conn, mode, output_name, source_name, source_session_id, target_session_id,
                      source_start, problem_count, notes=''):
    conn.execute(
        "INSERT INTO CombineProvenance "
        "(combine_mode, output_filename, source_filename, source_session_id, target_session_id, "
        "source_start_time, problem_count, combined_at, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (mode, output_name, source_name, source_session_id, target_session_id,
         source_start, problem_count, datetime.now(timezone.utc).isoformat(), notes),
    )
def _insert_session(conn, canonical, row):
    cols = [c for c in canonical.column_names('Sessions') if c != 'attempt_id']
    insert_row(conn, 'Sessions', cols, map_row(row, cols))
def _insert_problem(conn, canonical, row):
    cols = [c for c in canonical.column_names('ProblemAttempts') if c != 'attempt_id']
    insert_row(conn, 'ProblemAttempts', cols, map_row(row, cols))
def _insert_warmup(conn, canonical, row):
    if not canonical.has_table('WarmupAttempts'):
        return
    cols = [c for c in canonical.column_names('WarmupAttempts') if c != 'warmup_id']
    insert_row(conn, 'WarmupAttempts', cols, map_row(row, cols))
def _insert_mode_event(conn, canonical, row):
    if not canonical.has_table('ModeEvents'):
        return
    cols = [c for c in canonical.column_names('ModeEvents') if c != 'event_id']
    insert_row(conn, 'ModeEvents', cols, map_row(row, cols))
### Merge: multi-session
def combine_multi(bundles, canonical, canonical_user, output_path):
    conn = create_output_db(output_path, canonical)
    output_name = os.path.basename(output_path)
    insert_row(conn, 'Users', ['name'], [canonical_user])
    for bundle in bundles:
        for sess in bundle['sessions']:
            sid = sess['session_id']
            if conn.execute('SELECT 1 FROM Sessions WHERE session_id=?', (sid,)).fetchone():
                conn.close()
                raise ValueError(f"Duplicate session_id {sid} — cannot merge into multi mode")
            row = dict(sess)
            row['user_name'] = canonical_user
            row['session_filename'] = output_name
            _insert_session(conn, canonical, row)
            problems = bundle['problems_by_session'][sid]
            for p in problems:
                prow = dict(p)
                prow['session_id'] = sid
                _insert_problem(conn, canonical, prow)
            record_provenance(conn, 'multi', output_name, bundle['basename'], sid, sid,
                              sess['start_time'], len(problems))
        for w in bundle['warmups']:
            wrow = dict(w)
            wrow['user_name'] = canonical_user
            _insert_warmup(conn, canonical, wrow)
        for ev in bundle['mode_events']:
            erow = dict(ev)
            erow['user_name'] = canonical_user
            _insert_mode_event(conn, canonical, erow)
    conn.commit()
    conn.close()
### Merge: single-session
def combine_single(bundles, canonical, canonical_user, target_session_id, output_path):
    conn = create_output_db(output_path, canonical)
    output_name = os.path.basename(output_path)
    insert_row(conn, 'Users', ['name'], [canonical_user])
    target_template = None
    all_sessions = []
    merged_problems = []
    merged_warmups = []
    merged_events = []
    for bundle in bundles:
        all_sessions.extend(bundle['sessions'])
        for sess in bundle['sessions']:
            sid = sess['session_id']
            problems = list(bundle['problems_by_session'][sid])
            if sid == target_session_id:
                target_template = dict(sess)
            for p in problems:
                row = dict(p)
                if sid != target_session_id:
                    flags = []
                    if row.get('flags_json'):
                        try:
                            flags = json.loads(row['flags_json'])
                        except Exception:
                            flags = []
                    flags.append({'merged_from': bundle['basename'], 'source_session_id': sid})
                    row['flags_json'] = json.dumps(flags)
                merged_problems.append(row)
            record_provenance(conn, 'single', output_name, bundle['basename'], sid, target_session_id,
                              sess['start_time'], len(problems))
        merged_warmups.extend(bundle['warmups'])
        merged_events.extend(bundle['mode_events'])
    if target_template is None:
        conn.close()
        raise ValueError(f"target session_id {target_session_id} not found in sources")
    merged_start = earliest_start(all_sessions)
    merged_end = latest_end(all_sessions)
    total, correct, avg = session_summary(merged_problems)
    target_template['session_id'] = target_session_id
    target_template['user_name'] = canonical_user
    target_template['session_filename'] = output_name
    target_template['start_time'] = merged_start
    target_template['end_time'] = merged_end
    target_template['total_problems'] = total
    target_template['correct_answers'] = correct
    target_template['average_response_time_ms'] = avg
    if 'num_problems' in canonical.column_names('Sessions'):
        target_template['num_problems'] = total
    _insert_session(conn, canonical, target_template)
    for idx, p in enumerate(merged_problems):
        prow = dict(p)
        prow['session_id'] = target_session_id
        prow['problem_id'] = f"{merged_start}-{idx}"
        _insert_problem(conn, canonical, prow)
    for w in merged_warmups:
        wrow = dict(w)
        wrow['user_name'] = canonical_user
        wrow['session_id'] = target_session_id
        _insert_warmup(conn, canonical, wrow)
    for ev in merged_events:
        erow = dict(ev)
        erow['user_name'] = canonical_user
        erow['session_id'] = target_session_id
        _insert_mode_event(conn, canonical, erow)
    conn.commit()
    conn.close()
def find_target_session_id(bundles, target_basename):
    for bundle in bundles:
        if bundle['basename'] == target_basename or bundle['path'].endswith(target_basename):
            if len(bundle['sessions']) != 1:
                raise ValueError(f"Target file {target_basename} must have exactly one session")
            return bundle['sessions'][0]['session_id']
    raise ValueError(f"Target file {target_basename} not found in sources")
def run_merge(mode, bundles, canonical, canonical_user, output_path, target_basename=None):
    """Run the chosen merge atomically.

    Build into <output_path>.partial and os.replace it into place only after the merge
    fully succeeds; remove the partial on any error. This guarantees output_path is never a
    half-written DB (e.g. when multi mode hits a duplicate session_id partway through).
    """
    tmp_path = output_path + '.partial'
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    try:
        if mode == 'multi':
            combine_multi(bundles, canonical, canonical_user, tmp_path)
        else:
            if not target_basename:
                raise ValueError('single mode requires --target (basename of session to merge into)')
            target_sid = find_target_session_id(bundles, os.path.basename(target_basename))
            combine_single(bundles, canonical, canonical_user, target_sid, tmp_path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
    os.replace(tmp_path, output_path)
def archive_sources(source_paths, data_dir):
    archive_dir = os.path.join(data_dir, '_combined')
    os.makedirs(archive_dir, exist_ok=True)
    moved = []
    for path in source_paths:
        dest = os.path.join(archive_dir, os.path.basename(path))
        if os.path.exists(dest):
            raise ValueError(f"Archive destination already exists: {dest}")
        shutil.move(path, dest)
        moved.append(dest)
    return moved
def print_report(output_path, mode, canonical):
    conn = connect(output_path)
    print(f"\n=== Combined: {os.path.basename(output_path)} ({mode}) ===")
    print(f"  Schema from: {canonical.basename} (latest start_time {canonical.recency})")
    for row in conn.execute(
        "SELECT user_name, session_id, start_time, end_time, total_problems, correct_answers "
        "FROM Sessions ORDER BY start_time"
    ):
        print(f"  Session {row[1][:8]}…  user={row[0]}  {row[2]} → {row[3]}  problems={row[4]}  correct={row[5]}")
    n_prob = conn.execute("SELECT COUNT(*) FROM ProblemAttempts").fetchone()[0]
    n_wu = conn.execute("SELECT COUNT(*) FROM WarmupAttempts").fetchone()[0] if table_exists(conn, 'WarmupAttempts') else 0
    print(f"  ProblemAttempts: {n_prob}   WarmupAttempts: {n_wu}")
    print("  Provenance:")
    for row in conn.execute(
        "SELECT source_filename, source_session_id, source_start_time, problem_count "
        "FROM CombineProvenance ORDER BY combine_id"
    ):
        print(f"    ← {row[0]}  session={row[1][:8]}…  start={row[2]}  problems={row[3]}")
    conn.close()
### CLI
def build_parser():
    p = argparse.ArgumentParser(description='Combine anchor per-run SQLite files.')
    p.add_argument('mode', choices=['multi', 'single'], help='multi = separate sessions; single = one merged session')
    p.add_argument('--sources', nargs='+', required=True, help='SQLite files to combine (sorted by start_time unless --no-sort)')
    p.add_argument('--canonical-user', required=True, help='Username to store in the combined file')
    p.add_argument('--target', help='For single mode: basename of the file whose session_id becomes the merged session')
    p.add_argument('--output', help='Output path (default: anchor_<user>_session.sqlite in data dir)')
    p.add_argument('--data-dir', default=None, help=f'Directory containing sources (default: {default_data_dir()})')
    p.add_argument('--no-sort', action='store_true', help='Keep source order instead of sorting by session start_time')
    p.add_argument('--archive-sources', action='store_true', help='Move (not copy) source files into data-dir/_combined/')
    p.add_argument('--dry-run', action='store_true', help='Print plan only; do not write or move files')
    return p
def main():
    args = build_parser().parse_args()
    data_dir = args.data_dir or default_data_dir()
    source_paths = [resolve_path(data_dir, s) for s in args.sources]
    for path in source_paths:
        if not os.path.isfile(path):
            raise SystemExit(f"Source not found: {path}")
    snapshots = [introspect_file(p) for p in source_paths]
    try:
        canonical = pick_canonical(snapshots)
        check_all_compatible(snapshots, canonical)
    except SchemaError as e:
        raise SystemExit(f"Schema error: {e}") from e
    bundles = [load_source_bundle(p, canonical) for p in source_paths]
    if not args.no_sort:
        bundles = sort_bundles(bundles)
    output_path = args.output or resolve_path(data_dir, output_filename(args.canonical_user))
    print(f"Mode: {args.mode}")
    print(f"Canonical user: {args.canonical_user}")
    print(f"Canonical schema: {canonical.basename} (start_time {canonical.recency})")
    print(f"Sources ({len(bundles)}):")
    for b in bundles:
        sess = b['sessions'][0]
        n = len(b['problems_by_session'][sess['session_id']])
        print(f"  {b['basename']}  user={sess['user_name']}  start={sess['start_time']}  problems={n}")
    print(f"Output: {output_path}")
    if args.dry_run:
        return
    if args.mode == 'single' and not args.target:
        raise SystemExit('single mode requires --target (basename of session to merge into)')
    run_merge(args.mode, bundles, canonical, args.canonical_user, output_path, args.target)
    print_report(output_path, args.mode, canonical)
    if args.archive_sources:
        moved = archive_sources(source_paths, data_dir)
        print(f"\nArchived {len(moved)} source file(s) to {os.path.join(data_dir, '_combined')}/")
        for m in moved:
            print(f"  {os.path.basename(m)}")
if __name__ == '__main__':
    main()
