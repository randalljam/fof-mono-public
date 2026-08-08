# Delta: turns-database

## ADDED Requirements

### Requirement: Turns Database
The system SHALL maintain a SQLite database correlating AI-coding exchanges with git commits across all worktrees, rebuilt idempotently without losing cached digests.
#### Scenario: Exchanges are segmented
- **WHEN** session messages are ingested
- **THEN** each non-injected user message starts an exchange classified primary, quick, or info; short user messages arriving within the follow-up window fold into the prior exchange; auto-review sessions are excluded from exchange ingestion.
#### Scenario: Commits are linked
- **WHEN** a commit falls inside an exchange's active window or shortly after its response ends on the same branch or worktree
- **THEN** a link is recorded with method and confidence, and unmatched commits remain visibly unlinked.

### Requirement: Session Identity Labels
The system SHALL derive Randy's session-identifier labels (platform + interface + model + qualifiers) from store metadata and show them wherever sessions render, with relative time to the right of the label.
#### Scenario: Labels are derived
- **WHEN** sessions are collected
- **THEN** Cursor labels come from modelConfig and plan mode, Claude Code labels from message model and entrypoint, Codex labels from originator and per-turn model/effort, with a plain tool-name fallback.

### Requirement: Exchange Digests
The system SHALL produce on-demand LLM digests per exchange (asked bullets, notes bullets, recap preferring the response's own recap text) and cache them permanently.
#### Scenario: Digest on demand
- **WHEN** the user clicks Summarize on an undigested exchange (or runs the CLI with --digest)
- **THEN** one LLM call produces strict-JSON asked/notes/recap stored in the digests table; digests are never generated in bulk during collection, and a missing API key degrades with a clear message.

### Requirement: Turns View
The dashboard session drawer SHALL open with a turns view showing each exchange's kind, digest bullets, recap, and linked commits, with a full-response expander and the raw message list collapsed below.
#### Scenario: Exchange is reviewed
- **WHEN** the user opens a session from Status, a worktree card, or AI Sessions
- **THEN** the drawer lists that session's exchanges with digests where present, a Summarize button where absent, and linked commits with sha and subject.
