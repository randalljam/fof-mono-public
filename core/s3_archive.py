# ===== START OF FILE primary/s3_archive.py =====
# Library to manage archiving bulk corpus data to S3: manifest, upload, verify.
#
# Companion to primary/aws.py (general AWS helpers). This module is purpose-built
# for the repo pare-down / S3 archive effort: it builds per-corpus manifests of
# the files under data/, uploads them to S3 while recording sha256 checksums,
# and verifies uploads before any local deletion is considered.
#
# Design notes:
# - The stdlib-only core (scan, hash, manifest IO, planning, reporting) imports
#   with no third-party deps so it runs anywhere, including dry-run on a machine
#   without AWS credentials.
# - boto3 is imported lazily inside the upload/verify functions only, so building
#   and inspecting manifests never requires credentials or boto3 installed.
# - Nothing here deletes local files. Local deletion is a separate, explicitly
#   approved step the operator performs after verification (see README).
# - Default mode for upload/verify is a DRY RUN. Real S3 writes require execute=True.

import os
import sys
import json
import fnmatch
import hashlib
import argparse
import tempfile
import subprocess
from datetime import datetime, timezone

### Config: constants
# Private (non-public) bucket holding active corpus files. NOT an archive --
# these files are live; the bucket is the working store, with the repo holding
# code + manifests. Bucket must have Block Public Access ON and Versioning ON
# (versioning is the recovery path for accidental deletes/overwrites).
DEFAULT_BUCKET = "[S3-FILES-BUCKET]"
DEFAULT_REGION = "us-west-2"
# Repo-relative path is appended to this prefix to form the S3 key.
# Prefix is empty: keys mirror the repo-relative path directly.
# e.g. data/education/foo.mp3 -> data/education/foo.mp3
DEFAULT_KEY_PREFIX = ""
# Where per-corpus manifests are written (relative to repo root).
MANIFEST_SUBDIR = "manifests"
# File names matched here are skipped during scans.
EXCLUDE_NAMES = {".DS_Store"}
# Status values used in manifest records.
STATUS_PENDING = "pending_upload"
STATUS_UPLOADED = "uploaded"
STATUS_VERIFIED = "verified"
STATUS_ERROR = "error"
# Object exists in S3 / prior manifest but has no local file (a refresh found it
# removed locally). Kept for visibility unless explicitly pruned.
STATUS_LOCAL_MISSING = "local_missing"

# Archive areas beyond the data/ corpuses. These are top-level repo paths that
# the pare-down marked stage=archive (worth keeping) but that don't live in the
# git repo as code. Each area becomes one manifest named after "name".
#   recursive=False -> only the immediate files of the path (used for data/ root files).
# Dirs that are NOT carried into the new repo and NOT uploaded (ms-graphrag,
# _misc_to_be_sorted, limbo, lancedb, pretrained_models, langchain-layer, root junk)
# are listed in 2026-06-01_excluded-from-carryover.md, not here. They stay only in frozen main.
#
# Per-area keys:
#   recursive          -> walk subdirectories (True) or only immediate files (False).
#   respect_gitignore  -> drop files matched by .gitignore from the walk. Default True
#                         (set on the build function). Areas whose content is INTENTIONALLY
#                         gitignored but must still upload (the bulk data corpuses, logs,
#                         _archive, and PII) set this False so the filter does not erase them.
#   include_globs      -> optional list of basename fnmatch patterns; when set, only files
#                         whose basename matches one of them are taken (used to pick out just
#                         the PII files inside an otherwise-mixed folder).
#   bucket             -> target S3 bucket (defaults to DEFAULT_BUCKET / the CLI --bucket).
#   root               -> scan root for this area, absolute or relative to the repo root.
#                         Lets an area's source files live OUTSIDE this repo (e.g. the sibling
#                         ../corpus-tools working copy) while the manifest is still written here
#                         and the S3 key mirrors the path RELATIVE TO THAT ROOT (no extra prefix).
EXTRA_AREAS = [
    {"name": "data_root_files", "path": "data", "recursive": False, "respect_gitignore": False},
    {"name": "logs", "path": "logs", "recursive": True, "respect_gitignore": False},
    {"name": "_archive", "path": "_archive", "recursive": True, "respect_gitignore": False},
    # Selected QRAG exchange sets -> [S3-FILES-BUCKET]. Scoped one-area-per-set on purpose: a blanket
    # "exchanges/" area would sweep in the gitignored PII dbs. respect_gitignore=True so any
    # pii* / user_hash_log* files are filtered out and only the tracked exchange artifacts upload.
    {"name": "exchanges_qrag_deutsch", "path": "exchanges/qrag_deutsch", "recursive": True, "respect_gitignore": True},
    {"name": "exchanges_qrag_deutsch_early", "path": "exchanges/qrag_deutsch_early", "recursive": True, "respect_gitignore": True},
    {"name": "exchanges_qrag_fda-c19-townhalls", "path": "exchanges/qrag_fda-c19-townhalls", "recursive": True, "respect_gitignore": True},
    {"name": "exchanges_qrag_pv-evac", "path": "exchanges/qrag_pv-evac", "recursive": True, "respect_gitignore": True},
    {"name": "exchanges_qrag_sovereign-child", "path": "exchanges/qrag_sovereign-child", "recursive": True, "respect_gitignore": True},
    {"name": "exchanges_response_files", "path": "exchanges/response_files", "recursive": True, "respect_gitignore": True},
    {"name": "games_poly-files", "path": "apps/games/poly-files", "recursive": True, "respect_gitignore": False},
    {"name": "games_arnis-tile-cache", "path": "apps/games/arnis-tile-cache", "recursive": True, "respect_gitignore": False},
    {"name": "stellar-eval_m3b-five-review", "path": "data/stellar-eval/m3b-five-model-review", "recursive": True, "respect_gitignore": False},
    # Holodeck AI-session raw exports (Claude/Codex cloud transcripts). Source lives in the
    # durable local-files mount OUTSIDE this repo; root points there so the S3 key mirrors the
    # path relative to that root (s3://[S3-FILES-BUCKET]/ai-sessions/...). Non-PII coding sessions.
    {"name": "ai_sessions", "path": "ai-sessions", "recursive": True, "respect_gitignore": False, "root": "../_LOCAL_FILES/fof-mono"},
    # Holodeck compiled turns DB (sessions/exchanges/links). Same local-files mount as above;
    # include_globs keeps WAL/SHM/backups/snapshot out of the manifest.
    {"name": "holodeck_turns", "path": "apps/holodeck/data", "recursive": False, "respect_gitignore": False, "root": "../_LOCAL_FILES/fof-mono", "include_globs": ["turns.db"]},
    {"name": "focusonfoundations_applet-audio", "path": "apps/focusonfoundations/web/public/audio", "recursive": True, "respect_gitignore": False},
    # Canonical approved dragon GLBs for math-quiz (content_studio profile). Narrow path so
    # staging/previews under _data are not swept in; **/_data is gitignored so respect_gitignore=False.
    {"name": "content-studio_math-quiz-dragon-baby", "path": "apps/content_studio/_data/profiles/math-quiz-dragon-baby/approved", "recursive": False, "respect_gitignore": False, "include_globs": ["*.glb"]},
]

# PII areas -> the separate, stricter private bucket "[S3-BUCKET]" (Block Public Access ON,
# Versioning ON). These files are intentionally gitignored (**/pii*, **/user_hash_log*), so
# respect_gitignore=False -- otherwise the filter would drop the very files we must upload.
# They live in the sibling ../corpus-tools working copy, not in this repo, so root points there;
# the S3 key mirrors the path relative to that root, with NO "corpus-tools/" prefix.
# include_globs picks ONLY the PII files out of each otherwise-mixed folder.
# Deliberately kept OUT of area_specs()/build-all/upload-all/verify-all so a blanket run never
# touches PII or sends it to the wrong bucket: build/upload/verify these explicitly by name.
PII_BUCKET = "[S3-BUCKET]"
PII_ROOT = "../corpus-tools"
PII_AREAS = [
    {"name": "pii_exchanges_csv", "path": "exchanges", "recursive": False, "respect_gitignore": False, "bucket": PII_BUCKET, "root": PII_ROOT, "include_globs": ["pii_user_hash_log*"]},
    {"name": "pii_exchanges_qrag_deutsch", "path": "exchanges/qrag_deutsch", "recursive": False, "respect_gitignore": False, "bucket": PII_BUCKET, "root": PII_ROOT, "include_globs": ["pii-exchanges_*.db"]},
    {"name": "pii_exchanges_qrag_fda-c19-townhalls", "path": "exchanges/qrag_fda-c19-townhalls", "recursive": False, "respect_gitignore": False, "bucket": PII_BUCKET, "root": PII_ROOT, "include_globs": ["pii-exchanges_*.db"]},
    {"name": "pii_exchanges_qrag_pv-evac", "path": "exchanges/qrag_pv-evac", "recursive": False, "respect_gitignore": False, "bucket": PII_BUCKET, "root": PII_ROOT, "include_globs": ["pii-exchanges_*.db"]},
    {"name": "pii_exchanges_qrag_sovereign-child", "path": "exchanges/qrag_sovereign-child", "recursive": False, "respect_gitignore": False, "bucket": PII_BUCKET, "root": PII_ROOT, "include_globs": ["pii-exchanges_*.db"]},
    {"name": "pii_hash_store_logs", "path": "web-shared/aws_chalice/hash-store", "recursive": False, "respect_gitignore": False, "bucket": PII_BUCKET, "root": PII_ROOT, "include_globs": ["user_hash_log*"]},
]

### Config: paths and S3 keys
def repo_root_default():
    """
    Return the repo root inferred from this file's location.

    :return root: str, absolute path to the repo root (parent of primary/).
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def _posix_rel(abs_path, repo_root):
    """
    Return a repo-relative path using forward slashes.

    :param abs_path: str, absolute path to a file.
    :param repo_root: str, absolute path to the repo root.
    :return rel: str, repo-relative path with forward slashes.
    """
    return os.path.relpath(abs_path, repo_root).replace(os.sep, "/")
def s3_key_for(repo_rel, key_prefix=DEFAULT_KEY_PREFIX):
    """
    Build the S3 key for a repo-relative path.

    :param repo_rel: str, repo-relative path with forward slashes.
    :param key_prefix: str, prefix prepended to the repo-relative path (may be empty).
    :return key: str, the S3 object key.
    """
    prefix = key_prefix.strip("/")
    rel = repo_rel.lstrip("/")
    return f"{prefix}/{rel}" if prefix else rel
def s3_uri_for(bucket, key):
    """
    Build an s3:// URI from a bucket and key.

    :param bucket: str, S3 bucket name.
    :param key: str, S3 object key.
    :return uri: str, the s3:// URI.
    """
    return f"s3://{bucket}/{key}"
def manifest_path_for(corpus, repo_root=None):
    """
    Return the manifest file path for a corpus.

    :param corpus: str, corpus folder name under data/.
    :param repo_root: str, absolute repo root, or None to infer.
    :return path: str, absolute path to the corpus manifest jsonl.
    """
    repo_root = repo_root or repo_root_default()
    return os.path.join(repo_root, MANIFEST_SUBDIR, f"{corpus}.manifest.jsonl")

### Helpers: hashing and file walks
def sha256_file(file_path, chunk_size=1048576):
    """
    Compute the SHA-256 hex digest of a file by streaming it.

    :param file_path: str, path to the file.
    :param chunk_size: int, bytes read per chunk (default 1 MiB).
    :return digest: str, lowercase hex SHA-256 digest.
    """
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()
def git_ignored_subset(abs_paths, scan_root):
    """
    Return the subset of abs_paths that .gitignore marks as ignored.

    Batches the candidate paths through a single `git check-ignore --stdin` call
    rooted at scan_root. Fails OPEN (returns an empty set, i.e. nothing filtered)
    when git is unavailable or scan_root is not inside a git work tree, so the
    scanner still works outside a repo (e.g. in tests / temp dirs). Callers that
    must NOT leak gitignored files (the exchanges upload) rely on this being run
    inside the real repo where git is present.

    :param abs_paths: list, absolute file paths to test.
    :param scan_root: str, absolute directory git treats as the work tree root.
    :return ignored: set, the subset of abs_paths that are gitignored.
    """
    if not abs_paths:
        return set()
    rels = [os.path.relpath(p, scan_root) for p in abs_paths]
    try:
        proc = subprocess.run(
            ["git", "-C", scan_root, "check-ignore", "--stdin"],
            input="\n".join(rels) + "\n",
            capture_output=True, text=True,
        )
    except (FileNotFoundError, OSError):
        return set()
    # exit 0 -> some paths ignored (listed on stdout); 1 -> none ignored;
    # anything else (e.g. 128 "not a git repository") -> treat as no filtering.
    if proc.returncode not in (0, 1):
        return set()
    ignored_rels = set(line.strip() for line in proc.stdout.splitlines() if line.strip())
    return set(p for p, rel in zip(abs_paths, rels) if rel in ignored_rels)
def iter_files(local_dir, recursive=True, respect_gitignore=False, scan_root=None, include_globs=None):
    """
    Yield absolute paths of regular files in a directory, skipping symlinks.

    :param local_dir: str, directory to scan.
    :param recursive: bool, recurse into subdirectories (True) or only the immediate files (False).
    :param respect_gitignore: bool, drop files matched by .gitignore (uses git check-ignore).
    :param scan_root: str, git work-tree root for gitignore checks (defaults to local_dir).
    :param include_globs: list, optional basename fnmatch patterns; when set, only matching files are yielded.
    :return paths: generator of str, absolute file paths (excludes EXCLUDE_NAMES).
    """
    candidates = []
    if recursive:
        for root, dirs, files in os.walk(local_dir, followlinks=False):
            for name in files:
                if name in EXCLUDE_NAMES:
                    continue
                if include_globs and not _name_matches(name, include_globs):
                    continue
                fp = os.path.join(root, name)
                if os.path.islink(fp):
                    continue
                candidates.append(fp)
    else:
        for name in sorted(os.listdir(local_dir)):
            if name in EXCLUDE_NAMES:
                continue
            if include_globs and not _name_matches(name, include_globs):
                continue
            fp = os.path.join(local_dir, name)
            if os.path.isfile(fp) and not os.path.islink(fp):
                candidates.append(fp)
    if respect_gitignore:
        ignored = git_ignored_subset(candidates, scan_root or local_dir)
        candidates = [p for p in candidates if p not in ignored]
    for fp in candidates:
        yield fp
def _name_matches(name, globs):
    """
    Return True if a file basename matches any of the fnmatch patterns.

    :param name: str, file basename.
    :param globs: list, fnmatch patterns.
    :return matched: bool, True if any pattern matches.
    """
    return any(fnmatch.fnmatch(name, g) for g in globs)
def _now_iso():
    """
    Return the current UTC time as an ISO-8601 string.

    :return ts: str, current UTC timestamp.
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

### Manifest IO
def read_manifest(manifest_path):
    """
    Read a jsonl manifest into a list of records.

    :param manifest_path: str, path to the manifest jsonl file.
    :return records: list, manifest records (empty if file does not exist).
    """
    if not os.path.exists(manifest_path):
        return []
    records = []
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
def write_manifest(manifest_path, records):
    """
    Write manifest records to a jsonl file atomically.

    :param manifest_path: str, path to the manifest jsonl file.
    :param records: list, manifest records to write.
    :return manifest_path: str, the path written.
    """
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(manifest_path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        os.replace(tmp, manifest_path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return manifest_path
def index_by_repo_path(records):
    """
    Index manifest records by their repo_path.

    :param records: list, manifest records.
    :return mapping: dict, repo_path -> record.
    """
    return {r["repo_path"]: r for r in records}

### Build manifest
def _new_record(repo_rel, corpus, size_bytes, bucket, key_prefix, sha256=None, mtime=None):
    """
    Construct a fresh manifest record for a file.

    :param repo_rel: str, repo-relative path with forward slashes.
    :param corpus: str, corpus name (data subfolder).
    :param size_bytes: int, file size in bytes.
    :param bucket: str, target S3 bucket.
    :param key_prefix: str, S3 key prefix.
    :param sha256: str, precomputed sha256, or None.
    :param mtime: int, file modification time (epoch seconds), or None.
    :return record: dict, a manifest record in pending_upload status.
    """
    key = s3_key_for(repo_rel, key_prefix)
    return {
        "repo_path": repo_rel,
        "corpus": corpus,
        "size_bytes": size_bytes,
        "mtime": mtime,
        "sha256": sha256,
        "s3_bucket": bucket,
        "s3_key": key,
        "s3_uri": s3_uri_for(bucket, key),
        "status": STATUS_PENDING,
        "uploaded_at": None,
        "verified_at": None,
        "etag": None,
        "error": None,
    }
def resolve_scan_root(spec, repo_root):
    """
    Resolve the scan root for an area spec (where its source files actually live).

    Most areas scan inside the repo, so scan_root == repo_root. An area may set
    "root" (absolute, or relative to repo_root) to source files from OUTSIDE this
    repo (e.g. the sibling ../corpus-tools working copy) while still writing the
    manifest here and keying objects relative to that root.

    :param spec: dict, an area spec (may be None).
    :param repo_root: str, absolute repo root.
    :return scan_root: str, absolute directory to scan / make repo_path relative to.
    """
    root = (spec or {}).get("root")
    if not root:
        return repo_root
    if os.path.isabs(root):
        return os.path.normpath(root)
    return os.path.normpath(os.path.join(repo_root, root))
def build_area_manifest(name, local_relpath, repo_root=None, bucket=DEFAULT_BUCKET, key_prefix=DEFAULT_KEY_PREFIX, compute_hash=False, recursive=True, write=True, respect_gitignore=True, include_globs=None, scan_root=None):
    """
    Build or refresh the manifest for one area (a data corpus or top-level path).

    Existing records are reused when content is unchanged. A fast path skips
    hashing when size and mtime both match the prior record; otherwise the
    local sha256 is compared to the stored hash. Mtime-only changes (e.g. after
    copy/reorg) do not reset uploaded/verified status. New or content-changed
    files are reset to pending_upload.

    :param name: str, manifest/area name (e.g. "education", "logs").
    :param local_relpath: str, directory to scan, relative to scan_root (e.g. "data/education", "exchanges/qrag_deutsch").
    :param repo_root: str, absolute repo root (where the manifest is written), or None to infer.
    :param bucket: str, target S3 bucket.
    :param key_prefix: str, S3 key prefix.
    :param compute_hash: bool, whether to compute sha256 now (slow) or defer to upload.
    :param recursive: bool, recurse into subdirectories (True) or only immediate files (False).
    :param write: bool, whether to write the manifest file to disk.
    :param respect_gitignore: bool, drop gitignored files from the walk (default True).
    :param include_globs: list, optional basename patterns; only matching files are taken.
    :param scan_root: str, root the files live under and repo_path is relative to (defaults to repo_root).
    :return records: list, the manifest records (sorted by repo_path).
    """
    repo_root = repo_root or repo_root_default()
    scan_root = scan_root or repo_root
    area_dir = os.path.join(scan_root, local_relpath)
    if not os.path.isdir(area_dir):
        raise ValueError(f"Area directory not found: {area_dir}")
    mpath = manifest_path_for(name, repo_root)
    prior = index_by_repo_path(read_manifest(mpath))
    records = []
    for abs_path in sorted(iter_files(area_dir, recursive=recursive, respect_gitignore=respect_gitignore, scan_root=scan_root, include_globs=include_globs)):
        repo_rel = _posix_rel(abs_path, scan_root)
        st = os.stat(abs_path)
        size_bytes = st.st_size
        mtime = int(st.st_mtime)
        old = prior.get(repo_rel)
        if old and old.get("size_bytes") == size_bytes and old.get("mtime") == mtime:
            # Fast path: size and mtime unchanged — keep prior record as-is.
            rec = old
            if compute_hash and not rec.get("sha256"):
                rec["sha256"] = sha256_file(abs_path)
        elif old and old.get("sha256"):
            # Size or mtime changed — compare content hash before re-queueing upload.
            local_sha = sha256_file(abs_path)
            if local_sha == old["sha256"]:
                rec = dict(old)
                rec["mtime"] = mtime
                rec["size_bytes"] = size_bytes
            else:
                rec = _new_record(repo_rel, name, size_bytes, bucket, key_prefix, sha256=local_sha, mtime=mtime)
        elif old and old.get("status") in (STATUS_UPLOADED, STATUS_VERIFIED) and old.get("size_bytes") == size_bytes:
            # Legacy record without sha256; size unchanged — refresh metadata only.
            rec = dict(old)
            rec["mtime"] = mtime
            rec["sha256"] = sha256_file(abs_path)
        else:
            # New file or content/size change with no prior hash to compare.
            sha = sha256_file(abs_path) if compute_hash else None
            rec = _new_record(repo_rel, name, size_bytes, bucket, key_prefix, sha256=sha, mtime=mtime)
        # Keep bucket/key in sync with current config even for reused records.
        rec["s3_bucket"] = bucket
        rec["s3_key"] = s3_key_for(repo_rel, key_prefix)
        rec["s3_uri"] = s3_uri_for(bucket, rec["s3_key"])
        records.append(rec)
    if write:
        write_manifest(mpath, records)
    return records
def build_corpus_manifest(corpus, repo_root=None, bucket=DEFAULT_BUCKET, key_prefix=DEFAULT_KEY_PREFIX, compute_hash=False, write=True):
    """
    Build or refresh the manifest for one corpus under data/ (a data-area wrapper).

    :param corpus: str, corpus folder name under data/.
    :param repo_root: str, absolute repo root, or None to infer.
    :param bucket: str, target S3 bucket.
    :param key_prefix: str, S3 key prefix.
    :param compute_hash: bool, whether to compute sha256 now (slow) or defer to upload.
    :param write: bool, whether to write the manifest file to disk.
    :return records: list, the manifest records (sorted by repo_path).
    """
    # data/ is itself gitignored (bulk data lives in S3, not git), so respect_gitignore=False:
    # the filter would otherwise erase every file we intend to upload.
    return build_area_manifest(corpus, f"data/{corpus}", repo_root=repo_root, bucket=bucket, key_prefix=key_prefix, compute_hash=compute_hash, recursive=True, write=write, respect_gitignore=False)
def list_data_corpuses(repo_root=None):
    """
    List immediate subdirectories of data/ (the corpuses).

    :param repo_root: str, absolute repo root, or None to infer.
    :return corpuses: list, sorted corpus folder names.
    """
    repo_root = repo_root or repo_root_default()
    data_dir = os.path.join(repo_root, "data")
    if not os.path.isdir(data_dir):
        return []
    names = []
    for name in os.listdir(data_dir):
        full = os.path.join(data_dir, name)
        if os.path.isdir(full) and not os.path.islink(full):
            names.append(name)
    return sorted(names)
def manifest_names(repo_root=None):
    """
    List area names from manifest files on disk.

    :param repo_root: str, absolute repo root, or None to infer.
    :return names: list, sorted area names (one per *.manifest.jsonl in MANIFEST_SUBDIR).
    """
    repo_root = repo_root or repo_root_default()
    mdir = os.path.join(repo_root, MANIFEST_SUBDIR)
    if not os.path.isdir(mdir):
        return []
    return sorted(fn[:-len(".manifest.jsonl")] for fn in os.listdir(mdir) if fn.endswith(".manifest.jsonl"))
def area_specs(repo_root=None):
    """
    Return the full list of area specs to mirror: data corpuses plus EXTRA_AREAS.

    :param repo_root: str, absolute repo root, or None to infer.
    :return specs: list, dicts with keys name, path, recursive.
    """
    repo_root = repo_root or repo_root_default()
    specs = []
    for corpus in list_data_corpuses(repo_root):
        # Bulk data corpuses live under the gitignored data/ tree but are uploaded on purpose.
        specs.append({"name": corpus, "path": f"data/{corpus}", "recursive": True, "respect_gitignore": False})
    for area in EXTRA_AREAS:
        specs.append(dict(area))
    return specs
def area_spec_for(name, repo_root=None):
    """
    Look up a single area spec by name (data corpuses, EXTRA_AREAS, or PII areas).

    :param name: str, area/manifest name.
    :param repo_root: str, absolute repo root, or None to infer.
    :return spec: dict, the matching area spec, or None if not found.
    """
    for spec in area_specs(repo_root=repo_root):
        if spec["name"] == name:
            return spec
    for spec in PII_AREAS:
        if spec["name"] == name:
            return dict(spec)
    return None
def build_data_manifests(repo_root=None, bucket=DEFAULT_BUCKET, key_prefix=DEFAULT_KEY_PREFIX, compute_hash=False, corpuses=None):
    """
    Build manifests for every corpus subdirectory under data/.

    :param repo_root: str, absolute repo root, or None to infer.
    :param bucket: str, target S3 bucket.
    :param key_prefix: str, S3 key prefix.
    :param compute_hash: bool, whether to compute sha256 now (slow) or defer.
    :param corpuses: list, specific corpuses to build, or None for all.
    :return summary: dict, corpus name -> (file_count, total_bytes).
    """
    repo_root = repo_root or repo_root_default()
    corpuses = corpuses or list_data_corpuses(repo_root)
    summary = {}
    for corpus in corpuses:
        records = build_corpus_manifest(corpus, repo_root=repo_root, bucket=bucket, key_prefix=key_prefix, compute_hash=compute_hash)
        total = sum(r["size_bytes"] for r in records)
        summary[corpus] = (len(records), total)
        print(f"manifest: data/{corpus:<20} {len(records):>6,} files  {_fmt_mb(total):>8} MB  -> {manifest_path_for(corpus, repo_root)}")
    return summary
def build_all_manifests(repo_root=None, bucket=DEFAULT_BUCKET, key_prefix=DEFAULT_KEY_PREFIX, compute_hash=False):
    """
    Build manifests for every mirror area: data corpuses plus EXTRA_AREAS.

    :param repo_root: str, absolute repo root, or None to infer.
    :param bucket: str, target S3 bucket.
    :param key_prefix: str, S3 key prefix.
    :param compute_hash: bool, whether to compute sha256 now (slow) or defer.
    :return summary: dict, area name -> (file_count, total_bytes).
    """
    repo_root = repo_root or repo_root_default()
    summary = {}
    for spec in area_specs(repo_root=repo_root):
        scan_root = resolve_scan_root(spec, repo_root)
        area_path = os.path.join(scan_root, spec["path"])
        if not os.path.isdir(area_path):
            print(f"manifest: {spec['name']:<26} SKIPPED (path not present: {spec['path']})")
            continue
        records = build_area_manifest(spec["name"], spec["path"], repo_root=repo_root, bucket=spec.get("bucket", bucket), key_prefix=key_prefix, compute_hash=compute_hash, recursive=spec["recursive"], respect_gitignore=spec.get("respect_gitignore", True), include_globs=spec.get("include_globs"), scan_root=scan_root)
        total = sum(r["size_bytes"] for r in records)
        summary[spec["name"]] = (len(records), total)
        print(f"manifest: {spec['name']:<26} {len(records):>6,} files  {_fmt_mb(total):>8} MB")
    return summary

### Reporting
def _fmt_mb(n_bytes):
    """
    Format a byte count as integer megabytes with thousands separators.

    :param n_bytes: int, byte count.
    :return s: str, formatted megabytes (e.g. "1,024").
    """
    return f"{int(round(n_bytes / (1024 * 1024))):,}"
def manifest_summary(records):
    """
    Summarize a manifest's file counts and bytes by status.

    :param records: list, manifest records.
    :return summary: dict, with total_files, total_bytes, and by_status counts.
    """
    by_status = {}
    total_bytes = 0
    for r in records:
        st = r.get("status", STATUS_PENDING)
        c, b = by_status.get(st, (0, 0))
        by_status[st] = (c + 1, b + r.get("size_bytes", 0))
        total_bytes += r.get("size_bytes", 0)
    return {"total_files": len(records), "total_bytes": total_bytes, "by_status": by_status}
def print_status(repo_root=None, names=None):
    """
    Print a per-area status table read from existing manifests.

    :param repo_root: str, absolute repo root, or None to infer.
    :param names: list, specific area/manifest names, or None for all mirror areas.
    :return: None.
    """
    repo_root = repo_root or repo_root_default()
    if not names:
        names = manifest_names(repo_root=repo_root)
    print(f"{'area':<22} {'files':>7} {'MB':>8} {'pending':>8} {'uploaded':>9} {'verified':>9}")
    print("-" * 70)
    tot_files = tot_bytes = 0
    for name in names:
        records = read_manifest(manifest_path_for(name, repo_root))
        if not records:
            continue
        s = manifest_summary(records)
        bs = s["by_status"]
        pend = bs.get(STATUS_PENDING, (0, 0))[0]
        up = bs.get(STATUS_UPLOADED, (0, 0))[0]
        ver = bs.get(STATUS_VERIFIED, (0, 0))[0]
        print(f"{name:<22} {s['total_files']:>7,} {_fmt_mb(s['total_bytes']):>8} {pend:>8,} {up:>9,} {ver:>9,}")
        tot_files += s["total_files"]
        tot_bytes += s["total_bytes"]
    print("-" * 70)
    print(f"{'TOTAL':<22} {tot_files:>7,} {_fmt_mb(tot_bytes):>8}")

### S3 client (lazy boto3)
def _s3_client(region=DEFAULT_REGION):
    """
    Create a boto3 S3 client, importing boto3 lazily.

    :param region: str, AWS region name.
    :return client: boto3 S3 client.
    """
    import boto3
    return boto3.client("s3", region_name=region)
def s3_object_size(client, bucket, key):
    """
    Return the size of an S3 object, or None if it does not exist.

    :param client: boto3 S3 client.
    :param bucket: str, S3 bucket name.
    :param key: str, S3 object key.
    :return size: int size in bytes, or None if the object is absent.
    """
    from botocore.exceptions import ClientError
    try:
        resp = client.head_object(Bucket=bucket, Key=key)
        return resp["ContentLength"]
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            return None
        raise

### Upload
def upload_corpus(corpus, repo_root=None, execute=False, force=False, region=DEFAULT_REGION, save_every=25, verbose=True, path_prefix=None):
    """
    Upload a corpus's pending files to S3, recording sha256 and status.

    Dry run by default: with execute=False it prints the plan and writes nothing
    to S3 and does not modify the manifest. With execute=True it uploads each
    pending file, computes its sha256, and marks it uploaded, saving progress to
    the manifest periodically so the run is resumable.

    :param corpus: str, corpus folder name under data/.
    :param repo_root: str, absolute repo root, or None to infer.
    :param execute: bool, perform real S3 uploads when True; dry run when False.
    :param force: bool, re-upload files already marked uploaded/verified.
    :param region: str, AWS region name.
    :param save_every: int, save the manifest after this many uploads.
    :param verbose: bool, print per-file lines.
    :param path_prefix: str, optional repo_path prefix limiting the upload scope.
    :return summary: dict, counts of planned/uploaded/skipped/errors.
    """
    repo_root = repo_root or repo_root_default()
    # An area may source its files from outside this repo (e.g. ../corpus-tools for PII);
    # repo_path is stored relative to that scan_root, so resolve it to locate local files.
    scan_root = resolve_scan_root(area_spec_for(corpus, repo_root=repo_root), repo_root)
    mpath = manifest_path_for(corpus, repo_root)
    records = read_manifest(mpath)
    if not records:
        raise ValueError(f"No manifest found for corpus '{corpus}'. Build it first.")
    done_statuses = () if force else (STATUS_UPLOADED, STATUS_VERIFIED)
    todo = [r for r in records if r.get("status") not in done_statuses and (not path_prefix or r["repo_path"].startswith(path_prefix))]
    planned_bytes = sum(r["size_bytes"] for r in todo)
    mode = "EXECUTE" if execute else "DRY RUN"
    scope = f" under {path_prefix!r}" if path_prefix else ""
    print(f"[{mode}] upload area '{corpus}'{scope}: {len(todo):,} files, {_fmt_mb(planned_bytes)} MB to s3://{records[0]['s3_bucket']}/...")
    if not execute:
        for r in todo[:10]:
            print(f"  would upload {r['repo_path']}  ->  {r['s3_uri']}")
        if len(todo) > 10:
            print(f"  ... and {len(todo) - 10:,} more")
        print("  (dry run -- pass execute=True / --execute to perform the upload)")
        return {"planned": len(todo), "uploaded": 0, "skipped": 0, "errors": 0}
    client = _s3_client(region)
    uploaded = errors = 0
    since_save = 0
    for r in todo:
        abs_path = os.path.join(scan_root, r["repo_path"])
        try:
            if not os.path.exists(abs_path):
                raise FileNotFoundError(abs_path)
            r["sha256"] = sha256_file(abs_path)
            client.upload_file(abs_path, r["s3_bucket"], r["s3_key"])
            head = client.head_object(Bucket=r["s3_bucket"], Key=r["s3_key"])
            r["etag"] = head.get("ETag", "").strip('"')
            r["status"] = STATUS_UPLOADED
            r["uploaded_at"] = _now_iso()
            r["error"] = None
            uploaded += 1
            if verbose:
                print(f"  uploaded {r['repo_path']}  ({_fmt_mb(r['size_bytes'])} MB)")
        except Exception as e:
            r["status"] = STATUS_ERROR
            r["error"] = str(e)
            errors += 1
            print(f"  ERROR {r['repo_path']}: {e}")
        since_save += 1
        if since_save >= save_every:
            write_manifest(mpath, records)
            since_save = 0
    write_manifest(mpath, records)
    print(f"[done] uploaded {uploaded:,}, errors {errors:,}. Manifest: {mpath}")
    return {"planned": len(todo), "uploaded": uploaded, "skipped": 0, "errors": errors}

### Verify
def verify_corpus(corpus, repo_root=None, execute=False, sample=None, redownload=False, region=DEFAULT_REGION, verbose=True, path_prefix=None):
    """
    Verify uploaded objects exist in S3 with matching size, optionally checksumming.

    Confirms each uploaded record's object exists and its size matches the
    manifest. With redownload=True a sample (or all) of objects are downloaded
    to a temp file and their sha256 compared against the recorded checksum;
    matching records are marked verified.

    :param corpus: str, corpus folder name under data/.
    :param repo_root: str, absolute repo root, or None to infer.
    :param execute: bool, contact S3 when True; dry run when False.
    :param sample: int, number of records to deep-verify by re-download, or None for all.
    :param redownload: bool, re-download and checksum (slower, strongest check).
    :param region: str, AWS region name.
    :param verbose: bool, print per-file lines.
    :param path_prefix: str, optional repo_path prefix limiting the verification scope.
    :return summary: dict, counts of checked/verified/mismatched/missing.
    """
    repo_root = repo_root or repo_root_default()
    mpath = manifest_path_for(corpus, repo_root)
    records = read_manifest(mpath)
    candidates = [r for r in records if r.get("status") in (STATUS_UPLOADED, STATUS_VERIFIED) and (not path_prefix or r["repo_path"].startswith(path_prefix))]
    mode = "EXECUTE" if execute else "DRY RUN"
    scope = f" under {path_prefix!r}" if path_prefix else ""
    print(f"[{mode}] verify area '{corpus}'{scope}: {len(candidates):,} uploaded objects")
    if not execute:
        print("  (dry run -- pass execute=True / --execute to contact S3)")
        return {"checked": 0, "verified": 0, "mismatched": 0, "missing": 0}
    client = _s3_client(region)
    deep = candidates if sample is None else candidates[:sample]
    deep_ids = {id(r) for r in deep}
    checked = verified = mismatched = missing = 0
    for r in candidates:
        checked += 1
        remote_size = s3_object_size(client, r["s3_bucket"], r["s3_key"])
        if remote_size is None:
            missing += 1
            r["status"] = STATUS_ERROR
            r["error"] = "missing in S3 at verify time"
            print(f"  MISSING {r['s3_uri']}")
            continue
        if remote_size != r["size_bytes"]:
            mismatched += 1
            r["status"] = STATUS_ERROR
            r["error"] = f"size mismatch: s3={remote_size} local={r['size_bytes']}"
            print(f"  SIZE MISMATCH {r['s3_uri']}")
            continue
        if redownload and id(r) in deep_ids and r.get("sha256"):
            fd, tmp = tempfile.mkstemp(suffix=".verify")
            os.close(fd)
            try:
                client.download_file(r["s3_bucket"], r["s3_key"], tmp)
                if sha256_file(tmp) != r["sha256"]:
                    mismatched += 1
                    r["status"] = STATUS_ERROR
                    r["error"] = "sha256 mismatch on re-download"
                    print(f"  SHA MISMATCH {r['s3_uri']}")
                    continue
            finally:
                if os.path.exists(tmp):
                    os.remove(tmp)
        r["status"] = STATUS_VERIFIED
        r["verified_at"] = _now_iso()
        r["error"] = None
        verified += 1
        if verbose:
            print(f"  verified {r['repo_path']}")
    write_manifest(mpath, records)
    print(f"[done] verified {verified:,}, mismatched {mismatched:,}, missing {missing:,}. Manifest: {mpath}")
    return {"checked": checked, "verified": verified, "mismatched": mismatched, "missing": missing}

### Refresh (make S3 match local)
def refresh_corpus(corpus, repo_root=None, bucket=DEFAULT_BUCKET, key_prefix=DEFAULT_KEY_PREFIX, execute=False, prune=False, region=DEFAULT_REGION, verbose=True):
    """
    Make S3 match the current local state of a corpus: upload new/changed files.

    Re-scans the local corpus, re-uploads files that are new or changed (by size
    or mtime), and reports files that exist in S3 / the prior manifest but no
    longer exist locally. By default it is NON-destructive: removed files are
    kept in the manifest flagged 'local_missing', never deleted from S3. Deleting
    those S3 objects requires prune=True AND execute=True together. Dry run by
    default.

    :param corpus: str, corpus folder name under data/.
    :param repo_root: str, absolute repo root, or None to infer.
    :param bucket: str, target S3 bucket.
    :param key_prefix: str, S3 key prefix.
    :param execute: bool, apply changes (upload, and prune if requested); dry run when False.
    :param prune: bool, allow deleting S3 objects whose local file is gone (with execute).
    :param region: str, AWS region name.
    :param verbose: bool, print per-file lines.
    :return summary: dict, counts of upload/local_missing/pruned.
    """
    repo_root = repo_root or repo_root_default()
    spec = area_spec_for(corpus, repo_root=repo_root) or {"name": corpus, "path": f"data/{corpus}", "recursive": True, "respect_gitignore": False}
    scan_root = resolve_scan_root(spec, repo_root)
    bucket = spec.get("bucket", bucket)
    respect_gi = spec.get("respect_gitignore", True)
    include_globs = spec.get("include_globs")
    area_dir = os.path.join(scan_root, spec["path"])
    if not os.path.isdir(area_dir):
        raise ValueError(f"Area directory not found: {area_dir}")
    mpath = manifest_path_for(corpus, repo_root)
    prior = read_manifest(mpath)
    prior_index = index_by_repo_path(prior)
    local_rel = set(_posix_rel(p, scan_root) for p in iter_files(area_dir, recursive=spec["recursive"], respect_gitignore=respect_gi, scan_root=scan_root, include_globs=include_globs))
    removed = [r for r in prior if r["repo_path"] not in local_rel]
    new_rel = sorted(rel for rel in local_rel if rel not in prior_index)
    # Rebuild the manifest from local: new/changed -> pending, unchanged kept.
    records = build_area_manifest(spec["name"], spec["path"], repo_root=repo_root, bucket=bucket, key_prefix=key_prefix, compute_hash=False, recursive=spec["recursive"], respect_gitignore=respect_gi, include_globs=include_globs, scan_root=scan_root)
    pending = [r for r in records if r["status"] == STATUS_PENDING]
    mode = "EXECUTE" if execute else "DRY RUN"
    print(f"[{mode}] refresh area '{corpus}': {len(pending):,} to upload (new/changed), {len(removed):,} local-missing, prune={prune}")
    if not execute:
        for rel in new_rel[:10]:
            print(f"  new -> upload {rel}")
        changed = [r["repo_path"] for r in pending if r["repo_path"] not in set(new_rel)]
        for rel in changed[:10]:
            print(f"  changed -> re-upload {rel}")
        for r in removed[:10]:
            tag = "would PRUNE from S3" if prune else "kept as local_missing (use --prune to delete)"
            print(f"  local-missing: {r['s3_uri']}  ({tag})")
        print("  (dry run -- pass execute=True / --execute to apply)")
        return {"to_upload": len(pending), "local_missing": len(removed), "pruned": 0}
    # Execute: upload the pending (new/changed) files via the shared upload path.
    upload_corpus(corpus, repo_root=repo_root, execute=True, region=region, verbose=verbose)
    pruned = 0
    if removed:
        if prune:
            client = _s3_client(region)
            for r in removed:
                try:
                    client.delete_object(Bucket=r["s3_bucket"], Key=r["s3_key"])
                    pruned += 1
                    if verbose:
                        print(f"  pruned {r['s3_uri']}")
                except Exception as e:
                    print(f"  ERROR pruning {r['s3_uri']}: {e}")
            print(f"[done] pruned {pruned:,} object(s) from S3 (recoverable via bucket versioning).")
        else:
            # Keep removed objects visible in the manifest rather than silently orphaning them.
            records = read_manifest(mpath)
            for r in removed:
                r["status"] = STATUS_LOCAL_MISSING
                r["error"] = "present in S3 / prior manifest but no local file"
                records.append(r)
            write_manifest(mpath, records)
            print(f"[note] {len(removed):,} object(s) exist in S3 but not locally; kept as 'local_missing'. Use --prune to delete them from S3.")
    return {"to_upload": len(pending), "local_missing": len(removed), "pruned": pruned}

### CLI
def _build_arg_parser():
    """
    Build the argparse parser for the command-line interface.

    :return parser: argparse.ArgumentParser, the configured parser.
    """
    p = argparse.ArgumentParser(description="Mirror corpus-tools bulk areas (data/ + archive areas) to S3: manifest, upload, verify, refresh.")
    p.add_argument("--repo-root", default=None, help="Repo root (defaults to inferred).")
    p.add_argument("--bucket", default=DEFAULT_BUCKET, help=f"S3 bucket (default {DEFAULT_BUCKET}).")
    p.add_argument("--region", default=DEFAULT_REGION, help=f"AWS region (default {DEFAULT_REGION}).")
    sub = p.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="Build/refresh manifests. No name = all areas.")
    b.add_argument("--area", "--corpus", "--name", dest="name", default=None, help="Area/corpus name, or omit for all.")
    b.add_argument("--hash", action="store_true", help="Compute sha256 now (slow).")
    s = sub.add_parser("status", help="Print status table from existing manifests.")
    s.add_argument("--area", "--corpus", "--name", dest="name", default=None, help="Area/corpus name, or omit for all.")
    u = sub.add_parser("upload", help="Upload an area (dry run unless --execute). --all for everything.")
    u.add_argument("--area", "--corpus", "--name", dest="name", default=None, help="Area/corpus name.")
    u.add_argument("--all", action="store_true", help="Upload every area that has a manifest.")
    u.add_argument("--execute", action="store_true", help="Perform real uploads.")
    u.add_argument("--force", action="store_true", help="Re-upload already-uploaded files.")
    u.add_argument("--path-prefix", default=None, help="Limit work to manifest repo_path values beginning with this prefix.")
    v = sub.add_parser("verify", help="Verify an area's uploads (dry run unless --execute). --all for everything.")
    v.add_argument("--area", "--corpus", "--name", dest="name", default=None, help="Area/corpus name.")
    v.add_argument("--all", action="store_true", help="Verify every area that has a manifest.")
    v.add_argument("--execute", action="store_true", help="Contact S3 to verify.")
    v.add_argument("--sample", type=int, default=None, help="Deep-verify only N objects.")
    v.add_argument("--redownload", action="store_true", help="Re-download and checksum.")
    v.add_argument("--path-prefix", default=None, help="Limit work to manifest repo_path values beginning with this prefix.")
    r = sub.add_parser("refresh", help="Make S3 match local: upload new/changed (dry run unless --execute).")
    r.add_argument("--area", "--corpus", "--name", dest="name", required=True, help="Area/corpus name.")
    r.add_argument("--execute", action="store_true", help="Apply uploads (and prune if --prune).")
    r.add_argument("--prune", action="store_true", help="Delete S3 objects whose local file is gone (needs --execute).")
    return p
def _names_with_manifests(repo_root):
    """
    Return mirror-area names that currently have a manifest file on disk.

    :param repo_root: str, absolute repo root.
    :return names: list, area names with an existing manifest.
    """
    return manifest_names(repo_root=repo_root)
def main(argv=None):
    """
    Command-line entry point.

    :param argv: list, argument vector, or None to use sys.argv.
    :return code: int, process exit code.
    """
    args = _build_arg_parser().parse_args(argv)
    repo_root = args.repo_root or repo_root_default()
    if args.command == "build":
        if args.name:
            spec = area_spec_for(args.name, repo_root=repo_root) or {"name": args.name, "path": f"data/{args.name}", "recursive": True, "respect_gitignore": False}
            scan_root = resolve_scan_root(spec, repo_root)
            build_area_manifest(spec["name"], spec["path"], repo_root=repo_root, bucket=spec.get("bucket", args.bucket), compute_hash=args.hash, recursive=spec["recursive"], respect_gitignore=spec.get("respect_gitignore", True), include_globs=spec.get("include_globs"), scan_root=scan_root)
        else:
            build_all_manifests(repo_root=repo_root, bucket=args.bucket, compute_hash=args.hash)
    elif args.command == "status":
        names = [args.name] if args.name else None
        print_status(repo_root=repo_root, names=names)
    elif args.command == "upload":
        names = _names_with_manifests(repo_root) if args.all else [args.name]
        if not args.all and not args.name:
            print("upload needs --area NAME or --all")
            return 2
        for nm in names:
            upload_corpus(nm, repo_root=repo_root, execute=args.execute, force=args.force, region=args.region, path_prefix=args.path_prefix)
    elif args.command == "verify":
        names = _names_with_manifests(repo_root) if args.all else [args.name]
        if not args.all and not args.name:
            print("verify needs --area NAME or --all")
            return 2
        for nm in names:
            verify_corpus(nm, repo_root=repo_root, execute=args.execute, sample=args.sample, redownload=args.redownload, region=args.region, path_prefix=args.path_prefix)
    elif args.command == "refresh":
        refresh_corpus(args.name, repo_root=repo_root, bucket=args.bucket, execute=args.execute, prune=args.prune, region=args.region)
    return 0

### mrun execution stubs
def mrun_build_data_manifests():
    pass
#if __name__ == "__main__":
    build_data_manifests(compute_hash=False)
def mrun_upload_corpus_dry_run():
    pass
#if __name__ == "__main__":
    upload_corpus("education", execute=False)
def mrun_verify_corpus_dry_run():
    pass
#if __name__ == "__main__":
    verify_corpus("education", execute=False)
def mrun_refresh_corpus_dry_run():
    pass
#if __name__ == "__main__":
    refresh_corpus("education", execute=False)

if __name__ == "__main__":
    sys.exit(main())
# ===== END OF FILE primary/s3_archive.py =====
