#!/usr/bin/env python3
"""Mock eval for migrate-cursor-ai-sessions (temp dirs only; no live Cursor writes)."""

import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import migrate_cursor_ai_sessions as MIGRATE

### Fixtures
def _write_state_db(path, source_worktree, other_worktree, created_ms):
    """Create a tiny state.vscdb with source + unrelated composer rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("CREATE TABLE ItemTable (key TEXT, value BLOB)")
        conn.execute("CREATE TABLE cursorDiskKV (key TEXT, value BLOB)")
        conn.execute(
            "CREATE TABLE composerHeaders ("
            "composerId TEXT PRIMARY KEY, workspaceId TEXT, createdAt INTEGER, "
            "lastUpdatedAt INTEGER, isArchived INTEGER, isSubagent INTEGER, "
            "recency INTEGER, checkpointAt INTEGER, value TEXT)"
        )
        src = str(Path(source_worktree))
        other = str(Path(other_worktree))
        composer_src = {
            "composerId": "11111111-1111-1111-1111-111111111111",
            "name": "Source session",
            "createdAt": created_ms,
            "workspaceIdentifier": {
                "uri": {
                    "fsPath": src,
                    "external": Path(src).as_uri(),
                    "path": src,
                }
            },
            "trackedGitRepos": [{"repoPath": src}],
            "note": f"worked in {src}/README.md",
        }
        composer_other = {
            "composerId": "22222222-2222-2222-2222-222222222222",
            "name": "Other session",
            "createdAt": created_ms,
            "workspaceIdentifier": {
                "uri": {
                    "fsPath": other,
                    "external": Path(other).as_uri(),
                    "path": other,
                }
            },
            "note": f"worked in {other}/README.md",
        }
        conn.execute(
            "INSERT INTO cursorDiskKV(key, value) VALUES (?, ?)",
            (f"composerData:{composer_src['composerId']}", json.dumps(composer_src)),
        )
        conn.execute(
            "INSERT INTO cursorDiskKV(key, value) VALUES (?, ?)",
            (f"composerData:{composer_other['composerId']}", json.dumps(composer_other)),
        )
        conn.execute(
            "INSERT INTO ItemTable(key, value) VALUES (?, ?)",
            (
                "history.recentlyOpenedPathsList",
                json.dumps({"entries": [{"folderUri": Path(src).as_uri()}, {"folderUri": Path(other).as_uri()}]}),
            ),
        )
        # Tilde displayPath form used by Cursor workspaceMetadata.
        home = str(Path.home())
        if src.startswith(home + "/"):
            tilde_src = "~/" + src[len(home) + 1:]
            conn.execute(
                "INSERT INTO ItemTable(key, value) VALUES (?, ?)",
                (
                    "workspaceMetadata.entries",
                    json.dumps({"displayPath": tilde_src, "folder": Path(src).as_uri()}),
                ),
            )
        conn.execute(
            "INSERT INTO composerHeaders(composerId, workspaceId, createdAt, lastUpdatedAt, isArchived, isSubagent, recency, checkpointAt, value) VALUES (?,?,?,?,0,0,0,0,?)",
            (
                composer_src["composerId"],
                "abcd1234workspace",
                created_ms,
                created_ms,
                json.dumps({"composerId": composer_src["composerId"], "name": "Source session", "pathHint": src}),
            ),
        )
        conn.commit()
    finally:
        conn.close()
def _seed_projects(projects_root, worktree, names_and_ages_hours):
    """Create agent-transcript dirs with controlled mtimes."""
    root = Path(projects_root) / MIGRATE._project_token(worktree) / "agent-transcripts"
    root.mkdir(parents=True, exist_ok=True)
    now = datetime.now().timestamp()
    for name, age_hours in names_and_ages_hours:
        d = root / name
        d.mkdir()
        (d / f"{name}.jsonl").write_text('{"role":"user","text":"hi"}\n', encoding="utf-8")
        mtime = now - (age_hours * 3600)
        Path(d).touch()
        import os
        os.utime(d, (mtime, mtime))
        os.utime(d / f"{name}.jsonl", (mtime, mtime))
    return root
def _seed_workspace_storage(workspace_storage, worktree, workspace_id="abcd1234workspace"):
    """Create workspace.json pointing at worktree."""
    folder = Path(workspace_storage) / workspace_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "workspace.json"
    path.write_text(json.dumps({"folder": Path(worktree).as_uri()}, indent=2) + "\n", encoding="utf-8")
    return path

### Tests
class MigrateCursorAiSessionsTests(unittest.TestCase):
    """Temp-dir mock coverage for dry-run and execute paths."""
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="migrate-ai-sessions-eval-"))
        self.source = self.tmp / "Code" / "flex"
        self.target = self.tmp / "Code" / "export-public"
        self.other = self.tmp / "Code" / "fof-mono"
        self.source.mkdir(parents=True)
        self.target.mkdir(parents=True)
        self.other.mkdir(parents=True)
        self.state_db = self.tmp / "globalStorage" / "state.vscdb"
        self.projects_root = self.tmp / "projects"
        self.workspace_storage = self.tmp / "workspaceStorage"
        self.migrate_root = self.tmp / "migrate-root"
        created = int((datetime.now() - timedelta(hours=2)).timestamp() * 1000)
        _write_state_db(self.state_db, self.source, self.other, created)
        _seed_projects(
            self.projects_root,
            self.source,
            [
                ("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", 1),
                ("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", 48),
            ],
        )
        self.ws_json = _seed_workspace_storage(self.workspace_storage, self.source)
    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
    def _run(self, extra):
        argv = [
            "--source-worktree", str(self.source),
            "--target-worktree", str(self.target),
            "--state-db", str(self.state_db),
            "--projects-root", str(self.projects_root),
            "--workspace-storage", str(self.workspace_storage),
            "--migrate-root", str(self.migrate_root),
            "--no-prune-backups",
            "--yes",
        ] + extra
        return MIGRATE.main(argv)
    def test_dry_run_rewrites_copy_not_live(self):
        """Dry-run should modify only the copied DB and leave live paths intact."""
        before = self.state_db.read_bytes()
        rc = self._run(["--dry-run", "--skip-projects", "--skip-workspace-storage"])
        self.assertEqual(rc, 0)
        after = self.state_db.read_bytes()
        self.assertEqual(before, after, "live state.vscdb must be unchanged in dry-run")
        dry_files = list((self.migrate_root / "dry-run").glob("state.vscdb.dry-run.*"))
        self.assertTrue(dry_files, "expected dry-run DB copy")
        dry_db = dry_files[0]
        conn = sqlite3.connect(str(dry_db))
        try:
            rows = conn.execute("SELECT key, value FROM cursorDiskKV").fetchall()
        finally:
            conn.close()
        blob = "\n".join(
            (key or "") + "\n" + (value.decode("utf-8") if isinstance(value, bytes) else str(value))
            for key, value in rows
        )
        self.assertNotIn(str(self.source), blob)
        self.assertIn(str(self.target), blob)
        self.assertIn(str(self.other), blob)
        review = MIGRATE.review_state_db(dry_db, self.source, self.target, log_fh=None)
        self.assertEqual(review["source_abs"], 0)
        self.assertGreater(review["target_abs"], 0)
    def test_execute_migrates_projects_and_workspace(self):
        """Execute should rename project folder and retarget workspace.json."""
        rc = self._run(["--execute", "--force", "--skip-workspace-id-remap"])
        self.assertEqual(rc, 0)
        src_token = MIGRATE._project_token(self.source)
        tgt_token = MIGRATE._project_token(self.target)
        self.assertFalse((self.projects_root / src_token).exists())
        self.assertTrue((self.projects_root / tgt_token / "agent-transcripts").exists())
        data = json.loads(self.ws_json.read_text(encoding="utf-8"))
        self.assertEqual(data["folder"], Path(self.target).as_uri())
        conn = sqlite3.connect(str(self.state_db))
        try:
            values = [row[0] for row in conn.execute("SELECT value FROM cursorDiskKV")]
        finally:
            conn.close()
        joined = b"\n".join(v if isinstance(v, bytes) else str(v).encode() for v in values).decode("utf-8")
        self.assertNotIn(str(self.source), joined)
        self.assertIn(str(self.target), joined)
        self.assertIn(str(self.other), joined)
    def test_since_filters_transcript_copy(self):
        """With --since and existing target project, only recent transcripts copy."""
        tgt_token = MIGRATE._project_token(self.target)
        # Pre-create target so migrate uses copy-selected path.
        (self.projects_root / tgt_token / "agent-transcripts").mkdir(parents=True)
        since = (datetime.now() - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M")
        rc = self._run(["--execute", "--force", "--skip-db", "--skip-workspace-storage", "--since", since])
        self.assertEqual(rc, 0)
        dest = self.projects_root / tgt_token / "agent-transcripts"
        names = {p.name for p in dest.iterdir() if p.is_dir()}
        self.assertIn("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", names)
        self.assertNotIn("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", names)
    def test_backup_prune_keeps_newest(self):
        """Prune helper deletes older tool backups when confirmed."""
        backup_dir = self.migrate_root / "backups"
        backup_dir.mkdir(parents=True)
        older = backup_dir / "state.vscdb.backup-before-execute.2026-01-01_000000"
        newer = backup_dir / "state.vscdb.backup-before-execute.2026-08-06_120000"
        older.write_bytes(b"old")
        newer.write_bytes(b"new")
        import os
        os.utime(older, (1_700_000_000, 1_700_000_000))
        os.utime(newer, (1_800_000_000, 1_800_000_000))
        MIGRATE.maybe_prune_backups(backup_dir, log_fh=None, assume_yes=True)
        self.assertTrue(newer.exists())
        self.assertFalse(older.exists())
    def test_tilde_path_pairs(self):
        """Home-relative ~/... spellings should be rewritten."""
        home = Path.home()
        src = home / "Documents" / "Code" / "flex"
        tgt = home / "Documents" / "Code" / "export-public"
        pairs = dict(MIGRATE._replacement_pairs(src, tgt))
        self.assertEqual(pairs.get("~/Documents/Code/flex"), "~/Documents/Code/export-public")
        text = json.dumps({"displayPath": "~/Documents/Code/flex"})
        new_text, count = MIGRATE._rewrite_text(text, MIGRATE._replacement_pairs(src, tgt))
        self.assertGreater(count, 0)
        self.assertIn("~/Documents/Code/export-public", new_text)
        self.assertNotIn("~/Documents/Code/flex", new_text)
    def test_parse_opener_pids_and_holodeck_label(self):
        """Opener lines should yield PIDs; command_hint Cursor should label cursor-related."""
        lines = [
            "lsof non-Cursor opener: pid=56101; kind=holodeck-server; cwd=/Users/x/Code/holodeck",
            "lsof non-Cursor opener: pid=56101; kind=holodeck-server; cwd=/Users/x/Code/holodeck",
            "lsof non-Cursor opener: pid=99999; kind=python",
        ]
        self.assertEqual(MIGRATE._parse_opener_pids(lines), ["56101", "99999"])
        info = MIGRATE._describe_pid("1", command_hint="Cursor")
        self.assertEqual(info["kind"], "cursor-related")
        self.assertIn("pid=1", info["summary"])
    def test_remap_composer_workspace_ids(self):
        """composerHeaders.workspaceId should move from old hash to new hash."""
        old_id = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        new_id = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        conn = sqlite3.connect(str(self.state_db))
        try:
            conn.execute(
                "UPDATE composerHeaders SET workspaceId = ? WHERE composerId = ?",
                (old_id, "11111111-1111-1111-1111-111111111111"),
            )
            conn.execute("DELETE FROM ItemTable WHERE key = ?", ("workspaceMetadata.entries",))
            conn.execute(
                "INSERT INTO ItemTable(key, value) VALUES (?, ?)",
                (
                    "workspaceMetadata.entries",
                    json.dumps({
                        "entries": [
                            {"workspaceId": old_id, "folderUri": Path(self.source).as_uri()},
                            {"workspaceId": new_id, "folderUri": Path(self.target).as_uri()},
                            {"workspaceId": old_id, "folderUri": Path(self.target).as_uri()},
                        ]
                    }),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        stats = MIGRATE.remap_composer_workspace_ids(self.state_db, old_id, new_id, log_fh=None)
        self.assertEqual(stats["updated"], 1)
        self.assertEqual(stats["remaining_on_source"], 0)
        conn = sqlite3.connect(str(self.state_db))
        try:
            ws = conn.execute(
                "SELECT workspaceId FROM composerHeaders WHERE composerId = ?",
                ("11111111-1111-1111-1111-111111111111",),
            ).fetchone()[0]
            meta = json.loads(
                conn.execute(
                    "SELECT value FROM ItemTable WHERE key = ?",
                    ("workspaceMetadata.entries",),
                ).fetchone()[0]
            )
        finally:
            conn.close()
        self.assertEqual(ws, new_id)
        folder_ids = [(e.get("folderUri"), e.get("workspaceId")) for e in meta["entries"]]
        # Duplicate target folderUri rows should be collapsed; remaining target binding uses new id.
        target_uri = Path(self.target).as_uri()
        self.assertEqual(sum(1 for folder, _wid in folder_ids if folder == target_uri), 1)


if __name__ == "__main__":
    unittest.main()
