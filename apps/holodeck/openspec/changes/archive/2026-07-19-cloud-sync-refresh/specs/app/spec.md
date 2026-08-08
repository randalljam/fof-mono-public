# Delta: cloud-sync-refresh

## ADDED Requirements

### Requirement: AI-Session S3 Archival
The system SHALL archive raw AI-session exports to S3 with a committed manifest index, treating the exports as the durable source of truth and turns.db as a rebuildable cache.
#### Scenario: Export is archived
- **WHEN** a Claude cloud export is present in the ai-sessions mount and the ai_sessions area is uploaded
- **THEN** it is stored at s3://[S3-FILES-BUCKET]/ai-sessions/... and recorded in manifests/ai_sessions.manifest.jsonl with size and sha256, verified by content hash.

### Requirement: Refresh AI-Session Sync
Refresh SHALL run a background single-flight AI-session sync in addition to the snapshot: import any downloaded Claude export, rebuild the turns database, and incrementally sync exports to S3, without server-side Claude live fetch.
#### Scenario: Refresh syncs sessions
- **WHEN** the user triggers Refresh
- **THEN** the system picks up any ~/Downloads Claude export into the mount, rebuilds the turns DB (Codex cloud live + local + Claude imports), incrementally S3-syncs the ai_sessions area, and exposes the result at GET /api/ai-sync-status.
#### Scenario: Nothing changed
- **WHEN** Refresh runs with no new export
- **THEN** the S3 sync uploads zero objects and the turns DB rebuilds from existing sources.
