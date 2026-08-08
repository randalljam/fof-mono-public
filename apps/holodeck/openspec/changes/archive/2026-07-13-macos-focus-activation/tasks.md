# Tasks: macos-focus-activation

## Cursor feasibility
- [x] Inspect live Cursor Accessibility window names and `AXDocument`; ordinary Cursor windows expose usable titles while `AXDocument` is present but empty on the target Mac.
- [x] Verify unique ordinary-window activation, restore and raise a minimized window, and fail closed when a common candidate matches multiple Cursor windows.
- [x] Document full-screen/other-Space behavior as platform-dependent rather than making it a gate for the ordinary Cursor slice.

## Reusable macOS activation boundary
- [x] Add a stdlib-only Python module under `apps/mac` with fixed target adapters, stable result/error codes, bounded validation and execution, `shell=False`, and privacy-safe output handling.
- [x] Add reviewed Cursor, Chrome, and Safari AppleScripts that refuse to launch missing apps and require one unique live match.
- [x] Match Cursor by live Accessibility path/title data and browser tabs by exact URL and/or title; pass every matcher as a separate `osascript` argument.
- [x] Add unit tests for validation, argv safety, protocol parsing, ambiguity, permission redaction, timeouts, non-macOS behavior, and the checked-in scripts; compile all three scripts on macOS.
- [x] Document reusable calls, permissions, first-prompt retry behavior, and Space/full-screen limitations in `apps/mac/README.md`.

## Holodeck Cursor slice
- [x] Add Cursor-only `POST /api/focus` with a separate nonblocking lock, loopback peer/Host and same-origin checks, JSON plus fixed action-header requirements, and authorization against a fresh live git-worktree list.
- [x] Keep snapshot `cursor_open` unchanged as a rendering hint while live Accessibility windows remain authoritative for every click.
- [x] Make the open-state pill an accessible focus button outside sample mode, with sibling expand/focus controls and pending, success, permission, and failure status; focusing never toggles card expansion.
- [x] Add mocked FastAPI coverage for success, stable errors, invalid schemas, foreign clients, wrong content/header, lock contention, and safe unexpected failures without invoking TCC.
- [x] Add frontend source/parse smoke checks and exercise the live dashboard pointer path, success status, unchanged expansion state, and static sample-mode pill.
- [x] Update explicit loopback run commands, API/security/permission docs, the roadmap, and the living app specification.

## Deferred callers
- [x] Keep Chrome and Safari out of Holodeck's API until a later change defines concrete URL/title targets; no navigation, arbitrary browser matcher, or generic remote-control endpoint was added.
