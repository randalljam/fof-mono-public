"""Schema introspection and compatibility for anchor SQLite combine."""
import os
import sqlite3

### Contract: tables and columns the combiner depends on (names may need updating if schema renames)
REQUIRED_TABLES = ('Users', 'Sessions', 'ProblemAttempts')
OPTIONAL_TABLES = ('ModeEvents', 'WarmupAttempts')
MERGE_TABLES = REQUIRED_TABLES + OPTIONAL_TABLES
REQUIRED_COLUMNS = {
    'Users': ('name',),
    'Sessions': (
        'session_id', 'user_name', 'start_time', 'end_time', 'session_filename',
        'total_problems', 'correct_answers', 'average_response_time_ms',
    ),
    'ProblemAttempts': (
        'session_id', 'problem_id', 'problem_text', 'is_correct', 'response_time_ms',
    ),
}
OPTIONAL_COLUMNS = {
    'Sessions': (
        'num_problems', 'number_range_start', 'number_range_end', 'numbers_include',
        'numbers_exclude', 'num_numbers', 'operations',
    ),
    'ProblemAttempts': ('num1', 'num2', 'operation', 'correct_answer', 'user_answer_string', 'user_answer', 'flags_json'),
    'ModeEvents': ('user_name', 'session_id', 'from_mode', 'to_mode', 'trigger', 'timestamp'),
    'WarmupAttempts': ('user_name', 'session_id', 'round', 'target', 'entered', 'is_correct', 'response_time_ms', 'timestamp'),
}
COMBINE_PROVENANCE_DDL = """
CREATE TABLE IF NOT EXISTS CombineProvenance (
  combine_id INTEGER PRIMARY KEY AUTOINCREMENT,
  combine_mode TEXT NOT NULL,
  output_filename TEXT NOT NULL,
  source_filename TEXT NOT NULL,
  source_session_id TEXT,
  target_session_id TEXT,
  source_start_time TEXT,
  problem_count INTEGER,
  combined_at TEXT NOT NULL,
  notes TEXT
);
"""
class SchemaError(Exception):
    """Raised when a source file cannot be mapped into the canonical schema."""
    pass
class SchemaSnapshot:
    """Introspected schema + recency metadata for one SQLite file."""
    def __init__(self, path, recency, recency_mtime, tables):
        self.path = path
        self.basename = os.path.basename(path)
        self.recency = recency
        self.recency_mtime = recency_mtime
        self.tables = tables
    def has_table(self, name):
        return name in self.tables
    def column_names(self, table):
        if table not in self.tables:
            return []
        return [c['name'] for c in self.tables[table]['columns']]
    def create_sql(self, table):
        return self.tables[table]['create_sql']
    def mergeable_tables(self):
        return [t for t in MERGE_TABLES if self.has_table(t)]
### Introspection
def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
def _max_session_start(conn):
    if not _table_exists(conn, 'Sessions'):
        return None
    row = conn.execute('SELECT MAX(start_time) FROM Sessions').fetchone()
    return row[0] if row else None
def _table_exists(conn, name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None
def _read_table_info(conn, table):
    rows = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    return [{'name': r[1], 'type': r[2], 'notnull': r[3], 'pk': r[5]} for r in rows]
def introspect_file(path):
    conn = connect(path)
    try:
        recency = _max_session_start(conn)
        recency_mtime = os.path.getmtime(path)
        tables = {}
        for row in conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ):
            name, sql = row[0], row[1]
            if name == 'CombineProvenance':
                continue
            tables[name] = {'create_sql': sql, 'columns': _read_table_info(conn, name)}
        return SchemaSnapshot(path, recency, recency_mtime, tables)
    finally:
        conn.close()
def pick_canonical(snapshots):
    if not snapshots:
        raise SchemaError('No source files to pick canonical schema from')
    def sort_key(s):
        recency = s.recency or ''
        return (recency, s.recency_mtime)
    canonical = max(snapshots, key=sort_key)
    _validate_canonical(canonical)
    return canonical
def _validate_canonical(snapshot):
    for table in REQUIRED_TABLES:
        if not snapshot.has_table(table):
            raise SchemaError(
                f"Canonical file {snapshot.basename} missing required table {table}"
            )
    for table, cols in REQUIRED_COLUMNS.items():
        present = set(snapshot.column_names(table))
        missing = [c for c in cols if c not in present]
        if missing:
            raise SchemaError(
                f"Canonical file {snapshot.basename} table {table} missing required column(s): "
                + ', '.join(missing)
            )
### Compatibility
def check_compatible(source, canonical):
    """Raise SchemaError if source cannot map into canonical schema."""
    for table in canonical.mergeable_tables():
        if not source.has_table(table):
            if table in OPTIONAL_TABLES:
                continue
            raise SchemaError(
                f"{source.basename}: missing required table {table} "
                f"(canonical from {canonical.basename})"
            )
        canon_cols = set(canonical.column_names(table))
        src_cols = set(source.column_names(table))
        required = set(REQUIRED_COLUMNS.get(table, ()))
        optional = set(OPTIONAL_COLUMNS.get(table, ()))
        allowed_src = required | optional
        unknown = src_cols - allowed_src - canon_cols
        if unknown:
            raise SchemaError(
                f"{source.basename}: table {table} has unrecognized column(s) "
                f"{', '.join(sorted(unknown))} — possible rename vs canonical {canonical.basename}"
            )
        missing_required = [c for c in required if c not in src_cols]
        if missing_required:
            raise SchemaError(
                f"{source.basename}: table {table} missing required column(s) "
                f"{', '.join(missing_required)} (canonical from {canonical.basename})"
            )
def check_all_compatible(snapshots, canonical):
    for s in snapshots:
        check_compatible(s, canonical)
### Row mapping and insert
def map_row(source_row, canonical_columns):
    """Map a source row dict into canonical column order; absent cols -> None."""
    if isinstance(source_row, sqlite3.Row):
        source_row = dict(source_row)
    return [source_row.get(col) for col in canonical_columns]
def insert_row(conn, table, columns, values):
    placeholders = ', '.join('?' * len(columns))
    col_list = ', '.join(columns)
    conn.execute(f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})', values)
def fetch_table_rows(conn, table, columns, where_sql='', params=()):
    if not _table_exists(conn, table):
        return []
    col_list = ', '.join(f'"{c}"' for c in columns)
    sql = f'SELECT {col_list} FROM "{table}"'
    if where_sql:
        sql += f' WHERE {where_sql}'
    return conn.execute(sql, params).fetchall()
def source_select_columns(source_snapshot, canonical_snapshot, table):
    """Columns to SELECT from source: intersection with what source actually has."""
    if not source_snapshot.has_table(table):
        return []
    canon = canonical_snapshot.column_names(table)
    src = set(source_snapshot.column_names(table))
    return [c for c in canon if c in src]
### Output DB
def create_output_db(output_path, canonical):
    if os.path.exists(output_path):
        os.remove(output_path)
    out = connect(output_path)
    # DDL is taken from the canonical snapshot (already introspected), so we never
    # need to reopen the canonical file here.
    try:
        for table in canonical.mergeable_tables():
            sql = canonical.create_sql(table)
            if not sql:
                raise SchemaError(f"Canonical file {canonical.basename} has no CREATE SQL for {table}")
            out.execute(sql)
        out.executescript(COMBINE_PROVENANCE_DDL)
        out.commit()
    finally:
        out.close()
    return connect(output_path)
