file: skills/repo-ops/local-files-snapshot-backup/README.md
title: Local files snapshot backup
source-github-url: original
source-guide-url: original
history:
  - 2026-06-30 · Randy · Cursor [Local Files Backup](original) — created interim ZIP-to-S3 workflow for `_LOCAL_FILES/fof-mono`


**Use this skill to create an interim ZIP snapshot backup of `/Users/randytrue/Documents/Code/_LOCAL_FILES/fof-mono` and upload it to S3.**


## When to use
- The user asks to back up `_LOCAL_FILES`, local-only data, symlinked local files, or the fof-mono local files folder.
- The user wants a simple manual snapshot before a more robust backup system such as restic or kopia is set up.
- The user asks for the nightly/manual ZIP backup to S3.


## What it does
The script creates a ZIP named:
```text
_LOCAL_FILES_fof-mono_backup_YYYY-MM-DD_HHMM.zip
```
The timestamp is Pacific time (`America/Los_Angeles`).

By default, the ZIP is staged locally under:
```bash
/Users/randytrue/Documents/Code/_LOCAL_FILES/fof-mono/_backup-zips/
```
That folder starts with `_`, so it is excluded from future snapshots.

The upload destination is:
```bash
s3://[S3-FILES-BUCKET]/_LOCAL_FILES_fof-mono_backup/
```


## Exclusions
The script excludes top-level directories in `_LOCAL_FILES/fof-mono` whose names begin with `_`, including:
```text
_archive/
_sync-backups/
_backup-zips/
```


## Run
From the fof-mono repo root:
```bash
.venv/bin/python3 scripts/local_files_snapshot_backup.py
```

Create the ZIP without uploading:
```bash
.venv/bin/python3 scripts/local_files_snapshot_backup.py --skip-upload
```

Create the ZIP and print the AWS upload command without uploading:
```bash
.venv/bin/python3 scripts/local_files_snapshot_backup.py --dry-run-upload
```

Upload and remove the local ZIP after success:
```bash
.venv/bin/python3 scripts/local_files_snapshot_backup.py --delete-local-after-upload
```


## Requirements
- Run with the project virtual environment: `.venv/bin/python3`.
- The AWS CLI must be installed and authenticated for uploads.
- The active AWS identity must be able to write to `s3://[S3-FILES-BUCKET]/_LOCAL_FILES_fof-mono_backup/`.


## Scheduling
Prefer macOS `launchd` over classic cron for local nightly backups. `launchd` is the native scheduler, works better with per-user jobs, and can run a missed calendar job after the Mac wakes. It does not normally wake a fully sleeping Mac just to run this script; if the Mac is asleep at 2am, expect the job to run after wake rather than exactly at 2am.

Recommended command for a nightly job:
```bash
cd /Users/randytrue/Documents/Code/fof-mono && .venv/bin/python3 scripts/local_files_snapshot_backup.py --delete-local-after-upload
```

Use classic cron only for a quick temporary setup on a machine that is usually awake at the scheduled time:
```cron
0 2 * * * cd /Users/randytrue/Documents/Code/fof-mono && .venv/bin/python3 scripts/local_files_snapshot_backup.py --delete-local-after-upload >> /Users/randytrue/Documents/Code/_LOCAL_FILES/fof-mono/_backup-zips/nightly.log 2>&1
```


## Reporting back
After running, tell the user:
- The ZIP path.
- The number of files and source bytes included.
- The S3 URI uploaded to, or that upload was skipped/dry-run.
- Whether the local ZIP was kept or deleted.

Do not describe this as a complete long-term backup/versioning solution. It is an interim snapshot workflow until a deduplicated backup tool such as restic or kopia is configured.
