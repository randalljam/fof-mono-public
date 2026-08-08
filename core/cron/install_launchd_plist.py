#!/usr/bin/env python3
# Generic CLI to install/uninstall/list macOS LaunchAgents for fof-mono apps.
# Preferred over cron on Mac (survives sleep, clearer per-job logging).
#
# Nothing here is app-specific: jobs come from an app-owned JSON registry passed
# with --jobs. The reusable launchd logic lives in core/cron/launchd.py.
#
# Usage (from repo root):
#   .venv/bin/python3 core/cron/install_launchd_plist.py --jobs agents/hermes/cron_jobs.json list
#   .venv/bin/python3 core/cron/install_launchd_plist.py --jobs agents/hermes/cron_jobs.json install hermes_backup_weekly
#   .venv/bin/python3 core/cron/install_launchd_plist.py --jobs agents/hermes/cron_jobs.json uninstall hermes_backup_weekly
#
# Registry format (JSON): {"jobs": {"<key>": {<job spec>}, ...}}  — see launchd.py
# for the job-spec fields, and core/cron/README.md for the overall pattern.
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import launchd

### Helpers
def _load_registry(jobs_path):
    """Load an app job registry (JSON) into an ordered key->spec dict."""
    path = jobs_path if os.path.isabs(jobs_path) else os.path.join(launchd.repo_root(), jobs_path)
    if not os.path.isfile(path):
        print(f"Jobs registry not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        data = json.load(f)
    jobs = data.get("jobs", data) if isinstance(data, dict) else data
    if not isinstance(jobs, dict) or not jobs:
        print(f"No jobs found in registry: {path}", file=sys.stderr)
        sys.exit(1)
    return jobs
def _get_job(jobs, key):
    """Fetch one job spec by key, or exit with the valid choices."""
    if key not in jobs:
        valid = ", ".join(sorted(jobs))
        print(f"Unknown job {key!r}. Available: {valid}", file=sys.stderr)
        sys.exit(1)
    return jobs[key]

### Commands
def cmd_install(jobs, key):
    """Install and load one job."""
    job = _get_job(jobs, key)
    dest, log_out, log_err = launchd.install(job)
    print(f"Installed LaunchAgent: {dest}")
    print(f"  Label: {job['label']}")
    print(f"  Schedule: {job['schedule']} (machine local time)")
    print(f"  Logs: {log_out}")
    print(f"        {log_err}")
def cmd_uninstall(jobs, key):
    """Unload and remove one job."""
    job = _get_job(jobs, key)
    dest = launchd.uninstall(job["label"])
    if dest:
        print(f"Removed LaunchAgent: {dest}")
    else:
        print(f"Not installed: {launchd.plist_path(job['label'])}")
def cmd_list(jobs, _key):
    """List jobs in the registry and their install status."""
    print("Jobs in registry:")
    for key in sorted(jobs):
        job = jobs[key]
        status = "installed" if launchd.is_installed(job["label"]) else "not installed"
        print(f"  {key}: {status}")
        if job.get("description"):
            print(f"    {job['description']}")
        print(f"    label={job['label']} schedule={job['schedule']} (machine local time)")

### CLI
def main():
    parser = argparse.ArgumentParser(description="Install macOS LaunchAgents for fof-mono apps.")
    parser.add_argument("--jobs", required=True, help="Path to an app job registry JSON (repo-relative or absolute).")
    sub = parser.add_subparsers(dest="command", required=True)
    install_p = sub.add_parser("install", help="Install and load a LaunchAgent.")
    install_p.add_argument("job", help="Job key from the registry.")
    uninstall_p = sub.add_parser("uninstall", help="Unload and remove a LaunchAgent.")
    uninstall_p.add_argument("job", help="Job key from the registry.")
    sub.add_parser("list", help="List jobs in the registry and install status.")
    args = parser.parse_args()
    jobs = _load_registry(args.jobs)
    key = getattr(args, "job", None)
    if args.command == "install":
        cmd_install(jobs, key)
    elif args.command == "uninstall":
        cmd_uninstall(jobs, key)
    elif args.command == "list":
        cmd_list(jobs, key)
if __name__ == "__main__":
    main()
