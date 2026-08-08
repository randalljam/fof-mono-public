# Holodeck Specification

## Purpose
Holodeck is a local control center for the fof-mono AI-coding workspace. It aggregates worktrees, branches, apps, core modules, skills, OpenSpec stores, recent AI sessions, and deploy surfaces into a gitignored JSON snapshot, then serves that snapshot through a small FastAPI API and vanilla web dashboard.

This single `app` capability is the S1-dev baseline for the whole application. Split it into narrower capabilities later only when the file becomes too large or separate behavior areas need independent change control.
## Workflows
### Workflow: Build Snapshot
run collector -> collect or refresh layers -> write snapshot -> inspect layer summaries and metadata.
Exercises requirements: Snapshot CLI, Snapshot Shape and Resilience, Git Surface Inventory, App and Core Inventory, OpenSpec and Skill Inventory, Deploy Inventory, AI Session Inventory

### Workflow: Serve Local Control Center
start FastAPI server -> load dashboard or API snapshot -> trigger refresh -> request session detail when needed.
Exercises requirements: Snapshot HTTP API, Local Cursor Focus API, Activation Adapter Boundary, Session Detail API, Dashboard Snapshot Loading

### Workflow: Focus Open Worktree
open a worktree card with an open Cursor status -> activate its focus control -> validate the live worktree -> focus the unique live Cursor window or show an inline error.
Exercises requirements: Local Cursor Focus API, Activation Adapter Boundary, Cursor Focus Control, Interactive Worktree Cards

### Workflow: Triage Repo State
open dashboard -> review overview warnings and attention items -> inspect worktrees, branches, apps, core, specs, and skills.
Exercises requirements: Dashboard Overview, Dashboard Entity Views, Git Surface Inventory, App and Core Inventory, OpenSpec and Skill Inventory

### Workflow: Review Agent Work
open sessions section -> filter by tool or search text -> open a session drawer -> read messages -> close the drawer.
Exercises requirements: AI Session Inventory, Session Detail API, Dashboard Entity Views, Dashboard Local Interactions

### Workflow: Inspect Runtime Surfaces
open apps and deploy sections -> filter app cards -> copy local commands -> inspect deployment entries and links.
Exercises requirements: Deploy Inventory, App and Core Inventory, Dashboard Entity Views, Dashboard Local Interactions

### Workflow: Manage Work Queue
open overview and worktree cards -> set the primary AI interface -> record next steps on cards and the global to-do -> toggle active worktrees and reorder cards -> view or edit OpenSpec files in the drawer.
Exercises requirements: User State Store, Primary AI Interface, Global To-Do List, Worktree Next-Step Checklist, Interactive Worktree Cards, File Read and Write API, File Drawer, Dashboard Overview

### Workflow: Review Turns
open a session from Status or a worktree card -> read digest bullets and recap per exchange -> check linked commits -> Summarize undigested exchanges -> expand the full response when needed.
Exercises requirements: Turns Database, Session Identity Labels, Exchange Digests, Turns View

### Workflow: Inspect Branch History
open the Branches section -> read parent and tip-commit columns -> click a branch for its commits drawer -> page through full commit messages.
Exercises requirements: Branch Parent Information, Branch Commits API, Branches Section
## Requirements
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

### Requirement: Worktree App Mapping
The system SHALL report which app slugs each worktree's branch work touches, derived from committed diff against `origin/main` and uncommitted changes under `apps/`.
#### Scenario: Worktree touches an app
- **WHEN** a worktree has commits or local changes under an app directory
- **THEN** the worktree entry lists that app's slug in `apps_touched` using longest-prefix slug matching.

### Requirement: Git Surface Inventory
The system SHALL collect git worktree and branch status for the repository.
#### Scenario: Worktrees are collected
- **WHEN** the worktree layer runs
- **THEN** the system reports each git worktree with path, branch, head, current-worktree flag, missing-on-disk flag, last commit, dirty count, untracked count, ahead/behind counts against `origin/main`, upstream, and unpushed count when available.
#### Scenario: Branches are collected
- **WHEN** the branch layer runs
- **THEN** the system reports local and remote branches deduplicated by short name with tip, subject, date, author, local/remote flags, worktree path, ahead/behind counts, pull-request data when available, derived parent/fork-base, and purpose from a branch-start commit when available.
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
#### Scenario: App kind is always concrete
- **WHEN** an app has no registry kind
- **THEN** the system infers chalice, web, cli, docs, or scripts from the app's files, never leaving a bare or missing kind.
#### Scenario: Provisional stage fields pass through
- **WHEN** a registry entry carries `stage` or `spec_stage`
- **THEN** the system passes those values through to the apps layer unchanged.
#### Scenario: Core modules are collected
- **WHEN** the core layer runs
- **THEN** the system reports each `core/*.py` module except `__init__.py`, plus `core/cron` when present, with a short description (skipping decorative marker lines) and git activity.

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

### Requirement: Local Cursor Focus API
The system SHALL expose a loopback-only semantic action that focuses an already-open Cursor window for a current repo worktree without accepting executable input.
#### Scenario: Cursor worktree is focused
- **WHEN** an authorized local client posts a canonical path for a live repo worktree and exactly one live Cursor window matches its path or conservative title candidates
- **THEN** the system restores and raises that window, makes Cursor frontmost, uniquely rematches the resulting standard main window to the requested worktree, and only then returns a structured focused result.
#### Scenario: Cursor window is on another Space
- **WHEN** the unique matching Cursor window is on another macOS Space
- **THEN** the system activates the already-running Cursor process, waits within a bounded timeout for Accessibility enumeration and the target-Space transition, and fails without a success result if final main-window verification does not complete.
#### Scenario: Snapshot is stale
- **WHEN** `cursor_open` was true in the snapshot but no matching live window exists at click time
- **THEN** the system returns `target_not_found` and does not open Cursor or create a window.
#### Scenario: Match is ambiguous
- **WHEN** more than one live Cursor window matches the authorized worktree
- **THEN** the system returns `ambiguous_match` without choosing a window.
#### Scenario: Worktrees share a folder basename
- **WHEN** two live worktrees have the same folder basename
- **THEN** the system omits that ambiguous basename fallback and focuses only a live document-path match; otherwise it fails without choosing a window.
#### Scenario: Multi-root workspace shows an external folder
- **WHEN** a uniquely named `.code-workspace` window has a live document outside the worktree root
- **THEN** the system accepts its workspace-title match only when that document is inside a folder parsed from the requested worktree's workspace configuration, and rejects a document outside those authorized roots.
#### Scenario: Request is unsafe
- **WHEN** a request is nonlocal or cross-site, lacks the JSON action header, has an unknown field or target, or supplies a path outside current `git worktree list` output
- **THEN** the system rejects the request before invoking macOS automation.
#### Scenario: Activation cannot complete
- **WHEN** Cursor is not running, permissions are missing, another focus action is active, automation times out, the host is not macOS, or the adapter fails
- **THEN** the system returns a stable privacy-safe error without candidate window titles or raw automation output.

### Requirement: Cursor Focus Control
The dashboard SHALL use snapshot Cursor status as a rendering hint and live macOS state as the activation source of truth.
#### Scenario: Cursor was open at snapshot time
- **WHEN** a worktree card has `cursor_open` true outside sample mode
- **THEN** its `open in Cursor` pill is an accessible focus button, is a sibling of the card's expand button, sends only the worktree path to the focus API, and does not toggle expansion.
#### Scenario: Cursor was not open at snapshot time
- **WHEN** a worktree card has `cursor_open` false, or the dashboard is in sample mode
- **THEN** the Cursor pill remains non-actionable.
#### Scenario: Focus result is reported
- **WHEN** a focus request is pending, succeeds, or fails
- **THEN** the card exposes an accessible local status with guidance for stale state, ambiguity, permissions, and retryable automation errors.

### Requirement: Activation Adapter Boundary
The system SHALL invoke only fixed, reviewed macOS activation adapters with bounded input and execution and privacy-safe structured results.
#### Scenario: Adapter is invoked
- **WHEN** a validated Cursor focus target is dispatched
- **THEN** the system runs the checked-in Cursor script through a fixed `/usr/bin/osascript` argument vector with `shell=False`, a bounded timeout, and matcher values passed separately from script source.
#### Scenario: Adapter returns sensitive diagnostics
- **WHEN** macOS automation fails or writes diagnostic output
- **THEN** the system maps the result to a stable error without returning candidate window titles, paths, or raw automation output to the browser.

### Requirement: Session Detail API
The system SHALL serve capped message detail for sessions present in the current snapshot while rejecting unknown sessions and unsafe source locations.
#### Scenario: Valid session detail is requested
- **WHEN** a client requests `GET /api/sessions/{tool}/{session_id}` for a session in the snapshot
- **THEN** the system rereads the supported source and returns up to 200 messages with role, untruncated text, and timestamp fields.
#### Scenario: Session is unknown
- **WHEN** the requested tool and session id do not match a session in the snapshot
- **THEN** the system returns a not-found error.
#### Scenario: Source path is unsafe
- **WHEN** a snapshot session points outside the allowed Claude Code or Codex session roots, or a Cursor source id is not the composer id form
- **THEN** the system rejects the detail request.

### Requirement: User State Store
The system SHALL persist user-editable control-center state (next-steps queue and per-worktree card state keyed by branch) in a gitignored JSON file with normalized shapes, atomic writes, and serialized mutations.
#### Scenario: State file is missing
- **WHEN** state is read before any edit
- **THEN** the system returns an empty state document without error.
#### Scenario: Worktree state is merged
- **WHEN** a client sends `PUT /api/state/worktree/{branch}` with a subset of allowed fields (active, order, next_step, last_done, last_done_status, notes, primary_interface, steps, deactivated_at, and legacy submission fields)
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

### Requirement: Primary AI Interface
The system SHALL track a manually set primary AI interface per worktree branch (the main harness currently used there) and render it on worktree cards and in the overview Status rollup.
#### Scenario: Interface is set
- **WHEN** the user picks Cursor, Claude CLI, Claude app, Codex CLI, or Codex app in a card's Primary-AI-interface pulldown
- **THEN** the client persists primary_interface and the card and Status panel show it as a pill.
#### Scenario: Legacy value migrates
- **WHEN** stored state carries a legacy submitted_via value and no primary_interface
- **THEN** state normalization adopts the legacy value as primary_interface.
#### Scenario: Overview rollup
- **WHEN** worktrees are active
- **THEN** the overview Status panel lists them ordered by latest session recency with worktree-colored name chips, interface pill when set, first unchecked next step (or a muted hint), and latest session relative time.
#### Scenario: Invalid harness value
- **WHEN** a client sends a primary_interface value outside the allowed set
- **THEN** the server rejects it with a validation error.

### Requirement: Global To-Do List
The system SHALL provide a manual to-do queue on the overview with persistent ordering and a dated markdown archive.
#### Scenario: Items are managed
- **WHEN** the user adds, checks, or drag-reorders to-do items
- **THEN** the changes persist through the next-steps and next-steps-order APIs and the list renders in stored order.
#### Scenario: Item is archived
- **WHEN** the user archives an item
- **THEN** it is removed from state and appended to `apps/holodeck/data/todo-archive.md` under a `## YYYY-MM-DD` heading with added/archived times, and it no longer renders.

### Requirement: Worktree Next-Step Checklist
The system SHALL store a per-worktree checklist of next steps and render it on the card with a free-text entry that converts each entry into a checkbox item.
#### Scenario: Step is added
- **WHEN** the user types in the card's next-step input and presses Enter
- **THEN** the text becomes the newest checkbox item, the input clears for another entry, and the validated list persists via the worktree state API.

### Requirement: Branch Parent Information
The system SHALL use validated branch-lineage commits as the sole authority for each non-root branch's intended parent and purpose, SHALL preserve v1 compatibility, and SHALL never silently substitute structural inference or a side ledger.
#### Scenario: Branch-start record is structural evidence
- **WHEN** the first unique commit is a valid v2 `branch-start` record whose actual Git first parent equals its full `Fork-Commit`
- **THEN** the branch reports `structurally-verified` and projects its parent, fork, and purpose as accepted truth.
#### Scenario: Recorded-late evidence is approved
- **WHEN** the newest applicable record is a valid approved `recorded-late` declaration and its cited DAG or rewrite evidence validates
- **THEN** the branch reports `evidence-validated` and projects its declared parent, fork, and purpose as accepted truth.
#### Scenario: Existing v1 record is read
- **WHEN** the newest applicable record uses Lineage-Version 1
- **THEN** Holodeck maps its `Lineage-Type` directly, maps `explicit-reroot-merge` to `Relationship: rerooted-to`, maps other supported v1 evidence to `created-from`, and validates it without rewriting the record.
#### Scenario: Newest applicable record supersedes history
- **WHEN** multiple records for the exact branch occur on its first-parent history
- **THEN** Holodeck selects the newest applicable candidate before validation, validates its stable IDs and supersession links, and retains older records as immutable audit history.
#### Scenario: Stacked branch inherits another record
- **WHEN** a stacked child contains a parent's record in its history but that record's `Branch` field does not exactly equal the child name
- **THEN** Holodeck ignores that inherited record for selection.
#### Scenario: Newest record cannot be accepted
- **WHEN** the newest applicable record is pending, malformed, unsupported, has broken supersession, names a missing parent, participates in a cycle, or the local and remote same-name refs diverge
- **THEN** Holodeck visibly reports the corresponding pending, invalid, unsupported, parent-ref-missing, or ref-diverged state, exposes validation detail, and does not fall back to an older record or a guessed parent.
#### Scenario: Branch has no record
- **WHEN** a non-root branch has no applicable lineage record
- **THEN** Holodeck reports `missing` with no accepted parent or purpose.
#### Scenario: Root branch
- **WHEN** the branch is `main`
- **THEN** Holodeck reports `root` with no parent or fork.
#### Scenario: Record state is visible
- **WHEN** the dashboard renders a branch
- **THEN** it shows lineage type, relationship, update reason, verification and review state, record and evidence details, and validation errors; an unaccepted declared parent is never rendered as clickable truth.

### Requirement: Branch Commits API
The system SHALL serve paged full commit messages for branches present in the snapshot.
#### Scenario: Commits are paged
- **WHEN** a client requests `GET /api/branch-commits` for a known branch with skip and limit
- **THEN** the system resolves the local or origin ref and returns commits with sha, author, date, subject, and full body, plus a has-more flag.
#### Scenario: Unknown branch
- **WHEN** the requested branch is not in the snapshot's branches layer
- **THEN** the system returns not-found without invoking git on the input.

### Requirement: Branches Section
The dashboard SHALL render branches as their own numbered section with parent and tip-commit columns, worktree-colored branch names, and a commits drawer.
#### Scenario: Branch is inspected
- **WHEN** the user clicks a branch name in the table
- **THEN** a right-side drawer lists the last 20 full commit messages with timestamps and a Load more button while more exist.
#### Scenario: Worktree card links to branch
- **WHEN** the user clicks the branch name inside a worktree card
- **THEN** the page scrolls to that branch's row in the Branches section and highlights it briefly.

### Requirement: Startup Auto-Refresh
The system SHALL start one background full collection at server startup when the snapshot is missing or older than 30 minutes and the refresh lock is available.
#### Scenario: Stale snapshot at startup
- **WHEN** the server starts and the snapshot's generated time is older than 30 minutes
- **THEN** the system starts a background collect run and logs that it started.

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
- **THEN** the dashboard shows relative and absolute snapshot generation time with the refresh control adjacent, and a warning strip for any layer metadata errors.
#### Scenario: Stat tiles render and navigate
- **WHEN** a snapshot is loaded
- **THEN** the overview shows exactly five clickable stat tiles in one row (worktrees with dirty subtext, branches, open PRs, apps, AI sessions), each scrolling to its section.
#### Scenario: Overview panels render
- **WHEN** a snapshot is loaded
- **THEN** the overview shows two half-width panels: Status (the dev-cycle rollup, see Dev-Cycle Tracker) and the worktree-keyed Latest activity feed with platform tags, message snippets, and relative times; the next-steps API and stored data remain available without an overview panel.

### Requirement: Dashboard Entity Views
The system SHALL render navigable dashboard sections numbered 00 Overview, 01 Worktrees, 02 Branches, 03 Apps, 04 Core, 05 Skills, 06 Specs, 07 AI Sessions, 08 Deploy, with each section's descriptive lede as a heading tooltip instead of body text.
#### Scenario: Git sections render
- **WHEN** worktree and branch layers are present
- **THEN** the Worktrees section renders interactive worktree work cards (see Interactive Worktree Cards) and the Branches section renders the branch table (see Branches Section).
#### Scenario: App and spec sections render
- **WHEN** app, core, and specs layers are present
- **THEN** the dashboard renders filterable expand/collapse app cards with stage and spec-stage pills and worktree chips, a core module table, and OpenSpec cards whose spec, change, and archive entries open in the file drawer.
#### Scenario: Session and deploy sections render
- **WHEN** session and deploy layers are present
- **THEN** the dashboard renders the "AI Sessions" section with filterable rows and a lazy message drawer, and deploy entries grouped by kind.

### Requirement: Dashboard Local Interactions
The system SHALL support local interactions for filtering, copying text, refreshing, navigation highlighting, and session drawer dismissal.
#### Scenario: Filters and search are used
- **WHEN** a user changes app or session filters or search inputs
- **THEN** the dashboard rerenders the matching cards or rows from the in-memory snapshot.
#### Scenario: Copy button is clicked
- **WHEN** a user clicks a copy button for a path, command, or test command
- **THEN** the dashboard copies the text to the clipboard using the browser clipboard API or textarea fallback and briefly changes the button label.
#### Scenario: Drawer jumps to the end
- **WHEN** the user clicks the down-arrow button below the drawer close button
- **THEN** the drawer body scrolls to the final message of the thread.
#### Scenario: Session drawer is closed
- **WHEN** a user presses Escape, clicks the backdrop, or clicks the close button
- **THEN** the dashboard hides the session drawer and marks it aria-hidden.

### Requirement: Interactive Worktree Cards
The dashboard SHALL render worktree cards as an editable work-management surface backed by the state APIs.
#### Scenario: Collapsed card content
- **WHEN** a worktree card is collapsed
- **THEN** it shows the colored title bar, branch name (linking to the Branches section row), the ACTIVE/INACTIVE toggle badge, the primary-AI-interface pulldown and next-step checklist, apps-touched chips, and the last three matching sessions with hover tooltips showing each session's last user message and click-through to the session drawer — without path or drift details.
#### Scenario: Card expands
- **WHEN** the user clicks the card's title bar or chevron
- **THEN** it expands to full grid width adding path, drift badges, last commit, PR, recent sessions, and notes; the page scrolls so that card's title bar sits at the top of the viewport (same on collapse); clicking the title bar or chevron again collapses it; and clicks elsewhere in the card never toggle expansion.
#### Scenario: Cards are reordered
- **WHEN** the user drags a card or uses move-to-top
- **THEN** the new active-card order persists via the worktree-order API and survives reload.
#### Scenario: Inactive worktree
- **WHEN** the user clicks the ACTIVE badge to make a card inactive
- **THEN** deactivated_at is stamped, the card dims (inactive state, not Cursor-open state, drives dimming) and moves immediately to the top of the inactive group, which sorts by deactivated_at descending after all active cards.

### Requirement: File Drawer
The dashboard SHALL open spec and registry file references in a drawer that renders content read-only and offers edit-and-save only for write-allowlisted paths outside sample mode.
#### Scenario: Spec file is viewed and edited
- **WHEN** the user opens an OpenSpec file from an app card or the specs section and saves an edit
- **THEN** the client GETs the file, renders escaped content, and persists the change via the file write API with visible success or error feedback.

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
The system SHALL produce LLM digests per exchange (title, asked bullets, notes bullets, recap preferring the response's own recap text) with claude-sonnet-5, cache them permanently, and auto-digest recent operator exchanges after each turns refresh in addition to on-demand generation.
#### Scenario: Digest on demand
- **WHEN** the user clicks Summarize on an undigested exchange (or runs the CLI with --digest)
- **THEN** one LLM call produces strict-JSON asked/notes/recap stored in the digests table; digests are never generated in bulk during collection, and a missing API key degrades with a clear message.

### Requirement: Turns View
The dashboard session drawer SHALL open with a turns view showing each exchange's kind, digest bullets, recap, and linked commits, with a full-response expander and the raw message list collapsed below.
#### Scenario: Exchange is reviewed
- **WHEN** the user opens a session from Status, a worktree card, or AI Sessions
- **THEN** the drawer lists that session's exchanges with digests where present, a Summarize button where absent, and linked commits with sha and subject.

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
#### Scenario: Session-end command is not waiting on AI
- **WHEN** the latest operator user text is a session-end command (`/close`, `close`, `/exit`, `exit`, `/quit`, or `quit`) with no AI response
- **THEN** that exchange is ignored for turn status (and skipped at ingest on rebuild), and the status row uses the prior answered exchange as YOUR TURN — or YOUR TURN on the end command itself when no prior exchange exists.

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
