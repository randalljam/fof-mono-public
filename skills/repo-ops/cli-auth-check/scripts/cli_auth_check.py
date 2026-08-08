#!/usr/bin/env python3
"""CLI authentication status check (READ-ONLY).

Reports whether common machine-level CLIs are installed and authenticated.
Does not log in, log out, write credentials, or print secrets/tokens.

Usage:
    .venv/bin/python3 skills/repo-ops/cli-auth-check/scripts/cli_auth_check.py
    ... --timeout 20          # per-command timeout seconds (default 20)
    ... --skip chalice,cursor # skip named checks
"""
import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime

### Helpers: process / path
def _repo_root():
    """Return git toplevel, or None."""
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None
def _venv_bin(repo_root):
    """Return <repo>/.venv/bin if it exists."""
    if not repo_root:
        return None
    path = os.path.join(repo_root, ".venv", "bin")
    return path if os.path.isdir(path) else None
def _which(name, extra_dirs=None):
    """Resolve executable path; optionally search extra_dirs first."""
    if extra_dirs:
        for d in extra_dirs:
            candidate = os.path.join(d, name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
    return shutil.which(name)
def _run(argv, timeout_s):
    """Run argv; return (returncode, combined stdout+stderr, timed_out)."""
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=os.environ.copy(),
        )
    except FileNotFoundError:
        return 127, "executable not found", False
    except subprocess.TimeoutExpired as exc:
        out = ""
        if exc.stdout:
            out += exc.stdout if isinstance(exc.stdout, str) else exc.stdout.decode("utf-8", "replace")
        if exc.stderr:
            out += ("\n" if out else "") + (
                exc.stderr if isinstance(exc.stderr, str) else exc.stderr.decode("utf-8", "replace")
            )
        return None, out.strip(), True
    out = (proc.stdout or "") + (("\n" if proc.stdout and proc.stderr else "") + (proc.stderr or ""))
    return proc.returncode, out.strip(), False
def _redact(text):
    """Strip obvious secret-looking values from CLI output before printing."""
    if not text:
        return text
    lines = []
    for line in text.splitlines():
        low = line.lower()
        if any(k in low for k in ("token:", "api_key", "access_key", "secret", "password", "authorization:")):
            if ":" in line:
                left, _, _ = line.partition(":")
                lines.append(f"{left}: <redacted>")
            else:
                lines.append("<redacted>")
            continue
        lines.append(line)
    return "\n".join(lines)
def _first_lines(text, n=8):
    """Return first n lines of text."""
    if not text:
        return ""
    return "\n".join(text.splitlines()[:n])
def _extract_version(text):
    """Pull a semver-ish version from --version / version output."""
    if not text:
        return None
    m = re.search(r"aws-cli/(\d+(?:\.\d+)+)", text)
    if m:
        return m.group(1)
    m = re.search(r"\bchalice\s+(\d+(?:\.\d+)+)", text, re.I)
    if m:
        return m.group(1)
    m = re.search(r"\bfly(?:ctl)?\s+v?(\d+(?:\.\d+)+)", text, re.I)
    if m:
        return m.group(1)
    first = text.splitlines()[0]
    m = re.search(r"\b(\d+\.\d+(?:\.\d+)?(?:[-+][0-9A-Za-z.]+)?)\b", first)
    if m:
        return m.group(1)
    m = re.search(r"\b(\d+\.\d+(?:\.\d+)?(?:[-+][0-9A-Za-z.]+)?)\b", text)
    return m.group(1) if m else None
def _cli_version(path, timeout_s, argv_tail=None):
    """Run <cli> --version (or argv_tail) and return a short version string."""
    if not path:
        return None
    argv = [path] + (argv_tail if argv_tail is not None else ["--version"])
    rc, out, timed_out = _run(argv, min(timeout_s, 10))
    if timed_out or rc not in (0, None) or not out:
        if argv_tail is None:
            rc2, out2, timed2 = _run([path, "version"], min(timeout_s, 10))
            if not timed2 and rc2 == 0 and out2:
                return _extract_version(out2)
        return None
    return _extract_version(out)
def _cli_label(label):
    """Display name for the CLI column (GitHub, AWS, Fly.io, ...)."""
    return label or "-"
def _status_cell(auth):
    """Status cell with ✅/❌ before AUTH OK / AUTH FAIL (account is a separate column)."""
    if auth == "AUTH OK":
        return "✅ AUTH OK"
    if auth == "AUTH FAIL":
        return "❌ AUTH FAIL"
    if auth == "NOT INSTALLED":
        return "❌ NOT INSTALLED"
    return auth or "UNKNOWN"
def _md_escape(text):
    """Escape pipe characters for a markdown table cell."""
    return (text or "").replace("|", "\\|").replace("\n", " ")
def _base_row(label, binary, path, version=None):
    """Common row fields."""
    return {
        "label": label,
        "binary": binary,
        "path": path,
        "version": version,
        "installed": bool(path),
        "account": None,
        "auth": None,
        "detail": None,
        "fix": None,
        "note": None,
    }

### Checks
def check_gh(timeout_s):
    """GitHub CLI: gh auth status."""
    path = _which("gh")
    version = _cli_version(path, timeout_s)
    row = _base_row("GitHub", "gh", path, version)
    if not path:
        row["auth"] = "NOT INSTALLED"
        row["detail"] = "Install: https://cli.github.com/"
        row["fix"] = "brew install gh   # then: gh auth login -h github.com"
        return row
    rc, out, timed_out = _run([path, "auth", "status"], timeout_s)
    if timed_out:
        row["auth"] = "UNKNOWN"
        row["detail"] = f"timed out after {timeout_s}s"
        return row
    low = out.lower()
    m = re.search(r"account\s+(\S+)", out, re.I)
    account = m.group(1).strip("()") if m else None
    ok = rc == 0 and ("logged in to" in low or "✓" in out or "logged in" in low)
    fail = (
        rc != 0
        or "failed to log in" in low
        or "token in keyring is invalid" in low
        or "not logged into" in low
        or "no github hosts" in low
    )
    if ok and not fail:
        row["auth"] = "AUTH OK"
        row["account"] = account
        return row
    if fail:
        row["auth"] = "AUTH FAIL"
        row["detail"] = _first_lines(_redact(out), 8)
        row["fix"] = "gh auth login -h github.com"
        return row
    row["auth"] = "UNKNOWN"
    row["detail"] = _first_lines(_redact(out), 8)
    return row
def check_aws(timeout_s, venv_bin):
    """AWS CLI: prefer PATH/Homebrew aws; note venv awscli separately."""
    path = _which("aws")
    venv_aws = os.path.join(venv_bin, "aws") if venv_bin else None
    if venv_aws and not (os.path.isfile(venv_aws) and os.access(venv_aws, os.X_OK)):
        venv_aws = None
    version = _cli_version(path, timeout_s)
    row = _base_row("AWS", "aws", path, version)
    if venv_aws and path and os.path.realpath(venv_aws) != os.path.realpath(path):
        vver = _cli_version(venv_aws, timeout_s)
        row["note"] = f"also in .venv: awscli {vver or '?'}"
    elif venv_aws and not path:
        path = venv_aws
        row["path"] = path
        row["installed"] = True
        row["version"] = _cli_version(path, timeout_s)
        row["note"] = "using .venv aws (Homebrew/PATH aws not found)"
    if not path:
        row["auth"] = "NOT INSTALLED"
        row["detail"] = "Install: brew install awscli (recommended) or pip in .venv"
        row["fix"] = "brew install awscli   # then: aws configure"
        return row
    rc, out, timed_out = _run([path, "sts", "get-caller-identity"], timeout_s)
    if timed_out:
        row["auth"] = "UNKNOWN"
        row["detail"] = f"timed out after {timeout_s}s"
        return row
    if rc == 0 and ("Account" in out or "UserId" in out or "Arn" in out):
        user = None
        acct_num = None
        m = re.search(r'"Arn"\s*:\s*"([^"]+)"', out)
        if m:
            arn = m.group(1)
            user = arn.rsplit("/", 1)[-1] if "/" in arn else arn
        m = re.search(r'"Account"\s*:\s*"([^"]+)"', out)
        if m:
            acct_num = m.group(1)
        if user and acct_num:
            account = f"{user} ({acct_num})"
        else:
            account = user or acct_num
        row["auth"] = "AUTH OK"
        row["account"] = account
        return row
    row["auth"] = "AUTH FAIL"
    row["detail"] = _first_lines(_redact(out), 8) or f"exit {rc}"
    row["fix"] = "aws configure   # or: aws sso login --profile <name>"
    return row
def check_chalice(venv_bin, timeout_s, aws_row):
    """Chalice: no separate login — auth follows AWS credentials."""
    path = _which("chalice", extra_dirs=[venv_bin] if venv_bin else None)
    version = _cli_version(path, timeout_s)
    row = _base_row("Chalice", "chalice", path, version)
    row["note"] = (
        "No separate CLI login — Python package (usually in .venv); "
        "deploys with AWS credentials (same auth as AWS row)"
    )
    if not path:
        row["auth"] = "NOT INSTALLED"
        row["detail"] = "Install into repo .venv: .venv/bin/pip install chalice"
        row["fix"] = ".venv/bin/pip install chalice"
        return row
    aws_auth = (aws_row or {}).get("auth")
    if aws_auth == "AUTH OK":
        row["auth"] = "AUTH OK"
        row["account"] = (aws_row or {}).get("account")
        return row
    if aws_auth in ("AUTH FAIL", "NOT INSTALLED"):
        row["auth"] = "AUTH FAIL"
        row["detail"] = "Depends on AWS login — AWS row is not AUTH OK"
        row["fix"] = "Fix AWS auth first (aws configure / aws sso login)"
        return row
    row["auth"] = "UNKNOWN"
    row["detail"] = "Depends on AWS login — AWS status unclear"
    return row
def check_fly(timeout_s):
    """Fly.io: flyctl/fly auth whoami."""
    path = _which("fly") or _which("flyctl")
    version = _cli_version(path, timeout_s) or _cli_version(path, timeout_s, ["version"])
    row = _base_row("Fly.io", "fly", path, version)
    if not path:
        row["auth"] = "NOT INSTALLED"
        row["detail"] = "Install: https://fly.io/docs/flyctl/install/"
        row["fix"] = "curl -L https://fly.io/install.sh | sh   # then: fly auth login"
        return row
    rc, out, timed_out = _run([path, "auth", "whoami"], timeout_s)
    if timed_out:
        row["auth"] = "UNKNOWN"
        row["detail"] = f"timed out after {timeout_s}s"
        return row
    low = out.lower()
    if rc == 0 and out and "error" not in low and "not logged" not in low:
        row["auth"] = "AUTH OK"
        row["account"] = out.splitlines()[0].strip()
        return row
    row["auth"] = "AUTH FAIL"
    row["detail"] = _first_lines(_redact(out), 8) or f"exit {rc}"
    row["fix"] = "fly auth login"
    return row
def check_codex(timeout_s):
    """OpenAI Codex CLI: codex login status."""
    path = _which("codex")
    version = _cli_version(path, timeout_s)
    row = _base_row("Codex", "codex", path, version)
    if not path:
        row["auth"] = "NOT INSTALLED"
        row["detail"] = "Install: npm install -g @openai/codex"
        row["fix"] = "npm install -g @openai/codex   # then: codex login"
        return row
    rc, out, timed_out = _run([path, "login", "status"], timeout_s)
    if timed_out:
        row["auth"] = "UNKNOWN"
        row["detail"] = f"timed out after {timeout_s}s"
        return row
    low = out.lower()
    ok_hints = ("logged in", "authenticated", "auth method", "email", "chatgpt")
    fail_hints = (
        "not logged in",
        "logged out",
        "no auth",
        "unauthenticated",
        "authentication required",
        "please run",
        "login required",
    )
    account = None
    m = re.search(r"logged in using\s+(.+)$", out, re.I | re.M)
    if m:
        account = m.group(1).strip().rstrip(".")
    if not account:
        m = re.search(r"[\w.+-]+@[\w.-]+", out)
        if m:
            account = m.group(0)
    if rc == 0 and any(h in low for h in ok_hints) and "not logged" not in low and "logged out" not in low:
        row["auth"] = "AUTH OK"
        row["account"] = account
        return row
    if rc != 0 or any(h in low for h in fail_hints) or "error" in low:
        row["auth"] = "AUTH FAIL"
        row["detail"] = _first_lines(_redact(out), 8) or f"exit {rc}"
        row["fix"] = "codex login"
        return row
    row["auth"] = "UNKNOWN"
    row["detail"] = _first_lines(_redact(out), 8) or f"exit {rc}"
    row["fix"] = "codex login   # if status looks wrong; also: codex doctor"
    return row
def check_claude(timeout_s):
    """Anthropic Claude Code CLI: claude auth status."""
    path = _which("claude")
    version = _cli_version(path, timeout_s)
    row = _base_row("Claude", "claude", path, version)
    if not path:
        row["auth"] = "NOT INSTALLED"
        row["detail"] = "Install: https://claude.ai/code (Claude Code CLI)"
        row["fix"] = "claude auth login"
        return row
    rc, out, timed_out = _run([path, "auth", "status"], timeout_s)
    if timed_out:
        row["auth"] = "UNKNOWN"
        row["detail"] = f"timed out after {timeout_s}s"
        return row
    low = out.lower()
    account = None
    try:
        data = json.loads(out)
        if isinstance(data, dict):
            account = data.get("email") or data.get("account")
            if data.get("loggedIn") is True:
                row["auth"] = "AUTH OK"
                row["account"] = account
                return row
    except json.JSONDecodeError:
        m = re.search(r'"email"\s*:\s*"([^"]+)"', out)
        if m:
            account = m.group(1)
    if rc == 0 and ("logged in" in low or "authenticated" in low or '"loggedin": true' in low.replace(" ", "")):
        row["auth"] = "AUTH OK"
        row["account"] = account
        return row
    if rc != 0 or "not logged" in low or "logged out" in low or "unauthenticated" in low:
        row["auth"] = "AUTH FAIL"
        row["detail"] = _first_lines(_redact(out), 8) or f"exit {rc}"
        row["fix"] = "claude auth login"
        return row
    row["auth"] = "UNKNOWN"
    row["detail"] = _first_lines(_redact(out), 8) or f"exit {rc}"
    row["fix"] = "claude auth login"
    return row
def _cursor_app_email():
    """Read Cursor app Settings email only (never tokens) from global state DB."""
    db = os.path.expanduser("~/Library/Application Support/Cursor/User/globalStorage/state.vscdb")
    if not os.path.isfile(db):
        return None
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        cur = con.cursor()
        for key in ("cursorAuth/cachedEmail", "cursorAuth/email"):
            cur.execute("select value from ItemTable where key = ?", (key,))
            hit = cur.fetchone()
            if not hit or hit[0] is None:
                continue
            val = hit[0]
            if isinstance(val, bytes):
                val = val.decode("utf-8", "replace")
            val = str(val).strip().strip('"')
            if val and "@" in val and "token" not in val.lower():
                con.close()
                return val
        con.close()
    except Exception:
        return None
    return None
def check_cursor(timeout_s):
    """Cursor: CLI opens windows; account login is Cursor app Settings (not a CLI auth command)."""
    path = _which("cursor")
    version = _cli_version(path, timeout_s)
    row = _base_row("Cursor", "cursor", path, version)
    row["note"] = (
        "No separate CLI auth command — account is Cursor app Settings login "
        "(CLI only opens windows / talks to the running app)"
    )
    if not path:
        row["auth"] = "NOT INSTALLED"
        row["detail"] = "Install Cursor app; CLI usually at /usr/local/bin/cursor"
        return row
    email = _cursor_app_email()
    if email:
        row["auth"] = "AUTH OK"
        row["account"] = email
        return row
    # Fallback: active Cursor agent/session env without readable email
    if os.environ.get("CURSOR_AGENT") or (
        os.environ.get("VSCODE_IPC_HOOK") and "Cursor" in os.environ.get("VSCODE_IPC_HOOK", "")
    ):
        row["auth"] = "AUTH OK"
        row["account"] = "Cursor app session"
        return row
    row["auth"] = "AUTH FAIL"
    row["detail"] = "Cursor CLI present but no app Settings email/session found"
    row["fix"] = "Sign in via Cursor → Settings → Account"
    return row

### Report
def _print_table(rows):
    """Print a markdown table of CLI auth status."""
    print("")
    print("| CLI | Command | Version | Status | Account | Path | Notes |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for row in rows:
        cli = _cli_label(row["label"])
        command = (row.get("binary") or "-").lower()
        version = row.get("version") or "-"
        status = _status_cell(row.get("auth"))
        account = row.get("account") or "-"
        path = row.get("path") or "-"
        notes = row.get("note") or ""
        if row.get("auth") not in ("AUTH OK",) and row.get("detail"):
            extra = row["detail"].splitlines()[0]
            notes = f"{notes}; {extra}" if notes else extra
        print(
            f"| {_md_escape(cli)} | {_md_escape(command)} | {_md_escape(version)} | "
            f"{_md_escape(status)} | {_md_escape(account)} | {_md_escape(path)} | {_md_escape(notes)} |"
        )
def _print_fixes(rows):
    """Print fix commands for failed / missing rows."""
    fixes = [(r, r.get("fix")) for r in rows if r.get("fix") and r.get("auth") in ("AUTH FAIL", "NOT INSTALLED")]
    if not fixes:
        return
    print("")
    print("## Fixes")
    for row, fix in fixes:
        label = f"{_cli_label(row['label'])} ({(row.get('binary') or '').lower()})"
        print(f"- {label}: `{fix}`")
def _verdict(rows):
    """Build a short overall verdict from row statuses."""
    fails = [f"{_cli_label(r['label'])} ({(r.get('binary') or '').lower()})" for r in rows if r.get("auth") == "AUTH FAIL"]
    missing = [f"{_cli_label(r['label'])} ({(r.get('binary') or '').lower()})" for r in rows if r.get("auth") == "NOT INSTALLED"]
    unknown = [f"{_cli_label(r['label'])} ({(r.get('binary') or '').lower()})" for r in rows if r.get("auth") == "UNKNOWN"]
    if fails:
        return "STOP — fix AUTH FAIL before agent coding that needs those CLIs: " + "; ".join(fails)
    if unknown:
        return "CAUTION — some checks unclear: " + "; ".join(unknown)
    if missing:
        return "OK for installed CLIs — missing (install if needed): " + "; ".join(missing)
    return "OK — checked CLIs look authenticated."
def main():
    """Run CLI auth checks and print a stdout report (no file write)."""
    ap = argparse.ArgumentParser(description="Read-only CLI install + auth status report.")
    ap.add_argument("--timeout", type=int, default=20, help="per-command timeout seconds")
    ap.add_argument(
        "--skip",
        default="",
        help="comma-separated checks to skip: gh,aws,chalice,fly,codex,claude,cursor",
    )
    args = ap.parse_args()
    skip = {s.strip().lower() for s in args.skip.split(",") if s.strip()}

    repo_root = _repo_root()
    venv_bin = _venv_bin(repo_root)
    print("CLI authentication check")
    print(f"time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}".rstrip())
    print(f"host: {os.uname().nodename}")
    print(f"user: {os.environ.get('USER') or os.environ.get('LOGNAME') or '-'}")
    print(f"repo: {repo_root or '(not in a git checkout)'}")
    print(f"venv: {venv_bin or '(no .venv/bin found)'}")
    print(
        "note: machine-level CLIs (gh/aws/fly/codex/claude/cursor) are outside the repo; "
        "chalice is a Python package in .venv and uses AWS auth (no separate login)"
    )

    rows = []
    aws_row = None
    if "gh" not in skip:
        rows.append(check_gh(args.timeout))
    if "aws" not in skip:
        aws_row = check_aws(args.timeout, venv_bin)
        rows.append(aws_row)
    elif "chalice" not in skip:
        # Still need AWS status for Chalice dependency when AWS row is skipped
        aws_row = check_aws(args.timeout, venv_bin)
    if "chalice" not in skip:
        rows.append(check_chalice(venv_bin, args.timeout, aws_row))
    if "fly" not in skip:
        rows.append(check_fly(args.timeout))
    if "codex" not in skip:
        rows.append(check_codex(args.timeout))
    if "claude" not in skip:
        rows.append(check_claude(args.timeout))
    if "cursor" not in skip:
        rows.append(check_cursor(args.timeout))

    _print_table(rows)
    _print_fixes(rows)
    print("")
    print("## VERDICT")
    print(_verdict(rows))
    fails = any(r.get("auth") == "AUTH FAIL" for r in rows)
    return 1 if fails else 0

if __name__ == "__main__":
    sys.exit(main())
