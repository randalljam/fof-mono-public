# Proposal: turns-database

## Why
Every commit in this repo results from an AI turn (Randy writes no code by hand). Tracking work therefore means tracking turns: which prompt produced which commits, through which platform/interface/model. Sessions were shown as bare tool names and commits were uncorrelated; digest summaries of long responses (especially the recap) were unavailable at a glance.

## What Changes
- SQLite `data/turns.db` correlating AI exchanges with commits: sessions, segmented exchanges (primary/quick/info, follow-up folding), 60-day commit ingestion with agent-commit flagging, two-method links (agent-window 0.9 / after-response 0.6), cached digests.
- Session-identifier labels derived from store metadata (Cursor modelConfig + plan mode, Claude model + entrypoint, Codex originator + turn model/effort) shown in Status, cards, and AI Sessions with time to the right of the badge.
- On-demand LLM digests (`asked`/`notes`/`recap` JSON, prefers the response's own recap; Anthropic Haiku, OpenAI fallback) via CLI `--digest` and a per-exchange endpoint — never bulk-automatic.
- Turns view atop the session drawer: digest bullets, linked commits, full-response expander, Summarize button.

## Non-Goals
- Claude Code cloud-app sessions (not in the local store — appear via their pushed commits only); manual link editing; auto-digest on refresh.

## Impact
- New `apps/holodeck/turns/` package + `turns_cli.py`; `collectors/sessions.py`, `server.py`, `web/*`, tests (83 green).
