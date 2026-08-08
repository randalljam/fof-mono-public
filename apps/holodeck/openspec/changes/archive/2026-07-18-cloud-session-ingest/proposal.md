# Proposal: cloud-session-ingest

## Why
The operator-turns model breaks if cloud AI-coding sessions are invisible. Codex cloud tasks and Claude Code cloud VM sessions (claude.ai/code, e.g. Cataclysm) run server-side and were not captured. Local forensics + a verified web sweep found concrete access paths.

## What Changes
- Codex cloud collector: shells the official `codex cloud list --json` / `diff`, maps tasks to codex-cloud: operator sessions with source_url + diff, correlates to commits.
- Claude cloud poller: private claude.ai API (`GET /v1/code/sessions`, `/v1/code/sessions/{id}`, `/v1/code/sessions/{id}/events` with anthropic-version header + sessionKey cookie), reuses the CLI Claude parser to build claude-cloud: operator sessions correlated by branch. Auth via CLAUDE_AI_SESSION_KEY in .env; absent/expired skips cleanly.
- Claude desktop-app metadata enrichment by cliSessionId (no new sessions).
- sessions gain source_url; turns build ingests both cloud sources by default (--no-cloud to skip).

## Non-Goals
- Reading cookies/keychain programmatically (user supplies CLAUDE_AI_SESSION_KEY); decrypting the ChatGPT desktop cache (codex cloud CLI supersedes it).

## Impact
- New turns/cloud_codex.py, turns/cloud_claude.py; ingest.py, turns_cli.py, collectors/sessions.py, db.py, tests. Findings: plans/2026-07-09_holodeck/2026-07-17_cloud-session-access-findings.md.
