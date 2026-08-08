file: skills/browser/bring-tab-to-front/README.md
title: Bring a unique Chrome tab to the front (macOS)
source-github-url: original
source-guide-url: original
history:
  - 2026-08-04 · Randy · Cursor [Holodeck hard-reload skills](df1f7167-f419-47fa-94ba-9cef9cfccc51) — front-window-only activate + sibling snapshot/restore; no minimize; avoid process frontmost
  - 2026-08-04 · Randy · Cursor [Holodeck hard-reload skills](df1f7167-f419-47fa-94ba-9cef9cfccc51) — minimize sibling Chrome windows before process frontmost so only the matched window surfaces
  - 2026-08-04 · Randy · Cursor [Holodeck hard-reload skills](df1f7167-f419-47fa-94ba-9cef9cfccc51) — initial skill; focus-only subset of hard-reload-tab


**Raise one Google Chrome tab to the OS front by URL match.** Used when an agent must
focus Holodeck (or another unique local tab) before keystrokes. Does not reload.
Sibling Chrome windows stay where they were (not minimized, not forced above other apps).


## When to use
- Need the Holodeck UI tab frontmost before keyboard input (hard reload, paste, etc.).
- Parent skill `skills/browser/hard-reload-tab/README.md` needs focus verified first.
- Soft reload is not enough and you only need focus, not Cmd+Shift+R.


## Hard rules
1. NEVER target by Chrome window index (`window 1`, `window 2`, etc.). Indices change with focus and lie.
2. NEVER send keystrokes until you have VERIFIED that the frontmost Chrome tab URL contains the match needle (default `127.0.0.1:8790`).
3. NEVER use System Events `set frontmost` / blind `activate` as the focus step — that surfaces **every** Chrome window above other apps (breaks multi-monitor layouts).
4. Identify the target ONLY by URL containing the needle. If 0 matches → abort. If >1 matches → abort (do not guess).
5. Do not assume tab 1 of the “other” window — always scan every tab of every window.
6. Do not minimize sibling Chrome windows to “hide” them. Snapshot their geometry/index/minimized state and restore after raise.


## Procedure (osascript — needs full permissions / not sandboxed)
1. In Google Chrome AppleScript: find the unique tab whose URL contains the needle (default `127.0.0.1:8790`); set that window’s `active tab index` to that tab.
2. Snapshot sibling Chrome windows (active-tab title → Chrome index + miniaturized; System Events name → position/size/minimized).
3. Raise only that window:
   - Chrome **Window** menu → click the short tab title (makes it Chrome’s front window without activating the whole app)
   - `AXRaise` + `AXMain` on that System Events window
   - `activate_front_window_only.py <chromePID>` — `SetFrontProcessWithOptions(..., FrontWindowOnly)` so only Chrome’s front window comes above other apps
4. Restore sibling snapshots (index / miniaturized / position / size) so multi-monitor layouts stay put.
5. Poll until `URL of active tab of front window` contains the needle (e.g. up to ~3s). If it never matches → ABORT and report the actual front URL. Do not keystroke.


## Script
```bash
# defaults: urlNeedle=127.0.0.1:8790  windowNamePrefix=holodeck
skills/browser/bring-tab-to-front/scripts/bring_tab_to_front.sh

# custom needle / window-name prefix
skills/browser/bring-tab-to-front/scripts/bring_tab_to_front.sh "127.0.0.1:8790" "holodeck"
```

Run outside the sandbox (`required_permissions: ["all"]` in Cursor Shell). Needs macOS
Automation (+ Accessibility for System Events).

### Success output
One line, tab-separated:

```text
OK	<matchedURL>	<matchedTitle>	<frontURL>	<frontTitle>
```

Both URLs must contain the needle. Report matched URL/title **and** the front-tab URL/title.

### Abort output
```text
ABORT	<reason>	[detail...]
```

Stop and report the reason. Do not guess among multiple matches.


## Do NOT rely on
- System Events `set frontmost to true` on process "Google Chrome" — surfaces all Chrome windows.
- Minimizing siblings as a workaround.
- `apps/mac/scripts/focus_chrome.applescript` alone for Holodeck — exact URL + `set index of window to 1` without FrontWindowOnly / front-URL verify.
- Blind `activate` + `window 1`.
- Chrome window indices for targeting.
