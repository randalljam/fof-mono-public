## ADDED Requirements
### Requirement: Snapshot CLI
The system SHALL provide a collector CLI that lists supported layers, collects all layers, or refreshes selected layers into the local snapshot file.
#### Scenario: Layer names are listed
- **WHEN** the collector is run with `--list`
- **THEN** the system prints the supported layer names.
#### Scenario: All layers are collected
- **WHEN** the collector is run without `--layer`
- **THEN** the system collects every supported layer, prints one summary line per layer, and writes `apps/holodeck/data/snapshot.json`.
#### Scenario: Selected layers are refreshed
- **WHEN** the collector is run with one or more `--layer` options
- **THEN** the system refreshes only those layers and preserves the other layers from the existing snapshot.

### Requirement: Snapshot Shape and Resilience
The system SHALL store snapshot metadata and layer metadata for every supported layer while allowing individual layer failures to be reported without aborting the full collection run.
#### Scenario: A layer succeeds
- **WHEN** a collector returns items successfully
- **THEN** the system stores those items under the matching layer and records generated time, elapsed seconds, and a null error for that layer.
#### Scenario: A layer raises an exception
- **WHEN** an individual layer collector fails during collection
- **THEN** the system records an empty item list and the error message for that layer while continuing to collect later layers.
#### Scenario: Branch pull-request lookup fails
- **WHEN** GitHub CLI pull-request lookup fails during branch collection
- **THEN** the system keeps the collected branch rows and reports the pull-request lookup note in the branch layer metadata.

### Requirement: Git Surface Inventory
The system SHALL collect git worktree and branch status for the repository.
#### Scenario: Worktrees are collected
- **WHEN** the worktree layer runs
- **THEN** the system reports each git worktree with path, branch, head, current-worktree flag, missing-on-disk flag, last commit, dirty count, untracked count, ahead/behind counts against `origin/main`, upstream, and unpushed count when available.
#### Scenario: Branches are collected
- **WHEN** the branch layer runs
- **THEN** the system reports local and remote branches deduplicated by short name with tip, subject, date, author, local/remote flags, worktree path, ahead/behind counts, pull-request data when available, and branch-ledger data when available.
#### Scenario: Detached worktree is parsed
- **WHEN** git worktree porcelain output marks a worktree as detached
- **THEN** the system reports that worktree with branch value `detached`.

### Requirement: App and Core Inventory
The system SHALL inventory application directories, curated registry facts, app filesystem flags, git activity, and core module summaries.
#### Scenario: Registered app is discovered
- **WHEN** an app slug exists in `apps/holodeck/registry.yaml`
- **THEN** the system carries through curated fields such as name, purpose, kind, commands, port, URL, deploy entries, notes, and tags.
#### Scenario: Unregistered app directory is discovered
- **WHEN** an app directory exists under `apps/` but has no registry entry
- **THEN** the system includes it with computed path, registered flag, README/test/AGENTS/OpenSpec flags, last commit date, and 30-day commit count.
#### Scenario: Core modules are collected
- **WHEN** the core layer runs
- **THEN** the system reports each `core/*.py` module except `__init__.py`, plus `core/cron` when present, with a short description and git activity.

### Requirement: OpenSpec and Skill Inventory
The system SHALL inventory OpenSpec stores across known worktrees and reusable skill metadata from supported repo skill locations.
#### Scenario: OpenSpec stores are scanned
- **WHEN** the specs layer runs with existing worktrees
- **THEN** the system scans `apps/*/openspec` and `apps/*/*/openspec` in each non-missing worktree and reports spec domains, active changes, task counts, and archived changes.
#### Scenario: Active change tasks are counted
- **WHEN** an active OpenSpec change has a `tasks.md`
- **THEN** the system counts checked and unchecked Markdown task boxes, including nested checked boxes.
#### Scenario: Skills are collected
- **WHEN** the skills layer runs
- **THEN** the system reports shared skills, Claude skills, Claude commands, and Hermes skills when their configured directories exist.

### Requirement: Deploy Inventory
The system SHALL inventory deploy surfaces from the registry and from auto-discovered Fly and Chalice configuration files.
#### Scenario: Registry deploy entries exist
- **WHEN** registered apps include deploy entries
- **THEN** the system reports those entries with kind, owning app slug, name, command, URL, config path, and last deploy when provided.
#### Scenario: Fly and Chalice configs exist
- **WHEN** Fly or Chalice configuration files are found in supported app paths
- **THEN** the system parses their app names and emits deploy entries for those surfaces.
#### Scenario: Duplicate deploy entries are found
- **WHEN** registry and auto-discovered deploy entries share the same kind and name
- **THEN** the system keeps the first entry, which makes registry entries take precedence because they are processed first.

### Requirement: AI Session Inventory
The system SHALL collect recent Claude Code, Cursor, and Codex sessions that match known repo worktrees or the configured fallback repo path.
#### Scenario: JSONL sessions are collected
- **WHEN** recent Claude Code or Codex JSONL session files match this repo
- **THEN** the system extracts tool, id, title, project, worktree, branch, timestamps, message count, first and last non-injected user previews, and source path.
#### Scenario: Cursor sessions are collected
- **WHEN** the Cursor global storage database exists
- **THEN** the system opens it read-only by URI, reads composer rows by key prefix, filters sessions to this repo, and fetches preview text for the most recent matching sessions.
#### Scenario: Session results are bounded
- **WHEN** sessions are collected for any supported tool
- **THEN** the system sorts by last activity descending and caps returned sessions per tool.

### Requirement: Snapshot HTTP API
The system SHALL expose the snapshot and collector refresh operation through the local FastAPI server.
#### Scenario: Snapshot exists
- **WHEN** a client requests `GET /api/snapshot` and the snapshot file exists
- **THEN** the system returns the parsed snapshot JSON.
#### Scenario: Snapshot is missing
- **WHEN** a client requests `GET /api/snapshot` before a snapshot exists
- **THEN** the system returns a 404 JSON response telling the user to run the collector or refresh endpoint.
#### Scenario: Refresh is requested
- **WHEN** a client posts to `POST /api/refresh`
- **THEN** the system runs the collector as a subprocess, optionally passes requested layers, prevents concurrent refreshes with a lock, and returns success state, elapsed seconds, and stdout tail.

### Requirement: Session Detail API
The system SHALL serve capped message detail for sessions present in the current snapshot while rejecting unknown sessions and unsafe source locations.
#### Scenario: Valid session detail is requested
- **WHEN** a client requests `GET /api/sessions/{tool}/{session_id}` for a session in the snapshot
- **THEN** the system rereads the supported source and returns up to 200 messages with role, text, and timestamp fields.
#### Scenario: Session is unknown
- **WHEN** the requested tool and session id do not match a session in the snapshot
- **THEN** the system returns a not-found error.
#### Scenario: Source path is unsafe
- **WHEN** a snapshot session points outside the allowed Claude Code or Codex session roots, or a Cursor source id is not the composer id form
- **THEN** the system rejects the detail request.

### Requirement: Dashboard Snapshot Loading
The system SHALL render the static dashboard from either the API snapshot or the bundled sample snapshot and display visible errors instead of a blank page.
#### Scenario: API snapshot loads
- **WHEN** the dashboard opens without sample mode
- **THEN** the client fetches `/api/snapshot`, stores the snapshot in browser state, and renders all sections.
#### Scenario: Sample mode is requested
- **WHEN** the dashboard URL includes `?src=sample`
- **THEN** the client loads `sample-snapshot.json`, disables refresh, and renders from sample data.
#### Scenario: Snapshot load fails
- **WHEN** the snapshot request fails or reports an error
- **THEN** the client shows a visible error panel with the collector and server command.

### Requirement: Dashboard Overview
The system SHALL compute and render overview status, layer warnings, attention items, and latest activity from the loaded snapshot.
#### Scenario: Snapshot metadata is rendered
- **WHEN** a snapshot is loaded
- **THEN** the dashboard shows relative snapshot generation time and a warning strip for any layer metadata errors.
#### Scenario: Attention items are computed
- **WHEN** snapshot data contains dirty worktrees, unpushed commits, branches far behind main, missing worktrees, port collisions, zero-progress active spec changes, or layer errors
- **THEN** the dashboard lists those items in the overview with links to the relevant section.
#### Scenario: No attention items exist
- **WHEN** no attention condition is present
- **THEN** the dashboard shows the "All quiet on the holodeck." empty state.

### Requirement: Dashboard Entity Views
The system SHALL render navigable dashboard sections for worktrees and branches, apps and core, specs, skills, sessions, and deploy entries.
#### Scenario: Git section renders
- **WHEN** worktree and branch layers are present
- **THEN** the dashboard renders worktree cards with drift, local-change, pull-request, commit, and latest-session information plus a branch table.
#### Scenario: App and spec sections render
- **WHEN** app, core, and specs layers are present
- **THEN** the dashboard renders filterable app cards, a core module table, and OpenSpec cards with active-change progress and archived-change details.
#### Scenario: Session and deploy sections render
- **WHEN** session and deploy layers are present
- **THEN** the dashboard renders filterable session rows with a lazy message drawer and deploy entries grouped by kind.

### Requirement: Dashboard Local Interactions
The system SHALL support local interactions for filtering, copying text, refreshing, navigation highlighting, and session drawer dismissal.
#### Scenario: Filters and search are used
- **WHEN** a user changes app or session filters or search inputs
- **THEN** the dashboard rerenders the matching cards or rows from the in-memory snapshot.
#### Scenario: Copy button is clicked
- **WHEN** a user clicks a copy button for a path, command, or test command
- **THEN** the dashboard copies the text to the clipboard using the browser clipboard API or textarea fallback and briefly changes the button label.
#### Scenario: Session drawer is closed
- **WHEN** a user presses Escape, clicks the backdrop, or clicks the close button
- **THEN** the dashboard hides the session drawer and marks it aria-hidden.
