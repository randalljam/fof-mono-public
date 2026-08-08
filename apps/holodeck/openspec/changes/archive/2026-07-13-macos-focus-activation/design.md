# Design: macos-focus-activation

## Decision
Add a narrow reusable Python activation service under `apps/mac` with an explicit adapter registry (`cursor`, `chrome`, and `safari`) and reviewed AppleScript files invoked as argument arrays through `/usr/bin/osascript`. Use no new runtime dependency. Holodeck exposes only the Cursor caller in this change; browser adapters remain library capabilities until a concrete application supplies an allowlisted target.

The target Mac confirms the split: Cursor (`com.todesktop.230313mzl4w4u92`) has no scripting dictionary, while Chrome and Safari expose native window/tab scripting. Apple recommends `System Events` UI scripting when an app lacks the required scripting support; UI scripting relies on Accessibility permission ([Apple UI-scripting guide](https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/AutomatetheUserInterface.html)).

## Request flow
1. The card renders an action only when snapshot field `cursor_open` is true.
2. The client sends a semantic request, never executable input.
3. The server validates the local request and target-specific schema, then resolves a Cursor path against a fresh `git worktree list --porcelain` result.
4. The adapter confirms the target process is already running and queries live Accessibility windows. It derives candidates server-side from the canonical path, folder basename, and `.code-workspace` name; a fresh read of Cursor `windowsState.openedWindows` may add workspace-name hints but must never veto a unique live AX match.
5. One unique match is unminimized, raised, and brought frontmost. The adapter never calls `activate` before that live-process/match check, so a missing app is not launched. Zero or multiple matches fail without focusing an arbitrary window.
6. The UI shows a local result. It does not mutate the snapshot or trigger a refresh after success.

This deliberately separates two facts: the snapshot says an action was likely available when collected; the click-time OS query decides whether activation is possible now. A stale true becomes `target_not_found`. A stale false remains display-only until the next Worktrees refresh in v1.

## API sketch
Cursor v1:
```http
POST /api/focus
Content-Type: application/json
X-Holodeck-Action: focus

{
  "target": "cursor",
  "matcher": {"worktree_path": "/Users/randytrue/Documents/Code/feature-holodeck-start"}
}
```

Future browser shape:
```json
{
  "target": "chrome",
  "matcher": {
    "url": "https://example.test/path",
    "title": "Optional exact title",
    "mode": "exact"
  }
}
```

For the first browser phases, require URL and/or title and compare each supplied value exactly with the string reported by the browser. When both fields are supplied, both must match. Do not silently normalize trailing slashes, fragments, ports, percent encoding, query order, or redirects. A separately specified later change may add bounded `contains` or explicit URL-normalization modes. Detect duplicates across windows/profiles and return ambiguity.

Success:
```json
{"ok": true, "target": "cursor", "status": "focused", "matched_by": "title"}
```

Errors use a stable body, for example `{"ok":false,"error":{"code":"target_not_found","message":"Cursor window is no longer open."}}`:

| HTTP | Codes |
|---|---|
| 400 | `invalid_request` |
| 403 | `forbidden_client` |
| 404 | `app_not_running`, `target_not_found` |
| 409 | `ambiguous_match`, `focus_busy` |
| 501 | `unsupported_platform` |
| 502 | `automation_failed` |
| 503 | `permission_required` |
| 504 | `automation_timeout` |

Responses and logs must not include the full window/tab inventory, raw browser URLs or titles, or raw automation stderr. Log only target, coarse result, duration, and a stable worktree identifier.

## Security boundary
- Bind and document the server explicitly on `127.0.0.1`; also verify the focus request's peer is loopback and reject forwarded-client assumptions.
- Allow only loopback Host values and same-origin requests when `Origin` is present; reject cross-site `Sec-Fetch-Site` values.
- Require JSON and the custom action header. Do not enable permissive CORS. A future proxy or remote mode requires real authentication rather than weakening these checks.
- Reject unknown fields, bundle IDs, process names, commands, script source, regexes, control characters, and oversized matcher values.
- For Cursor v1, accept only a canonical path that exactly matches a live repo worktree. Derive all window-title candidates on the server.
- Invoke fixed, checked-in scripts with `subprocess.run([...], shell=False, timeout=3-5, capture_output=True)`. Pass values as separate argv entries, never source interpolation. Bound captured output.
- Serialize focus operations with a separate nonblocking lock because foreground activation is global; do not share the refresh or state locks.

## UI behavior
- Replace the open-state `<span>` with a `.pill.open` button only outside sample mode; retain a static `not open` pill when false.
- Restructure the current title bar so the focus button is not nested inside an element with `role="button"`: use a non-interactive group containing sibling expand and focus controls. Keep pointer expansion on the title area through the dedicated expand control, preserve Enter/Space and logical focus order, and ensure focus activation never changes card expansion state.
- Add an explicit accessible label, disable the focus control while pending, and expose local status through `aria-live`.
- Use `Focusing...` then briefly `Focused` on success. On not-found, locally demote the control and say to refresh Worktrees. On ambiguity, explain that multiple windows matched without exposing their titles. On TCC failure, keep a Retry action and show setup guidance.

## Permissions
Cursor selection through `System Events` needs Accessibility approval and may also prompt for Automation. Direct Chrome/Safari scripting normally needs Automation approval for each browser, without Accessibility. macOS exposes these under System Settings -> Privacy & Security -> Accessibility and Automation ([Apple Accessibility guidance](https://support.apple.com/guide/mac-help/mh43185/mac), [Apple Automation guidance](https://support.apple.com/guide/mac-help/mchl07817563/mac)).

During development, macOS may attribute approval to Terminal, the Python interpreter, `osascript`, or another launcher. Onboarding must name what the user actually sees and recommend restarting/retrying after approval. A later signed helper would provide a stable TCC identity; it is not needed for v1.

## Alternatives considered
| Approach | Decision |
|---|---|
| AppleScript via `osascript` | Recommended: built in, auditable, and native Chrome/Safari support. |
| JXA via `osascript -l JavaScript` | Same Apple Events/TCC model with less ergonomic app terminology; no needed capability gain. |
| Swift/ObjC Accessibility helper | Strong long-term option for a packaged/signed Holodeck, but too much build, signing, and distribution work for v1. |
| PyObjC | Adds a dependency without solving TCC identity or Cursor matching. |
| `open -a` | Can activate or open resources but cannot reliably select one existing Cursor window or browser tab and may create new UI. |
| Hammerspoon/yabai/cliclick | Adds installation and permission burden; reserve for a proven built-in API gap. |

## Main risks and feasibility gate
The largest risk was correlating worktree paths with Accessibility windows: Cursor storage has no AX window identifier and can lag. Live inspection on the target Mac found useful window titles while `AXDocument` was present but empty. The shipped fallback therefore accepts only an exact candidate title or the verified `editor — workspace`/`Git Graph — workspace` convention with the workspace candidate at the end; it does not accept a candidate at the start, where a same-named file could produce a false match. Ordinary and minimized unique windows passed live checks, and duplicate candidates fail closed. Full-screen/other-Space behavior remains documented as a platform-dependent limitation.

Browser risks are duplicate URLs across profiles/windows, Chrome incognito behavior, and Safari private windows/Tab Groups. Each adapter must query live state and fail closed on ambiguity.
