#!/usr/bin/env python3
"""Migrate Cursor AI sessions from one worktree path to another.

Designed to run from a normal terminal with Cursor fully quit for --execute.
Default mode is --dry-run: copy state.vscdb, apply path rewrites on the copy,
review the result, and leave the live Cursor DB untouched.
"""

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

TOOL_NAME = "migrate-cursor-ai-sessions"
DEFAULT_ROOT = Path.home() / ".cursor" / "ai-session-migrate"

### Helpers: logging / time
def _now_stamp():
    """Return local timestamp string YYYY-MM-DD_HHMMSS."""
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")
def _parse_since(value):
    """Parse --since into epoch milliseconds. Accepts YYYY-MM-DD or ISO datetime."""
    if value is None or value == "":
        return None
    text = value.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d_%H%M", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return int(datetime.strptime(text, fmt).timestamp() * 1000)
        except ValueError:
            pass
    if text.isdigit():
        num = int(text)
        return num if num > 10_000_000_000 else num * 1000
    raise SystemExit(f"Could not parse --since value: {value!r}")
def _ms_to_local(ms):
    """Format epoch milliseconds as local datetime string."""
    if ms is None:
        return ""
    return datetime.fromtimestamp(ms / 1000.0).strftime("%Y-%m-%d %H:%M:%S")
def _ensure_dir(path):
    """Create directory if needed and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path
def _log(log_fh, message):
    """Print and append one log line."""
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line)
    if log_fh is not None:
        log_fh.write(line + "\n")
        log_fh.flush()

### Helpers: paths
def _project_token(worktree):
    """Return Cursor project-folder token for an absolute worktree path."""
    return str(Path(worktree).expanduser().resolve()).strip("/").replace("/", "-")
def _default_state_db():
    """Return default Cursor state.vscdb path for this OS."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
    return Path.home() / ".config" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
def _default_workspace_storage():
    """Return default Cursor workspaceStorage directory."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Cursor" / "User" / "workspaceStorage"
    return Path.home() / ".config" / "Cursor" / "User" / "workspaceStorage"
def _default_projects_root():
    """Return ~/.cursor/projects."""
    return Path.home() / ".cursor" / "projects"
def _norm_worktree(path):
    """Expand a worktree path; prefer resolve() but keep existence optional."""
    return Path(path).expanduser().resolve(strict=False)
def _path_spellings(worktree):
    """Return unique absolute-path spellings (macOS /var vs /private/var, etc.)."""
    raw = Path(worktree).expanduser()
    spellings = []
    for candidate in (raw, Path(str(raw.absolute())), Path(str(raw.resolve(strict=False)))):
        text = str(candidate)
        if text not in spellings:
            spellings.append(text)
        # Common macOS symlink pair.
        if text.startswith("/var/"):
            alt = "/private" + text
            if alt not in spellings:
                spellings.append(alt)
        elif text.startswith("/private/var/"):
            alt = text[len("/private"):]
            if alt not in spellings:
                spellings.append(alt)
    return spellings
def _path_variants(worktree):
    """Return primary absolute path and file-URI for a worktree."""
    abs_path = _path_spellings(worktree)[0]
    return abs_path, Path(abs_path).as_uri()
def _home_relative_spelling(abs_path):
    """Return ~/... form when abs_path is under the user home directory."""
    home = str(Path.home())
    text = str(abs_path)
    if text == home:
        return "~"
    prefix = home.rstrip("/") + "/"
    if text.startswith(prefix):
        return "~/" + text[len(prefix):]
    return None
def _replacement_pairs(source_worktree, target_worktree):
    """Build longest-first (old, new) string pairs for safe path rewriting."""
    src_paths = _path_spellings(source_worktree)
    tgt_paths = _path_spellings(target_worktree)
    # Pair by index when possible; otherwise map every source spelling to primary target.
    primary_tgt = tgt_paths[0]
    pairs = []
    for idx, src in enumerate(src_paths):
        tgt = tgt_paths[idx] if idx < len(tgt_paths) else primary_tgt
        pairs.append((Path(src).as_uri(), Path(tgt).as_uri()))
        pairs.append((src, tgt))
        pairs.append((_project_token(src), _project_token(tgt)))
        src_home = _home_relative_spelling(src)
        tgt_home = _home_relative_spelling(tgt)
        if src_home and tgt_home:
            pairs.append((src_home, tgt_home))
    # Deduplicate while preserving order.
    seen = set()
    out = []
    for old, new in pairs:
        if old == new or old in seen:
            continue
        seen.add(old)
        out.append((old, new))
    out.sort(key=lambda item: len(item[0]), reverse=True)
    return out
def _rewrite_text(text, pairs):
    """Apply all replacement pairs to text; return (new_text, change_count)."""
    if text is None:
        return text, 0
    changed = 0
    for old, new in pairs:
        if old in text:
            count = text.count(old)
            text = text.replace(old, new)
            changed += count
    return text, changed

### Helpers: process / io
def _is_cursor_main_command(command):
    """Return True for the Cursor app main binary (not Helper / agent helpers)."""
    if not command:
        return False
    if "Cursor Helper" in command:
        return False
    if "/Applications/Cursor.app/Contents/Resources/helpers/" in command:
        return False
    if "/Applications/Cursor.app/Contents/MacOS/Cursor" in command:
        return True
    if re.search(r"/Cursor\.app/Contents/MacOS/Cursor(\s|$)", command):
        return True
    return False
def _run_capture(args):
    """Run a subprocess; return stdout text, or '' on missing binary / permission errors."""
    try:
        proc = subprocess.run(args, capture_output=True, text=True, check=False)
    except (FileNotFoundError, PermissionError, OSError):
        return ""
    return proc.stdout or ""
def _describe_pid(pid, command_hint=""):
    """Return dict identity for a PID (command, cwd, listen, kind, summary)."""
    pid = str(pid)
    cmd = _run_capture(["ps", "-p", pid, "-ww", "-o", "command="]).strip()
    cwd = ""
    for line in _run_capture(["lsof", "-a", "-p", pid, "-d", "cwd", "-Fn"]).splitlines():
        if line.startswith("n"):
            cwd = line[1:]
            break
    listen = ""
    for line in _run_capture(["lsof", "-nP", "-p", pid, "-a", "-iTCP", "-sTCP:LISTEN"]).splitlines()[1:]:
        if "8790" in line:
            listen = "127.0.0.1:8790"
            break
        cols = line.split()
        if cols:
            listen = cols[-1]
            break
    label = "unknown"
    blob = f"{command_hint} {cmd} {cwd} {listen}".lower()
    if "holodeck" in blob or listen.endswith(":8790") or "/code/holodeck" in blob:
        label = "holodeck-server"
    elif command_hint.lower().startswith("cursor") or "cursor.app" in blob or re.search(r"\bcursor\b", blob):
        label = "cursor-related"
    elif "python" in blob:
        label = "python"
    bits = [f"pid={pid}", f"kind={label}"]
    if cwd:
        bits.append(f"cwd={cwd}")
    if listen:
        bits.append(f"listen={listen}")
    if cmd:
        bits.append(f"cmd={cmd[:180]}")
    return {
        "pid": pid,
        "kind": label,
        "cwd": cwd,
        "listen": listen,
        "cmd": cmd,
        "summary": "; ".join(bits),
    }
def _pid_details(pid):
    """Return a short identity string for a PID (command + cwd hints)."""
    return _describe_pid(pid)["summary"]
def _pid_alive(pid):
    """Return True if pid still exists."""
    out = _run_capture(["ps", "-p", str(pid), "-o", "pid="])
    if out.strip():
        return True
    # Fallback when ps is restricted: lsof -p
    out = _run_capture(["lsof", "-p", str(pid)])
    return bool(out.strip())
def _signal_pids(pids, sig="TERM"):
    """Send signal to pids. Returns list of (pid, ok, message)."""
    results = []
    for pid in pids:
        proc = subprocess.run(["kill", f"-{sig}", str(pid)], capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            results.append((str(pid), True, f"sent SIG{sig}"))
        else:
            err = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
            results.append((str(pid), False, err))
    return results
def _wait_pids_exit(pids, timeout_s=8.0, poll_s=0.25):
    """Wait until pids exit or timeout. Returns still-alive pid list."""
    deadline = time.time() + timeout_s
    alive = [str(p) for p in pids]
    while alive and time.time() < deadline:
        alive = [p for p in alive if _pid_alive(p)]
        if not alive:
            break
        time.sleep(poll_s)
    return alive
def _parse_opener_pids(lines):
    """Extract unique PIDs from opener detail lines."""
    pids = []
    seen = set()
    for line in lines:
        match = re.search(r"pid=(\d+)", line)
        if not match:
            continue
        pid = match.group(1)
        if pid in seen:
            continue
        seen.add(pid)
        pids.append(pid)
    return pids
def _collect_db_gate_evidence():
    """Collect Cursor-running evidence and other state.vscdb openers separately."""
    cursor_evidence = []
    other_openers = []
    seen_cursor = set()
    seen_other = set()
    def _add(bucket, seen, line):
        line = line.strip()
        if not line or line in seen:
            return
        seen.add(line)
        bucket.append(line)
    # Method 1: ps for Cursor main binary.
    for raw in _run_capture(["ps", "-ax", "-o", "pid=,command="]).splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) < 2:
            continue
        pid, command = parts[0], parts[1]
        if _is_cursor_main_command(command):
            _add(cursor_evidence, seen_cursor, f"ps pid={pid} cmd={command}")
    # Method 2: pgrep -lf
    for line in _run_capture(["pgrep", "-lf", "Cursor"]).splitlines():
        if _is_cursor_main_command(line):
            _add(cursor_evidence, seen_cursor, f"pgrep {line.strip()}")
    # Method 3: who still has state.vscdb open.
    state_db = _default_state_db()
    if state_db.exists():
        my_pid = str(os.getpid())
        seen_pids = set()
        for line in _run_capture(["lsof", "-nP", str(state_db)]).splitlines()[1:]:
            cols = line.split()
            if len(cols) < 2:
                continue
            command, pid = cols[0], cols[1]
            if pid == my_pid or pid in seen_pids:
                continue
            seen_pids.add(pid)
            detail = _describe_pid(pid, command_hint=command)["summary"]
            if command.lower().startswith("cursor") or _is_cursor_main_command(line):
                _add(cursor_evidence, seen_cursor, f"lsof Cursor opener: {detail}")
            else:
                _add(other_openers, seen_other, f"lsof non-Cursor opener: {detail}")
    return cursor_evidence, other_openers
def _format_gate_details(cursor_evidence, other_openers):
    """Format gate evidence for logs/UI."""
    parts = []
    if cursor_evidence:
        parts.append("CURSOR processes:")
        parts.extend(cursor_evidence[:12])
    if other_openers:
        parts.append("OTHER processes still holding state.vscdb (must close these too):")
        parts.extend(other_openers[:12])
    return "\n".join(parts)
def _cursor_running():
    """Return (blocked, details_text). Blocked if Cursor or any DB opener remains."""
    cursor_evidence, other_openers = _collect_db_gate_evidence()
    return bool(cursor_evidence or other_openers), _format_gate_details(cursor_evidence, other_openers)
def prompt_kill_non_cursor_openers(other_openers, assume_yes=False, log_fh=None):
    """Prompt to kill Holodeck/other DB openers; never kills Cursor. Returns True if cleared."""
    if not other_openers:
        return True
    pids = _parse_opener_pids(other_openers)
    if not pids:
        _log(log_fh, "Could not parse PIDs from other openers; cannot auto-kill.")
        return False
    print()
    print("Non-Cursor processes are holding state.vscdb open (rewrite is unsafe until they exit):")
    for line in other_openers:
        print(f"  {line}")
    print()
    print("These are often Holodeck (`apps/holodeck/server.py` on 127.0.0.1:8790).")
    print("This prompt will NEVER kill the Cursor app itself — only the PIDs listed above.")
    if assume_yes:
        answer = "kill"
        print("(--yes) auto-confirming kill of non-Cursor DB openers")
    else:
        try:
            answer = input("Type 'kill' to send SIGTERM to those PIDs, or anything else to skip: ").strip().lower()
        except EOFError:
            answer = ""
    if answer != "kill":
        _log(log_fh, "User declined killing non-Cursor DB openers.")
        print("Skipped kill. Quit those processes yourself, then re-run --check-cursor.")
        return False
    _log(log_fh, f"Sending SIGTERM to non-Cursor DB openers: {', '.join(pids)}")
    for pid, ok, msg in _signal_pids(pids, "TERM"):
        line = f"  kill -TERM {pid}: {'ok' if ok else 'failed'} ({msg})"
        _log(log_fh, line)
        print(line)
    alive = _wait_pids_exit(pids, timeout_s=8.0)
    if alive:
        print(f"Still alive after SIGTERM: {', '.join(alive)}")
        if assume_yes:
            escalate = "kill9"
            print("(--yes) escalating to SIGKILL")
        else:
            try:
                escalate = input("Type 'kill9' to send SIGKILL to remaining PIDs, or anything else to stop: ").strip().lower()
            except EOFError:
                escalate = ""
        if escalate == "kill9":
            _log(log_fh, f"Sending SIGKILL to remaining openers: {', '.join(alive)}")
            for pid, ok, msg in _signal_pids(alive, "KILL"):
                line = f"  kill -KILL {pid}: {'ok' if ok else 'failed'} ({msg})"
                _log(log_fh, line)
                print(line)
            alive = _wait_pids_exit(alive, timeout_s=4.0)
    # Confirm against live lsof, not only ps.
    _cursor_ev, remaining = _collect_db_gate_evidence()
    still = _parse_opener_pids(remaining)
    if still:
        _log(log_fh, f"After kill attempt, still holding state.vscdb: {', '.join(still)}")
        print("CONFIRM FAILED: these non-Cursor PIDs still hold state.vscdb:")
        for line in remaining:
            print(f"  {line}")
        return False
    _log(log_fh, "CONFIRM OK: no non-Cursor processes hold state.vscdb.")
    print("CONFIRM OK: non-Cursor DB openers are gone.")
    return True
def run_closed_gate(force=False, assume_yes=False, offer_kill=True, log_fh=None):
    """Run closed-gate with optional kill prompt for Holodeck/other openers.

    Returns (ok, details). ok True means safe for --execute (or force).
    """
    cursor_evidence, other_openers = _collect_db_gate_evidence()
    details = _format_gate_details(cursor_evidence, other_openers)
    _log(log_fh, f"cursor_closed_gate initial cursor={bool(cursor_evidence)} other={bool(other_openers)}")
    if details:
        _log(log_fh, f"cursor_closed_gate evidence:\n{details}")
    if other_openers and offer_kill and not force:
        cleared = prompt_kill_non_cursor_openers(other_openers, assume_yes=assume_yes, log_fh=log_fh)
        cursor_evidence, other_openers = _collect_db_gate_evidence()
        details = _format_gate_details(cursor_evidence, other_openers)
        _log(log_fh, f"cursor_closed_gate after-kill cursor={bool(cursor_evidence)} other={bool(other_openers)} cleared={cleared}")
    blocked = bool(cursor_evidence or other_openers)
    if blocked and not force:
        tips = []
        if cursor_evidence:
            tips.append("- Quit Cursor fully with Cmd+Q (all windows). Do not leave other Cursor windows open.")
        if other_openers:
            tips.append("- Non-Cursor DB openers remain (often Holodeck). Re-run with --check-cursor and type 'kill'.")
            for pid in _parse_opener_pids(other_openers):
                tips.append(f"- Or manually: kill {pid}")
                break
        tips.append("- Re-run: migrate_cursor_ai_sessions.py --check-cursor")
        tips.append("- Only when that prints CURSOR_RUNNING=no, run --execute.")
        message = (
            "ABORT: live state.vscdb is still open — refusing --execute.\n"
            "Detected:\n"
            f"{details}\n\n"
            "What to do:\n"
            + "\n".join(tips)
            + "\nDo not use --force unless you accept corruption risk."
        )
        _log(log_fh, message)
        return False, message
    if blocked and force:
        _log(log_fh, "WARNING: --force set; proceeding while Cursor/DB still looks open.")
        return True, details
    _log(log_fh, "cursor_closed_gate OK: no Cursor main process / DB opener found.")
    return True, details
def assert_cursor_closed_for_execute(force=False, assume_yes=False, log_fh=None):
    """Abort --execute unless Cursor is fully closed and no other process holds state.vscdb."""
    ok, details = run_closed_gate(force=force, assume_yes=assume_yes, offer_kill=True, log_fh=log_fh)
    if not ok:
        raise SystemExit(details)
    return ok, details
def _copy_db_bundle(state_db, dest_path, log_fh):
    """Copy state.vscdb and sibling -wal/-shm into dest_path (exact file name).

    Returns dict with copied paths. Uses file copy so live Cursor is not written.
    Note: if Cursor is open, RAM/WAL contents may be newer than the copied main file.
    """
    state_db = Path(state_db)
    if not state_db.exists():
        raise SystemExit(f"state.vscdb not found: {state_db}")
    _ensure_dir(dest_path.parent)
    shutil.copy2(state_db, dest_path)
    copied = {"db": dest_path}
    for suffix in ("-wal", "-shm"):
        sibling = Path(str(state_db) + suffix)
        if sibling.exists():
            dest_sib = Path(str(dest_path) + suffix)
            shutil.copy2(sibling, dest_sib)
            copied[suffix.lstrip("-")] = dest_sib
    _log(log_fh, f"Copied DB bundle -> {dest_path} ({dest_path.stat().st_size} bytes)")
    for key, path in copied.items():
        if key != "db":
            _log(log_fh, f"  + {key}: {path} ({path.stat().st_size} bytes)")
    return copied
def _checkpoint_copy_via_sqlite(state_db, dest_path, log_fh):
    """Prefer SQLite backup API for a consistent snapshot into dest_path."""
    state_db = Path(state_db)
    _ensure_dir(dest_path.parent)
    if dest_path.exists():
        dest_path.unlink()
    src = sqlite3.connect(f"file:{state_db}?mode=ro", uri=True)
    try:
        dest = sqlite3.connect(str(dest_path))
        try:
            src.backup(dest)
            dest.commit()
        finally:
            dest.close()
    finally:
        src.close()
    _log(log_fh, f"SQLite backup API copy -> {dest_path} ({dest_path.stat().st_size} bytes)")
    return {"db": dest_path}

### Core: DB rewrite
def _blob_to_text(value):
    """Decode a DB value to text when possible; return (text, encoding_or_None)."""
    if value is None:
        return None, None
    if isinstance(value, str):
        return value, "str"
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytes):
        for enc in ("utf-8", "utf-8-sig"):
            try:
                return value.decode(enc), enc
            except UnicodeDecodeError:
                continue
        return None, None
    return str(value), "str"
def _text_to_blob(text, encoding):
    """Encode rewritten text back to the original storage shape."""
    if encoding == "str":
        return text
    return text.encode(encoding or "utf-8")
def _table_has_columns(conn, table, required):
    """Return True when table exists and has all required columns."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    if not rows:
        return False
    names = {row[1] for row in rows}
    return set(required).issubset(names)
def rewrite_state_db(db_path, pairs, since_ms, source_worktree, log_fh):
    """Rewrite path strings in a state.vscdb copy/file. Returns stats dict."""
    db_path = Path(db_path)
    src_paths = _path_spellings(source_worktree)
    stats = {
        "tables": {},
        "rows_scanned": 0,
        "rows_updated": 0,
        "replacements": 0,
        "composers_matching_source": 0,
        "composers_matching_since": 0,
        "composer_samples": [],
    }
    conn = sqlite3.connect(str(db_path))
    try:
        # Inventory composers for the source worktree (for report / since filter).
        if _table_has_columns(conn, "cursorDiskKV", ["key", "value"]):
            for key, value in conn.execute(
                "SELECT key, value FROM cursorDiskKV WHERE key LIKE 'composerData:%'"
            ):
                text, _enc = _blob_to_text(value)
                if not text or not any(src in text for src in src_paths):
                    continue
                try:
                    obj = json.loads(text)
                except json.JSONDecodeError:
                    continue
                ws = ((obj.get("workspaceIdentifier") or {}).get("uri") or {})
                fs_path = (ws.get("fsPath") or ws.get("path") or "").rstrip("/")
                matched = False
                for src_abs in src_paths:
                    src_norm = src_abs.rstrip("/")
                    if fs_path == src_norm or fs_path.startswith(src_norm + "/"):
                        matched = True
                        break
                    if f'"fsPath":"{src_abs}"' in text or f'"path":"{src_abs}"' in text:
                        matched = True
                        break
                if not matched:
                    continue
                created = obj.get("createdAt")
                stats["composers_matching_source"] += 1
                since_ok = since_ms is None or (isinstance(created, (int, float)) and created >= since_ms)
                if since_ok:
                    stats["composers_matching_since"] += 1
                if len(stats["composer_samples"]) < 15:
                    stats["composer_samples"].append(
                        {
                            "composerId": (key or "").split(":", 1)[-1],
                            "createdAt": created,
                            "createdAtLocal": _ms_to_local(created) if isinstance(created, (int, float)) else "",
                            "name": obj.get("name") or "",
                            "since_ok": since_ok,
                        }
                    )
        for table, key_col, value_col in (
            ("cursorDiskKV", "key", "value"),
            ("ItemTable", "key", "value"),
        ):
            if not _table_has_columns(conn, table, [key_col, value_col]):
                continue
            updated = 0
            replacements = 0
            scanned = 0
            rows = conn.execute(f"SELECT rowid, {key_col}, {value_col} FROM {table}").fetchall()
            for rowid, key, value in rows:
                scanned += 1
                key_text = key if isinstance(key, str) else None
                val_text, enc = _blob_to_text(value)
                new_key = key_text
                key_changes = 0
                val_changes = 0
                if key_text:
                    new_key, key_changes = _rewrite_text(key_text, pairs)
                new_val = val_text
                if val_text is not None:
                    new_val, val_changes = _rewrite_text(val_text, pairs)
                if key_changes or val_changes:
                    params = []
                    sets = []
                    if key_changes:
                        sets.append(f"{key_col} = ?")
                        params.append(new_key)
                    if val_changes:
                        sets.append(f"{value_col} = ?")
                        params.append(_text_to_blob(new_val, enc))
                    params.append(rowid)
                    conn.execute(f"UPDATE {table} SET {', '.join(sets)} WHERE rowid = ?", params)
                    updated += 1
                    replacements += key_changes + val_changes
            stats["tables"][table] = {
                "rows_scanned": scanned,
                "rows_updated": updated,
                "replacements": replacements,
            }
            stats["rows_scanned"] += scanned
            stats["rows_updated"] += updated
            stats["replacements"] += replacements
            _log(log_fh, f"DB {table}: scanned={scanned} updated={updated} replacements={replacements}")
        if _table_has_columns(conn, "composerHeaders", ["composerId", "value"]):
            updated = 0
            replacements = 0
            scanned = 0
            for rowid, value in conn.execute("SELECT rowid, value FROM composerHeaders"):
                scanned += 1
                text, enc = _blob_to_text(value)
                if text is None:
                    continue
                new_text, changes = _rewrite_text(text, pairs)
                if changes:
                    conn.execute(
                        "UPDATE composerHeaders SET value = ? WHERE rowid = ?",
                        (_text_to_blob(new_text, enc or "str"), rowid),
                    )
                    updated += 1
                    replacements += changes
            stats["tables"]["composerHeaders"] = {
                "rows_scanned": scanned,
                "rows_updated": updated,
                "replacements": replacements,
            }
            stats["rows_scanned"] += scanned
            stats["rows_updated"] += updated
            stats["replacements"] += replacements
            _log(log_fh, f"DB composerHeaders: scanned={scanned} updated={updated} replacements={replacements}")
        conn.commit()
    finally:
        conn.close()
    return stats
def review_state_db(db_path, source_worktree, target_worktree, log_fh):
    """Count remaining source vs target path hits after rewrite."""
    src_paths = _path_spellings(source_worktree)
    tgt_paths = _path_spellings(target_worktree)
    src_home = [p for p in (_home_relative_spelling(x) for x in src_paths) if p]
    tgt_home = [p for p in (_home_relative_spelling(x) for x in tgt_paths) if p]
    needles = {
        "source_abs": src_paths,
        "source_uri": [Path(p).as_uri() for p in src_paths],
        "source_token": [_project_token(p) for p in src_paths],
        "source_home": src_home,
        "target_abs": tgt_paths,
        "target_uri": [Path(p).as_uri() for p in tgt_paths],
        "target_token": [_project_token(p) for p in tgt_paths],
        "target_home": tgt_home,
    }
    counts = {name: 0 for name in needles}
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        texts = []
        for table in ("cursorDiskKV", "ItemTable"):
            if not _table_has_columns(conn, table, ["key", "value"]):
                continue
            for key, value in conn.execute(f"SELECT key, value FROM {table}"):
                text_parts = []
                if isinstance(key, str):
                    text_parts.append(key)
                val_text, _enc = _blob_to_text(value)
                if val_text:
                    text_parts.append(val_text)
                texts.append("\n".join(text_parts))
        if _table_has_columns(conn, "composerHeaders", ["value"]):
            for (value,) in conn.execute("SELECT value FROM composerHeaders"):
                text, _enc = _blob_to_text(value)
                if text:
                    texts.append(text)
    finally:
        conn.close()
    for blob in texts:
        for name, needle_list in needles.items():
            for needle in needle_list:
                if needle and needle in blob:
                    counts[name] += blob.count(needle)
    _log(log_fh, "DB review counts after rewrite:")
    for name, count in counts.items():
        _log(log_fh, f"  {name}: {count}")
    return counts

### Core: projects + workspaceStorage
def list_transcript_dirs(projects_root, worktree, since_ms):
    """List agent-transcript UUID dirs for a worktree, optionally filtered by mtime."""
    root = Path(projects_root) / _project_token(worktree) / "agent-transcripts"
    if not root.exists():
        return root, []
    dirs = []
    for path in sorted(root.iterdir()):
        if not path.is_dir():
            continue
        mtime_ms = int(path.stat().st_mtime * 1000)
        if since_ms is not None and mtime_ms < since_ms:
            continue
        dirs.append((path, mtime_ms))
    return root, dirs
def migrate_projects_folder(projects_root, source_worktree, target_worktree, since_ms, execute, log_fh):
    """Rename or selectively copy project transcript data. Returns plan/result dict."""
    projects_root = Path(projects_root)
    src_token = _project_token(source_worktree)
    tgt_token = _project_token(target_worktree)
    src_proj = projects_root / src_token
    tgt_proj = projects_root / tgt_token
    src_transcripts, dirs = list_transcript_dirs(projects_root, source_worktree, since_ms)
    result = {
        "source_project": str(src_proj),
        "target_project": str(tgt_proj),
        "source_exists": src_proj.exists(),
        "target_exists": tgt_proj.exists(),
        "transcript_dirs_selected": [str(p) for p, _ms in dirs],
        "action": None,
        "executed": False,
    }
    if not src_proj.exists():
        result["action"] = "skip-missing-source-project"
        _log(log_fh, f"Projects: source missing, skip: {src_proj}")
        return result
    # Full folder rename when no since-filter and target absent.
    if since_ms is None and not tgt_proj.exists():
        result["action"] = "rename-project-folder"
        _log(log_fh, f"Projects: would rename {src_proj} -> {tgt_proj}")
        if execute:
            src_proj.rename(tgt_proj)
            result["executed"] = True
            _log(log_fh, "Projects: rename executed")
        return result
    result["action"] = "copy-selected-transcripts"
    _log(log_fh, f"Projects: would copy {len(dirs)} transcript dir(s) into {tgt_proj / 'agent-transcripts'}")
    for path, mtime_ms in dirs:
        _log(log_fh, f"  transcript {path.name} mtime={_ms_to_local(mtime_ms)}")
    if execute:
        dest_root = _ensure_dir(tgt_proj / "agent-transcripts")
        for path, _mtime_ms in dirs:
            dest = dest_root / path.name
            if dest.exists():
                _log(log_fh, f"  skip existing {dest}")
                continue
            shutil.copytree(path, dest)
            _log(log_fh, f"  copied {path.name}")
        # Copy other useful top-level dirs when doing a first-time target create.
        if since_ms is None:
            for child in src_proj.iterdir():
                if child.name == "agent-transcripts":
                    continue
                dest = tgt_proj / child.name
                if dest.exists():
                    continue
                if child.is_dir():
                    shutil.copytree(child, dest)
                else:
                    shutil.copy2(child, dest)
        result["executed"] = True
    return result
def find_workspace_storage_entries(workspace_storage, source_worktree):
    """Find workspace.json files whose folder URI matches the source worktree."""
    workspace_storage = Path(workspace_storage)
    match_values = set()
    for spelling in _path_spellings(source_worktree):
        match_values.add(spelling)
        match_values.add(Path(spelling).as_uri())
    hits = []
    if not workspace_storage.exists():
        return hits
    for path in workspace_storage.glob("*/workspace.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        folder = (data.get("folder") or "").rstrip("/")
        if folder in match_values or folder + "/" in match_values:
            hits.append(path)
            continue
        for value in match_values:
            if folder == value.rstrip("/"):
                hits.append(path)
                break
    return hits
def migrate_workspace_storage(workspace_storage, source_worktree, target_worktree, execute, log_fh, target_workspace_id=None):
    """Retarget source workspace.json only when target has no dedicated workspace yet.

    If the target path already has its own workspace hash (created by opening the
    renamed folder once), do NOT retarget the old hash onto the same URI — that
    creates a dual-binding and the UI binds to the empty new hash.
    """
    tgt_uri = Path(_path_spellings(target_worktree)[0]).as_uri()
    target_hits = find_workspace_storage_entries(workspace_storage, target_worktree)
    source_hits = find_workspace_storage_entries(workspace_storage, source_worktree)
    result = {
        "files": [str(p) for p in source_hits],
        "target_files": [str(p) for p in target_hits],
        "updated": [],
        "skipped_dual_bind": False,
        "action": "retarget-workspace-json",
    }
    if target_hits and target_workspace_id:
        # Target already has a workspace; skip retarget to avoid dual folderUri binding.
        result["action"] = "skip-retarget-target-workspace-exists"
        result["skipped_dual_bind"] = True
        _log(
            log_fh,
            "workspaceStorage: target already has workspace id(s); skipping source workspace.json retarget "
            f"to avoid dual-bind. target_hits={[str(p) for p in target_hits]}",
        )
        return result
    if not source_hits:
        _log(log_fh, "workspaceStorage: no matching workspace.json for source")
        return result
    for path in source_hits:
        data = json.loads(path.read_text(encoding="utf-8"))
        old = data.get("folder")
        new_uri = tgt_uri
        if isinstance(old, str) and old.startswith("file:///var/") and new_uri.startswith("file:///private/var/"):
            new_uri = "file://" + new_uri[len("file:///private"):]
        elif isinstance(old, str) and old.startswith("file:///private/var/") and new_uri.startswith("file:///var/"):
            new_uri = "file:///private" + new_uri[len("file://"):]
        _log(log_fh, f"workspaceStorage: {path} folder {old!r} -> {new_uri!r}")
        if execute:
            data["folder"] = new_uri
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            result["updated"].append(str(path))
    return result

### Core: workspace ID discover / remap
def discover_workspace_ids_for_path(workspace_storage, worktree, state_db=None):
    """Return workspace hash infos for a folder path, newest-first.

    Sources:
    1. workspaceStorage/*/workspace.json folder URI match
    2. ItemTable workspaceMetadata.entries (when state_db provided)
    """
    workspace_storage = Path(workspace_storage)
    infos = []
    seen = set()
    for path in find_workspace_storage_entries(workspace_storage, worktree):
        wid = path.parent.name
        if wid in seen:
            continue
        seen.add(wid)
        mtime = path.parent.stat().st_mtime if path.parent.exists() else 0
        infos.append({
            "workspace_id": wid,
            "workspace_json": str(path),
            "mtime": mtime,
            "mtime_local": _ms_to_local(int(mtime * 1000)),
            "source": "workspaceStorage",
        })
    if state_db and Path(state_db).exists():
        try:
            conn = sqlite3.connect(f"file:{state_db}?mode=ro", uri=True)
            try:
                row = conn.execute(
                    "SELECT value FROM ItemTable WHERE key = ?",
                    ("workspaceMetadata.entries",),
                ).fetchone()
            finally:
                conn.close()
        except sqlite3.Error:
            row = None
        if row:
            text, _enc = _blob_to_text(row[0])
            try:
                obj = json.loads(text) if text else {}
            except json.JSONDecodeError:
                obj = {}
            match_uris = set()
            for spelling in _path_spellings(worktree):
                match_uris.add(Path(spelling).as_uri())
                match_uris.add(spelling)
            for entry in obj.get("entries") or []:
                folder = (entry.get("folderUri") or "").rstrip("/")
                wid = entry.get("workspaceId") or ""
                if not wid or wid in seen:
                    continue
                if folder in match_uris or any(folder == u.rstrip("/") for u in match_uris):
                    seen.add(wid)
                    ws_dir = workspace_storage / wid
                    mtime = ws_dir.stat().st_mtime if ws_dir.exists() else 0
                    infos.append({
                        "workspace_id": wid,
                        "workspace_json": str(ws_dir / "workspace.json"),
                        "mtime": mtime,
                        "mtime_local": _ms_to_local(int(mtime * 1000)) if mtime else "",
                        "source": "workspaceMetadata.entries",
                        "displayPath": entry.get("displayPath") or "",
                    })
    infos.sort(key=lambda item: item.get("mtime") or 0, reverse=True)
    return infos
def choose_workspace_id(infos, explicit=None, role="target"):
    """Pick one workspace id from discover results or an explicit override."""
    if explicit:
        return explicit
    if not infos:
        return None
    if len(infos) == 1:
        return infos[0]["workspace_id"]
    # Prefer newest for target (post-rename open). Prefer oldest for source (original).
    if role == "source":
        return infos[-1]["workspace_id"]
    return infos[0]["workspace_id"]
def remap_composer_workspace_ids(db_path, source_workspace_id, target_workspace_id, log_fh):
    """Remap composerHeaders.workspaceId from source hash to target hash."""
    if not source_workspace_id or not target_workspace_id:
        raise SystemExit("remap requires both source_workspace_id and target_workspace_id")
    if source_workspace_id == target_workspace_id:
        _log(log_fh, "workspace-id remap skipped: source and target ids are identical")
        return {"updated": 0, "source_workspace_id": source_workspace_id, "target_workspace_id": target_workspace_id}
    conn = sqlite3.connect(str(db_path))
    try:
        before = conn.execute(
            "SELECT COUNT(*) FROM composerHeaders WHERE workspaceId = ?",
            (source_workspace_id,),
        ).fetchone()[0]
        conn.execute(
            "UPDATE composerHeaders SET workspaceId = ? WHERE workspaceId = ?",
            (target_workspace_id, source_workspace_id),
        )
        # Also rewrite workspaceId string inside composerHeaders.value JSON when present.
        value_updates = 0
        if _table_has_columns(conn, "composerHeaders", ["value"]):
            for rowid, value in conn.execute(
                "SELECT rowid, value FROM composerHeaders WHERE workspaceId = ?",
                (target_workspace_id,),
            ):
                text, enc = _blob_to_text(value)
                if not text or source_workspace_id not in text:
                    continue
                new_text, n = _rewrite_text(text, [(source_workspace_id, target_workspace_id)])
                if n:
                    conn.execute(
                        "UPDATE composerHeaders SET value = ? WHERE rowid = ?",
                        (_text_to_blob(new_text, enc or "str"), rowid),
                    )
                    value_updates += 1
        # Deduplicate workspaceMetadata.entries folderUri bindings.
        meta_updates = 0
        if _table_has_columns(conn, "ItemTable", ["key", "value"]):
            row = conn.execute(
                "SELECT rowid, value FROM ItemTable WHERE key = ?",
                ("workspaceMetadata.entries",),
            ).fetchone()
            if row:
                rowid, value = row
                text, enc = _blob_to_text(value)
                if text:
                    try:
                        obj = json.loads(text)
                    except json.JSONDecodeError:
                        obj = None
                    if isinstance(obj, dict) and isinstance(obj.get("entries"), list):
                        entries = obj["entries"]
                        kept = []
                        seen_folder = set()
                        changed = False
                        # Prefer target workspace id for any entry that used source id.
                        for entry in entries:
                            if not isinstance(entry, dict):
                                kept.append(entry)
                                continue
                            wid = entry.get("workspaceId")
                            folder = (entry.get("folderUri") or "").rstrip("/")
                            if wid == source_workspace_id:
                                entry = dict(entry)
                                entry["workspaceId"] = target_workspace_id
                                wid = target_workspace_id
                                changed = True
                            # Drop duplicate folderUri rows; keep first occurrence after remap.
                            if folder and folder in seen_folder:
                                changed = True
                                continue
                            if folder:
                                seen_folder.add(folder)
                            kept.append(entry)
                        if changed:
                            obj["entries"] = kept
                            conn.execute(
                                "UPDATE ItemTable SET value = ? WHERE rowid = ?",
                                (_text_to_blob(json.dumps(obj, separators=(",", ":")), enc or "str"), rowid),
                            )
                            meta_updates = 1
        conn.commit()
        after_src = conn.execute(
            "SELECT COUNT(*) FROM composerHeaders WHERE workspaceId = ?",
            (source_workspace_id,),
        ).fetchone()[0]
        after_tgt = conn.execute(
            "SELECT COUNT(*) FROM composerHeaders WHERE workspaceId = ?",
            (target_workspace_id,),
        ).fetchone()[0]
    finally:
        conn.close()
    stats = {
        "updated": before,
        "value_updates": value_updates,
        "metadata_updates": meta_updates,
        "source_workspace_id": source_workspace_id,
        "target_workspace_id": target_workspace_id,
        "remaining_on_source": after_src,
        "count_on_target": after_tgt,
    }
    _log(
        log_fh,
        "workspace-id remap: "
        f"moved={before} value_json_updates={value_updates} metadata_updates={meta_updates} "
        f"remaining_on_source={after_src} count_on_target={after_tgt}",
    )
    return stats
def print_discover_and_execute_command(source_worktree, target_worktree, source_id, target_id, since=None, script_path=None):
    """Print discovered ids and a copy-paste Terminal execute command."""
    script_path = script_path or Path(__file__).resolve()
    py = Path(__file__).resolve().parents[4] / ".venv" / "bin" / "python3"
    if not py.exists():
        py = Path(sys.executable)
    print()
    print("Discovered workspace IDs:")
    print(f"  source_workspace_id={source_id or '(none)'}")
    print(f"  target_workspace_id={target_id or '(none)'}")
    if not source_id or not target_id:
        print()
        print("Cannot build execute command until BOTH workspace IDs are known.")
        print("Open the target worktree once in Cursor (expect empty history), close that window,")
        print("then re-run --discover-workspace-ids.")
        return
    since_arg = f" \\\n  --since {since}" if since else ""
    cmd = (
        f"{py} \\\n"
        f"  {script_path} \\\n"
        f"  --source-worktree {source_worktree} \\\n"
        f"  --target-worktree {target_worktree} \\\n"
        f"  --source-workspace-id {source_id} \\\n"
        f"  --target-workspace-id {target_id}"
        f"{since_arg} \\\n"
        f"  --execute \\\n"
        f"  --yes"
    )
    print()
    print("Copy this into Terminal.app AFTER fully quitting Cursor (Cmd+Q) and stopping Holodeck:")
    print()
    print(cmd)
    print()

### Core: backups listing / prune
def list_tool_backups(backup_dir):
    """List state.vscdb backups created by this tool, newest first."""
    backup_dir = Path(backup_dir)
    if not backup_dir.exists():
        return []
    files = []
    for path in backup_dir.glob("state.vscdb.*"):
        name = path.name
        if name.endswith("-wal") or name.endswith("-shm"):
            continue
        files.append(path)
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files
def maybe_prune_backups(backup_dir, log_fh, assume_yes=False):
    """List backups and optionally delete all but the newest."""
    backups = list_tool_backups(backup_dir)
    if not backups:
        _log(log_fh, "No tool backups found to prune.")
        return
    _log(log_fh, "Backups created by this tool (newest first):")
    for path in backups:
        _log(log_fh, f"  {path} ({path.stat().st_size} bytes, mtime={_ms_to_local(int(path.stat().st_mtime * 1000))})")
    if len(backups) <= 1:
        _log(log_fh, "Only one backup present; nothing to prune.")
        return
    keep = backups[0]
    drop = backups[1:]
    prompt = (
        f"Delete {len(drop)} older backup(s) and keep only the newest?\n"
        f"  keep: {keep}\n"
        "Type 'yes' to delete older backups, anything else to keep all: "
    )
    if assume_yes:
        answer = "yes"
    else:
        try:
            answer = input(prompt).strip().lower()
        except EOFError:
            answer = ""
    if answer != "yes":
        _log(log_fh, "Keeping all backups.")
        return
    for path in drop:
        for sibling in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
            if sibling.exists():
                sibling.unlink()
                _log(log_fh, f"Deleted backup file: {sibling}")

### Main
def build_parser():
    """Create CLI parser."""
    parser = argparse.ArgumentParser(
        description="Migrate Cursor AI sessions across a worktree rename/path change."
    )
    parser.add_argument("--source-worktree", help="Absolute source worktree path (old). Required unless --check-cursor.")
    parser.add_argument("--target-worktree", help="Absolute target worktree path (new). Required unless --check-cursor.")
    parser.add_argument("--since", help="Only highlight/move sessions at or after this time (YYYY-MM-DD or ISO).")
    parser.add_argument("--source-workspace-id", help="Old Cursor workspaceStorage hash (composerHeaders.workspaceId).")
    parser.add_argument("--target-workspace-id", help="New workspaceStorage hash from opening the renamed folder once.")
    parser.add_argument(
        "--discover-workspace-ids",
        action="store_true",
        help="Discover source/target workspace hashes and print a copy-paste --execute command (read-only).",
    )
    parser.add_argument("--state-db", help="Override path to state.vscdb.")
    parser.add_argument("--projects-root", help="Override ~/.cursor/projects.")
    parser.add_argument("--workspace-storage", help="Override workspaceStorage directory.")
    parser.add_argument("--migrate-root", default=str(DEFAULT_ROOT), help="Root for backups/logs/dry-run copies.")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Copy DB and apply changes only to the copy (default).")
    parser.add_argument("--execute", action="store_true", help="Apply changes to live Cursor data (requires Cursor fully quit).")
    parser.add_argument("--force", action="store_true", help="DANGEROUS: allow --execute even if Cursor/DB still looks open.")
    parser.add_argument("--yes", action="store_true", help="Non-interactive yes for execute confirmation and backup prune.")
    parser.add_argument(
        "--check-cursor",
        action="store_true",
        help="Only check whether Cursor is running; exit 0 if closed, exit 1 if running. Ignores other migrate actions.",
    )
    parser.add_argument("--skip-db", action="store_true", help="Do not copy/rewrite state.vscdb.")
    parser.add_argument("--skip-projects", action="store_true", help="Do not rename/copy ~/.cursor/projects data.")
    parser.add_argument("--skip-workspace-storage", action="store_true", help="Do not retarget workspace.json.")
    parser.add_argument("--skip-workspace-id-remap", action="store_true", help="Do not remap composerHeaders.workspaceId.")
    parser.add_argument("--copy-mode", choices=("sqlite-backup", "file-copy"), default="sqlite-backup",
                        help="How to snapshot state.vscdb for dry-run/backup.")
    parser.add_argument("--prune-backups", action="store_true", default=True, help="Offer to prune older tool backups at end (default).")
    parser.add_argument("--no-prune-backups", action="store_true", help="Do not offer backup pruning.")
    return parser
def main(argv=None):
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    # Standalone Cursor-closed check (no worktree args required).
    if args.check_cursor:
        cursor_evidence, other_openers = _collect_db_gate_evidence()
        if cursor_evidence or other_openers:
            print("CURSOR_RUNNING=yes")
            print(_format_gate_details(cursor_evidence, other_openers))
            if other_openers:
                print(
                    "\nNote: Activity Monitor may not list these under 'Cursor' "
                    "(e.g. Holodeck python on 127.0.0.1:8790)."
                )
                prompt_kill_non_cursor_openers(other_openers, assume_yes=args.yes, log_fh=None)
                cursor_evidence, other_openers = _collect_db_gate_evidence()
        if cursor_evidence or other_openers:
            print("\nResult after preflight:")
            print(_format_gate_details(cursor_evidence, other_openers) or "(unexpected empty details)")
            if cursor_evidence:
                print("Cursor is still open — quit with Cmd+Q, then re-run --check-cursor.")
            if other_openers:
                print("Non-Cursor DB openers remain — kill them, then re-run --check-cursor.")
            print("Result: do NOT run --execute yet.")
            return 1
        print("CURSOR_RUNNING=no")
        print("Result: no Cursor main process / state.vscdb opener found — safe to run --execute.")
        return 0
    if not args.source_worktree or not args.target_worktree:
        parser.error("--source-worktree and --target-worktree are required unless --check-cursor")
    execute = bool(args.execute)
    dry_run = not execute
    since_ms = _parse_since(args.since)
    source_worktree = _norm_worktree(args.source_worktree)
    target_worktree = _norm_worktree(args.target_worktree)
    if str(source_worktree) == str(target_worktree):
        raise SystemExit("source-worktree and target-worktree must differ")
    state_db = Path(args.state_db) if args.state_db else _default_state_db()
    projects_root = Path(args.projects_root) if args.projects_root else _default_projects_root()
    workspace_storage = Path(args.workspace_storage) if args.workspace_storage else _default_workspace_storage()
    source_ws_infos = discover_workspace_ids_for_path(workspace_storage, source_worktree, state_db=state_db)
    target_ws_infos = discover_workspace_ids_for_path(workspace_storage, target_worktree, state_db=state_db)
    # After a rename + open, both hashes may bind to the target path (dual-bind).
    # Newest = target window Cursor created; oldest = migrated/old workspace.
    if not source_ws_infos and len(target_ws_infos) >= 2 and not args.source_workspace_id:
        source_ws_infos = [target_ws_infos[-1]]
        _source_from_dual = True
    else:
        _source_from_dual = False
    source_workspace_id = choose_workspace_id(
        source_ws_infos, explicit=args.source_workspace_id, role="source"
    )
    target_workspace_id = choose_workspace_id(
        target_ws_infos, explicit=args.target_workspace_id, role="target"
    )
    if args.discover_workspace_ids:
        print("source workspace candidates:")
        for info in source_ws_infos or []:
            print(f"  {info}")
        if _source_from_dual:
            print("  (source inferred as oldest dual-bind on target path)")
        print("target workspace candidates:")
        for info in target_ws_infos or []:
            print(f"  {info}")
        print_discover_and_execute_command(
            source_worktree,
            target_worktree,
            source_workspace_id,
            target_workspace_id,
            since=args.since,
        )
        return 0 if source_workspace_id and target_workspace_id else 2
    migrate_root = _ensure_dir(Path(args.migrate_root).expanduser())
    backup_dir = _ensure_dir(migrate_root / "backups")
    log_dir = _ensure_dir(migrate_root / "logs")
    dry_dir = _ensure_dir(migrate_root / "dry-run")
    stamp = _now_stamp()
    mode = "execute" if execute else "dry-run"
    log_path = log_dir / f"{TOOL_NAME}_{mode}_{stamp}.log"
    pairs = _replacement_pairs(source_worktree, target_worktree)
    with log_path.open("w", encoding="utf-8") as log_fh:
        _log(log_fh, f"{TOOL_NAME} starting mode={mode}")
        _log(log_fh, f"log_file={log_path}")
        _log(log_fh, f"source_worktree={source_worktree}")
        _log(log_fh, f"target_worktree={target_worktree}")
        _log(log_fh, f"source_token={_project_token(source_worktree)}")
        _log(log_fh, f"target_token={_project_token(target_worktree)}")
        _log(log_fh, f"source_workspace_id={source_workspace_id}")
        _log(log_fh, f"target_workspace_id={target_workspace_id}")
        _log(log_fh, f"since={args.since!r} since_ms={since_ms} ({_ms_to_local(since_ms) if since_ms else 'none'})")
        _log(log_fh, f"state_db={state_db} exists={state_db.exists()}")
        _log(log_fh, "replacement pairs:")
        for old, new in pairs:
            _log(log_fh, f"  {old} -> {new}")
        running, details = _cursor_running()
        _log(log_fh, f"cursor_running={running}")
        if details:
            _log(log_fh, f"cursor_process_sample:\n{details}")
        if execute:
            needs_remap = (not args.skip_db) and (not args.skip_workspace_id_remap)
            if needs_remap and (not source_workspace_id or not target_workspace_id):
                raise SystemExit(
                    "ABORT: --execute needs both workspace IDs for composer history remap.\n"
                    "Recommended workflow:\n"
                    "  1) Rename worktree on disk\n"
                    "  2) Open the new folder once in Cursor (history will look empty)\n"
                    "  3) Close that window\n"
                    "  4) Run --discover-workspace-ids and copy the printed command\n"
                    "  5) Quit Cursor fully, then run that --execute command\n"
                    "Or pass --source-workspace-id / --target-workspace-id explicitly.\n"
                    "Use --skip-workspace-id-remap only if you intentionally skip history attach."
                )
            # Hard gate: same detection as --check-cursor (+ kill prompt for Holodeck/others).
            assert_cursor_closed_for_execute(force=args.force, assume_yes=args.yes, log_fh=log_fh)
            if not args.yes:
                print(
                    "\nAbout to modify LIVE Cursor data:\n"
                    f"  state.vscdb: {state_db}\n"
                    f"  projects: {projects_root}\n"
                    f"  workspaceStorage: {workspace_storage}\n"
                    f"  source_workspace_id: {source_workspace_id}\n"
                    f"  target_workspace_id: {target_workspace_id}\n"
                )
                answer = input("Type 'migrate' to proceed with LIVE changes: ").strip()
                if answer != "migrate":
                    _log(log_fh, "Execute aborted by user confirmation.")
                    print(f"Aborted. Log: {log_path}")
                    return 1
        summary = {
            "mode": mode,
            "log_file": str(log_path),
            "source_worktree": str(source_worktree),
            "target_worktree": str(target_worktree),
            "source_workspace_id": source_workspace_id,
            "target_workspace_id": target_workspace_id,
            "since": args.since,
            "cursor_running": running,
            "db": None,
            "workspace_id_remap": None,
            "projects": None,
            "workspace_storage": None,
            "review": None,
            "backup_db": None,
            "dry_run_db": None,
        }
        # DB path
        if not args.skip_db:
            if not state_db.exists():
                raise SystemExit(f"state.vscdb not found: {state_db}")
            if dry_run:
                dry_db = dry_dir / f"state.vscdb.dry-run.{stamp}"
                t0 = time.time()
                if args.copy_mode == "file-copy":
                    _copy_db_bundle(state_db, dry_db, log_fh)
                else:
                    try:
                        _checkpoint_copy_via_sqlite(state_db, dry_db, log_fh)
                    except sqlite3.Error as exc:
                        _log(log_fh, f"SQLite backup API failed ({exc}); falling back to file-copy")
                        _copy_db_bundle(state_db, dry_db, log_fh)
                _log(log_fh, f"DB copy elapsed_s={time.time() - t0:.1f}")
                summary["dry_run_db"] = str(dry_db)
                target_db = dry_db
                # Also keep a named backup snapshot of the pre-change copy.
                backup_db = backup_dir / f"state.vscdb.backup-before-dry-run.{stamp}"
                shutil.copy2(dry_db, backup_db)
                summary["backup_db"] = str(backup_db)
                _log(log_fh, f"Saved dry-run baseline backup: {backup_db}")
            else:
                backup_db = backup_dir / f"state.vscdb.backup-before-execute.{stamp}"
                t0 = time.time()
                if args.copy_mode == "file-copy":
                    _copy_db_bundle(state_db, backup_db, log_fh)
                else:
                    try:
                        _checkpoint_copy_via_sqlite(state_db, backup_db, log_fh)
                    except sqlite3.Error as exc:
                        _log(log_fh, f"SQLite backup API failed ({exc}); falling back to file-copy")
                        _copy_db_bundle(state_db, backup_db, log_fh)
                _log(log_fh, f"Live DB backup elapsed_s={time.time() - t0:.1f}")
                summary["backup_db"] = str(backup_db)
                target_db = state_db
            t0 = time.time()
            db_stats = rewrite_state_db(target_db, pairs, since_ms, source_worktree, log_fh)
            _log(log_fh, f"DB rewrite elapsed_s={time.time() - t0:.1f}")
            _log(log_fh, f"composers_matching_source={db_stats['composers_matching_source']}")
            _log(log_fh, f"composers_matching_since={db_stats['composers_matching_since']}")
            for sample in db_stats["composer_samples"]:
                _log(
                    log_fh,
                    "  composer {composerId} createdAt={createdAtLocal} since_ok={since_ok} name={name!r}".format(
                        **sample
                    ),
                )
            review = review_state_db(target_db, source_worktree, target_worktree, log_fh)
            summary["db"] = db_stats
            summary["review"] = review
            if not args.skip_workspace_id_remap and source_workspace_id and target_workspace_id:
                summary["workspace_id_remap"] = remap_composer_workspace_ids(
                    target_db,
                    source_workspace_id,
                    target_workspace_id,
                    log_fh,
                )
            elif args.skip_workspace_id_remap:
                _log(log_fh, "Skipping workspace-id remap (--skip-workspace-id-remap)")
            else:
                _log(log_fh, "Skipping workspace-id remap (missing source/target workspace id)")
            if dry_run:
                _log(log_fh, f"DRY-RUN DB ready for inspection: {target_db}")
                _log(log_fh, "Live state.vscdb was NOT modified.")
        else:
            _log(log_fh, "Skipping DB rewrite (--skip-db)")
        # Projects folder
        if not args.skip_projects:
            summary["projects"] = migrate_projects_folder(
                projects_root,
                source_worktree,
                target_worktree,
                since_ms,
                execute=execute,
                log_fh=log_fh,
            )
        else:
            _log(log_fh, "Skipping projects folder (--skip-projects)")
        # workspaceStorage
        if not args.skip_workspace_storage:
            summary["workspace_storage"] = migrate_workspace_storage(
                workspace_storage,
                source_worktree,
                target_worktree,
                execute=execute,
                log_fh=log_fh,
                target_workspace_id=target_workspace_id,
            )
        else:
            _log(log_fh, "Skipping workspaceStorage (--skip-workspace-storage)")
        summary_path = log_dir / f"{TOOL_NAME}_{mode}_{stamp}.summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
        _log(log_fh, f"Wrote summary JSON: {summary_path}")
        _log(log_fh, "Done.")
        print()
        print(f"Mode: {mode}")
        print(f"Log: {log_path}")
        print(f"Summary: {summary_path}")
        if summary.get("dry_run_db"):
            print(f"Dry-run DB copy (modified): {summary['dry_run_db']}")
        if summary.get("backup_db"):
            print(f"Backup DB: {summary['backup_db']}")
        if dry_run:
            print("Live Cursor database was not modified.")
            if running:
                print(
                    "NOTE: Cursor was running during dry-run copy. "
                    "Sessions only in RAM / not yet flushed to disk may be missing from the copy."
                )
        if not args.no_prune_backups and args.prune_backups:
            maybe_prune_backups(backup_dir, log_fh, assume_yes=args.yes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
