# Proposal: operator-turns

## Why
The founding insight of this system: Randy never reads code — the only human interaction points are a voice-dictated intent prompt and testing-time feedback. Session stores assume user-role = human, but most "user" messages here are AI-authored delegation prompts. The dashboard must organize around Randy's operator turns and treat agent-to-agent traffic as machinery, and must answer "whose turn is it?" per worktree at a glance.

## What Changes
- origin (operator|delegated) classification through sessions, exchanges, DB, and APIs; delegated codex sessions relabel to Codex CLI (fable5-w-codex); /api/turns defaults to operator only.
- /api/turns/status: per-worktree waiting-on-ai vs your-turn with elapsed time, digest turn title, and recap; Status panel rebuilt as the loop tracker (worktree color chip, short sub-branch pill, state badge, title, label, absolute time, hover recap, drawer click-through).
- Digest titles (3-7 word work names) replace transcription snippets everywhere; digest model switched to claude-sonnet-5; auto-digest of recent operator exchanges after refresh (explicit user reversal of the no-auto rule).
- AI Sessions: one worktree-colored short-branch pill, dual timestamps, machinery filter for delegated rows.

## Non-Goals
- Cloud session export (no supported API exists at either provider — researched 2026-07-17; roadmap watch item).

## Impact
- turns package, collectors/sessions.py, server.py, web/*, tests (97 green).
