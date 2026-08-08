file: 2026-06-01_excluded-from-carryover.md
title: Excluded from carry-over -- not in the new repo, not uploaded to S3

## What this is
A single consolidated list of directories and files that are NOT carried into the new repo (fof-mono) and NOT uploaded to S3. They stay only in the frozen `corpus-tools` `main` checkout, which remains on disk as a reference snapshot after cutover. Nothing here is deleted -- it just isn't carried forward.

This replaces the earlier split between "off-limits" and "discard" categories; they are all the same thing: pared out, not worth carrying forward. Sizes are as observed on the `claude/s3-upload-prep-19Hfb` branch (off `main`).


## Excluded items
| path | size | files | what it was / why not carried |
| --- | --- | --- | --- |
| `ms-graphrag/` | 251 MB | 3,585 | Vendored Microsoft GraphRAG experiment. Not an active project; reproducible from upstream if ever needed. Off-limits per AGENTS.md. |
| `_misc_to_be_sorted/` | 41 MB | 12 | Catch-all of unsorted files that never got triaged. Off-limits per AGENTS.md. If anything here turns out to matter, pull it from frozen `main`. |
| `limbo/` | 28 KB | 4 | Tiny holding area for files mid-decision. Off-limits per AGENTS.md. |
| `lancedb/` | 12 MB | 6 | Local LanceDB vector-store state. Reproducible by re-indexing; no need to preserve. |
| `pretrained_models/` | 28 KB | 0 | Empty in the tree; model weights are downloaded on demand at runtime. |
| `<root junk>` | ~1 MB | ~9 | Scratch/backup files: `=`, `scratch.py`, `scratch.md`, `temp.json`, `test_audio_nova2gen.json`, `Default.code-profile`, `settings COPY TO USER SETTINGS.json`, `token.pickle`, `.sesskey`. All scratch or already in git history. |
| `web/aws_chalice/langchain-layer/` | 128 MB | 4,000 | Built Lambda layer (incl. macOS .dylib). Rebuildable from requirements.txt; not worth uploading. |


## What IS uploaded to S3 (for contrast)
Everything worth keeping goes to the private `[S3-FILES-BUCKET]` bucket: all of `data/` (corpuses + root files), plus `logs/` and `_archive/`. See `2026-06-01_s3-upload-prep.md` and the punch list.


## If you change your mind on any item
To upload one of these later, add it to `EXTRA_AREAS` in `primary/s3_archive.py` (one line: name, path, recursive) and run `build --area <name>` then `upload --area <name> --execute`. Nothing about excluding it now is irreversible -- the files remain in frozen `main`.
