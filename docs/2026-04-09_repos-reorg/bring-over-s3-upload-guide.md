file: bring-over-s3-upload-guide.md
title: S3 upload guide for bring-over operations
last-updated: 2026-07-05_0530
ai: Claude Code - Opus 4.6
session: `math-quiz bring-over (continued)`

**Superseded for agent use:** live procedure is [`skills/repo-ops/s3-archive-upload/README.md`](../../skills/repo-ops/s3-archive-upload/README.md). This file is kept as historical reference from the corpus-tools reorg.


## Purpose
Reusable guide for uploading bulk data from an imported repo to S3 during a bring-over operation. Uses the existing `core/s3_archive.py` module -- the ONLY approved method for S3 uploads in this monorepo.


## Critical rules

**DO NOT** install the AWS CLI to perform uploads.
**DO NOT** use direct `boto3` commands at the terminal.
**DO NOT** use `aws s3 sync`, `aws s3 cp`, or any other AWS CLI commands.
**ONLY** use the functions in `core/s3_archive.py` (build, upload, verify, refresh).
**NEVER** copy bulk data files into git-tracked paths -- they belong in S3.
All S3 writes are DRY RUN by default; real writes require `--execute`.


## Background
fof-mono's data model: code and manifests live in git; bulk data (media, session files, databases, corpora) lives in S3. The repo was deliberately pared down from 5+ GB to ~80 MB during the corpus-tools migration. Every bring-over must preserve this separation.

- **Bucket**: `[S3-FILES-BUCKET]` (private, us-west-2, Block Public Access ON, Versioning ON)
- **PII bucket**: `[S3-BUCKET]` (separate, stricter -- for user data with names, hashes, etc.)
- **Key scheme**: 1:1 with repo-relative paths, NO prefix. E.g. `apps/math-quiz/math_quiz_data/foo.json` -> `s3://[S3-FILES-BUCKET]/apps/math-quiz/math_quiz_data/foo.json`
- **Manifests**: per-area JSONL at `plans/2026-04-09_repos-reorg/s3_manifests/<area>.manifest.jsonl`
- **Module**: `core/s3_archive.py` -- handles manifest building, upload, verify, refresh. Stdlib-only core; boto3 imported lazily so manifests build and dry-run anywhere without credentials.

Reference docs:
- `plans/2026-04-09_repos-reorg/2026-06-01_s3-upload-prep.md` -- design doc for the original S3 migration
- `plans/2026-04-09_repos-reorg/2026-06-01_s3-upload-PUNCHLIST.md` -- original upload execution guide
- `AGENTS.md` -- "Data and S3" section


## Prerequisites
- fof-mono virtual environment active: `.venv/bin/python3` or `source .venv/bin/activate`
- AWS credentials configured locally (boto3 must reach `[S3-FILES-BUCKET]` bucket in us-west-2)
- Source repo checkout accessible (for copying data to staging location)
- **Cloud/remote sessions have NO AWS creds** -- the upload always runs locally via a punch-list the session creates. Only skip this if AWS creds are in the environment's secrets.


## Step-by-step workflow

### 1. Classify files during bring-over planning (Phase 3)
During the bring-over plan, classify each file/group using the disposition framework (`bring-over-code-playbook.md`):
- **REPO** -- source code, small configs, runtime assets
- **S3** -- bulk data, media, binaries, anything worth preserving that isn't source code
- **REBUILD-LOCAL** -- package installs, build output, caches (recreated from source)
- **DISCARD** -- superseded docs, legacy configs, duplicates

S3-disposition items typically include: session/performance data (JSON, CSV, DB), audio/video recordings (WAV, MP3, MP4), large datasets, model outputs.

**Key principle**: data files NEVER enter fof-mono's git tree. They go directly from the source repo to S3, with only a manifest tracked in git.

### 2. Add gitignore rules in fof-mono FIRST
BEFORE any data files touch the working tree, add gitignore rules so they can never be accidentally committed:

```gitignore
# <app-name>: bulk data lives in S3 (see s3_manifests/<area-name>.manifest.jsonl)
apps/<app-name>/<data-dir>/
```

Commit the gitignore change on the import branch. This is a safety net -- if the data directory already has a global ignore rule covering its file types (e.g. `*.wav`), the directory-level rule adds defense in depth for types that aren't globally ignored (e.g. `*.json`, `*.db`).

### 3. Add an area definition in core/s3_archive.py
Add an entry to the `EXTRA_AREAS` list in `core/s3_archive.py`:

```python
{"name": "<area-name>", "path": "apps/<app-name>/<data-dir>", "recursive": True, "respect_gitignore": False},
```

**Area naming convention**: underscore between fields, dash within multi-word field values. Examples:
- `math-quiz_data` (app: math-quiz, content: data)
- `kid-games_assets` (app: kid-games, content: assets)
- `robo-polly_recordings` (app: robo-polly, content: recordings)

Set `respect_gitignore=False` because the data files are intentionally gitignored but must still upload.

Commit the area definition on the import branch (but NOT any data files).

### 4. Stage the data files locally
Copy the S3-disposition files from the source repo into the gitignored target directory in fof-mono:

```bash
# Ensure you're on the source repo's main branch (where all data files exist)
cd <source-repo> && git checkout main

# Copy into fof-mono's gitignored data directory
cp -r <source-repo>/<data-dir>/* <fof-mono>/apps/<app-name>/<data-dir>/
```

Verify the files are gitignored -- `git status` in fof-mono should NOT show them as untracked.

**Why copy locally first?** The S3 key is derived from the repo-relative path. By placing files at `apps/<app-name>/<data-dir>/` in fof-mono, the keys naturally become `apps/<app-name>/<data-dir>/...` -- matching the 1:1 convention.

### 5. Build the manifest
```bash
.venv/bin/python3 core/s3_archive.py build --area <area-name>
```

This scans the local files and creates (or updates) the manifest at:
`plans/2026-04-09_repos-reorg/s3_manifests/<area-name>.manifest.jsonl`

Review the manifest to confirm:
- File paths are correct (repo-relative, using the NEW kebab-case app name)
- S3 keys match the repo-relative paths (1:1, no extra prefix)
- File count and total size match expectations

### 6. Dry-run upload
```bash
.venv/bin/python3 core/s3_archive.py upload --area <area-name>
```

No `--execute` = dry run. Prints what WOULD be uploaded. Review the output -- every line should show the source path and target S3 URI.

### 7. Execute upload
```bash
.venv/bin/python3 core/s3_archive.py upload --area <area-name> --execute
```

Real upload to S3. Files are uploaded with no public ACL (they inherit the private bucket policy). Resumable: if interrupted, re-run the same command -- already-uploaded files are skipped.

### 8. Verify
```bash
.venv/bin/python3 core/s3_archive.py verify --area <area-name> --execute --redownload --sample 10
```

Re-downloads a sample of 10 objects and verifies checksums against the manifest. Check for any errors in the output.

### 9. Check status
```bash
.venv/bin/python3 core/s3_archive.py status --area <area-name>
```

Should show all files as `verified`, 0 `pending_upload` or `error`.

### 10. Commit the manifest
```bash
git add plans/2026-04-09_repos-reorg/s3_manifests/<area-name>.manifest.jsonl
git commit -m "Add <area-name> S3 manifest after upload"
```

The manifest records every uploaded file's path, size, sha256, S3 URI, and status. This is the only artifact that enters the git tree.

### 11. Clean up local copies (optional)
Local data copies can be deleted after verification, or kept as a working cache. The s3_archive module never deletes local files automatically. The operator decides when to remove them.


## If something goes wrong
- **Upload failed (auth/network)**: re-check credentials (step in Prerequisites), then re-run. Already-uploaded files are skipped.
- **A few files show `error`**: re-upload with `--force`: `.venv/bin/python3 core/s3_archive.py upload --area <area-name> --execute --force`
- **Wrong keys or files uploaded**: the bucket has Versioning ON, so overwrites and deletes are recoverable. Fix the area config or manifest, then refresh.
- **Need to re-sync after edits**: use `refresh`: `.venv/bin/python3 core/s3_archive.py refresh --area <area-name> --execute`
- **Need to delete S3 objects for removed local files**: add `--prune` to refresh (recoverable via bucket versioning).


## Using the `root` parameter (advanced)
If the data must be scanned from a directory OUTSIDE fof-mono (e.g. a sibling repo), add `root` to the area spec:

```python
{"name": "<area-name>", "path": "<relative-path-within-root>", "recursive": True, "respect_gitignore": False, "root": "<path-to-external-dir>"},
```

**Warning**: with `root`, the S3 key is the path relative to THAT root, not relative to fof-mono. Ensure the resulting key matches the intended repo-relative path in fof-mono. The recommended approach (Step 4 above) avoids this complexity by staging files inside fof-mono.


## PII handling
Files containing PII (user names, email addresses, hash logs) go to the `[S3-BUCKET]` bucket, not `[S3-FILES-BUCKET]`. Use PII_AREAS in `core/s3_archive.py` (they are deliberately excluded from `--all` operations to prevent accidental cross-bucket uploads). See the PII_AREAS definition and `AGENTS.md` for details.
