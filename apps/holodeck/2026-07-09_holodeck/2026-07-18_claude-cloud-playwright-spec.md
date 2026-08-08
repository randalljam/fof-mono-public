file: 2026-07-18_claude-cloud-playwright-spec.md
title: Holodeck Claude cloud — Playwright transport (real-browser session)
last-updated: 2026-07-18_0900
ai: Claude Code - Fable 5 (fable5-w-codex orchestration)
session: `holodeck control center build`

# Claude cloud Playwright transport — build spec (branch feature/holodeck-commits)

Backend-only. The claude.ai `/v1/code` API is behind Cloudflare AND requires the full browser session (a valid `sessionKey` cookie alone returns 401 even after curl_cffi clears Cloudflare — verified 2026-07-18). Solution: fetch via a real Playwright Chromium persistent context that holds the logged-in session. Preserve existing behavior; keep tests green. Style: no type hints, no blank lines between functions, `### ` headers.

## Facts (verified)
- `playwright` (python) is installed; Chromium is cached at `~/Library/Caches/ms-playwright` — the collector MUST set `os.environ["PLAYWRIGHT_BROWSERS_PATH"]` to that path (default `Path.home()/ "Library/Caches/ms-playwright"`) before launching, or Chromium isn't found.
- API (unchanged from the verified poller): base `https://claude.ai`, header `anthropic-version: 2023-06-01`; list `/v1/code/sessions?statuses=active&statuses=paused&limit=50`; detail `/v1/code/sessions/{id}`; events `/v1/code/sessions/{id}/events?limit=500&sort_order=asc&cursor=<next_cursor>`. In a real browser context, cookies + Cloudflare are handled automatically.

## Design — add a Playwright transport to cloud_claude.py
- Profile dir: `PLAYWRIGHT_PROFILE = Path.home()/".holodeck/playwright-claude"` (persistent user-data-dir; survives runs; gitignored by location).
- `playwright_available()`: True if the `playwright` module imports.
- `claude_login(headed=True)` (also exposed as CLI `turns_cli.py cloud-claude-login`): launch `chromium.launch_persistent_context(PLAYWRIGHT_PROFILE, headless=False)`, open a page to `https://claude.ai/code`, then POLL every 3s (timeout 240s) a probe: `page.request.get("https://claude.ai/v1/code/sessions?statuses=active&limit=1", headers={"anthropic-version":...})` — when it returns 200, print "Claude cloud login captured" and close. If timeout, print "login not detected; re-run cloud-claude-login". This is the ONE-TIME interactive step.
- `playwright_api_get(path, params=None)`: launch `launch_persistent_context(PLAYWRIGHT_PROFILE, headless=True)`; open a page to `https://claude.ai` once (establishes origin); use `page.request.get(url, headers={"anthropic-version": API_VERSION})` for each call; parse JSON. Raise `CloudClaudeAuthError("run: turns_cli.py cloud-claude-login")` on 401/redirect-to-login; `CloudClaudeError` on launch failure. Reuse ONE context for a whole collection pass (pass the context into fetch_session_list/detail/events rather than launching per call) — add `playwright_session()` context-manager that yields a `get(path, params)` callable and closes the browser after.
- Transport selection in the existing fetchers: when `urlopen` is injected (tests) → urllib path (unchanged). Else if the Playwright profile exists AND playwright is available → Playwright transport. Else → curl_cffi (may 401). This makes Playwright the real-runtime default for Claude once logged in, without breaking tests.
- `collect_cloud_claude(...)` (the ingest entry): if no session key AND no Playwright profile → skip with AUTH_MISSING note. If Playwright profile exists → use it. Wrap the whole pass so a launch/timeout failure degrades to a note, never raises into the build.

## Wire-in
- `ingest.py` / `turns_cli.py`: unchanged flow; Claude cloud ingest now succeeds when the Playwright profile is logged in. Add `cloud-claude-login` subcommand to turns_cli.py that calls `claude_login()`.
- `server.py` cloud-status claude probe: if the Playwright profile exists, report `ok` when a headless probe returns 200, `expired` when it needs re-login; if no profile and no key, `absent` with hint "run turns_cli.py cloud-claude-login". (Keep it cheap/cached; a headless launch is heavier — cache 300s.)
- `requirements.txt`: add `playwright`. README: document the one-time `cloud-claude-login` and that Chromium must be installed (`playwright install chromium`).
- `.gitignore`: ensure `~/.holodeck/` isn't relevant (it's outside repo); nothing to add.

## Tests (no network, no browser launch)
- Transport selection: injected urlopen → urllib path (existing tests unchanged); assert playwright path chosen only when profile dir exists AND playwright importable (monkeypatch a fake `playwright_available` + `PLAYWRIGHT_PROFILE.exists`).
- `playwright_session` get→parse wiring with a fake get callable (returns fixture JSON) → events_to_messages/to_session produce correct exchanges (reuse existing fixtures).
- Auth/absent skip notes.
- Keep all existing tests green.

## Acceptance
- `turns_cli.py cloud-claude-login` opens a headed Chromium; after the user logs into claude.ai, it captures the session and exits 0.
- `turns_cli.py build` then ingests real Claude cloud sessions (the "Branch naming convention for Holodeck" session appears as a `claude-cloud:` operator session with the full prompt + assistant events, correlated to its branch commits).
- Without the profile: clean skip; everything else unaffected.
- All tests green. Report files changed, verification, deviations.
