# Delta: operator-turns

## ADDED Requirements

### Requirement: Operator Turn Model
The system SHALL classify every session and exchange as operator (human-prompted) or delegated (AI-prompted machinery) and organize all turn surfaces around operator turns.
#### Scenario: Delegation is detected
- **WHEN** a session's originator, executor-preamble prompt, or delegation label indicates an AI author
- **THEN** the session and its exchanges are origin delegated, codex delegations relabel to Codex CLI (fable5-w-codex), and delegated turns are excluded from default turn listings and digest priority.

### Requirement: Worktree Turn State
The system SHALL derive and display, per worktree, whether the latest operator turn is waiting on the AI or waiting on Randy.
#### Scenario: State is shown
- **WHEN** the latest operator exchange for a worktree has an unanswered user message
- **THEN** the status row shows WAITING ON AI with elapsed time; otherwise it shows YOUR TURN since the response ended, with the digest turn title, session label, absolute time, hover recap, and drawer click-through.

## MODIFIED Requirements

### Requirement: Exchange Digests
Digests additionally produce a 3-7 word work title used wherever sessions or turns render a title; the Anthropic model is claude-sonnet-5; recent operator exchanges auto-digest after each turns refresh (capped, operator-only) per explicit user decision.

### Requirement: Dashboard Entity Views
AI Sessions rows show one worktree-colored short-branch pill in place of project and branch columns, relative plus absolute timestamps, and hide delegated sessions behind a machinery filter.
