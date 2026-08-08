file: skills/repo-ops/s3-archive-upload/README.md
title: S3 archive upload — build, upload, and verify manifests
source-github-url: original
source-guide-url: original
history:
  - 2026-08-06 · Randy · Codex — add path-scoped upload and verification for mixed pending manifests
  - 2026-07-07 · Randy · Cursor — content-hash change detection: mtime-only changes no longer trigger re-upload; see `build`/`refresh` notes below
  - 2026-07-05 · Randy · Cursor [Relocate S3 manifests plan](2026-07-05_ops_relocate-s3-manifests) — initial skill; converted from plans/2026-04-09_repos-reorg/bring-over-s3-upload-guide.md; manifest path now `manifests/`


**Use this skill when uploading bulk data to S3, creating a new per-area manifest, or onboarding a bring-over app's data.** This is the **only** approved upload path in fof-mono — never AWS CLI, never raw terminal `boto3`, never `aws s3 sync`/`cp`.


## When to use
- Bring-over operation has files classified as **S3** disposition (bulk data, media, session DBs, corpora).
- A new app or area needs its first `manifests/<area>.manifest.jsonl`.
- Re-upload, verify, or refresh an existing area after local edits or failed uploads.
- Stellar-transcriber or other apps need eval/support files uploaded under a new manifest area.

Do **not** run `build` or `refresh` on `exchanges/` areas without explicit user confirmation (see `AGENTS.md` → Data and S3).


## Critical rules
- **ONLY** use `core/s3_archive.py` subcommands: `build`, `upload`, `verify`, `refresh`, `status`.
- **NEVER** copy bulk data into git-tracked paths — data belongs in S3; only manifests enter git.
- All S3 writes are **dry run by default**; real writes require `--execute`.
- PII → `[S3-BUCKET]` bucket via `PII_AREAS` in `core/s3_archive.py`, not `[S3-FILES-BUCKET]`.


## Background
- **Bucket**: `[S3-FILES-BUCKET]` (private, us-west-2, Block Public Access ON, Versioning ON)
- **PII bucket**: `[S3-BUCKET]` (user names, hash logs, etc.)
- **Key scheme**: 1:1 with repo-relative paths, no prefix — e.g. `apps/math-quiz/math_quiz_data/foo.json` → `s3://[S3-FILES-BUCKET]/apps/math-quiz/math_quiz_data/foo.json`
- **Manifests**: per-area JSONL at `manifests/<area>.manifest.jsonl`
- **Module**: `core/s3_archive.py` — stdlib-only core; boto3 imported lazily for upload/verify

Reference docs:
- `manifests/s3_archive_manifest_README.md` — legacy area-level manifest schema (reference)
- `docs/2026-04-09_repos-reorg/2026-06-01_s3-upload-prep.md` — original S3 migration design
- `AGENTS.md` — "Data and S3" section


## Prerequisites
- fof-mono virtual environment: `.venv/bin/python3` or `source .venv/bin/activate`
- AWS credentials configured locally (boto3 must reach `[S3-FILES-BUCKET]` in us-west-2)
- Source data accessible (source repo checkout or already staged locally)
- **Cloud/remote sessions have NO AWS creds** — create a punch-list for the user to run locally unless creds are in environment secrets


## Step-by-step workflow


### 1. Classify files during planning
During bring-over or feature planning, classify each file/group:
- **REPO** — source code, small configs, runtime assets
- **S3** — bulk data, media, binaries, anything worth preserving that is not source code
- **REBUILD-LOCAL** — package installs, build output, caches
- **DISCARD** — superseded docs, legacy configs, duplicates

S3-disposition items: session/performance data (JSON, CSV, DB), audio/video (WAV, MP3, MP4), large datasets, model outputs.

**Key principle**: data files never enter fof-mono's git tree. They go from source to S3; only the manifest is committed.


### 2. Add gitignore rules FIRST
Before data files touch the working tree:

```gitignore
# <app-name>: bulk data lives in S3 (see manifests/<area-name>.manifest.jsonl)
apps/<app-name>/<data-dir>/
```

Commit the gitignore change. Directory-level rules add defense in depth beyond global type ignores.


### 3. Add an area definition in core/s3_archive.py
Add an entry to `EXTRA_AREAS`:

```python
{"name": "<area-name>", "path": "apps/<app-name>/<data-dir>", "recursive": True, "respect_gitignore": False},
```

**Area naming**: underscore between fields, dash within multi-word values — e.g. `math-quiz_data`, `stellar-eval_m3b-five-review`.

Set `respect_gitignore=False` when data is intentionally gitignored but must still upload.

Commit the area definition (not the data files).


### 4. Stage the data files locally
Copy S3-disposition files into the gitignored target directory:

```bash
cd <source-repo> && git checkout main
cp -r <source-repo>/<data-dir>/* <fof-mono>/apps/<app-name>/<data-dir>/
```

Verify with `git status` — files must not appear as untracked.

Staging inside fof-mono ensures S3 keys match repo-relative paths naturally.


### 5. Build the manifest
```bash
.venv/bin/python3 core/s3_archive.py build --area <area-name>
```

Creates or updates `manifests/<area-name>.manifest.jsonl`. Review:
- Repo-relative paths use the correct app naming (kebab-case)
- S3 keys match paths 1:1 (no extra prefix)
- File count and total size match expectations

**Change detection:** `build` and `refresh` compare **content** (sha256), not mtime alone. Copying or reorganizing files updates the file modification timestamp but does not queue a re-upload when the stored hash matches. Only new paths or files whose bytes changed become `pending_upload`. Expect a local sha256 pass over files whose size or mtime differs from the manifest — that is normal and much cheaper than re-uploading unchanged bulk data.


### 6. Dry-run upload
```bash
.venv/bin/python3 core/s3_archive.py upload --area <area-name>
```

No `--execute` = dry run. Review every source path and target S3 URI.

If a shared area has unrelated pending records, limit both upload and verification to an exact repo-relative prefix:

```bash
.venv/bin/python3 core/s3_archive.py upload --area <area-name> --path-prefix data/<area>/<in-scope-path>/
```

Review the full manifest first. Use the narrowest prefix that contains the authorized files; out-of-prefix records remain unchanged and visible in status.


### 7. Execute upload
```bash
.venv/bin/python3 core/s3_archive.py upload --area <area-name> --execute
```

For a scoped upload, repeat the same `--path-prefix` and add `--execute`.

Resumable: re-run skips already-uploaded files. No public ACL — private bucket policy applies.


### 8. Verify
```bash
.venv/bin/python3 core/s3_archive.py verify --area <area-name> --execute --redownload --sample 10
```

Re-downloads a sample and checks checksums against the manifest.

For a scoped upload, repeat the same `--path-prefix` during verification so the reported object count and checksum sample cover the intended subset.


### 9. Check status
```bash
.venv/bin/python3 core/s3_archive.py status --area <area-name>
```

Normally expect all files `verified`, 0 `pending_upload` or `error`. After an intentionally scoped upload, out-of-prefix pending records remain visible and must be reported rather than silently uploaded.


### 10. Commit the manifest
```bash
git add manifests/<area-name>.manifest.jsonl
git commit -m "feat(<app>): add <area-name> S3 manifest after upload"
```

Use scoped conventional commits per `AGENTS.md`. The manifest is the only artifact that enters git.


### 11. Clean up local copies (optional)
Local data copies can be deleted after verification or kept as cache. `s3_archive` never deletes local files automatically.


## If something goes wrong
- **Upload failed (auth/network)**: re-check credentials, re-run upload — already-uploaded files are skipped.
- **A few files show `error`**: `.venv/bin/python3 core/s3_archive.py upload --area <area-name> --execute --force`
- **Wrong keys uploaded**: bucket has Versioning ON — fix area config or manifest, then `refresh`.
- **Re-sync after local edits**: `.venv/bin/python3 core/s3_archive.py refresh --area <area-name> --execute`
- **Many pending files after copy/reorg but content unchanged**: run `build --area <area-name>` (or `refresh` dry-run first). Mtime-only changes are ignored when sha256 matches; pending count should drop to genuinely new/changed files only.
- **Delete S3 objects for removed local files**: add `--prune` to refresh (recoverable via versioning).


## Using the `root` parameter (advanced)
Scan from a directory outside fof-mono:

```python
{"name": "<area-name>", "path": "<relative-path-within-root>", "recursive": True, "respect_gitignore": False, "root": "<path-to-external-dir>"},
```

**Warning**: with `root`, the S3 key is relative to that root, not fof-mono. Prefer staging inside fof-mono (Step 4) to avoid key mismatches.


## PII handling
Files with PII go to `[S3-BUCKET]`, not `[S3-FILES-BUCKET]`. Use `PII_AREAS` in `core/s3_archive.py` (excluded from `--all` operations). See `AGENTS.md` for details.
