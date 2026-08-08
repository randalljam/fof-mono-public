# Delta: macos-focus-activation

## ADDED Requirements

### Requirement: Local Cursor Focus API
The system SHALL expose a loopback-only semantic focus action for allowlisted macOS targets without accepting arbitrary executable input.
#### Scenario: Cursor worktree is focused
- **WHEN** an authorized local client posts a Cursor target with a canonical path for a live repo worktree and exactly one live Cursor window matches
- **THEN** the system raises that window, activates Cursor, and returns a structured focused result.
#### Scenario: Snapshot is stale
- **WHEN** `cursor_open` was true in the snapshot but no matching live window exists at click time
- **THEN** the system returns `target_not_found` and does not open a new Cursor window.
#### Scenario: Match is ambiguous
- **WHEN** more than one live window or tab satisfies the validated matcher
- **THEN** the system returns `ambiguous_match` without choosing a target.
#### Scenario: Request is unsafe
- **WHEN** a request is nonlocal/cross-site, lacks the required JSON action header, names an unknown target or field, or supplies a Cursor path outside the live repo worktrees
- **THEN** the system rejects it before running automation.
#### Scenario: Host is unsupported
- **WHEN** focus is requested on a non-macOS host
- **THEN** the system returns `unsupported_platform` without invoking a subprocess.

### Requirement: Activation Adapter Boundary
The system SHALL dispatch only fixed, reviewed macOS adapters with bounded execution and privacy-safe structured results.
#### Scenario: Adapter is invoked
- **WHEN** a validated target is dispatched
- **THEN** the system runs a checked-in script through a fixed `/usr/bin/osascript` argument vector with `shell=False`, a short timeout, bounded output, and matcher values passed separately from script source.
#### Scenario: Activation cannot complete
- **WHEN** an app is not running, a target is absent, permissions are missing, another focus operation is active, automation times out, or the adapter fails
- **THEN** the system returns the corresponding stable error code without returning candidate titles, URLs, or raw automation output.

### Requirement: Cursor Focus Control
The dashboard SHALL use the Cursor snapshot status as a rendering hint and live activation as the source of truth.
#### Scenario: Cursor was open at snapshot time
- **WHEN** a worktree card has `cursor_open` true outside sample mode
- **THEN** its `open in Cursor` pill is an accessible focus control that is a sibling of a dedicated expand control, sends the worktree path to the focus API, and never toggles card expansion.
#### Scenario: Cursor was not open at snapshot time
- **WHEN** a worktree card has `cursor_open` false, or the dashboard is in sample mode
- **THEN** the Cursor pill remains non-actionable.
#### Scenario: Focus result is reported
- **WHEN** a focus request is pending, succeeds, or fails
- **THEN** the card exposes a local accessible status and actionable guidance for stale state, ambiguity, permissions, or retryable automation errors.
