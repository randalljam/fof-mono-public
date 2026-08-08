# Proposal: session-schema-rework

## Why
The session object overloaded `tool` (claude-code/claude-cloud/cursor/codex/codex-cloud), conflating platform, interface, and host. Randy's terminology (AI-SESSIONS.md) separates these into orthogonal axes and adds Remote Control detection.

## What Changes
- tool -> platform (claude/codex/cursor); entrypoint values -> cli/app/subagent; new host (local/cloud); remote_control + bridge_session_id.
- Remote Control detected from JSONL bridge-session records and the Claude app index bridgeSessionIds (RC = local CLI bridged via /rc; host stays local).
- In-place DB migration (rename + new columns + legacy-row normalization, schema v5); delegation keys on platform=codex + entrypoint cli/subagent; labels compose Platform + Entrypoint (+ Cloud / Remote Control) - Model; frontend filters become All/Claude/Codex/Cursor with cloud/RC tags.

## Non-Goals
- Cloud VM session ingestion changes; the (Cursor) interface context beyond platform.

## Impact
- db.py, ingest.py, cloud_claude.py, cloud_codex.py, labels.py, collectors/sessions.py, server.py, web/*, tests.
