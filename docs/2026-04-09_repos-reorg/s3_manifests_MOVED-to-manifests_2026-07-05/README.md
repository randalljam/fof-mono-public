file: plans/2026-04-09_repos-reorg/s3_manifests_MOVED-to-manifests_2026-07-05/README.md
title: S3 manifests relocated to manifests/

The S3 manifest catalog moved out of this reorg folder on 2026-07-05 (branch `refactor/manifests-relocation`, parent `stellar-transcriber-start`).

## What moved

| Old path | New path |
| --- | --- |
| `plans/2026-04-09_repos-reorg/s3_manifests/*.manifest.jsonl` | `manifests/*.manifest.jsonl` |
| `plans/2026-04-09_repos-reorg/s3_archive_manifest.jsonl` | `manifests/s3_archive_manifest.jsonl` |
| `plans/2026-04-09_repos-reorg/s3_archive_manifest_README.md` | `manifests/s3_archive_manifest_README.md` |

## What did not move

- `core/s3_archive.py` — operational library; `MANIFEST_SUBDIR` now points to `manifests/`.
- Dated docs in `plans/2026-04-09_repos-reorg/` — left as historical records; agents should use the new paths above for live work.

## Related artifacts

- Plan: `manifests/2026-07-05_relocate-s3-manifests.plan.md`
- Move index entry: `plans/2026-04-09_repos-reorg/MOVE_MANIFEST.md` (Step 19)
- Skill: `skills/repo-ops/s3-archive-upload/README.md`
