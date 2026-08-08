file: 2026-07-19_refresh-sync-spec.md
title: Holodeck — fold AI-session sync + S3 archive into Refresh
last-updated: 2026-07-19_1030
ai: Claude Code - Fable 5 (fable5-w-codex orchestration)
session: `holodeck control center build`

# Refresh = full AI-session sync — build spec (branch feature/holodeck-commits)

The dashboard Refresh must do everything automatable to sync AI sessions — NO separate button, NO bookmarklet. Preserve existing behavior; keep tests green. Style: no type hints, no blank lines between functions, `### ` headers.

## Constraint (do not try to work around)
The claude.ai `/v1/code` FETCH cannot run server-side: Cloudflare Turnstile blocks all automation (Playwright included), and only the user's logged-in browser passes. So Refresh automates everything EXCEPT the live claude.ai fetch: Codex cloud (its own token — automated), all local stores, ingest of any Claude export the user has already downloaded, and the S3 sync. The user's periodic browser export (console snippet → file in ~/Downloads) is the one manual step; Refresh then picks it up.

## Behavior — extend the existing POST /api/refresh (server.py)
After the snapshot collectors run (unchanged), Refresh ALSO performs, in a background thread guarded by a lock (never block the snapshot response beyond what it already does; return a combined status the frontend can poll or show):
1. **Downloads pickup**: move any `~/Downloads/holodeck-claude-cloud*.json` and `~/Downloads/holodeck-cc-*.json` into `~/Documents/Code/_LOCAL_FILES/fof-mono/ai-sessions/cloud_claude/` renamed `YYYY-MM-DD_HHMMSS_claude-cloud.json` (use the file mtime for the date; do not overwrite an identical existing file — compare size+mtime; skip dotfiles). Log how many moved. (Path helpers: home-relative; guard when Downloads or the mount is absent.)
2. **Turns rebuild**: run `turns_ingest.build(root=ROOT, db_path=TURNS_DB_PATH)` (this already ingests Codex cloud live + all local + any files in the cloud_claude_import dir). Reuse the existing TURNS_REFRESH_LOCK so it doesn't collide with /api/turns/refresh.
3. **S3 sync (best-effort)**: run `core/s3_archive.py build --area ai_sessions` then `upload --area ai_sessions --execute` as subprocesses (sys.executable, cwd=ROOT, 600s timeout each). Incremental (content-hash) so it's cheap when nothing changed. Capture stdout tail; on non-zero exit or missing AWS creds, record the error in the status but DO NOT fail the refresh. Never print/log AWS keys.
- The refresh response gains `ai_sync: {downloads_moved: int, turns: {...summary}, s3: {ok: bool, tail: str}}` (or an error string per step). Keep the existing snapshot refresh fields.
- Concurrency: if an AI-sync is already running, skip re-launching (single-flight), note "already running".

Also expose a tiny `GET /api/ai-sync-status` returning the last ai_sync result (so the frontend can show completion after the async work).

## Frontend (web/)
- The existing Refresh button is unchanged in placement. Update its flow: after POST /api/refresh, show a brief inline status that AI sessions are syncing, then poll `GET /api/ai-sync-status` (every ~3s, up to ~60s) and surface a one-line result: "AI sessions synced — N codex cloud, imported M claude exports, S3 ✓" or the error. Keep it subtle (near the snapshot line), dismissible, null-safe, no secrets.
- If cloud-status (existing) reports claude-cloud not fresh, the existing banner already hints to run the export; leave that.

## Tests (no network/browser/S3)
- Downloads-pickup pure helper: given a fake Downloads dir with matching + non-matching files, returns the correct move list; skips an identical existing target; ignores dotfiles. (tmp_path, monkeypatched home.)
- Refresh orchestration wiring: monkeypatch the turns build + s3 subprocess + pickup to fakes; assert /api/refresh returns the combined ai_sync shape and single-flights.
- ai-sync-status returns the last result.
- Keep all existing tests green.

## Acceptance
- Hitting Refresh (no new export present) runs turns rebuild + S3 sync incrementally and reports success without re-uploading unchanged data.
- Dropping a fresh Claude export in ~/Downloads, then Refresh: the file moves into the mount, gets ingested (new claude-cloud sessions), and S3-synced — all from the one button.
- Codex cloud is fetched live on every Refresh (no manual step).
- All tests green. Report files changed, verification, deviations.
