file: apps/education/lesson-logger/dashboard/2026-06-09_fly-deploy-checklist.md
title: Lesson Logger Dashboard — Fly.io Deploy Checklist
last-updated: 2026-06-09_1258

Build plan:
[`/.cursor/plans/2026-06-09_direct_lesson_sync_37b245ef.plan.md`](../../../../.cursor/plans/2026-06-09_direct_lesson_sync_37b245ef.plan.md)


## Architecture
```
TL / Randy (Telegram)
  → Hermes agent ([FLY-APP-NAME], Fly)
    → save_lesson.py writes JSON + upserts /opt/data/lesson-logs/lessons.db
    → lesson_db_server.py serves a WAL-safe snapshot on Fly private networking

Dashboard app (fof-lesson-dash, Fly)
  → on cold start: GET http://[FLY-APP-NAME].internal:8081/lesson-logger/lessons.db
  → validates SQLite integrity, stores cached copy at /data/lessons.db
  → serves the read-only dashboard at https://fof-lesson-dash.fly.dev
```

**No runtime AWS/S3.** Lesson DB sync is direct Fly-to-Fly over private networking. Hermes
S3 backups remain separate Mac-side disaster recovery (`agents/hermes/hermes_backup.py`).

**Fly private networking requirement:** `[FLY-APP-NAME]` and `fof-lesson-dash` must be in
the same Fly org. `.internal` DNS resolves inside Fly's IPv6-only private network, so the
Hermes DB server binds to `::`.

**Dashboard cache behavior:** If Hermes is briefly unavailable, dashboard startup logs a
warning and keeps using the existing `/data/lessons.db` cache.


## Deployment Status (2026-06-09)
**Initial two-app deploy is COMPLETE.** This file is now a deploy log + redeploy/rollback
reference, not an open to-do list. Phases 1–5 below were all executed during the build
session and merged to `main` via PR #14.

- [x] **Phase 1** — code built, tested (43 dashboard tests), merged to `main`.
- [x] **Phase 2** — Hermes deployed; DB server runs on `[::]:8081`.
- [x] **Phase 3** — `fof-lesson-dash` app + `dashboard_data` volume + 4 auth secrets created.
- [x] **Phase 4** — dashboard deployed; reachable over `.internal` from startup.
- [x] **Phase 5** — browser verified; `randy` / `tl` return 200.

### ONE remaining action: redeploy Hermes for the HERMES_LESSONS_DB fix
The `HERMES_LESSONS_DB` env pin (commit `5e02e0b`) merged *after* the build-session deploy,
so the running Hermes machine still has the old config. Apply it with a single deploy —
a `fly.toml [env]` change only takes effect via `fly deploy` (not a machine/volume restart):

```bash
cd agents/hermes
fly deploy
fly status -a [FLY-APP-NAME]
./check_hermes.sh
```

Then verify real data flows end-to-end:
1. Log one real lesson via Telegram.
2. Restart the dashboard so it cold-starts and re-syncs:
   ```bash
   fly machine restart -a fof-lesson-dash
   fly logs -a fof-lesson-dash --no-tail | grep -i "synced\|sync failed"
   ```
   Expect `Synced N bytes from Hermes` — not a "missing entries table" rejection.
3. Open `https://fof-lesson-dash.fly.dev` and confirm the real lesson replaces the seeded
   dev sample.

Before assuming nothing needs migrating, check for pre-fix lessons at the old fallback path:
```bash
fly ssh console -a [FLY-APP-NAME] -C "sh -lc 'ls -la /opt/data/lesson-logs/lessons.db /opt/data/.hermes/lesson-logs/lessons.db 2>/dev/null'"
```
If a populated DB exists at `/opt/data/.hermes/lesson-logs/lessons.db`, copy it to
`/opt/data/lesson-logs/lessons.db` before logging new lessons.

### Until then
The dashboard volume is seeded with the synthetic `lessons_dev.db` and temporary dev auth
(`DASH_DEV_PASSWORDS=true`, `randy/randy` + `tl/tl`) is enabled, so the deployed
dashboard loads with sample data. Once real lessons flow, drop `DASH_DEV_PASSWORDS` and rely
on the real `DASH_PASS*` secrets.


## Phase 1: Code Build (agent-run)
Expected code changes from `feature/fly-fly-sync`:

- `agents/hermes/lesson_db_server.py` — IPv6 internal server, SQLite online-backup snapshot.
- `agents/hermes/run-fly-main.sh` — respawn loop for the DB server, while Hermes gateway remains s6-managed.
- `agents/hermes/Dockerfile` — copy DB server/wrapper; no boto3 install.
- `agents/hermes/fly.toml` — `LESSON_DB_PATH`, `LESSON_DB_SERVER_PORT`; no S3 runtime env.
- `apps/education/lesson-logger/scripts/save_lesson.py` — no S3 upload after DB upsert.
- Dashboard `sync_db.py`, `app.py`, `fly.toml`, `requirements.txt`, tests, README — direct Hermes sync.

Verification before deploy:

```bash
.venv/bin/python3 -m py_compile agents/hermes/lesson_db_server.py apps/education/lesson-logger/dashboard/sync_db.py apps/education/lesson-logger/scripts/save_lesson.py
cd apps/education/lesson-logger/dashboard
.venv/bin/pytest test_dashboard.py -v
```

Commit/push checkpoint after tests pass:

```bash
git commit -m "$(cat <<'EOF'
Replace lesson DB S3 sync with Fly private sync.

EOF
)"
git push
```


## Phase 2: Deploy Hermes (manual stop + verify)
Do this after Phase 1 is committed/pushed and merged to `main`, or when you intentionally
deploy from `feature/fly-fly-sync`.

```bash
cd agents/hermes
fly deploy
fly status -a [FLY-APP-NAME]
```

### Verify Hermes before continuing
```bash
fly status -a [FLY-APP-NAME]
fly logs -a [FLY-APP-NAME] --no-tail | grep -i "db-server\\|error\\|crash"
fly secrets list -a [FLY-APP-NAME]
```

Expected:
- Machine is `started`, not crash-looping.
- Logs include DB server startup, e.g. serving `/opt/data/lesson-logs/lessons.db` on `[::]:8081`.
- No AWS secrets are required for runtime lesson sync.
- `fly.toml` still has no public `[http_service]` for Hermes.

If Hermes crashes or the DB server does not start, stop here and inspect logs before
deploying the dashboard.


## Phase 3: Create Dashboard App (manual stop + verify)
Skip app/volume creation if `fof-lesson-dash` already exists.

```bash
cd apps/education/lesson-logger/dashboard

fly apps create fof-lesson-dash --org personal
fly volumes create dashboard_data -a fof-lesson-dash -r sjc -s 1 -y
```

Set Basic Auth secrets with real passwords:

```bash
fly secrets set -a fof-lesson-dash \
  DASH_USER1=randy \
  DASH_PASS1='<pick-a-real-password>' \
  DASH_USER2=tl \
  DASH_PASS2='<pick-a-real-password>'
```

The actual dashboard usernames/passwords are also stored locally in the repo-root `.env`
(gitignored) so scripts or future automations can read them programmatically if needed.
Do not commit or paste the values into markdown.

### Verify dashboard app setup before deploy
```bash
fly apps list | grep lesson
fly volumes list -a fof-lesson-dash
fly secrets list -a fof-lesson-dash
```

Expected:
- Dashboard app exists in the same Fly org as `[FLY-APP-NAME]`.
- One `dashboard_data` volume exists in `sjc`.
- Secret names include `DASH_USER1`, `DASH_PASS1`, `DASH_USER2`, `DASH_PASS2`.
- No `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` is needed for dashboard runtime sync.


## Phase 4: Deploy Dashboard (manual stop + verify)
```bash
cd apps/education/lesson-logger/dashboard
fly deploy -a fof-lesson-dash
```

### Verify dashboard deploy before browser test
```bash
fly status -a fof-lesson-dash
fly logs -a fof-lesson-dash --no-tail
```

Look for:
- Machine running or stopped (auto-stop is normal after startup).
- `Synced ... bytes from Hermes -> /data/lessons.db`.
- No crash loops.

If logs show `Hermes DB sync failed`, capture the full log line. The dashboard may still
serve a cached DB, but the sync issue should be diagnosed before calling deploy complete.


## Phase 5: End-To-End Browser Verification (manual stop + verify)
Open `https://fof-lesson-dash.fly.dev`.

Expected:
- Browser prompts for Basic Auth.
- The credentials from Phase 3 work.
- Dashboard loads with lesson data.
- After logging a new test lesson through Telegram and restarting or redeploying the
  dashboard, the new lesson appears without a manual SQLite checkpoint. This verifies
  the WAL-safe snapshot path.


## Manual Fallback: Pull DB From Hermes
For local inspection or emergency manual seeding:

```bash
cd apps/education/lesson-logger/dashboard
./sync_lessons_db_from_hermes.sh /tmp/lessons.db
```

This uses `fly ssh sftp` to pull `/opt/data/lesson-logs/lessons.db` from Hermes. It does
not upload to S3 and does not affect dashboard runtime sync.


## Rollback
```bash
# Check dashboard logs
fly logs -a fof-lesson-dash --no-tail

# SSH in to inspect dashboard cache
fly ssh console -a fof-lesson-dash
ls -la /data/

# Destroy and start over if needed
fly apps destroy fof-lesson-dash
```

Lesson data remains authoritative on Hermes (`/opt/data/lesson-logs/lessons.db`) and in
Hermes backups. Dashboard data is only a cache plus user preferences.


## Key IDs
| Resource | Value |
|----------|-------|
| Hermes Fly app | `[FLY-APP-NAME]` |
| Hermes DB source | `/opt/data/lesson-logs/lessons.db` |
| Hermes DB private URL | `http://[FLY-APP-NAME].internal:8081/lesson-logger/lessons.db` |
| Dashboard Fly app | `fof-lesson-dash` |
| Dashboard region | `sjc` |
| Dashboard volume | `dashboard_data` (1 GB) |
| Dashboard URL | `https://fof-lesson-dash.fly.dev` |
