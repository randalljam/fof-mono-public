file: skills/coding/change-snapshots/README.md
title: Change snapshots — screenshot this turn's UI changes into a phone-friendly page
source-github-url: original
source-guide-url: original
history:
  - 2026-07-25 · Randy · Claude Code (Fable 5) — initial skill: Playwright captures → gitignored data folder → HTML page served by the app's local dev server

**Use this skill when the user asks for "change snapshots" / "snap the changes" at the end of a coding turn.** The agent screenshots the key UI states it changed this turn, writes them plus one-line captions into a small HTML page in a gitignored data folder, and hands back a link the user can open on their phone — no click-through of the app needed to see what changed.


## Output contract
- **Folder:** `<app>/data/change-snapshots/<YYYY-MM-DD_HHMMSS>_<shortsha>/` — Pacific timestamp plus the short SHA of the **final commit of this round of commits**. The repo-wide `data/` gitignore rule keeps it out of git (verify with `git check-ignore`); placing it under the app dir means the app's local dev server serves it.
- **Contents:** the `.png` screenshots, a `manifest.json` (see below), and the generated `index.html`.
- **Link:** printed at the end of the turn. Local serving is the default:
  `http://<host>:<port>/data/change-snapshots/<folder>/index.html` on the app's dev server (for math-quiz: `tools/dev_server.py`, port 8907). For phone access give the Mac's LAN IP (`ipconfig getifaddr en0`), not `127.0.0.1`.
- **Publish option:** local-only by default. "Push it live" (S3 or a hosted page) is an explicit user opt-in and is **not yet implemented** — say so and offer the local link if asked.


## Procedure
1. **Scope the shots.** List the user-visible states this turn changed (new buttons, panels, layouts, flows). 3–6 shots is the sweet spot; each needs a one-line caption saying what changed.
2. **Capture with Playwright.** Write a throwaway driver script (scratchpad or a dot-file inside the app's `tests/` dir so `@playwright/test` resolves from its `node_modules`; delete it after). Serve the app on a scratch port (`python3 -m http.server`) or reuse the e2e server setup; drive to each changed state exactly like the app's e2e specs do (query-param overrides like `?setup=1`, `?fb=0`, `?teachms=` keep it fast); prefer element screenshots (`locator.screenshot()`) of the changed card/panel over full pages.
3. **Write `manifest.json`** in the output folder:
   ```json
   { "title": "…", "branch": "…", "commit": "<shortsha>", "stamp": "YYYY-MM-DD_HHMMSS",
     "summary": "one-line turn summary",
     "items": [ { "image": "01_thing.png", "caption": "what changed here" } ] }
   ```
4. **Generate the page:** `python3 skills/coding/change-snapshots/scripts/build_snapshot_page.py <output-folder>` — reads `manifest.json`, writes `index.html` (mobile-friendly, images full-width, caption under each).
5. **Verify + link.** `git check-ignore` the folder; confirm the dev server serves the URL (curl the index) when it's running; print the phone-ready link (LAN IP) as the last line of the turn.

## Notes
- Screenshots may contain learner names/data — the gitignored data folder is the point; never commit them or move them into the repo tree.
- Correlate to the **final** commit of the round: run the captures after the last commit, so the page reflects exactly what was pushed.
