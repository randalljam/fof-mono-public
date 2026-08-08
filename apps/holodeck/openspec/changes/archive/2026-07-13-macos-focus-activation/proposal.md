# Proposal: macos-focus-activation

## Why
Holodeck already reports whether each worktree was open in Cursor when the snapshot was collected, but the status pill is display-only. The dashboard should become a safe launcher for already-open local work: first by focusing the matching Cursor window, then by reusing the same boundary for Chrome and Safari tabs.

## What Changes
- Add a local-only `POST /api/focus` action with a fixed target/matcher schema, structured results, and no browser-supplied commands, scripts, process names, or bundle IDs.
- Add a small macOS activation dispatcher. Use checked-in AppleScript invoked by `/usr/bin/osascript`: Accessibility UI scripting for Cursor and native scripting dictionaries for Chrome and Safari.
- Turn the `open in Cursor` pill into an accessible button when `cursor_open` is true. Resolve the worktree and enumerate windows live on every click; the snapshot remains only a rendering hint.
- Return actionable inline feedback for closed, missing, ambiguous, permission-denied, timed-out, and unsupported targets.
- Keep Holodeck's first caller Cursor-only. Put exact-match Chrome and Safari adapters in the reusable `apps/mac` boundary so later application changes can add concrete, allowlisted callers without duplicating automation code.

## Recommended Approach
AppleScript is the lightest built-in bridge from the existing Python/FastAPI process. Cursor has no scripting dictionary on the target Mac, so its adapter must use `System Events` and fail closed unless one Accessibility window uniquely matches the live worktree. Chrome and Safari expose scriptable windows, tabs, URLs, and titles, making native Apple Events preferable to UI clicking for those phases.

## Non-Goals
- Opening a worktree that is not already open in Cursor.
- Navigating, creating, closing, or modifying browser tabs.
- Arbitrary shell/AppleScript execution, remote control, non-macOS activation, or remote-host support.
- A signed native helper in v1.

## Impact
- Reusable macOS boundary: `apps/mac/window_activation.py`, reviewed scripts under `apps/mac/scripts/`, focused tests, and `apps/mac/README.md`.
- Holodeck caller: `server.py`, `web/app.js`, `web/style.css`, API/web tests, README/registry updates, and the living OpenSpec.
