file: docs/2026-07-06_cloud-agent-s3-access.md
title: Cloud Agent S3 Access
last-updated: 2026-07-06_1431
ai: Cursor - GPT-5.5
session: `Cloud agent S3 access setup`

# Cloud Agent S3 Access

This repo uses scoped AWS credentials for cloud coding agents. Cloud credentials are more exposed than local credentials because they are injected into third-party, ephemeral agent environments, so they should be broad enough to remove development friction but not powerful enough to erase data.


## Default Development Grant
Use one general cloud-development IAM user for non-PII repo data:

- IAM user: `claude-cloud-[S3-FILES-BUCKET]-data-s3`
- Env vars: `FOF_FILES_DATA_S3_ACCESS_KEY_ID`, `FOF_FILES_DATA_S3_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION=us-west-2`
- Bucket/prefix: `s3://[S3-FILES-BUCKET]/data/*`
- Permissions: `s3:ListBucket`, `s3:GetObject`, `s3:PutObject`
- No delete permission

Create or refresh it from the repo root with:

```bash
.venv/bin/python3 core/grant_cloud_s3_access.py "data" --bucket [S3-FILES-BUCKET] --app [S3-FILES-BUCKET]-data --access readwrite
.venv/bin/python3 core/grant_cloud_s3_access.py "data" --bucket [S3-FILES-BUCKET] --app [S3-FILES-BUCKET]-data --access readwrite --execute
```

The first command is a dry run. The second command creates or updates the IAM user, attaches the no-delete read/write policy, and prints the access key block. The secret is shown only when a new key is created.

If credentials were originally created with `--app cloud-dev`, the permission boundary can stay the same. Add the same access key values under `FOF_FILES_DATA_S3_ACCESS_KEY_ID` and `FOF_FILES_DATA_S3_SECRET_ACCESS_KEY`, then remove the old `CLOUD_DEV_S3_*` aliases after active cloud sessions have moved over.


## Cloud Environment Setup
Add the printed variables to the Claude Code cloud environment. In the macOS app, click the cloud icon, choose the target environment, paste the variables into the environment variables window, and save. If a tool expects boto3's standard names, also map the same values to `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in that environment.

Add S3 network egress for:

- `s3.us-west-2.amazonaws.com`
- `[S3-FILES-BUCKET].s3.us-west-2.amazonaws.com`


## Deletion Rule
Cloud agents do not get S3 delete permission by default. If an agent believes S3 objects should be deleted, it must report the exact bucket/key list and give Randy local commands to review and run manually. Do not add `--allow-delete` to the general `[S3-FILES-BUCKET]-data` grant.


## Higher-Risk Access
Keep separate, narrower credentials for:

- Any `[S3-BUCKET]` access
- Any PII or user-identifying data
- Production buckets
- Delete permission
- Broad write access outside `s3://[S3-FILES-BUCKET]/data/*`

Prefer read-only grants for real capture/reference data and use a separate output prefix when agents need to write generated artifacts.
