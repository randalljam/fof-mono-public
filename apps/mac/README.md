# macOS utilities

`apps/mac/` holds reusable local macOS automation and utility code. It is not a server and exposes no remote control surface.

## Window activation

`window_activation.py` focuses targets that are already open:

```python
from apps.mac.window_activation import focus_browser_tab, focus_cursor_window

focus_cursor_window(
    "/absolute/worktree/path",
    title_candidates=["feature-name"],
    document_roots=["/absolute/worktree/path", "/absolute/workspace/shared-folder"],
)
focus_browser_tab("chrome", url="https://example.com/exact-url")
focus_browser_tab("safari", title="Exact tab title")
```

The module runs only the reviewed scripts in `apps/mac/scripts/`, passes match values as separate `osascript` arguments, never uses a shell, never launches a missing app, and fails when zero or multiple targets match. Cursor matching considers only standard editor windows, lets callers omit title candidates when a folder basename is ambiguous, and never lets a title match override a usable document path outside the caller-authorized roots. Additional document roots support folders parsed from a multi-root `.code-workspace`; they are accepted only together with its workspace title. The adapter reports success only after the requested window is uniquely rematched as Cursor's main window and Cursor is frontmost. Browser URL/title comparisons are exact.

Cursor uses `System Events` UI scripting and therefore needs Accessibility permission; it may also prompt for Automation permission. Chrome and Safari use their native scripting dictionaries and normally need Automation permission. macOS shows these under System Settings -> Privacy & Security -> Accessibility and Automation. The permission may be attributed to Terminal, Python, `osascript`, or the app that launched the Python process.

On first use, a macOS permission prompt can outlast the adapter timeout. Approve the named launcher or browser and retry. The Cursor adapter activates the already-running app before enumeration because macOS can hide its Accessibility windows while Cursor is on another Space, then uses bounded polling to allow a target-Space transition to finish. Ordinary cross-Space windows are covered; full-screen behavior remains dependent on the user's macOS Space-switching settings.

Run the reusable module tests from the repo root:

```bash
.venv/bin/python3 -m pytest apps/mac/tests -q
```
