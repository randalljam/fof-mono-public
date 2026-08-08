# Run tests with python -m unittest discover -s tests

import os
import sys
# Add the parent directory to the Python path so we can import the 'core' module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from core import s3_archive

### Helpers
def _make_repo(root):
    """
    Create a minimal fake repo tree with one data corpus and return its path.

    :param root: str, base temp directory.
    :return repo_root: str, path to the fake repo root.
    """
    corpus_dir = os.path.join(root, "data", "education")
    os.makedirs(corpus_dir)
    with open(os.path.join(corpus_dir, "a.md"), "w") as f:
        f.write("hello")
    sub = os.path.join(corpus_dir, "sub")
    os.makedirs(sub)
    with open(os.path.join(sub, "b.txt"), "w") as f:
        f.write("world!!")
    return root

### Tests: manifest index (no local data/)
class TestManifestNames(unittest.TestCase):
    def test_list_data_corpuses_missing_data_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(s3_archive.list_data_corpuses(repo_root=tmp), [])
    def test_manifest_names_from_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            mdir = os.path.join(tmp, s3_archive.MANIFEST_SUBDIR)
            os.makedirs(mdir)
            open(os.path.join(mdir, "education.manifest.jsonl"), "w").close()
            open(os.path.join(mdir, "logs.manifest.jsonl"), "w").close()
            open(os.path.join(mdir, "readme.txt"), "w").close()
            self.assertEqual(s3_archive.manifest_names(repo_root=tmp), ["education", "logs"])
    def test_manifest_names_missing_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(s3_archive.manifest_names(repo_root=tmp), [])
    def test_names_with_manifests_uses_manifest_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            mdir = os.path.join(tmp, s3_archive.MANIFEST_SUBDIR)
            os.makedirs(mdir)
            rec = {"repo_path": "data/education/a.md", "corpus": "education", "size_bytes": 5, "mtime": 0, "sha256": None, "s3_bucket": "[S3-FILES-BUCKET]", "s3_key": "data/education/a.md", "s3_uri": "s3://[S3-FILES-BUCKET]/data/education/a.md", "status": s3_archive.STATUS_VERIFIED, "uploaded_at": None, "verified_at": None, "etag": None, "error": None}
            with open(os.path.join(mdir, "education.manifest.jsonl"), "w") as f:
                f.write(json.dumps(rec) + "\n")
            self.assertEqual(s3_archive._names_with_manifests(tmp), ["education"])

### Tests: keys and hashing
class TestKeysAndHashing(unittest.TestCase):
    def test_s3_key_for_empty_default_prefix(self):
        key = s3_archive.s3_key_for("data/education/a.md")
        self.assertEqual(key, "data/education/a.md")
    def test_s3_key_for_empty_prefix_no_leading_slash(self):
        key = s3_archive.s3_key_for("/data/education/a.md", key_prefix="")
        self.assertEqual(key, "data/education/a.md")
    def test_s3_key_for_joins_prefix(self):
        key = s3_archive.s3_key_for("data/education/a.md", key_prefix="some-prefix/")
        self.assertEqual(key, "some-prefix/data/education/a.md")
    def test_s3_uri_for(self):
        uri = s3_archive.s3_uri_for("[S3-FILES-BUCKET]", "data/a.md")
        self.assertEqual(uri, "s3://[S3-FILES-BUCKET]/data/a.md")
    def test_sha256_file_matches_known(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write("hello")
            path = f.name
        try:
            # sha256 of "hello"
            expected = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
            self.assertEqual(s3_archive.sha256_file(path), expected)
        finally:
            os.remove(path)

### Tests: manifest build and IO
class TestManifestBuild(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = _make_repo(self.tmp)
    def tearDown(self):
        shutil.rmtree(self.tmp)
    def test_build_corpus_manifest_records(self):
        records = s3_archive.build_corpus_manifest("education", repo_root=self.repo)
        self.assertEqual(len(records), 2)
        paths = sorted(r["repo_path"] for r in records)
        self.assertEqual(paths, ["data/education/a.md", "data/education/sub/b.txt"])
        for r in records:
            self.assertEqual(r["status"], s3_archive.STATUS_PENDING)
            self.assertIsNone(r["sha256"])
            self.assertTrue(r["s3_key"].startswith("data/education/"))
    def test_build_with_hash_fills_sha256(self):
        records = s3_archive.build_corpus_manifest("education", repo_root=self.repo, compute_hash=True)
        for r in records:
            self.assertEqual(len(r["sha256"]), 64)
    def test_rebuild_preserves_uploaded_status(self):
        records = s3_archive.build_corpus_manifest("education", repo_root=self.repo)
        mpath = s3_archive.manifest_path_for("education", self.repo)
        # Simulate one file already uploaded.
        records[0]["status"] = s3_archive.STATUS_UPLOADED
        records[0]["sha256"] = "deadbeef"
        s3_archive.write_manifest(mpath, records)
        # Rebuild: unchanged file should keep its uploaded status.
        rebuilt = s3_archive.build_corpus_manifest("education", repo_root=self.repo)
        by_path = s3_archive.index_by_repo_path(rebuilt)
        self.assertEqual(by_path[records[0]["repo_path"]]["status"], s3_archive.STATUS_UPLOADED)
    def test_changed_size_resets_to_pending(self):
        records = s3_archive.build_corpus_manifest("education", repo_root=self.repo)
        mpath = s3_archive.manifest_path_for("education", self.repo)
        records[0]["status"] = s3_archive.STATUS_UPLOADED
        s3_archive.write_manifest(mpath, records)
        # Grow the file so its size changes.
        target = os.path.join(self.repo, records[0]["repo_path"])
        with open(target, "a") as f:
            f.write("more content")
        rebuilt = s3_archive.build_corpus_manifest("education", repo_root=self.repo)
        by_path = s3_archive.index_by_repo_path(rebuilt)
        self.assertEqual(by_path[records[0]["repo_path"]]["status"], s3_archive.STATUS_PENDING)
    def test_mtime_only_preserves_uploaded_status(self):
        records = s3_archive.build_corpus_manifest("education", repo_root=self.repo, compute_hash=True)
        mpath = s3_archive.manifest_path_for("education", self.repo)
        records[0]["status"] = s3_archive.STATUS_UPLOADED
        s3_archive.write_manifest(mpath, records)
        target = os.path.join(self.repo, records[0]["repo_path"])
        st = os.stat(target)
        os.utime(target, (st.st_atime, st.st_mtime + 100))
        rebuilt = s3_archive.build_corpus_manifest("education", repo_root=self.repo)
        by_path = s3_archive.index_by_repo_path(rebuilt)
        rec = by_path[records[0]["repo_path"]]
        self.assertEqual(rec["status"], s3_archive.STATUS_UPLOADED)
        self.assertEqual(rec["sha256"], records[0]["sha256"])
        self.assertNotEqual(rec["mtime"], records[0]["mtime"])

### Tests: dry run does not touch S3
class TestDryRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = _make_repo(self.tmp)
        s3_archive.build_corpus_manifest("education", repo_root=self.repo)
    def tearDown(self):
        shutil.rmtree(self.tmp)
    def test_upload_dry_run_no_client(self):
        # _s3_client must never be called in a dry run.
        with patch.object(s3_archive, "_s3_client", side_effect=AssertionError("client created in dry run")) as mock_client:
            summary = s3_archive.upload_corpus("education", repo_root=self.repo, execute=False)
        mock_client.assert_not_called()
        self.assertEqual(summary["uploaded"], 0)
    def test_upload_execute_uses_client_and_marks_uploaded(self):
        fake = MagicMock()
        fake.head_object.return_value = {"ETag": '"abc123"', "ContentLength": 5}
        with patch.object(s3_archive, "_s3_client", return_value=fake):
            summary = s3_archive.upload_corpus("education", repo_root=self.repo, execute=True, verbose=False)
        self.assertEqual(summary["errors"], 0)
        self.assertEqual(summary["uploaded"], 2)
        self.assertTrue(fake.upload_file.called)
        records = s3_archive.read_manifest(s3_archive.manifest_path_for("education", self.repo))
        for r in records:
            self.assertEqual(r["status"], s3_archive.STATUS_UPLOADED)
            self.assertEqual(len(r["sha256"]), 64)
            self.assertEqual(r["etag"], "abc123")
    def test_upload_and_verify_can_be_limited_to_repo_path_prefix(self):
        prefix = "data/education/a.md"
        fake = MagicMock()
        fake.head_object.return_value = {"ETag": '"scoped"', "ContentLength": 5}
        with patch.object(s3_archive, "_s3_client", return_value=fake):
            uploaded = s3_archive.upload_corpus("education", repo_root=self.repo, execute=True, verbose=False, path_prefix=prefix)
        self.assertEqual(uploaded["uploaded"], 1)
        self.assertEqual(fake.upload_file.call_count, 1)
        records = s3_archive.read_manifest(s3_archive.manifest_path_for("education", self.repo))
        by_path = s3_archive.index_by_repo_path(records)
        self.assertEqual(by_path["data/education/a.md"]["status"], s3_archive.STATUS_UPLOADED)
        self.assertEqual(by_path["data/education/sub/b.txt"]["status"], s3_archive.STATUS_PENDING)

        with patch.object(s3_archive, "_s3_client", return_value=fake):
            verified = s3_archive.verify_corpus("education", repo_root=self.repo, execute=True, verbose=False, path_prefix=prefix)
        self.assertEqual(verified["checked"], 1)
        self.assertEqual(verified["verified"], 1)
        records = s3_archive.read_manifest(s3_archive.manifest_path_for("education", self.repo))
        by_path = s3_archive.index_by_repo_path(records)
        self.assertEqual(by_path["data/education/a.md"]["status"], s3_archive.STATUS_VERIFIED)
        self.assertEqual(by_path["data/education/sub/b.txt"]["status"], s3_archive.STATUS_PENDING)

### Tests: refresh (make S3 match local)
class TestRefresh(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = _make_repo(self.tmp)
        s3_archive.build_corpus_manifest("education", repo_root=self.repo)
    def tearDown(self):
        shutil.rmtree(self.tmp)
    def _fake_client(self):
        fake = MagicMock()
        fake.head_object.return_value = {"ETag": '"e"', "ContentLength": 5}
        return fake
    def test_refresh_dry_run_no_client(self):
        with patch.object(s3_archive, "_s3_client", side_effect=AssertionError("client in dry run")):
            summary = s3_archive.refresh_corpus("education", repo_root=self.repo, execute=False)
        self.assertEqual(summary["to_upload"], 2)
        self.assertEqual(summary["local_missing"], 0)
    def test_refresh_uploads_new_file(self):
        fake = self._fake_client()
        with patch.object(s3_archive, "_s3_client", return_value=fake):
            s3_archive.refresh_corpus("education", repo_root=self.repo, execute=True, verbose=False)
        # Add a new local file, refresh again: only the new file uploads.
        with open(os.path.join(self.repo, "data", "education", "c.md"), "w") as f:
            f.write("new!")
        fake2 = self._fake_client()
        with patch.object(s3_archive, "_s3_client", return_value=fake2):
            summary = s3_archive.refresh_corpus("education", repo_root=self.repo, execute=True, verbose=False)
        self.assertEqual(summary["to_upload"], 1)
        self.assertEqual(fake2.upload_file.call_count, 1)
    def test_refresh_removed_file_kept_without_prune(self):
        fake = self._fake_client()
        with patch.object(s3_archive, "_s3_client", return_value=fake):
            s3_archive.refresh_corpus("education", repo_root=self.repo, execute=True, verbose=False)
        os.remove(os.path.join(self.repo, "data", "education", "a.md"))
        fake2 = self._fake_client()
        with patch.object(s3_archive, "_s3_client", return_value=fake2):
            summary = s3_archive.refresh_corpus("education", repo_root=self.repo, execute=True, prune=False, verbose=False)
        self.assertEqual(summary["local_missing"], 1)
        self.assertEqual(summary["pruned"], 0)
        fake2.delete_object.assert_not_called()
        records = s3_archive.read_manifest(s3_archive.manifest_path_for("education", self.repo))
        statuses = [r["status"] for r in records]
        self.assertIn(s3_archive.STATUS_LOCAL_MISSING, statuses)
    def test_refresh_prune_deletes_from_s3(self):
        fake = self._fake_client()
        with patch.object(s3_archive, "_s3_client", return_value=fake):
            s3_archive.refresh_corpus("education", repo_root=self.repo, execute=True, verbose=False)
        os.remove(os.path.join(self.repo, "data", "education", "a.md"))
        fake2 = self._fake_client()
        with patch.object(s3_archive, "_s3_client", return_value=fake2):
            summary = s3_archive.refresh_corpus("education", repo_root=self.repo, execute=True, prune=True, verbose=False)
        self.assertEqual(summary["pruned"], 1)
        fake2.delete_object.assert_called_once()

### Tests: gitignore-honoring walk, include_globs, scan_root
class TestGitignoreAndScanRoot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
    def tearDown(self):
        shutil.rmtree(self.tmp)
    def _git(self, *args):
        import subprocess
        subprocess.run(["git", "-C", self.tmp, *args], check=True, capture_output=True, text=True)
    def test_include_globs_filters_by_basename(self):
        d = os.path.join(self.tmp, "area")
        os.makedirs(d)
        for name in ("pii-exchanges_x.db", "exchanges_x.db", "notes.txt"):
            with open(os.path.join(d, name), "w") as f:
                f.write("x")
        got = sorted(os.path.basename(p) for p in s3_archive.iter_files(d, recursive=False, include_globs=["pii-exchanges_*.db"]))
        self.assertEqual(got, ["pii-exchanges_x.db"])
    def test_respect_gitignore_drops_ignored_file(self):
        self._git("init")
        with open(os.path.join(self.tmp, ".gitignore"), "w") as f:
            f.write("**/pii*\n")
        d = os.path.join(self.tmp, "exchanges")
        os.makedirs(d)
        with open(os.path.join(d, "pii-secret.db"), "w") as f:
            f.write("secret")
        with open(os.path.join(d, "keep.json"), "w") as f:
            f.write("ok")
        kept = sorted(os.path.basename(p) for p in s3_archive.iter_files(d, recursive=True, respect_gitignore=True, scan_root=self.tmp))
        self.assertEqual(kept, ["keep.json"])
        # Without the filter the ignored file is still walked.
        allf = sorted(os.path.basename(p) for p in s3_archive.iter_files(d, recursive=True, respect_gitignore=False))
        self.assertEqual(allf, ["keep.json", "pii-secret.db"])
    def test_gitignore_fails_open_outside_repo(self):
        # Not a git repo: nothing is filtered (fail-open) so scanning still works.
        d = os.path.join(self.tmp, "area")
        os.makedirs(d)
        with open(os.path.join(d, "pii-secret.db"), "w") as f:
            f.write("x")
        kept = list(s3_archive.iter_files(d, recursive=True, respect_gitignore=True, scan_root=self.tmp))
        self.assertEqual(len(kept), 1)
    def test_scan_root_keys_relative_with_no_prefix(self):
        # Files sourced from a scan_root outside the manifest's repo_root must key
        # relative to scan_root (no leading path component).
        sibling = os.path.join(self.tmp, "sibling")
        area = os.path.join(sibling, "exchanges")
        os.makedirs(area)
        with open(os.path.join(area, "pii-x.db"), "w") as f:
            f.write("x")
        repo = os.path.join(self.tmp, "repo")
        os.makedirs(repo)
        records = s3_archive.build_area_manifest("pii_x", "exchanges", repo_root=repo, bucket="[S3-BUCKET]", recursive=False, respect_gitignore=False, include_globs=["pii-*.db"], scan_root=sibling, write=False)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["repo_path"], "exchanges/pii-x.db")
        self.assertEqual(records[0]["s3_key"], "exchanges/pii-x.db")
        self.assertEqual(records[0]["s3_bucket"], "[S3-BUCKET]")
        self.assertEqual(records[0]["s3_uri"], "s3://[S3-BUCKET]/exchanges/pii-x.db")
    def test_resolve_scan_root_relative_and_absolute(self):
        self.assertEqual(s3_archive.resolve_scan_root(None, "/repo"), "/repo")
        self.assertEqual(s3_archive.resolve_scan_root({"root": "../corpus-tools"}, "/a/b/repo"), "/a/b/corpus-tools")
        self.assertEqual(s3_archive.resolve_scan_root({"root": "/abs/path"}, "/repo"), "/abs/path")

### Tests: PII areas are isolated from the default mirror set
class TestPiiAreaIsolation(unittest.TestCase):
    def test_pii_areas_not_in_default_specs(self):
        with tempfile.TemporaryDirectory() as tmp:
            names = [s["name"] for s in s3_archive.area_specs(repo_root=tmp)]
            for spec in s3_archive.PII_AREAS:
                self.assertNotIn(spec["name"], names)
    def test_pii_areas_target_[S3-BUCKET]_and_corpus_tools(self):
        for spec in s3_archive.PII_AREAS:
            self.assertEqual(spec["bucket"], "[S3-BUCKET]")
            self.assertEqual(spec["root"], "../corpus-tools")
            self.assertFalse(spec["respect_gitignore"])
    def test_area_spec_for_finds_pii(self):
        spec = s3_archive.area_spec_for("pii_hash_store_logs", repo_root="/nonexistent")
        self.assertIsNotNone(spec)
        self.assertEqual(spec["bucket"], "[S3-BUCKET]")
    def test_exchanges_areas_respect_gitignore(self):
        names = {s["name"]: s for s in s3_archive.EXTRA_AREAS}
        self.assertTrue(names["exchanges_qrag_deutsch"]["respect_gitignore"])
        self.assertFalse(names["logs"]["respect_gitignore"])

if __name__ == "__main__":
    unittest.main()
