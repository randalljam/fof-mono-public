file: 2026-06-01_s3-upload-PUNCHLIST.md
title: S3 upload punch list -- run on main (after PR merge), overnight

## Read me first
The PR merges this branch into `main`. Everything below you run **on `main`**, locally, in your venv. The cloud session can't run the upload (no AWS creds there), so this is yours to drive. It's organized to **kick off the full upload before bed and confirm in the morning** -- no separate test step.

Scope: S3 becomes a 1:1 mirror of the local paths for the 20 areas worth keeping -- all `data/` corpuses + `data/` root files, plus `logs/` and `_archive/`. **Total ~10,400 files / ~6.52 GB.**

NOT in this upload (decide later, see prep doc): the `exchanges/` QRAG stream and the PII -> `[S3-BUCKET]` stream. Excluded entirely (frozen `main` only): `ms-graphrag/`, `_misc_to_be_sorted/`, `limbo/`, `lancedb/`, `pretrained_models/`, `web/aws_chalice/langchain-layer/`, root junk -- see `2026-06-01_excluded-from-carryover.md`.


## Tonight -- before bed
1. [x] Merge the PR into `main` (GitHub), then locally:
   `git checkout main && git pull origin main`
2. [x] Create the bucket `[S3-FILES-BUCKET]` in `us-west-2`, PRIVATE:
   - Block Public Access: ON (all four)
   - Bucket Versioning: ON  <-- your recovery net for accidental deletes/overwrites
3. [x] Pre-flight (instant -- confirms creds + that the bucket is reachable; do NOT skip, it's what keeps the overnight run from failing on a typo):
   `.venv/bin/python3 -c "import boto3; print([b['Name'] for b in boto3.client('s3').list_buckets()['Buckets']])"`
   You should see `[S3-FILES-BUCKET]` in the list.
4. [x] Sanity-check the manifests + plan (no writes):
   `.venv/bin/python3 primary/s3_archive.py status`
   [skipped] `.venv/bin/python3 primary/s3_archive.py upload --all`   # dry run -- prints the full plan
5. [x] Kick off the real upload + verify, kept awake and logged:
   ```
   caffeinate -i bash -c '.venv/bin/python3 primary/s3_archive.py upload --all --execute && .venv/bin/python3 primary/s3_archive.py verify --all --execute --redownload --sample 10' 2>&1 | tee ~/s3_upload_$(date +%F).log
   ```
   - `caffeinate -i` stops idle sleep. **Keep the laptop plugged in with the lid open** (closing the lid still sleeps).
   - Watch the first ~30 seconds: the first area (`audio_inbox`, ~1 MB) should print `uploaded ...` lines. Once you see uploads happening with no auth error, go to bed.
   - It's resumable: if anything interrupts it, just re-run the same command -- already-uploaded files are skipped.


## In the morning -- confirm
6. [no file] Read the tail of the log for the final per-area `[done] uploaded ... verified ...` lines:
   `tail -40 ~/s3_upload_$(date +%F).log`   (use yesterday's date if it rolled past midnight)
7. [x] Status table -- expect files = verified for every area, 0 pending/errors:
   `.venv/bin/python3 primary/s3_archive.py status`
8. [NA] If any area shows `error`/pending (e.g. a network blip): re-run for just that area, then re-verify:
   `.venv/bin/python3 primary/s3_archive.py upload --area <name> --execute --force`
   `.venv/bin/python3 primary/s3_archive.py verify --area <name> --execute --redownload --sample 10`
9. Commit the updated manifests to `main` (they now carry sha256 + uploaded/verified status) and push:
   `git add plans/2026-04-09_repos-reorg/s3_manifests`
   `git commit -m "Record S3 upload results in manifests"`
   `git push origin main`
10. Done: `[S3-FILES-BUCKET]` mirrors everything worth keeping. Local files are untouched -- delete later only when you choose (the tool never deletes local files).


## If something goes wrong
- Whole run failed immediately at step 5: almost always creds or a wrong/missing bucket -- re-check step 3, fix, re-run. Nothing partial was lost.
- A few files show `error` in `status`: handled by step 8 (re-upload --force that area).
- Accidental delete/overwrite on S3 later with no local copy: restore from S3 Versioning (remove the delete-marker or copy back the prior version). The manifest in git tells you the expected key + sha256.
- Do NOT run `git clean` / "Discard all" -- it would wipe your un-uploaded local data stashes.


## Useful single-area commands
- Dry run (no writes): drop `--execute` from any upload/verify/refresh.
- One area: `upload --area logs --execute`, `verify --area logs --execute`.
- After editing a folder later: `refresh --area education --execute` (uploads new/changed; add `--prune` to delete S3 objects whose local file is gone -- recoverable via versioning).


## Sync / cutover model
`pare-down` stays FROZEN -- nothing mirrored back. The new `fof-mono` repo is assembled from two sources: the `pare-down` snapshot, and a subset of `main` (the s3_archive code + manifests + these docs). So the S3 code lives in one place, not duplicated into `pare-down`. The repo-reorg markdown pulled from `pare-down` is here purely as context.
