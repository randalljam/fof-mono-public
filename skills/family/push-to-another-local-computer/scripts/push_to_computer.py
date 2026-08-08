#!/usr/bin/env python3
"""Push local files to another computer over SSH/rsync.

Stdlib only. Real transfers require --execute. Default is dry-run.
Computer registry is loaded from a private TOML config (never hardcoded).
"""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import tomllib


DEFAULT_CONFIG_REL = "docs/personal/push-computers.toml"
ENV_CONFIG = "FOF_PUSH_COMPUTERS_CONFIG"
SSH_OPTS = [
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=5",
    "-o", "StrictHostKeyChecking=accept-new",
]

### Paths / repo root
def find_repo_root(start=None):
    """Walk up from start (or this file) until .git or setup.py is found."""
    here = os.path.abspath(start or os.path.dirname(__file__))
    cur = here
    while True:
        if os.path.isdir(os.path.join(cur, ".git")) or os.path.isfile(os.path.join(cur, "setup.py")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return here
        cur = parent
def default_config_path(repo_root=None):
    """Return default private registry path under the repo root."""
    root = repo_root or find_repo_root()
    return os.path.join(root, DEFAULT_CONFIG_REL)
def resolve_config_path(explicit=None, repo_root=None):
    """Resolve config path: --config, then env, then default local path."""
    if explicit:
        return os.path.abspath(explicit)
    env = (os.environ.get(ENV_CONFIG) or "").strip()
    if env:
        return os.path.abspath(env)
    return default_config_path(repo_root)

### Config load / validate
def _has_control_chars(value):
    """Return True if value contains ASCII control characters."""
    return any(ord(ch) < 32 for ch in value)
def _require_abs_remote_path(label, value):
    """Require a non-empty absolute remote path with no control chars."""
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip()
    if _has_control_chars(text):
        raise SystemExit("%s contains control characters" % label)
    if not text.startswith("/"):
        raise SystemExit("%s must be an absolute remote path (got %r)" % (label, text))
    return text
def _normalize_computer(raw, index):
    """Normalize one [[computers]] table into the internal dict shape."""
    if not isinstance(raw, dict):
        raise SystemExit("computers[%d] must be a table" % index)
    cid = (raw.get("id") or "").strip()
    if not cid:
        raise SystemExit("computers[%d] missing id" % index)
    if _has_control_chars(cid):
        raise SystemExit("computers[%d] id contains control characters" % index)
    ssh = (raw.get("ssh") or "").strip()
    if not ssh or "@" not in ssh:
        raise SystemExit("computers[%d] (%s) needs ssh as user@host" % (index, cid))
    if _has_control_chars(ssh):
        raise SystemExit("computers[%d] (%s) ssh contains control characters" % (index, cid))
    aliases_raw = raw.get("aliases") or []
    if isinstance(aliases_raw, str):
        aliases_raw = [aliases_raw]
    aliases = []
    for a in aliases_raw:
        text = str(a).strip().lower()
        if not text:
            continue
        if _has_control_chars(text):
            raise SystemExit("computers[%d] (%s) alias contains control characters" % (index, cid))
        aliases.append(text)
    if cid.lower() not in aliases:
        aliases.insert(0, cid.lower())
    return {
        "id": cid,
        "aliases": tuple(aliases),
        "ssh": ssh,
        "primary_checkout": _require_abs_remote_path(
            "computers[%d] (%s) primary_checkout" % (index, cid),
            raw.get("primary_checkout"),
        ),
        "local_files_root": _require_abs_remote_path(
            "computers[%d] (%s) local_files_root" % (index, cid),
            raw.get("local_files_root"),
        ),
    }
def load_computers(config_path):
    """Load and validate computers from a TOML registry file."""
    if not os.path.isfile(config_path):
        raise SystemExit(
            "computer registry not found: %s\n"
            "Copy skills/family/push-to-another-local-computer/references/computers.example.toml\n"
            "to docs/personal/push-computers.toml (or set %s / --config), then fill in real values."
            % (config_path, ENV_CONFIG)
        )
    try:
        with open(config_path, "rb") as handle:
            raw = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise SystemExit("invalid TOML in %s: %s" % (config_path, exc)) from exc
    rows = raw.get("computers")
    if not isinstance(rows, list) or not rows:
        raise SystemExit("%s must contain a non-empty [[computers]] list" % config_path)
    computers = {}
    for i, row in enumerate(rows):
        info = _normalize_computer(row, i)
        cid = info["id"]
        if cid in computers:
            raise SystemExit("duplicate computer id %r in %s" % (cid, config_path))
        computers[cid] = info
    return computers

### Resolve computer / destination
def resolve_computer(name, computers):
    """Return (canonical_id, computer_dict) for an alias or id."""
    key = (name or "").strip().lower()
    if not key:
        raise SystemExit("computer name is required")
    for cid, info in computers.items():
        if key == cid.lower() or key in info["aliases"]:
            return cid, info
    raise SystemExit(
        "unknown computer %r; known: %s"
        % (name, ", ".join(sorted(computers)))
    )
def sanitize_rel(dest_rel):
    """Return a safe relative subpath under a configured root (or '')."""
    rel = (dest_rel or "").strip().replace("\\", "/")
    if not rel:
        return ""
    if _has_control_chars(rel):
        raise SystemExit("--rel contains control characters")
    if rel.startswith("/"):
        raise SystemExit("--rel must be relative (not absolute): %r" % dest_rel)
    parts = [p for p in rel.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise SystemExit("--rel must not contain '..': %r" % dest_rel)
    return "/".join(parts)
def resolve_dest_dir(computer, dest_mode, dest_rel):
    """Return absolute remote destination directory."""
    rel = sanitize_rel(dest_rel)
    if dest_mode == "local-files":
        root = computer.get("local_files_root")
        if not root:
            raise SystemExit(
                "local-files root not recorded for this computer; "
                "pass --dest-dir with an absolute remote path, then update the private registry"
            )
        return root.rstrip("/") + ("/" + rel if rel else "")
    if dest_mode == "primary-checkout":
        root = computer.get("primary_checkout")
        if not root:
            raise SystemExit(
                "primary checkout not recorded for this computer; "
                "pass --dest-dir with an absolute remote path"
            )
        return root.rstrip("/") + ("/" + rel if rel else "")
    raise SystemExit("internal error: unknown dest_mode %r" % dest_mode)

### SSH / rsync
def ssh_reachable(ssh_target):
    """Return True if BatchMode ssh to target succeeds."""
    args = ["ssh"] + SSH_OPTS + [ssh_target, "true"]
    try:
        completed = subprocess.run(args, capture_output=True, text=True, timeout=8, check=False)
    except (subprocess.TimeoutExpired, OSError):
        return False
    return completed.returncode == 0
def ensure_remote_dir(ssh_target, remote_dir, execute):
    """Create remote destination directory (dry-run prints only)."""
    if _has_control_chars(remote_dir) or not remote_dir.startswith("/"):
        raise SystemExit("remote dir must be an absolute path without control characters")
    quoted = shlex.quote(remote_dir)
    cmd = ["ssh"] + SSH_OPTS + [ssh_target, "mkdir -p " + quoted]
    if not execute:
        print("DRY-RUN would run:", " ".join(shlex.quote(a) for a in cmd), flush=True)
        return True
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr or completed.stdout or "mkdir failed\n")
        return False
    return True
def build_rsync_args(ssh_target, sources, remote_dir, execute):
    """Build rsync argv; sources follow '--' so names cannot be treated as options."""
    if _has_control_chars(remote_dir) or not remote_dir.startswith("/"):
        raise SystemExit("remote dir must be an absolute path without control characters")
    remote_dest = ssh_target + ":" + remote_dir.rstrip("/") + "/"
    ssh_shell = "ssh " + " ".join(SSH_OPTS)
    args = [
        "rsync",
        "-avh",
        "--progress",
        "-e", ssh_shell,
    ]
    if not execute:
        args.append("--dry-run")
    args.append("--")
    args.extend(sources)
    args.append(remote_dest)
    return args
def rsync_push(ssh_target, sources, remote_dir, execute):
    """rsync sources into remote_dir. Trailing slash on a source dir copies contents."""
    args = build_rsync_args(ssh_target, sources, remote_dir, execute)
    print("Running:", " ".join(shlex.quote(a) for a in args), flush=True)
    completed = subprocess.run(args, check=False)
    return completed.returncode == 0

### CLI
def build_parser():
    """Argparse for push_to_computer."""
    p = argparse.ArgumentParser(
        description=(
            "Push files to another computer (rsync over SSH). "
            "Dry-run unless --execute. Computers come from a private TOML registry."
        )
    )
    p.add_argument(
        "--config",
        help="Path to push-computers.toml (default: $%s or %s)" % (ENV_CONFIG, DEFAULT_CONFIG_REL),
    )
    p.add_argument(
        "--list-computers",
        action="store_true",
        help="Print known computers and exit",
    )
    p.add_argument("--computer", help="Alias or id from the private registry")
    dest = p.add_mutually_exclusive_group()
    dest.add_argument(
        "--local-files",
        action="store_true",
        help="Destination = that computer's _LOCAL_FILES/fof-mono root (+ optional --rel)",
    )
    dest.add_argument(
        "--primary-checkout",
        action="store_true",
        help="Destination = that computer's primary fof-mono checkout (+ optional --rel)",
    )
    dest.add_argument(
        "--dest-dir",
        help="Absolute destination directory on the remote machine",
    )
    p.add_argument(
        "--rel",
        default="",
        help="Relative path under local-files or primary-checkout root",
    )
    p.add_argument(
        "sources",
        nargs="*",
        help="Local source file(s) or director(ies) to push",
    )
    p.add_argument(
        "--execute",
        action="store_true",
        help="Perform the transfer (default is dry-run)",
    )
    return p
def list_computers(computers):
    """Print registry summary."""
    for cid, info in computers.items():
        print(cid)
        print("  aliases:", ", ".join(info["aliases"]))
        print("  ssh:", info["ssh"])
        print("  primary_checkout:", info["primary_checkout"] or "(unknown)")
        print("  local_files_root:", info["local_files_root"] or "(unknown)")
def main(argv=None):
    """CLI entry."""
    parser = build_parser()
    args = parser.parse_args(argv)
    config_path = resolve_config_path(args.config)
    computers = load_computers(config_path)
    if args.list_computers:
        list_computers(computers)
        return 0
    if not args.computer:
        raise SystemExit("--computer is required (or pass --list-computers)")
    if not (args.local_files or args.primary_checkout or args.dest_dir):
        raise SystemExit("one of --local-files, --primary-checkout, or --dest-dir is required")
    if not args.sources:
        raise SystemExit("at least one source path is required")
    cid, computer = resolve_computer(args.computer, computers)
    ssh_target = computer["ssh"]
    if args.dest_dir:
        remote_dir = _require_abs_remote_path("--dest-dir", args.dest_dir)
        dest_label = "explicit --dest-dir"
    elif args.local_files:
        remote_dir = resolve_dest_dir(computer, "local-files", args.rel)
        dest_label = "local-files"
    else:
        remote_dir = resolve_dest_dir(computer, "primary-checkout", args.rel)
        dest_label = "primary-checkout"
    missing = [s for s in args.sources if not os.path.exists(s)]
    if missing:
        raise SystemExit("source path(s) not found: " + ", ".join(missing))
    def _out(*parts):
        print(*parts, flush=True)
    _out("config:", config_path)
    _out("computer:", cid)
    _out("ssh:", ssh_target)
    _out("dest mode:", dest_label)
    _out("remote dir:", remote_dir)
    _out("sources:")
    for s in args.sources:
        _out(" ", os.path.abspath(s))
    _out("mode:", "EXECUTE" if args.execute else "DRY-RUN")
    if not ssh_reachable(ssh_target):
        raise SystemExit("SSH unreachable: " + ssh_target)
    _out("ssh: reachable")
    if not ensure_remote_dir(ssh_target, remote_dir, args.execute):
        return 1
    ok = rsync_push(ssh_target, args.sources, remote_dir, args.execute)
    if not ok:
        return 1
    if not args.execute:
        _out("Dry-run OK. Re-run with --execute to transfer.")
    else:
        _out("Transfer complete.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
