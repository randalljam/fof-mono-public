file: skills/browser/hard-reload-tab/README.md
title: Hard-reload a unique Chrome tab (macOS / Holodeck)
source-github-url: original
source-guide-url: original
history:
  - 2026-08-04 · Randy · Cursor [Holodeck hard-reload skills](df1f7167-f419-47fa-94ba-9cef9cfccc51) — use bring-tab-to-front front-window-only path (no sibling minimize / no process frontmost)
  - 2026-08-04 · Randy · Cursor [Holodeck hard-reload skills](df1f7167-f419-47fa-94ba-9cef9cfccc51) — note sibling-window minimize behavior from bring-tab-to-front (process frontmost otherwise surfaces all Chrome windows)
  - 2026-08-04 · Randy · Cursor [Holodeck hard-reload skills](df1f7167-f419-47fa-94ba-9cef9cfccc51) — initial skill; Holodeck Chrome hard-reload + soft-reload


## Holodeck Chrome hard-reload (macOS) — REQUIRED procedure

Holodeck local UI: http://127.0.0.1:8790/  (URL may include a hash, e.g. #active-ai)

### Hard rules
1. NEVER target by Chrome window index (`window 1`, `window 2`, etc.). Indices change with focus and lie.
2. NEVER send Cmd+Shift+R until you have VERIFIED that the frontmost Chrome tab URL contains `127.0.0.1:8790`.
3. NEVER use `set index of <window> to 1` as your only focus step — it often fails to raise the OS window; keystrokes then hit the wrong window.
4. Identify Holodeck ONLY by URL containing `127.0.0.1:8790`. If 0 matches → abort. If >1 matches → abort (do not guess).
5. Do not assume tab 1 of the “other” window — always scan every tab of every window.

### Correct hard-reload sequence (osascript, needs full permissions / not sandboxed)
1. In Google Chrome AppleScript: find the unique tab whose URL contains `127.0.0.1:8790`; set that window’s `active tab index` to that tab.
2. Raise only the Holodeck Chrome window (see `skills/browser/bring-tab-to-front/README.md`):
   - snapshot sibling Chrome window geometry/index/minimized (never minimize them as a workaround)
   - Window menu → Holodeck tab title; `AXRaise` + `AXMain`
   - front-window-only process activate (`SetFrontProcessWithOptions` FrontWindowOnly) — not System Events `set frontmost`
   - restore sibling snapshots
3. Poll until `URL of active tab of front window` contains `127.0.0.1:8790` (e.g. up to ~3s). If it never matches → ABORT and report the actual front URL. Do not keystroke.
4. Only then: System Events → keystroke "r" using {command down, shift down}.

Focus steps 1–3 are implemented by the subset skill
`skills/browser/bring-tab-to-front/README.md`. Prefer that script (or this wrapper) over
re-implementing focus inline.

### Soft reload (no focus needed; use when hard reload is not required)
- Find the tab object by URL `127.0.0.1:8790`, then `reload` that tab object directly.
- This does not need AXRaise or keyboard and cannot hit the wrong window.

### Do NOT rely on
- `execute <tab> javascript "location.reload(true)"` unless the user has enabled Chrome: View → Developer → Allow JavaScript from Apple Events (often off; error is explicit).
- Blind `activate` + `window 1` + Cmd+Shift+R.
- `apps/mac/scripts/focus_chrome.applescript` alone — exact URL + `set index … to 1` without AXRaise / front-URL verify.

### One-liner success check to report
Return: matched URL/title AND the front-tab URL/title immediately before the keystroke. Both must contain `127.0.0.1:8790`.


## Script
```bash
# hard reload (default) — focus via bring-tab-to-front, verify front URL, then Cmd+Shift+R
skills/browser/hard-reload-tab/scripts/hard_reload_tab.sh

# soft reload — reload tab object by URL; no focus / no keystrokes
skills/browser/hard-reload-tab/scripts/hard_reload_tab.sh --soft

# optional overrides: urlNeedle  windowNamePrefix
skills/browser/hard-reload-tab/scripts/hard_reload_tab.sh "127.0.0.1:8790" "holodeck"
skills/browser/hard-reload-tab/scripts/hard_reload_tab.sh --soft "127.0.0.1:8790"
```

Run outside the sandbox (`required_permissions: ["all"]` in Cursor Shell). Needs macOS
Automation (+ Accessibility for System Events AXRaise / keystroke).

### Soft-only AppleScript
```bash
osascript skills/browser/hard-reload-tab/scripts/soft_reload_tab.applescript
osascript skills/browser/hard-reload-tab/scripts/soft_reload_tab.applescript "127.0.0.1:8790"
```


## Related
- Focus-only subset: `skills/browser/bring-tab-to-front/README.md`
