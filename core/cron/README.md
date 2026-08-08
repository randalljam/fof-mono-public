file: README.md
title: core/cron — shared scheduled-job helpers
last-updated: 2026-06-06_0530

**core/cron — shared scheduled-job helpers**

Reusable, app-agnostic scheduling for fof-mono. On macOS we use **launchd**
LaunchAgents (preferred over cron: survives sleep, per-job logs). Apps own their
job definitions; this folder owns the install/build machinery.

## What's here

| File | Role |
|------|------|
| `launchd.py` | Reusable library: `build_plist`, `install`, `uninstall`, `is_installed`. Knows nothing about any specific app. |
| `install_launchd_plist.py` | Generic CLI driven by `--jobs <registry.json>`. |
| `crontab.example` | Template for the cron alternative (non-macOS / preference). |
| `launchd_job.plist.example` | Annotated example of a generated plist (reference only — do not hand-install). |

## How an app registers jobs

1. Add a JSON registry in the app folder, e.g. `agents/<app>/cron_jobs.json`:
   ```json
   {
     "jobs": {
       "<job_key>": {
         "label": "org.focusonfoundations.<app>-<job>",
         "description": "what it does",
         "python_script": "agents/<app>/<script>.py",
         "python_args": ["..."],
         "schedule": {"Weekday": 0, "Hour": 3, "Minute": 0},
         "log_basename": "<app>-<job>"
       }
     }
   }
   ```
   Job-spec fields (including `program_arguments` for non-Python jobs) are
   documented at the top of `launchd.py`.

2. Install / list / remove with the generic CLI (from repo root):
   ```bash
   .venv/bin/python3 core/cron/install_launchd_plist.py --jobs agents/<app>/cron_jobs.json list
   .venv/bin/python3 core/cron/install_launchd_plist.py --jobs agents/<app>/cron_jobs.json install <job_key>
   .venv/bin/python3 core/cron/install_launchd_plist.py --jobs agents/<app>/cron_jobs.json uninstall <job_key>
   ```

Logs land in `~/Library/Logs/fof-mono/<log_basename>.{log,err.log}`.

## Conventions & gotchas

- **Time zone:** launchd's `StartCalendarInterval` runs in the **machine's local
  time zone** — there is no per-job time-zone key. Choose schedule values in the
  Mac's local time (Pacific for our machines) and note it in the registry.
- **venv:** `python_script` jobs run under the repo `.venv` interpreter; the job's
  working directory defaults to the repo root.
- **Environment:** the installer captures the current `PATH`/`HOME` into the plist
  so jobs find tools (e.g. `~/.fly/bin`) and credentials (`~/.aws`) like a shell would.
- First app to use this: Hermes (`agents/hermes/cron_jobs.json`).
