# Delta: session-schema-rework

## ADDED Requirements

### Requirement: Normalized Session Schema
The system SHALL describe each session with orthogonal fields: platform (claude|codex|cursor), entrypoint (cli|app|subagent), host (local|cloud), and remote_control (bool) with bridge_session_id, replacing the overloaded tool field.
#### Scenario: Session fields are normalized
- **WHEN** sessions are collected or ingested
- **THEN** each carries platform/entrypoint/host and no legacy tool/entrypoint values remain, and labels compose Platform + Entrypoint (+ Cloud / Remote Control) - Model.
#### Scenario: DB migrates in place
- **WHEN** an existing turns.db with a tool column is opened
- **THEN** it is renamed to platform, the new columns are added, and legacy rows are normalized without data loss.

### Requirement: Remote Control Detection
The system SHALL flag Claude local CLI sessions bridged via /rc as remote_control while keeping host=local.
#### Scenario: Bridge markers present
- **WHEN** a Claude CLI JSONL has a bridge-session record or the app index has non-empty bridgeSessionIds for the session
- **THEN** remote_control is true with bridge_session_id set and host remains local; sessions without bridge markers are remote_control false.

## MODIFIED Requirements

### Requirement: Dashboard Entity Views
AI Sessions filter chips are All/Claude/Codex/Cursor (platform), with cloud and Remote Control shown as row tags; delegation and subagent nesting operate on platform=codex + entrypoint cli/subagent.
