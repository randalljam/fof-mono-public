#!/usr/bin/env python3
# Reusable macOS launchd (LaunchAgent) scheduling helpers for fof-mono.
#
# App-agnostic: callers pass job specs as plain dicts; nothing here is tied to
# Hermes or any one app. Job registries live with the owning app (for example
# agents/hermes/cron_jobs.json) and are driven through install_launchd_plist.py,
# or an app can call install()/uninstall() directly.
#
# A job spec is a dict:
#   {
#     "label": "org.focusonfoundations.hermes-backup-weekly",  # required, unique
#     "description": "Hermes weekly S3 backup",                 # optional -> plist Comment
#     "python_script": "agents/hermes/hermes_backup.py",        # repo-relative; runs under .venv
#     "python_args": ["backup", "--tier", "weekly"],            # optional args for python_script
#     "program_arguments": ["/usr/bin/true"],                   # OR a full argv (instead of python_script)
#     "schedule": {"Weekday": 0, "Hour": 3, "Minute": 0},       # StartCalendarInterval dict or list of dicts
#     "log_basename": "hermes-backup-weekly",                   # optional; defaults to last label segment
#     "working_directory": "/abs/path"                          # optional; defaults to repo root
#   }
#
# Time-zone note: launchd's StartCalendarInterval runs in the machine's LOCAL
# time zone — launchd has no per-job time-zone key. Pick schedule values in the
# Mac's local time (Pacific for our machines) and say so in the registry.
import os
import plistlib
import subprocess

### Config
LAUNCH_AGENTS = os.path.expanduser("~/Library/LaunchAgents")
DEFAULT_LOG_DIR = os.path.expanduser("~/Library/Logs/fof-mono")

### Helpers: paths
def repo_root():
    """Repo root, inferred from this file's location (core/cron/launchd.py)."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
def venv_python(root=None):
    """Absolute path to the project venv interpreter."""
    return os.path.join(root or repo_root(), ".venv", "bin", "python3")
def plist_path(label):
    """Installed LaunchAgent path for a job label."""
    return os.path.join(LAUNCH_AGENTS, f"{label}.plist")
def is_installed(label):
    """True if a LaunchAgent plist for this label exists."""
    return os.path.isfile(plist_path(label))

### Helpers: build
def _program_arguments(job, root):
    """Resolve the job's argv: an explicit program_arguments, or venv python + script."""
    if job.get("program_arguments"):
        return list(job["program_arguments"])
    script = job.get("python_script")
    if not script:
        raise ValueError(f"Job {job.get('label')!r} needs 'python_script' or 'program_arguments'")
    python = venv_python(root)
    if not os.path.isfile(python):
        raise FileNotFoundError(f"Missing venv python: {python} (create .venv first)")
    script_abs = script if os.path.isabs(script) else os.path.join(root, script)
    if not os.path.isfile(script_abs):
        raise FileNotFoundError(f"Missing script: {script_abs}")
    return [python, script_abs] + list(job.get("python_args") or [])
def _log_basename(job):
    """Log file stem: explicit log_basename, else the last dotted segment of the label."""
    return job.get("log_basename") or job["label"].rsplit(".", 1)[-1]
def build_plist(job, root=None, log_dir=DEFAULT_LOG_DIR):
    """Build a launchd plist dict for a job spec; returns (plist, log_out, log_err)."""
    root = root or repo_root()
    if not job.get("label"):
        raise ValueError("Job spec missing 'label'")
    if not job.get("schedule"):
        raise ValueError(f"Job {job['label']!r} missing 'schedule'")
    os.makedirs(log_dir, exist_ok=True)
    base = _log_basename(job)
    log_out = os.path.join(log_dir, f"{base}.log")
    log_err = os.path.join(log_dir, f"{base}.err.log")
    plist = {
        "Label": job["label"],
        "ProgramArguments": _program_arguments(job, root),
        "WorkingDirectory": job.get("working_directory") or root,
        "StandardOutPath": log_out,
        "StandardErrorPath": log_err,
        # Capture the installer's PATH/HOME so the job finds tools (e.g. ~/.fly/bin)
        # and credentials (~/.aws) the same way an interactive shell would.
        "EnvironmentVariables": {
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "HOME": os.path.expanduser("~"),
        },
        "StartCalendarInterval": job["schedule"],
        "RunAtLoad": False,
    }
    if job.get("description"):
        plist["Comment"] = job["description"]
    return plist, log_out, log_err

### Commands
def _launchctl(args, check):
    """Run launchctl with the given args."""
    subprocess.run(["launchctl"] + list(args), check=check)
def install(job, root=None, log_dir=DEFAULT_LOG_DIR):
    """Write and load a LaunchAgent for a job spec; returns (dest, log_out, log_err)."""
    plist, log_out, log_err = build_plist(job, root, log_dir)
    label = plist["Label"]
    dest = plist_path(label)
    os.makedirs(LAUNCH_AGENTS, exist_ok=True)
    if os.path.isfile(dest):
        _launchctl(["unload", dest], check=False)
    with open(dest, "wb") as f:
        plistlib.dump(plist, f)
    _launchctl(["load", "-w", dest], check=True)
    return dest, log_out, log_err
def uninstall(label):
    """Unload and remove a LaunchAgent by label; returns the removed path or None."""
    dest = plist_path(label)
    if not os.path.isfile(dest):
        return None
    _launchctl(["unload", dest], check=False)
    os.remove(dest)
    return dest
