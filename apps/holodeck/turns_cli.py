"""CLI for the Holodeck turns database."""

import argparse
from pathlib import Path

try:
    from apps.holodeck.turns import backup
    from apps.holodeck.turns import cloud_claude
    from apps.holodeck.turns import db
    from apps.holodeck.turns import digest
    from apps.holodeck.turns import hash_map
    from apps.holodeck.turns import ingest
    from apps.holodeck.turns import purge_cursor
except ImportError:
    from turns import backup
    from turns import cloud_claude
    from turns import db
    from turns import digest
    from turns import hash_map
    from turns import ingest
    from turns import purge_cursor

### Paths
def repo_root():
    return Path(__file__).resolve().parents[2]

### Commands
def run_build(args):
    root = repo_root()
    db_path = Path(args.db) if args.db else db.default_db_path(root)
    if not args.no_backup:
        backup_path = backup.backup_turns_db(db_path, reason="pre-build")
        if backup_path:
            print("backup:", backup_path)
    summary = ingest.build(root=root, db_path=db_path, include_cloud=not args.no_cloud)
    print("turns build complete")
    print("db:", summary["db_path"])
    print("sessions:", summary["sessions"])
    print("exchanges:", summary["exchanges"])
    print("cloud tasks:", summary["cloud_tasks"])
    print("claude cloud sessions:", summary["claude_cloud_sessions"])
    print("commits:", summary["commits"])
    print("links:", summary["links"])
    if summary.get("notes"):
        print("notes:", "; ".join(summary["notes"]))
    if not args.no_digest:
        conn = db.connect(db_path)
        db.init_db(conn)
        try:
            if args.digest:
                digest_summary = digest.digest_missing(conn, limit=args.limit, root=root)
            else:
                digest_summary = digest.auto_digest_recent(conn, root=root)
        finally:
            conn.close()
        print("digests generated:", len(digest_summary["generated"]))
        for exchange_id in digest_summary["generated"]:
            print("digest:", exchange_id)
        for skipped in digest_summary["skipped"]:
            print("digest skipped:", skipped)
    return 0
def run_backup(args):
    root = repo_root()
    db_path = Path(args.db) if args.db else db.default_db_path(root)
    path = backup.backup_turns_db(db_path, reason=args.reason or "manual backup")
    if path is None:
        print("error: turns.db not found at", db_path)
        return 1
    print("backup:", path)
    return 0
def run_restore(args):
    root = repo_root()
    db_path = Path(args.db) if args.db else db.default_db_path(root)
    backup_path = Path(args.backup) if args.backup else backup.latest_backup(db_path)
    if backup_path is None:
        print("error: no backup found")
        return 1
    restored = backup.restore_turns_db(backup_path, db_path)
    print("restored:", restored)
    print("from:", backup_path)
    return 0
def run_cloud_claude_login(args):
    return 0 if cloud_claude.claude_login() else 1
def run_load_hash_map(args):
    root = repo_root()
    db_path = Path(args.db) if args.db else db.default_db_path(root)
    conn = db.connect(db_path)
    db.init_db(conn)
    try:
        summary = hash_map.load_maps_from_files(
            conn,
            commit_map_path=args.commit_map,
            branch_tip_map_path=args.branch_tip_map,
            root=root,
        )
        remapped = None
        if not args.no_remap:
            remapped = hash_map.remap_commits_to_new_shas(conn)
        conn.commit()
    finally:
        conn.close()
    print("hash map loaded")
    print("db:", db_path)
    print("commit map rows:", summary["commit_map_rows"])
    print("branch tip map rows:", summary["branch_tip_map_rows"])
    print("commit map path:", summary["commit_map_path"])
    if remapped is not None:
        print("remapped commits:", remapped["remapped_commits"])
        print("links moved:", remapped["links_moved"])
        print("skipped pruned:", remapped["skipped_pruned"])
    return 0
def run_resolve_sha(args):
    root = repo_root()
    db_path = Path(args.db) if args.db else db.default_db_path(root)
    conn = db.connect(db_path)
    db.init_db(conn)
    try:
        row = hash_map.lookup_map_row(conn, args.sha)
        resolved = hash_map.resolve_sha(conn, args.sha, direction=args.direction)
    finally:
        conn.close()
    if not row and resolved is None:
        print("not found:", args.sha)
        return 1
    print("input:", args.sha)
    print("resolved:", resolved)
    if row:
        print("old_sha:", row.get("old_sha"))
        print("new_sha:", row.get("new_sha"))
        print("status:", row.get("status"))
        print("subject:", row.get("subject"))
        print("branches:", row.get("branches"))
    return 0
def _print_purge_report(report):
    print("composer_id:", report.get("composer_id"))
    print("session_id:", report.get("session_id"))
    print("in_cursor:", report.get("in_cursor"))
    print("deleted_from_cursor:", report.get("deleted_from_cursor"))
    if report.get("skipped"):
        print("skipped:", report.get("skip_reason"))
    if report.get("dry_run"):
        print("dry_run: True")
        print("would_purge:", report.get("would_purge"))
    print("executed:", report.get("executed"))
    print("purged:", report.get("purged"))
    holodeck = report.get("holodeck") or {}
    turns = holodeck.get("turns") or {}
    snapshot = holodeck.get("snapshot") or {}
    print("turns.session_present:", turns.get("session_present"))
    print("turns.exchange_count:", turns.get("exchange_count"))
    print("turns.digest_count:", turns.get("digest_count"))
    print("turns.link_count:", turns.get("link_count"))
    print("turns.child_session_ids:", ", ".join(turns.get("child_session_ids") or []) or "-")
    print("snapshot.present:", snapshot.get("present"))
    print("agent_transcripts:", ", ".join(holodeck.get("agent_transcripts") or []) or "-")
    verification = report.get("verification")
    if verification is not None:
        print("verify.ok:", verification.get("ok"))
        for problem in verification.get("problems") or []:
            print("verify.problem:", problem)
def run_purge_cursor(args):
    root = repo_root()
    common = {
        "execute": args.execute,
        "force": args.force,
        "include_agent_transcripts": args.agent_transcripts,
        "cursor_db": args.cursor_db,
        "root": root,
        "turns_db_path": args.db,
        "snapshot_path": args.snapshot,
        "projects_root": args.projects_root,
    }
    if args.all_missing:
        summary = purge_cursor.purge_all_deleted_cursor_sessions(**common)
        print("purge-cursor scan")
        print("checked:", summary["checked"])
        print("still_in_cursor_skipped:", summary["skipped_still_in_cursor"])
        print("would_purge_count:" if not args.execute else "purged_count:",
              summary["would_purge_count"] if not args.execute else summary["purged_count"])
        print("executed:", summary["executed"])
        for report in summary["reports"]:
            if report.get("skipped") and not args.verbose:
                continue
            if report.get("dry_run") and not report.get("would_purge") and not args.verbose:
                continue
            print("---")
            _print_purge_report(report)
        return 0
    if not args.composer_id:
        print("error: pass a composer id, or --all-missing")
        return 2
    report = purge_cursor.purge_deleted_cursor_session(args.composer_id, **common)
    _print_purge_report(report)
    if report.get("skipped"):
        return 1
    if report.get("executed") and not report.get("purged") and report.get("had_holodeck_traces"):
        return 1
    return 0

### CLI
def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Build and maintain the Holodeck turns database")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build", help="Ingest sessions and commits, then correlate links")
    build_parser.add_argument("--db", help="SQLite DB path; defaults to apps/holodeck/data/turns.db")
    build_parser.add_argument("--digest", action="store_true", help="Backfill missing operator exchange digests after build")
    build_parser.add_argument("--no-digest", action="store_true", help="Skip the default recent operator auto-digest pass")
    build_parser.add_argument("--no-cloud", action="store_true", help="Skip Codex and Claude cloud ingestion")
    build_parser.add_argument("--no-backup", action="store_true", help="Skip the automatic pre-build turns.db backup")
    build_parser.add_argument("--limit", type=int, default=20, help="Digest limit, newest primary exchanges first")
    build_parser.set_defaults(func=run_build)
    backup_parser = subparsers.add_parser("backup", help="Copy turns.db to data/backups/turns_YYYY-MM-DD_HHMMSS.db")
    backup_parser.add_argument("--db", help="SQLite DB path; defaults to apps/holodeck/data/turns.db")
    backup_parser.add_argument("--reason", help="Optional note stored beside the backup")
    backup_parser.set_defaults(func=run_backup)
    restore_parser = subparsers.add_parser("restore", help="Restore turns.db from a backup (safety-backs up current first)")
    restore_parser.add_argument("--backup", help="Backup file path; defaults to the newest turns_*.db backup")
    restore_parser.add_argument("--db", help="SQLite DB path; defaults to apps/holodeck/data/turns.db")
    restore_parser.set_defaults(func=run_restore)
    login_parser = subparsers.add_parser("cloud-claude-login", help="Open Chromium and capture a Claude cloud browser session")
    login_parser.set_defaults(func=run_cloud_claude_login)
    map_parser = subparsers.add_parser("load-hash-map", help="Load history-purge old→new commit hash map into turns.db")
    map_parser.add_argument("--db", help="SQLite DB path; defaults to apps/holodeck/data/turns.db")
    map_parser.add_argument("--commit-map", help="Path to commit map TSV; defaults to docs/git/2026-07-22_history-purge-commit-map.tsv")
    map_parser.add_argument("--branch-tip-map", help="Path to branch tip map TSV; defaults to docs/git/2026-07-22_history-purge-branch-tip-map.tsv")
    map_parser.add_argument("--no-remap", action="store_true", help="Load the lookup tables without rewriting commits/links SHAs")
    map_parser.set_defaults(func=run_load_hash_map)
    resolve_parser = subparsers.add_parser("resolve-sha", help="Resolve a commit SHA across the history-purge rewrite")
    resolve_parser.add_argument("sha", help="Old or new commit SHA")
    resolve_parser.add_argument("--db", help="SQLite DB path; defaults to apps/holodeck/data/turns.db")
    resolve_parser.add_argument("--direction", choices=["to_new", "to_old", "either"], default="to_new", help="Resolution direction (default: to_new)")
    resolve_parser.set_defaults(func=run_resolve_sha)
    purge_parser = subparsers.add_parser(
        "purge-cursor",
        help="Scrub Holodeck copies of a Cursor chat deleted from state.vscdb (dry-run unless --execute)",
    )
    purge_parser.add_argument(
        "composer_id",
        nargs="?",
        help="Cursor composer UUID (also accepts cursor:<uuid> or composerData:<uuid>)",
    )
    purge_parser.add_argument("--all-missing", action="store_true", help="Scan turns.db cursor sessions and purge those absent from Cursor")
    purge_parser.add_argument("--execute", action="store_true", help="Actually delete Holodeck rows/files (default is dry-run)")
    purge_parser.add_argument("--force", action="store_true", help="Purge even if composerData still exists in Cursor")
    purge_parser.add_argument("--agent-transcripts", action="store_true", help="Also delete matching ~/.cursor/projects/*/agent-transcripts files")
    purge_parser.add_argument("--db", help="SQLite DB path; defaults to apps/holodeck/data/turns.db")
    purge_parser.add_argument("--snapshot", help="snapshot.json path; defaults to apps/holodeck/data/snapshot.json")
    purge_parser.add_argument("--cursor-db", help="Cursor state.vscdb path; defaults to the global Cursor DB")
    purge_parser.add_argument("--projects-root", help="Override ~/.cursor/projects for agent-transcript lookup")
    purge_parser.add_argument("--verbose", action="store_true", help="With --all-missing, print every checked session")
    purge_parser.set_defaults(func=run_purge_cursor)
    return parser.parse_args(argv)
def main(argv=None):
    args = parse_args(argv)
    return args.func(args)
if __name__ == "__main__":
    raise SystemExit(main())
