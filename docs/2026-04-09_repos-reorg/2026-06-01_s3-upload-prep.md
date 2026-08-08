file: 2026-06-01_s3-upload-prep.md
title: S3 upload prep -- tooling, plan, workflow, and working-tree cleanup

## Purpose
Everything needed to upload the bulk corpus files to S3 before the cutover, with nothing uploaded yet. This branch (`claude/s3-upload-prep-19Hfb`) is off `main`, where `data/` and the other bulk dirs are intact on disk. The companion run-list is `2026-06-01_s3-upload-PUNCHLIST.md`; the excluded items are in `2026-06-01_excluded-from-carryover.md`.

This doc consolidates the earlier `s3-upload-prep` and `s3-upload` notes into one.


## What was added
- `primary/s3_archive.py` — module that manages the manifest, upload, verify, and refresh. Companion to `primary/aws.py`. Stdlib-only core; `boto3` imported lazily so manifests build and dry-run anywhere without credentials.
- `plans/2026-04-09_repos-reorg/s3_manifests/<area>.manifest.jsonl` — one per-file manifest per area: every `data/` corpus + `data/` root files, plus `logs/` and `_archive/`. Size + mtime + path; sha256 filled at upload.
- `2026-06-01_s3-upload-PUNCHLIST.md` — the step-by-step you run locally, then merge to `main`.
- `2026-06-01_excluded-from-carryover.md` — the consolidated list of dirs not carried forward / not uploaded.
- `s3_archive_manifest.jsonl` + `_README.md` — the original high-level area manifest from `pare-down`, kept as reference.
- `tests/test_s3_archive.py` — unit tests (keys, hashing, manifest build/merge, dry-run vs execute, refresh). All passing.


## How the module works
Two manifest layers: the high-level `s3_archive_manifest.jsonl` (one row per area, from pare-down) and the per-file `s3_manifests/<area>.manifest.jsonl` (what upload/verify actually operate on). Per-file fields: `repo_path`, `corpus`, `size_bytes`, `mtime`, `sha256`, `s3_bucket`, `s3_key`, `s3_uri`, `status`, `uploaded_at`, `verified_at`, `etag`, `error`.

Bucket: `[S3-FILES-BUCKET]` — PRIVATE (Block Public Access on), `us-west-2`. Named "files" not "archive" because these are active/live files. Key scheme mirrors repo paths 1:1, e.g. `data/education/foo.md` → `s3://[S3-FILES-BUCKET]/data/education/foo.md`. Bucket + prefix (prefix is empty) are one constant block at the top of the module.

Safety properties:
- Upload, verify, and refresh are DRY RUN by default; real S3 writes require `--execute`.
- Objects upload with no public ACL — they inherit the private bucket, never world-readable.
- Rebuilding a manifest preserves prior `sha256`/`status` for unchanged files (same size + mtime), so uploads are resumable/idempotent.
- sha256 computed and recorded at upload; verify re-checks size and can re-download a sample to compare checksums.
- The module never deletes local files. `refresh --prune` deletes S3 objects whose local file is gone, only with `--execute`, and those deletes are recoverable via bucket versioning.


## Usage (locally, in the venv)
```
.venv/bin/python3 primary/s3_archive.py build                 # build/refresh all manifests
.venv/bin/python3 primary/s3_archive.py status                # per-area status table
.venv/bin/python3 primary/s3_archive.py upload --area education            # dry run
.venv/bin/python3 primary/s3_archive.py upload --area education --execute  # real upload
.venv/bin/python3 primary/s3_archive.py verify --area education --execute --redownload --sample 20
.venv/bin/python3 primary/s3_archive.py upload --all --execute   # upload every area
.venv/bin/python3 primary/s3_archive.py verify --all --execute --redownload --sample 25
# After editing a folder later, re-sync local -> S3:
.venv/bin/python3 primary/s3_archive.py refresh --area education --execute        # uploads new/changed
.venv/bin/python3 primary/s3_archive.py refresh --area education --execute --prune # also delete S3 orphans
```
First real upload: a small area like `education` (66 MB) to validate bucket/creds/round-trip before the big ones (`floodlamp` 2,157 MB, `pv` 1,801 MB, `deutsch` 962 MB).


## Refresh: making S3 match local after edits
`refresh` re-scans an area, compares against the manifest by size + mtime, then uploads new/changed files, leaves unchanged ones, and reports files in S3 but no longer local. Non-destructive by default: removed files are flagged `local_missing`, never deleted. Deleting those S3 objects needs `--prune` AND `--execute`. A rename = one new upload + one `local_missing` (old key), so `--prune` cleans up old keys after renaming.


## Recovery: undoing a mistaken delete/overwrite on S3
Strongest first:
- S3 Versioning (REQUIRED on `[S3-FILES-BUCKET]`): a delete writes a delete-marker over the old version; an overwrite keeps the prior version. Recover by removing the delete-marker or copying the previous version back. This is the real net for "deleted on S3, no local copy." Turn it on before the first upload.
- The manifest in git records every object (key + sha256 + size); `git log` on it shows what existed at any past commit.
- Normal case: these are active files you usually also have locally, and `main` still has the original `data/`. Local + git is the primary backup; versioning covers the "only in S3" edge case.
- Optional hardening: MFA Delete, and/or a lifecycle rule keeping noncurrent versions 30–90 days.

Bottom line: with Versioning on, a mistaken `--prune` is fully reversible.


## Local working-tree cleanup (.gitignore for pare-down leftovers)
When you switch to this branch from `pare-down`, Cursor shows a dirty tree (~461 untracked files in 6 folders): `apps/`, `web-shared/`, and four `_archive/` subdirs (`aws_chalice`, `dependencies`, `docs-vis`, `secondary`). These are NOT created by this branch and NOT in any commit:
- `apps/` and `web-shared/` are your pare-down reorg folders (535 + 147 files committed on `pare-down`). Switching to `main` removed their tracked content but left behind the gitignored bits inside (mostly Chalice `.chalice/deployments/` deploy-state and old archived copies), so the folder shells linger.
- The `_archive/` subdirs are old archived copies that were gitignored on pare-down and never committed.

Why 6 lines (not 3): `git status` collapses a fully-untracked dir to one line (`apps/`, `web-shared/`), but `_archive/` contains tracked files too, so git descends and lists each untracked child — hence 4 `_archive/*` entries + 2 = 6.

Fix applied on this branch: a commented section was added to `.gitignore` listing those 6 paths, so the working tree is clean WITHOUT deleting the local files (do NOT `git clean` — it would also wipe un-uploaded local data stashes). The real reorg content stays committed on `pare-down`, the cutover source. These ignore rules are specific to frozen `main` and don't propagate to `fof-mono` (assembled separately).


## Future S3-backed data workflow (post-cutover)
After the bulk upload, S3 is the source of truth; local copies are caches; the manifest is the index (S3 URI, size, sha256, date).
- Day-to-day: a download script reads the manifest, pulls the files you want into `data/<area>/`, verifies sha. You work as today (Cursor, scripts pointed at folders). Read-only = nothing to do; modified/new = re-upload, recompute sha, update + commit the manifest row.
- Collaborator sync (you and EA): the repo only carries manifest changes; files travel through S3. A sha/last_modified mismatch on pull triggers a re-pull. PII goes to `[S3-BUCKET]` with stricter access.
- A small CLI (`corpus pull/push/status`) belongs as an app in the new repo — build it after the bulk upload lands.
- Cross-window at cutover: Window 1 = frozen `corpus-tools` (on `main`, full history + original files as fallback); Window 2 = `fof-mono` (catalog only; data files gray because gitignored, appear when downloaded). To upload a file not yet in S3: find it in Window 1, run the upload script from Window 2 pointed at its absolute path, commit the manifest update in `fof-mono`.


## Additional pre-cutover streams NOT yet in the tooling
The current `s3_archive.py` covers `data/` + `logs/` + `_archive/`. Excluded (frozen `main` only): `langchain-layer/` and the dirs in `2026-06-01_excluded-from-carryover.md`. Two other pre-cutover streams were flagged in the pare-down notes and are NOT yet automated — decide whether to fold them in before/with this upload:
1. Selected QRAG exchanges → S3 (PRE-cutover). Curated list at `apps/qrag/selected_exchanges_manifest.md`: `exchanges/qrag_deutsch`, `qrag_deutsch_early`, `qrag_fda-c19-townhalls`, `qrag_pv-evac`, `qrag_sovereign-child`, plus `response_files/` (~680 files). Note: `apps/` lives on `pare-down`, not on this branch.
2. PII files → `[S3-BUCKET]` (separate, stricter bucket). `exchanges/pii_user_hash_log_2024-12-17.csv` (+ `_test.csv`), every `pii-exchanges_<corpus>.db`, and the hash logs under `web-shared/aws_chalice/hash-store/user_hash_log_*.csv`.

If you want these covered, I can add an `exchanges` area and a `[S3-BUCKET]`/PII target to the module. Flagged here so they aren't forgotten.


## Background: why `data/` looked divergent on pare-down (resolved)
On `pare-down`, `data/` appeared mostly empty because (a) pare-down ran `git rm --cached` (untracked, didn't delete) and rewrote `.gitignore` to ignore `data/`, and (b) the contents of `pv/`, `deutsch/`, etc. were physically removed from disk around 2026-05-25 (a manual/sync cleanup; directory mtimes confirm the timing). This does NOT affect us: we upload from `main`, where `data/` is fully intact (9,842 files / 5.6 GB confirmed). The pare-down-only local stashes `data/0_gitignore/` (6.1 GB) and `data/audio_0_pv_gitignore/` (1.7 GB) do not exist on `main`; if their bulk audio isn't already inside `data/pv/` on `main`, it needs its own decision.


## Mirror inventory (from the generated manifests)
| area | files | MB |
| --- | --- | --- |
| floodlamp | 5,496 | 2,157 |
| pv | 960 | 1,801 |
| deutsch | 2,916 | 962 |
| misc_transcripts | 167 | 516 |
| logs | 279 | 535 |
| _archive | 287 | 285 |
| sovereign-child | 178 | 172 |
| education | 57 | 66 |
| pdfs_dev | 27 | 17 |
| programming | 3 | 11 |
| (data: 10 smaller corpuses + root files) | ~51 | ~5 |
| TOTAL (20 areas) | 10,408 | 6,524 |

Excluded / not uploaded (stay only in frozen `main`): `ms-graphrag/`, `_misc_to_be_sorted/`, `limbo/`, `lancedb/`, `pretrained_models/`, `web/aws_chalice/langchain-layer/`, root junk. See `2026-06-01_excluded-from-carryover.md`.


## Decisions / open items
1. Bucket: DECIDED — `[S3-FILES-BUCKET]`, private, `us-west-2`. Action: create it and turn ON Versioning before the first upload.
2. Reorg-as-upload: DECIDED — no reorg before cutover; S3 mirrors repo paths 1:1.
3. Storage class: DECIDED — S3 Standard only, no Glacier.
4. PII bucket: confirm `[S3-BUCKET]` for the PII stream above (if doing it now).
5. Exchanges + PII streams: decide whether to automate them into the module now or handle post-cutover.
6. Bring-back: which small canonical `data/` files (dictionaries, `names.md`, style guides) to keep in the repo vs archive-only.
7. floodlamp is mixed code + documents — wholesale archive (current) or filter code out? I can add an include/exclude filter.


## Sync / cutover model
`pare-down` stays FROZEN — nothing mirrored back into it. This branch merges into `main` via PR. The new `fof-mono` repo is assembled from two sources: the `pare-down` snapshot, and a subset of `main` (the s3_archive code + manifests + these docs). So the S3 code lives in one place, not duplicated into `pare-down`. The repo-reorg markdown pulled from `pare-down` is here purely as context.
