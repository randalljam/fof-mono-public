#!/usr/bin/env python3
"""
file: apps/math-quiz/tools/problem_list_store.py
title: Manage problem lists in math-quiz SQLite files

Adds a schema extension for ordered problem lists and provides a CLI to:
- migrate an existing DB with ProblemLists / ProblemListItems tables
- import a list from a .txt file (standard "3 + 8" format + richer metadata forms)
- display lists in terminal text or export markdown
"""
import argparse
import os
import re
import sqlite3
from datetime import datetime

_BULLET_PREFIX_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[\.\)]\s+)")
_PROBLEM_RE = re.compile(r"(-?\d+)\s*([+\-*/xX×÷−])\s*(-?\d+)")

### Helpers: parsing
def _normalize_operation(op):
    if op in ('x', 'X', '×', '*'):
        return '*'
    if op in ('−', '-'):
        return '-'
    if op in ('÷', '/'):
        return '/'
    return '+'
def _parse_metadata_tail(tail):
    category = None
    notes = None
    raw = str(tail or '').strip()
    if not raw:
        return category, notes
    raw = raw.lstrip('|,;:- \t').strip()
    if raw.startswith('(') and raw.endswith(')') and len(raw) > 2:
        raw = raw[1:-1].strip()
    if not raw:
        return category, notes
    split_delim = None
    for delim in ('|', '\t', ';'):
        if delim in raw:
            split_delim = delim
            break
    if split_delim is not None:
        parts = [p.strip() for p in raw.split(split_delim) if p.strip()]
    else:
        parts = [raw]
    if len(parts) == 1 and ',' in parts[0]:
        maybe = [p.strip() for p in parts[0].split(',', 1)]
        parts = [p for p in maybe if p]
    if parts:
        category = parts[0] or None
    if len(parts) > 1:
        notes = ' | '.join(parts[1:]).strip() or None
    return category, notes
def parse_problem_line(line, default_category=''):
    raw = str(line or '').rstrip('\n')
    stripped = _BULLET_PREFIX_RE.sub('', raw).strip()
    if not stripped or stripped.startswith('#'):
        return None
    match = _PROBLEM_RE.search(stripped)
    if not match:
        raise ValueError(f'Could not parse problem line: "{line}"')
    num1 = int(match.group(1))
    op = _normalize_operation(match.group(2))
    num2 = int(match.group(3))
    category, notes = _parse_metadata_tail(stripped[match.end():])
    if not category:
        category = default_category.strip() if default_category else None
    return {
        'problem_text': f'{num1} {op} {num2}',
        'num1': num1,
        'operation': op,
        'num2': num2,
        'category': category,
        'notes': notes,
    }
def parse_problem_list_text(text, default_category=''):
    problems = []
    for line in str(text or '').splitlines():
        parsed = parse_problem_line(line, default_category=default_category)
        if parsed is not None:
            problems.append(parsed)
    if not problems:
        raise ValueError('No valid problem lines found.')
    return problems

### Helpers: sqlite
def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
def ensure_problem_list_schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ProblemLists (
            problem_list_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            list_order INTEGER NOT NULL DEFAULT 0,
            list_name TEXT NOT NULL,
            added_at TEXT NOT NULL,
            source TEXT,
            retain INTEGER NOT NULL DEFAULT 1,
            times_used INTEGER NOT NULL DEFAULT 0,
            last_used_at TEXT,
            FOREIGN KEY (user_name) REFERENCES Users(name)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_problem_lists_user_order
        ON ProblemLists (user_name, list_order, problem_list_id)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ProblemListItems (
            problem_list_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            problem_list_id INTEGER NOT NULL,
            item_order INTEGER NOT NULL,
            problem_text TEXT NOT NULL,
            num1 INTEGER NULL,
            operation TEXT NULL,
            num2 INTEGER NULL,
            category TEXT,
            notes TEXT,
            FOREIGN KEY (problem_list_id) REFERENCES ProblemLists(problem_list_id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_problem_list_items_list_order
        ON ProblemListItems (problem_list_id, item_order)
    """)
    for stmt in (
        "ALTER TABLE ProblemLists ADD COLUMN list_order INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE ProblemLists ADD COLUMN source TEXT",
        "ALTER TABLE ProblemLists ADD COLUMN added_at TEXT",
        # retain defaults to 1 (keep): a used list stays unless explicitly marked to consume.
        "ALTER TABLE ProblemLists ADD COLUMN retain INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE ProblemLists ADD COLUMN times_used INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE ProblemLists ADD COLUMN last_used_at TEXT",
        "ALTER TABLE ProblemListItems ADD COLUMN category TEXT",
        "ALTER TABLE ProblemListItems ADD COLUMN notes TEXT",
    ):
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError:
            pass
    conn.commit()
def next_list_order(conn, user_name):
    row = conn.execute(
        "SELECT COALESCE(MAX(list_order), 0) FROM ProblemLists WHERE user_name = ?",
        (user_name,),
    ).fetchone()
    return int(row[0] or 0) + 1
def add_problem_list(conn, user_name, list_name, source, problems, added_at=None, list_order=None, retain=True):
    if not user_name:
        raise ValueError('user_name is required')
    if not list_name:
        raise ValueError('list_name is required')
    if not problems:
        raise ValueError('problems cannot be empty')
    ensure_problem_list_schema(conn)
    conn.execute("INSERT OR IGNORE INTO Users(name) VALUES(?)", (user_name,))
    timestamp = added_at or datetime.now().isoformat(timespec='seconds')
    order_value = int(list_order) if list_order is not None else next_list_order(conn, user_name)
    cur = conn.execute(
        "INSERT INTO ProblemLists(user_name, list_order, list_name, added_at, source, retain) VALUES(?, ?, ?, ?, ?, ?)",
        (user_name, order_value, list_name, timestamp, source or '', 1 if retain else 0),
    )
    problem_list_id = cur.lastrowid
    for idx, item in enumerate(problems, start=1):
        conn.execute(
            "INSERT INTO ProblemListItems(problem_list_id, item_order, problem_text, num1, operation, num2, category, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                problem_list_id,
                idx,
                item.get('problem_text'),
                item.get('num1'),
                item.get('operation'),
                item.get('num2'),
                item.get('category'),
                item.get('notes'),
            ),
        )
    conn.commit()
    return {'problem_list_id': problem_list_id, 'list_order': order_value, 'item_count': len(problems)}
def fetch_problem_lists(conn, user_name=None):
    ensure_problem_list_schema(conn)
    cols = ("problem_list_id, user_name, list_order, list_name, added_at, source, "
            "retain, times_used, last_used_at")
    if user_name:
        list_rows = conn.execute(
            f"SELECT {cols} FROM ProblemLists WHERE user_name = ? ORDER BY user_name, list_order, problem_list_id",
            (user_name,),
        ).fetchall()
    else:
        list_rows = conn.execute(
            f"SELECT {cols} FROM ProblemLists ORDER BY user_name, list_order, problem_list_id"
        ).fetchall()
    out = []
    for row in list_rows:
        items = conn.execute(
            "SELECT item_order, problem_text, num1, operation, num2, category, notes FROM ProblemListItems "
            "WHERE problem_list_id = ? ORDER BY item_order",
            (row['problem_list_id'],),
        ).fetchall()
        out.append({
            'problem_list_id': row['problem_list_id'],
            'user_name': row['user_name'],
            'list_order': row['list_order'],
            'list_name': row['list_name'],
            'added_at': row['added_at'],
            'source': row['source'],
            'retain': int(row['retain']) if row['retain'] is not None else 1,
            'times_used': int(row['times_used']) if row['times_used'] is not None else 0,
            'last_used_at': row['last_used_at'],
            'item_count': len(items),
            'items': [dict(item) for item in items],
        })
    return out

### Helpers: ordering + consumption (the "use internal" stack/queue)
def reindex_problem_lists(conn, user_name):
    """Renumber a user's list_order to a contiguous 1..N (by current order, then id), so the
    run order always starts at 1 with no gaps after a list is consumed. Returns the new count."""
    ensure_problem_list_schema(conn)
    rows = conn.execute(
        "SELECT problem_list_id FROM ProblemLists WHERE user_name = ? ORDER BY list_order, problem_list_id",
        (user_name,),
    ).fetchall()
    for new_order, row in enumerate(rows, start=1):
        conn.execute("UPDATE ProblemLists SET list_order = ? WHERE problem_list_id = ?", (new_order, row[0]))
    conn.commit()
    return len(rows)
def next_problem_list(conn, user_name):
    """The next list to run for a user (the lowest list_order), with items — or None."""
    lists = fetch_problem_lists(conn, user_name=user_name)
    return lists[0] if lists else None
def set_retain(conn, problem_list_id, retain):
    """Mark a list keep (retain=True) or consume-after-use (retain=False)."""
    ensure_problem_list_schema(conn)
    conn.execute("UPDATE ProblemLists SET retain = ? WHERE problem_list_id = ?",
                 (1 if retain else 0, problem_list_id))
    conn.commit()
    return conn.execute("SELECT changes()").fetchone()[0]
def consume_problem_list(conn, problem_list_id, used_at=None):
    """Pop a just-used list. If retain is set, bump times_used / last_used_at and KEEP it; else
    DELETE it (and its items) and reindex the owner's remaining lists to a contiguous 1..N.
    Returns {action: retained|deleted|missing, ...}. Idempotent for a missing id."""
    ensure_problem_list_schema(conn)
    row = conn.execute(
        "SELECT problem_list_id, user_name, list_order, list_name, retain, times_used "
        "FROM ProblemLists WHERE problem_list_id = ?",
        (problem_list_id,),
    ).fetchone()
    if not row:
        return {'action': 'missing', 'problem_list_id': problem_list_id}
    user_name, list_order, list_name = row['user_name'], row['list_order'], row['list_name']
    retain = int(row['retain']) if row['retain'] is not None else 1
    times_used = int(row['times_used']) if row['times_used'] is not None else 0
    timestamp = used_at or datetime.now().isoformat(timespec='seconds')
    summary = {'problem_list_id': problem_list_id, 'user_name': user_name,
               'list_order': list_order, 'list_name': list_name}
    if retain:
        conn.execute("UPDATE ProblemLists SET times_used = ?, last_used_at = ? WHERE problem_list_id = ?",
                     (times_used + 1, timestamp, problem_list_id))
        conn.commit()
        summary.update({'action': 'retained', 'times_used': times_used + 1, 'last_used_at': timestamp})
        return summary
    conn.execute("DELETE FROM ProblemListItems WHERE problem_list_id = ?", (problem_list_id,))
    conn.execute("DELETE FROM ProblemLists WHERE problem_list_id = ?", (problem_list_id,))
    conn.commit()
    reindex_problem_lists(conn, user_name)
    summary['action'] = 'deleted'
    return summary

### Helpers: editing (manual CRUD for the problem-list editor)
def replace_list_items(conn, problem_list_id, problems):
    """Replace ALL items of a list with `problems` (re-numbered item_order 1..N), keeping the
    list row. Used by the editor's auto-save when a list's text is edited. Returns the count."""
    ensure_problem_list_schema(conn)
    if conn.execute("SELECT 1 FROM ProblemLists WHERE problem_list_id = ?", (problem_list_id,)).fetchone() is None:
        raise ValueError(f'No problem list with id {problem_list_id}')
    conn.execute("DELETE FROM ProblemListItems WHERE problem_list_id = ?", (problem_list_id,))
    for idx, item in enumerate(problems, start=1):
        conn.execute(
            "INSERT INTO ProblemListItems(problem_list_id, item_order, problem_text, num1, operation, num2, category, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (problem_list_id, idx, item.get('problem_text'), item.get('num1'), item.get('operation'),
             item.get('num2'), item.get('category'), item.get('notes')),
        )
    conn.commit()
    return len(problems)
def create_list(conn, user_name, list_name, problems=None, source='editor', retain=True):
    """Create a list that MAY be empty (the editor adds a blank card, then fills it via
    replace_list_items as you type). Appended at the end of the queue (next list_order).
    Returns {problem_list_id, list_order, item_count}."""
    if not user_name:
        raise ValueError('user_name is required')
    ensure_problem_list_schema(conn)
    conn.execute("INSERT OR IGNORE INTO Users(name) VALUES(?)", (user_name,))
    timestamp = datetime.now().isoformat(timespec='seconds')
    order_value = next_list_order(conn, user_name)
    cur = conn.execute(
        "INSERT INTO ProblemLists(user_name, list_order, list_name, added_at, source, retain) VALUES(?, ?, ?, ?, ?, ?)",
        (user_name, order_value, str(list_name or '').strip() or 'New list', timestamp, source or 'editor', 1 if retain else 0),
    )
    problem_list_id = cur.lastrowid
    if problems:
        replace_list_items(conn, problem_list_id, problems)
    conn.commit()
    return {'problem_list_id': problem_list_id, 'list_order': order_value, 'item_count': len(problems or [])}
def rename_list(conn, problem_list_id, list_name):
    """Update a list's display name. Returns the number of rows changed (0 if id absent)."""
    ensure_problem_list_schema(conn)
    conn.execute("UPDATE ProblemLists SET list_name = ? WHERE problem_list_id = ?",
                 (str(list_name or '').strip() or 'Untitled', problem_list_id))
    conn.commit()
    return conn.execute("SELECT changes()").fetchone()[0]
def reorder_lists(conn, user_name, ordered_ids):
    """Set the queue order from `ordered_ids` (the full set of a user's list ids, in the desired
    left-to-right order), then reindex to a contiguous 1..N. Ids not present keep their relative
    order after the listed ones. Returns the new count."""
    ensure_problem_list_schema(conn)
    for pos, pid in enumerate(ordered_ids, start=1):
        conn.execute("UPDATE ProblemLists SET list_order = ? WHERE problem_list_id = ? AND user_name = ?",
                     (pos, pid, user_name))
    # Anything not listed sorts after the listed block (so reindex appends it cleanly).
    if ordered_ids:
        marks = ",".join("?" for _ in ordered_ids)
        conn.execute(f"UPDATE ProblemLists SET list_order = list_order + ? WHERE user_name = ? "
                     f"AND problem_list_id NOT IN ({marks})",
                     (len(ordered_ids) + 1000, user_name, *ordered_ids))
    conn.commit()
    return reindex_problem_lists(conn, user_name)
def delete_list(conn, problem_list_id):
    """Unconditionally delete a list (+items) regardless of retain, then reindex its owner.
    Returns {action: deleted|missing, ...}."""
    ensure_problem_list_schema(conn)
    row = conn.execute("SELECT user_name, list_name FROM ProblemLists WHERE problem_list_id = ?",
                       (problem_list_id,)).fetchone()
    if not row:
        return {'action': 'missing', 'problem_list_id': problem_list_id}
    user_name = row['user_name']
    conn.execute("DELETE FROM ProblemListItems WHERE problem_list_id = ?", (problem_list_id,))
    conn.execute("DELETE FROM ProblemLists WHERE problem_list_id = ?", (problem_list_id,))
    conn.commit()
    reindex_problem_lists(conn, user_name)
    return {'action': 'deleted', 'problem_list_id': problem_list_id, 'user_name': user_name,
            'list_name': row['list_name']}

### Helpers: rendering
def render_problem_lists_text(problem_lists):
    if not problem_lists:
        return 'No problem lists found.'
    lines = []
    for plist in problem_lists:
        retain = 'keep' if plist.get('retain', 1) else 'consume'
        used = plist.get('times_used', 0)
        lines.append(
            f'[{plist["user_name"]}] list #{plist["list_order"]}: {plist["list_name"]} '
            f'({len(plist["items"])} problems, added {plist["added_at"]}, source: {plist["source"] or "n/a"}, '
            f'retain: {retain}, used: {used})'
        )
        for item in plist['items']:
            detail = ''
            if item.get('category'):
                detail += f' | category: {item["category"]}'
            if item.get('notes'):
                detail += f' | notes: {item["notes"]}'
            lines.append(f'  {item["item_order"]:>2}. {item["problem_text"]}{detail}')
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'
def render_problem_lists_markdown(problem_lists, title='Problem Lists'):
    now = datetime.now().isoformat(timespec='seconds')
    lines = [f'# {title}', '', f'_Generated: {now}_', '']
    if not problem_lists:
        lines.extend(['No problem lists found.', ''])
        return '\n'.join(lines)
    for plist in problem_lists:
        lines.extend([
            f'## {plist["user_name"]} — list #{plist["list_order"]}: {plist["list_name"]}',
            '',
            f'- Added: `{plist["added_at"]}`',
            f'- Source: `{plist["source"] or "n/a"}`',
            f'- Count: `{len(plist["items"])}`',
            '',
            '| # | Problem | Category | Notes |',
            '|---:|---|---|---|',
        ])
        for item in plist['items']:
            lines.append(
                f'| {item["item_order"]} | {item["problem_text"]} | '
                f'{item.get("category") or ""} | {item.get("notes") or ""} |'
            )
        lines.append('')
    return '\n'.join(lines)
def _safe_name(text):
    cleaned = re.sub(r'[^a-zA-Z0-9_-]+', '-', str(text or '').strip())
    return cleaned.strip('-') or 'all-users'
def default_markdown_filename(user_name):
    stamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    return f'problem-lists_{_safe_name(user_name)}_{stamp}.md'
def _write_text(path, content):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

### CLI commands
def cmd_migrate(args):
    conn = connect(args.db)
    try:
        ensure_problem_list_schema(conn)
    finally:
        conn.close()
    print(f'Migrated schema in {args.db}')
def cmd_add_from_txt(args):
    with open(args.txt, 'r', encoding='utf-8') as f:
        text = f.read()
    problems = parse_problem_list_text(text, default_category=args.default_category or '')
    conn = connect(args.db)
    try:
        out = add_problem_list(
            conn,
            user_name=args.user,
            list_name=args.name,
            source=args.source or '',
            problems=problems,
            added_at=args.added_at,
            list_order=args.list_order,
            retain=not args.consume,
        )
    finally:
        conn.close()
    print(
        f'Added list #{out["list_order"]} "{args.name}" for {args.user} '
        f'({out["item_count"]} problems, list_id={out["problem_list_id"]}, '
        f'retain={"consume" if args.consume else "keep"})'
    )
def cmd_set_retain(args):
    conn = connect(args.db)
    try:
        changed = set_retain(conn, args.list_id, retain=not args.consume)
    finally:
        conn.close()
    state = 'consume-after-use' if args.consume else 'keep'
    print(f'Set list {args.list_id} retain={state} ({changed} row(s) updated)')
def cmd_reindex(args):
    conn = connect(args.db)
    try:
        n = reindex_problem_lists(conn, args.user)
    finally:
        conn.close()
    print(f'Reindexed {n} list(s) for {args.user} to a contiguous 1..{n}')
def cmd_consume(args):
    conn = connect(args.db)
    try:
        out = consume_problem_list(conn, args.list_id)
    finally:
        conn.close()
    print(f'Consume list {args.list_id}: {out["action"]}'
          + (f' (now used {out["times_used"]}x)' if out.get('action') == 'retained' else ''))
def cmd_show(args):
    conn = connect(args.db)
    try:
        lists = fetch_problem_lists(conn, user_name=args.user)
    finally:
        conn.close()
    if args.format == 'markdown':
        text = render_problem_lists_markdown(lists, title=args.title or 'Problem Lists')
    else:
        text = render_problem_lists_text(lists)
    out_path = args.output
    if args.save_markdown:
        out_path = out_path or default_markdown_filename(args.user or 'all-users')
    if out_path:
        _write_text(out_path, text)
        print(f'Wrote {out_path}')
        return
    print(text, end='' if text.endswith('\n') else '\n')
def build_parser():
    parser = argparse.ArgumentParser(description='Manage problem lists in math-quiz SQLite files.')
    sub = parser.add_subparsers(dest='cmd', required=True)
    p_migrate = sub.add_parser('migrate', help='Create/migrate problem-list tables in the DB.')
    p_migrate.add_argument('--db', required=True, help='Path to .sqlite file')
    p_migrate.set_defaults(func=cmd_migrate)
    p_add = sub.add_parser('add-from-txt', help='Import a problem list from a .txt file.')
    p_add.add_argument('--db', required=True, help='Path to .sqlite file')
    p_add.add_argument('--user', required=True, help='User name that owns this list')
    p_add.add_argument('--name', required=True, help='Problem-list name')
    p_add.add_argument('--source', default='', help='Source label, e.g. filename or note')
    p_add.add_argument('--txt', required=True, help='Text file containing one problem per line')
    p_add.add_argument('--default-category', default='', help='Default category for lines without category metadata')
    p_add.add_argument('--added-at', default=None, help='Optional timestamp override (ISO recommended)')
    p_add.add_argument('--list-order', type=int, default=None, help='Optional explicit order for this user')
    p_add.add_argument('--consume', action='store_true',
                       help='Mark this list consume-after-use (default keeps it / retain=on)')
    p_add.set_defaults(func=cmd_add_from_txt)
    p_retain = sub.add_parser('set-retain', help='Mark a list keep (default) or consume-after-use.')
    p_retain.add_argument('--db', required=True, help='Path to .sqlite file')
    p_retain.add_argument('--list-id', type=int, required=True, help='problem_list_id to update')
    p_retain.add_argument('--consume', action='store_true', help='Set consume-after-use (omit to set keep)')
    p_retain.set_defaults(func=cmd_set_retain)
    p_reindex = sub.add_parser('reindex', help="Renumber a user's list_order to a contiguous 1..N.")
    p_reindex.add_argument('--db', required=True, help='Path to .sqlite file')
    p_reindex.add_argument('--user', required=True, help='User whose lists to reindex')
    p_reindex.set_defaults(func=cmd_reindex)
    p_consume = sub.add_parser('consume', help='Pop a used list (delete if consume, else bump usage).')
    p_consume.add_argument('--db', required=True, help='Path to .sqlite file')
    p_consume.add_argument('--list-id', type=int, required=True, help='problem_list_id to consume')
    p_consume.set_defaults(func=cmd_consume)
    p_show = sub.add_parser('show', help='Show problem lists as terminal text or markdown.')
    p_show.add_argument('--db', required=True, help='Path to .sqlite file')
    p_show.add_argument('--user', default=None, help='Optional user filter')
    p_show.add_argument('--format', choices=('text', 'markdown'), default='text')
    p_show.add_argument('--title', default='Problem Lists', help='Markdown title override')
    p_show.add_argument('--output', default=None, help='Write output to this path')
    p_show.add_argument('--save-markdown', action='store_true', help='Save markdown to a timestamped file')
    p_show.set_defaults(func=cmd_show)
    return parser
def main():
    args = build_parser().parse_args()
    args.func(args)
if __name__ == '__main__':
    main()
