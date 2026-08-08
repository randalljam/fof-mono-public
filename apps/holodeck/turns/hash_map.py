"""Load and apply the history-purge old→new commit hash map."""

from pathlib import Path

try:
    from apps.holodeck.turns import db
except ImportError:
    from turns import db

DEFAULT_COMMIT_MAP_REL = Path("docs/git/2026-07-22_history-purge-commit-map.tsv")
DEFAULT_BRANCH_TIP_MAP_REL = Path("docs/git/2026-07-22_history-purge-branch-tip-map.tsv")
ZERO_SHA = "0" * 40

### Paths
def default_commit_map_path(root=None):
    return Path(root or db.repo_root()) / DEFAULT_COMMIT_MAP_REL
def default_branch_tip_map_path(root=None):
    return Path(root or db.repo_root()) / DEFAULT_BRANCH_TIP_MAP_REL

### TSV parsing
def _split_tsv_line(line):
    return line.rstrip("\n").split("\t")
def parse_commit_map_tsv(text):
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    header = _split_tsv_line(lines[0])
    expected = ["old_hash", "new_hash", "status", "author_date", "author", "subject", "branches", "new_exists", "new_subject"]
    if header != expected:
        raise ValueError("unexpected commit map header: " + "\t".join(header))
    rows = []
    for line in lines[1:]:
        parts = _split_tsv_line(line)
        if len(parts) < 9:
            parts = parts + [""] * (9 - len(parts))
        rows.append({
            "old_sha": parts[0].strip(),
            "new_sha": parts[1].strip(),
            "status": parts[2].strip() or None,
            "author_date": parts[3].strip() or None,
            "author": parts[4].strip() or None,
            "subject": parts[5].strip() or None,
            "branches": parts[6].strip() or None,
            "new_exists": parts[7].strip() or None,
            "new_subject": parts[8].strip() or None,
        })
    return rows
def parse_branch_tip_map_tsv(text):
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    header = _split_tsv_line(lines[0])
    expected = ["branch", "old_tip", "new_tip", "old_date", "old_subject", "new_exists", "new_subject"]
    if header != expected:
        raise ValueError("unexpected branch tip map header: " + "\t".join(header))
    rows = []
    for line in lines[1:]:
        parts = _split_tsv_line(line)
        if len(parts) < 7:
            parts = parts + [""] * (7 - len(parts))
        rows.append({
            "branch": parts[0].strip(),
            "old_tip": parts[1].strip(),
            "new_tip": parts[2].strip(),
            "old_date": parts[3].strip() or None,
            "old_subject": parts[4].strip() or None,
            "new_exists": parts[5].strip() or None,
            "new_subject": parts[6].strip() or None,
        })
    return rows
def read_tsv_rows(path, parser):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    return parser(path.read_text(encoding="utf-8"))

### Load into DB
def replace_commit_hash_map(conn, rows):
    conn.execute("DELETE FROM commit_hash_map")
    for row in rows:
        if not row.get("old_sha"):
            continue
        db.upsert_commit_hash_map(conn, row)
    return len(rows)
def replace_branch_tip_map(conn, rows):
    conn.execute("DELETE FROM branch_tip_map")
    for row in rows:
        if not row.get("branch"):
            continue
        db.upsert_branch_tip_map(conn, row)
    return len(rows)
def load_maps_from_files(conn, commit_map_path=None, branch_tip_map_path=None, root=None):
    root = Path(root or db.repo_root())
    commit_path = Path(commit_map_path or default_commit_map_path(root))
    tip_path = Path(branch_tip_map_path or default_branch_tip_map_path(root))
    commit_rows = read_tsv_rows(commit_path, parse_commit_map_tsv)
    tip_rows = []
    if tip_path.is_file():
        tip_rows = read_tsv_rows(tip_path, parse_branch_tip_map_tsv)
    commit_count = replace_commit_hash_map(conn, commit_rows)
    tip_count = replace_branch_tip_map(conn, tip_rows)
    db.set_meta(conn, "commit_hash_map_source", str(commit_path))
    db.set_meta(conn, "commit_hash_map_loaded_at", db.now_iso())
    db.set_meta(conn, "commit_hash_map_rows", commit_count)
    db.set_meta(conn, "branch_tip_map_rows", tip_count)
    return {"commit_map_rows": commit_count, "branch_tip_map_rows": tip_count, "commit_map_path": str(commit_path), "branch_tip_map_path": str(tip_path) if tip_path.is_file() else None}

### Resolve
def normalize_sha(value):
    if not value:
        return None
    text = str(value).strip().lower()
    if not text or text == ZERO_SHA:
        return None
    return text
def lookup_map_row(conn, sha):
    sha = normalize_sha(sha)
    if not sha:
        return None
    row = conn.execute(
        """
        SELECT old_sha, new_sha, status, author_date, author, subject, branches, new_exists, new_subject
        FROM commit_hash_map
        WHERE lower(old_sha) = ? OR lower(new_sha) = ?
        LIMIT 1
        """,
        (sha, sha),
    ).fetchone()
    return dict(row) if row else None
def resolve_sha(conn, sha, direction="to_new"):
    """Resolve a SHA across the purge rewrite.

    direction:
      - to_new: old→new (default; GitHub PR stale hashes → current git)
      - to_old: new→old
      - either: return the counterpart when present, else the input
    """
    sha = normalize_sha(sha)
    if not sha:
        return None
    row = lookup_map_row(conn, sha)
    if not row:
        return sha
    old_sha = normalize_sha(row.get("old_sha"))
    new_sha = normalize_sha(row.get("new_sha"))
    if direction == "to_old":
        return old_sha or sha
    if direction == "either":
        if sha == old_sha and new_sha:
            return new_sha
        if sha == new_sha and old_sha:
            return old_sha
        return sha
    if row.get("status") == "pruned" or not new_sha:
        return None
    if sha == new_sha:
        return new_sha
    return new_sha

### Remap stored commit/link rows
def _copy_commit_row(conn, old_sha, new_sha):
    row = conn.execute("SELECT * FROM commits WHERE sha = ?", (old_sha,)).fetchone()
    if not row:
        return False
    payload = dict(row)
    payload["sha"] = new_sha
    db.upsert_commit(conn, payload)
    return True
def _remap_links_for_sha(conn, old_sha, new_sha):
    moved = 0
    for link in conn.execute("SELECT exchange_id, method, confidence FROM links WHERE sha = ?", (old_sha,)).fetchall():
        existing = conn.execute(
            "SELECT 1 FROM links WHERE exchange_id = ? AND sha = ?",
            (link["exchange_id"], new_sha),
        ).fetchone()
        if existing:
            conn.execute("DELETE FROM links WHERE exchange_id = ? AND sha = ?", (link["exchange_id"], old_sha))
        else:
            conn.execute(
                "UPDATE links SET sha = ? WHERE exchange_id = ? AND sha = ?",
                (new_sha, link["exchange_id"], old_sha),
            )
        moved += 1
    return moved
def remap_commits_to_new_shas(conn):
    """Rewrite commits/links from pre-purge SHAs to post-purge SHAs using commit_hash_map."""
    rows = conn.execute(
        """
        SELECT c.sha AS old_sha, m.new_sha AS new_sha, m.status AS status
        FROM commits c
        JOIN commit_hash_map m ON m.old_sha = c.sha
        WHERE m.new_sha IS NOT NULL
          AND m.new_sha != ''
          AND m.new_sha != ?
          AND m.new_sha != c.sha
        """,
        (ZERO_SHA,),
    ).fetchall()
    remapped = 0
    links_moved = 0
    skipped_pruned = 0
    for row in rows:
        old_sha = row["old_sha"]
        new_sha = row["new_sha"]
        if row["status"] == "pruned" or not normalize_sha(new_sha):
            skipped_pruned += 1
            continue
        _copy_commit_row(conn, old_sha, new_sha)
        links_moved += _remap_links_for_sha(conn, old_sha, new_sha)
        conn.execute("DELETE FROM commits WHERE sha = ?", (old_sha,))
        remapped += 1
    db.set_meta(conn, "commit_hash_map_last_remap_at", db.now_iso())
    db.set_meta(conn, "commit_hash_map_last_remap_count", remapped)
    return {"remapped_commits": remapped, "links_moved": links_moved, "skipped_pruned": skipped_pruned}
def ensure_hash_map_loaded(conn, root=None, remap=True):
    """Load map files when present; optionally remap stale commit SHAs in turns.db."""
    root = Path(root or db.repo_root())
    commit_path = default_commit_map_path(root)
    summary = {"loaded": False, "remapped": None, "notes": []}
    if not commit_path.is_file():
        summary["notes"].append("commit hash map missing: " + str(commit_path))
        return summary
    load_summary = load_maps_from_files(conn, commit_map_path=commit_path, root=root)
    summary["loaded"] = True
    summary.update(load_summary)
    if remap:
        summary["remapped"] = remap_commits_to_new_shas(conn)
    return summary
