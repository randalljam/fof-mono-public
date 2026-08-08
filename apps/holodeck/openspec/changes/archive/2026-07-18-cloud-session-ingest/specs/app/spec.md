# Delta: cloud-session-ingest

## ADDED Requirements

### Requirement: Cloud Session Ingestion
The system SHALL ingest cloud AI-coding sessions (Codex cloud tasks and Claude Code cloud VM sessions) into the turns database as operator sessions correlated to commits, degrading cleanly when a source is unavailable.
#### Scenario: Codex cloud tasks are ingested
- **WHEN** the turns build runs and the codex CLI is logged in
- **THEN** `codex cloud list --json` tasks become codex-cloud: sessions with a primary operator exchange, source_url, and diff summary, correlated to commits by task url or time window.
#### Scenario: Claude cloud sessions are ingested
- **WHEN** CLAUDE_AI_SESSION_KEY is set and the turns build runs
- **THEN** the poller lists claude.ai/code sessions, fetches paginated events via the private /v1/code API with the anthropic-version header, builds claude-cloud: operator sessions using the shared Claude parser, and correlates them to commits on the session branch.
#### Scenario: A cloud source is unavailable
- **WHEN** the codex CLI is not logged in or CLAUDE_AI_SESSION_KEY is absent or expired (HTTP 401)
- **THEN** that cloud source is skipped with a clear note and local ingest is unaffected.
