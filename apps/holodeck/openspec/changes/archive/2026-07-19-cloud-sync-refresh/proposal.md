# Proposal: cloud-sync-refresh

## Why
Cloud session access is solved (Codex cloud via CLI token; Claude cloud via browser export, since Cloudflare blocks all automation). This change makes the raw exports durable + synced (S3 manifests) and folds all automatable syncing into the single Refresh button, so the user's only manual step is the periodic browser export.

## What Changes
- S3 archival: new ai_sessions area in core/s3_archive.py (root = ../_LOCAL_FILES/fof-mono), manifest committed, exports uploaded to s3://[S3-FILES-BUCKET]/ai-sessions/. Raw exports are source of truth in _LOCAL_FILES/fof-mono/ai-sessions/; turns.db is a per-worktree derived cache.
- Refresh folds in AI-session sync: background single-flight that picks up any Claude export from ~/Downloads into the mount, rebuilds the turns DB (Codex cloud live + local + Claude imports), and incrementally S3-syncs. GET /api/ai-sync-status + a subtle dashboard status line.
- Claude ingest is import-only from the mount (no server-side live fetch — Cloudflare). Cloud-status guidance points to the browser-export -> Refresh workflow.

## Non-Goals
- Server-side Claude live fetch (Cloudflare Turnstile blocks automation, verified); superwhisper ingest (pinned, privacy-sensitive).

## Impact
- core/s3_archive.py, manifests/ai_sessions.manifest.jsonl, server.py, turns/cloud_claude.py, web/*, tests.
