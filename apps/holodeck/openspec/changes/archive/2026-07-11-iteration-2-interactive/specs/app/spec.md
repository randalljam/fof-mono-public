# Delta: iteration-2-interactive

## ADDED Requirements

### Requirement: User State Store
The system SHALL persist user-editable control-center state (next-steps queue and per-worktree card state keyed by branch) in a gitignored JSON file with normalized shapes, atomic writes, and serialized mutations.
#### Scenario: State file is missing
- **WHEN** state is read before any edit
- **THEN** the system returns an empty state document without error.
#### Scenario: Worktree state is merged
- **WHEN** a client sends `PUT /api/state/worktree/{branch}` with a subset of allowed fields (active, order, next_step, last_done, last_done_status, notes)
- **THEN** the system shallow-merges the fields into that branch's entry, validates values, persists atomically, and returns the updated entry; unknown fields are rejected.
#### Scenario: Next steps are managed
- **WHEN** a client creates, updates, or deletes next-step items via `/api/next-steps`
- **THEN** the system persists the queue with generated ids and creation timestamps, and returns not-found for unknown ids.
#### Scenario: Worktree order is assigned
- **WHEN** a client sends `PUT /api/state/worktree-order` with an ordered branch list
- **THEN** the system assigns list indexes as order values, clears order on unlisted branches, and persists the result.

### Requirement: File Read and Write API
The system SHALL serve small text files from the repo or known worktrees and SHALL accept writes only to allowlisted paths (OpenSpec markdown/config files and the holodeck registry), atomically.
#### Scenario: Safe read
- **WHEN** a client requests `GET /api/file` for an allowed-suffix file under the repo root or a snapshot worktree
- **THEN** the system returns path, content capped at 200 KB, and a truncation flag.
#### Scenario: Unsafe read or write
- **WHEN** the resolved path escapes the allowed roots or has a disallowed suffix
- **THEN** the system rejects the request.
#### Scenario: Allowlisted write
- **WHEN** a client sends `PUT /api/file` for a path containing `/openspec/` ending in `.md` or `config.yaml`, or ending in `apps/holodeck/registry.yaml`
- **THEN** the system writes the content atomically and confirms; all other writes return a permission error.

### Requirement: Startup Auto-Refresh
The system SHALL start one background full collection at server startup when the snapshot is missing or older than 30 minutes and the refresh lock is available.
#### Scenario: Stale snapshot at startup
- **WHEN** the server starts and the snapshot's generated time is older than 30 minutes
- **THEN** the system starts a background collect run and logs that it started.

### Requirement: Worktree App Mapping
The system SHALL report which app slugs each worktree's branch work touches, derived from committed diff against `origin/main` and uncommitted changes under `apps/`.
#### Scenario: Worktree touches an app
- **WHEN** a worktree has commits or local changes under an app directory
- **THEN** the worktree entry lists that app's slug in `apps_touched` using longest-prefix slug matching.

### Requirement: Interactive Worktree Cards
The dashboard SHALL render worktree cards as an editable work-management surface backed by the state APIs.
#### Scenario: Collapsed card content
- **WHEN** a worktree card is collapsed
- **THEN** it shows branch name, active state, editable next step, editable just-done text with review-status pill, apps-touched chips, and the latest matching session — without path or drift details.
#### Scenario: Card expands
- **WHEN** the user clicks a card
- **THEN** it expands to full grid width adding path, drift badges, last commit, PR, ledger, recent sessions, and notes; clicking again collapses it.
#### Scenario: Cards are reordered
- **WHEN** the user drags a card or uses move-to-top
- **THEN** the new active-card order persists via the worktree-order API and survives reload.
#### Scenario: Inactive worktree
- **WHEN** the user switches a card to inactive
- **THEN** the card renders dimmed and sorts after active cards.

### Requirement: File Drawer
The dashboard SHALL open spec and registry file references in a drawer that renders content read-only and offers edit-and-save only for write-allowlisted paths outside sample mode.
#### Scenario: Spec file is viewed and edited
- **WHEN** the user opens an OpenSpec file from an app card or the specs section and saves an edit
- **THEN** the client GETs the file, renders escaped content, and persists the change via the file write API with visible success or error feedback.

## MODIFIED Requirements

### Requirement: Dashboard Overview
Overview additions: exactly five clickable stat tiles in one row (worktrees with dirty subtext, branches, open PRs, apps, AI sessions) each scrolling to its section; a next-steps scratchpad panel backed by the state API (read-only in sample mode); latest activity keyed by worktree branch with platform tags; snapshot status showing relative and absolute time with the refresh control adjacent.

### Requirement: App and Core Inventory
Apps always carry a concrete kind (registry value or inferred chalice/web/cli/docs/scripts fallback — never a bare "app"), pass through provisional `stage` and `spec_stage` registry fields, and core module descriptions skip decorative marker lines.

### Requirement: Dashboard Entity Views
App cards adopt the expand/collapse pattern with stage and spec-stage pills and worktree chips linking to worktree cards; the specs section renders every store with clickable spec/change/archive file rows opening the file drawer; the sessions section is titled "AI Sessions".
