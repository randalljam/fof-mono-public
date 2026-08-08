#!/usr/bin/env python3
"""Local dev server for the math-quiz app + backup broker for the anchor (math-flu) store.

Run LOCALLY (it holds the .env AWS creds a browser can't):
    cd apps/math-quiz && python3 tools/dev_server.py
    # http://127.0.0.1:8907/anchor.html  (laptop)   http://<lan-ip>:8907/  (phone/iPad)

It serves the static app and brokers the per-person SQLite store under local _data/ (the
source of truth; in local worktrees this path is symlinked into _LOCAL_FILES):
  GET  /api/data-folders            -> source-folder choices (subfolders of _data/, always
                                       incl. real + test) for the page's Source selector.
  GET  /api/list?folder=<name>      -> .sqlite basenames in local _data/<folder>.
  GET  /api/folder-users?folder=<name>
                                    -> kid-landing names from top-level math-flu_*.sqlite files
                                       in that source folder (date appended when a name is not unique).
  GET/POST /api/visual-config       -> per-user VisualPracticeConfig read/write.
  GET  /api/latest-user-db?folder=<name>&user=<name>
                                    -> the learner's most-recent per-person .sqlite in that
                                       source folder as base64 (+ session count), so the page
                                       can auto-load it on name entry ("Continue latest").
  POST /api/clone-user-file {folder,sourceUser,targetUser,sourceFile?}
                                    -> copy sourceUser's latest per-person .sqlite as targetUser
                                       (or the exact top-level sourceFile when supplied; filename +
                                       in-file rename). Snapshots target's existing
                                       file(s) to BACKUP_ROOT first. Source file is never modified.
                                       Used by the landing "clone from…" flow for Randy/Tester.
  POST /api/save-run {sourceFolder,destination,name,stamp,testDescription,base64,forceNew?,sourceFile?}
       The page sends the finished single-session .sqlite. It is always archived (timestamped)
       to _data/_single-session-sqlite-files/; then destination 'source' accumulates it into the
       source folder (anchor_store.resolve_save / append_session) and destination 'test' writes a
       seeded trial into a dated _data/test/test_<stamp>[_desc]/ subfolder without touching the
       source. forceNew=true ("Start New") begins a fresh lineage. Every single-session
       archive is best-effort uploaded to S3; Continue append also creates an external
       pre-change snapshot and best-effort S3 mirror. Returns singleSessionPath for the page
       to show.

Local dev only — never deploy. Naming rules: docs/SPEC.md §8a–8c.

Config (env or .env):
  ANCHOR_BIND        default "0.0.0.0"  (127.0.0.1 to block LAN/phone access)
  ANCHOR_S3_BUCKET   default "[S3-BUCKET]"
  ANCHOR_S3_SINGLE_SESSION_BASE  default "math-quiz/single-sessions/"
  ANCHOR_S3_BACKUP_BASE  default "math-quiz/_backup-s3/"
  ANCHOR_BACKUP_DIR  default "/Users/randytrue/Documents/Code/_BACKUP/math-quiz/sqlite-snapshots"
  ANCHOR_DATA_DIR    default "_data"        (under apps/math-quiz/)
  ANCHOR_PORT        default 8907
  ANCHOR_S3_REGION   default "us-west-2"
  ANCHOR_PREVENT_SLEEP  default "1" on macOS
  ANCHOR_S3_DISABLE  default "0"  ("1" skips ALL best-effort S3 uploads — for
                     simulated/test runs, e.g. the dragon playthrough apparatus,
                     so junk data never reaches the real bucket)
"""
import os
import re
import json
import base64
import sqlite3
import tempfile
import time
import http.server
import socket
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anchor_store  # noqa: E402
import problem_list_store  # noqa: E402
import targeted_store  # noqa: E402
import visual_store  # noqa: E402
import quick_practice_store  # noqa: E402
import fluency_feast_store  # noqa: E402
import profile_store  # noqa: E402
import clone_user_file  # noqa: E402
import dragon_assets  # noqa: E402
import dragon_display_names  # noqa: E402
import dragon_handoff_store as dragon_handoff  # noqa: E402

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)  # load AWS creds etc. from .env (see core/aws.py)
except Exception:
    pass

APP_DIR = Path(__file__).resolve().parent.parent          # apps/math-quiz
DATA_DIR = APP_DIR / os.environ.get("ANCHOR_DATA_DIR", "_data")
BUCKET = os.environ.get("ANCHOR_S3_BUCKET", "[S3-BUCKET]")
BACKUP_ROOT = Path(os.environ.get("ANCHOR_BACKUP_DIR", "/Users/randytrue/Documents/Code/_BACKUP/math-quiz/sqlite-snapshots")).expanduser()
S3_SINGLE_SESSION_BASE = os.environ.get("ANCHOR_S3_SINGLE_SESSION_BASE", "math-quiz/single-sessions/").strip("/")
S3_BACKUP_BASE = os.environ.get("ANCHOR_S3_BACKUP_BASE", "math-quiz/_backup-s3/").strip("/")
REGION = os.environ.get("ANCHOR_S3_REGION", "us-west-2")
S3_DISABLED = os.environ.get("ANCHOR_S3_DISABLE", "0").lower() in ("1", "true", "yes")
PORT = int(os.environ.get("ANCHOR_PORT", "8907"))
BIND = os.environ.get("ANCHOR_BIND", "0.0.0.0")
PREVENT_SLEEP = os.environ.get("ANCHOR_PREVENT_SLEEP", "1" if sys.platform == "darwin" else "0").lower() not in ("0", "false", "no")
_caffeinate_proc = None


def _resolve_user(user):
    return dragon_display_names.resolve_data_user(user)


def _start_sleep_guard():
    global _caffeinate_proc
    if not PREVENT_SLEEP or sys.platform != "darwin":
        return
    try:
        _caffeinate_proc = subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())],
                                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Mac sleep disabled while server is running (caffeinate). Ctrl+C to stop both.")
    except Exception as exc:
        print(f"Note: could not disable sleep ({exc}) — keep the Mac awake manually.")


def _stop_sleep_guard():
    global _caffeinate_proc
    if _caffeinate_proc and _caffeinate_proc.poll() is None:
        _caffeinate_proc.terminate()
        _caffeinate_proc.wait(timeout=2)
    _caffeinate_proc = None


def _lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and ip != "127.0.0.1":
            return ip
    except Exception:
        pass
    return None


def _normalize_static_path(path):
    """Map bookmark-friendly URLs to real files (e.g. /dragon/index on an iPad)."""
    key = path.rstrip("/") if path != "/" else path
    lower = key.lower()
    if lower in ("/dragon", "/dragon/index"):
        return "/dragon/index.html"
    if lower == "/dragon/gm":
        return "/dragon/gm.html"
    return path


def _pids_listening_on(port):
    """Return PIDs listening on TCP port (excludes this process). Needs lsof."""
    try:
        out = subprocess.check_output(
            ["lsof", f"-tiTCP:{port}", "-sTCP:LISTEN"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    pids = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pid = int(line)
        except ValueError:
            continue
        if pid != os.getpid():
            pids.append(pid)
    return pids


def _free_port(port):
    """Stop whatever is already listening on port so a plain restart just works."""
    import signal
    pids = _pids_listening_on(port)
    if not pids:
        return
    for pid in pids:
        try:
            print(f"Port {port} in use by pid {pid} — stopping it.")
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except PermissionError as exc:
            print(f"Could not stop pid {pid}: {exc}")
            raise SystemExit(1) from exc
    deadline = time.time() + 3.0
    while time.time() < deadline:
        if not _pids_listening_on(port):
            return
        time.sleep(0.1)
    for pid in _pids_listening_on(port):
        try:
            print(f"Port {port} still held by pid {pid} — force-killing.")
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    time.sleep(0.2)
    if _pids_listening_on(port):
        print(f"Port {port} is still in use after kill; exiting.")
        raise SystemExit(1)


def _s3():
    import boto3
    return boto3.client("s3", region_name=REGION)


def _folder_dir(folder):
    return DATA_DIR / folder


SINGLE_SESSION_DIR = "_single-session-sqlite-files"     # every session's raw single-session file is archived here
EXCLUDED_FOLDERS = {"local-only", SINGLE_SESSION_DIR}   # not offered as source folders


def data_folders():
    """Source-folder choices: the immediate subfolders of _data/ (always including real +
    test), minus internal ones. Populates the page's Source folder selector so a custom
    folder the user creates under _data/ shows up automatically."""
    found = {"real", "test"}
    if DATA_DIR.exists():
        for p in DATA_DIR.iterdir():
            if p.is_dir() and p.name not in EXCLUDED_FOLDERS:
                found.add(p.name)
    return sorted(found)


def list_filenames(folder):
    """Basenames of .sqlite files in local _data/<folder> (recursive, so test subfolders
    are included)."""
    base = _folder_dir(folder)
    if not base.exists():
        return []
    return sorted({p.name for p in base.rglob("*.sqlite")})


def list_folder_users(folder):
    """Distinct learner names encoded in math-flu filenames under _data/<folder>."""
    names = set()
    for fn, _mod in list_entries(folder):
        parsed = anchor_store.parse_filename(fn)
        if parsed and parsed.get("name"):
            names.add(parsed["name"])
    return sorted(names)
def list_top_filenames(folder):
    """Basenames of .sqlite files directly in local _data/<folder> (not subfolders). The kid
    landing reads this so dragon-*/test-trial subfolders don't become name buttons."""
    base = _folder_dir(folder)
    if not base.exists():
        return []
    return sorted(p.name for p in base.iterdir() if p.is_file() and p.suffix.lower() == ".sqlite")
def folder_users(folder):
    """Kid-landing entries for the source folder: [{name, label, filename}, ...]."""
    return {
        "ok": True,
        "folder": folder,
        "users": anchor_store.list_landing_users(list_top_filenames(folder)),
    }


def list_entries(folder):
    """(basename, mtime) for each .sqlite in local _data/<folder>, keeping the newest
    occurrence of a repeated basename. mtime drives the most-recently-used lineage pick
    (anchor_store.pick_latest). The local _data/ folder is the source of truth for reads;
    S3 receives automatic single-session archives and append snapshots only."""
    out = {}
    base = _folder_dir(folder)
    if base.exists():
        for p in base.rglob("*.sqlite"):
            try:
                ts = p.stat().st_mtime
            except Exception:
                ts = None
            if p.name not in out or (ts is not None and (out[p.name] is None or ts > out[p.name])):
                out[p.name] = ts
    return sorted(out.items())


def s3_upload(local_path, key):
    if S3_DISABLED:
        raise RuntimeError("S3 uploads disabled (ANCHOR_S3_DISABLE=1)")
    _s3().upload_file(str(local_path), BUCKET, key)
    return f"s3://{BUCKET}/{key}"


def _upload_single_session(single_path):
    """Best-effort S3 upload for the immutable single-session capture."""
    key = f"{S3_SINGLE_SESSION_BASE}/{Path(single_path).name}"
    try:
        return {"singleSessionS3Uri": s3_upload(single_path, key)}
    except Exception as exc:
        return {"singleSessionS3Error": str(exc)}


def _slug(text):
    return re.sub(r"[^a-z0-9_-]+", "-", (text or "").strip().lower()).strip("-")


def _safe_folder(folder):
    """A source-folder name limited to a single path segment — reject path separators and
    traversal but PRESERVE the actual folder name (spaces and other display chars included),
    so a folder like 'TL kids' resolves to _data/TL kids/ rather than being mangled."""
    f = str(folder or "").strip()
    if not f or "/" in f or "\\" in f or f in (".", ".."):
        return ""
    return f


def _local_find(folder, filename):
    """Locate a basename in the local mirror (recursive). When several copies exist (common
    under test/ subfolders), prefer an exact top-level file; otherwise return the recursive
    copy with the newest mtime."""
    base = DATA_DIR / folder
    if not base.exists():
        return None
    top_level = base / filename
    if top_level.is_file():
        return top_level
    best = None
    best_ts = None
    for p in base.rglob(filename):
        try:
            ts = p.stat().st_mtime
        except Exception:
            ts = None
        if best is None or (ts is not None and (best_ts is None or ts > best_ts)):
            best, best_ts = p, ts
    return best


def save_run(source_folder, destination, name, stamp, test_description, raw_bytes, force_new=False,
             consumed_problem_list_id=None, targeted_config=None, visual_config=None,
             source_file=None):
    """Route a finished single-session run from a SOURCE folder to a DESTINATION:
      destination 'source' -> accumulate into the source folder (create / Continue-latest
                              append / Start-New) — the learner's growing per-person file.
      destination 'test'   -> a trial seeded from the source's latest file, written into a
                              dated _data/test/test_<stamp>[_desc]/ subfolder; the source
                              folder is never modified.
    The run is saved to local _data/. Every single-session archive is uploaded to S3
    best-effort. Continue append first creates an external snapshot backup, then best-effort
    uploads that snapshot to S3. force_new ("Start New") begins a fresh single-session
    lineage instead of appending. "Continue latest" (force_new=False) requires an existing
    source file; with none it returns an error (ok=False) rather than silently creating one."""
    name = _resolve_user(name)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    individual_name = anchor_store.single_session_name(name, stamp)

    # The finished single session, staged in a temp file for create / append / seed.
    tmp = Path(tempfile.mkdtemp()) / individual_name
    tmp.write_bytes(raw_bytes)

    # Always archive the raw single-session file (timestamped) to one folder, regardless of
    # source / destination / continue — the canonical per-session capture artifact.
    single_dir = DATA_DIR / SINGLE_SESSION_DIR
    single_dir.mkdir(parents=True, exist_ok=True)
    single_path = single_dir / individual_name
    single_path.write_bytes(raw_bytes)
    archive = {"singleSessionFile": individual_name, "singleSessionPath": str(single_path)}
    archive.update(_upload_single_session(single_path))

    # "Continue latest" needs an existing file to continue; a brand-new lineage is the
    # explicit "Start New" action. Surface a clear error instead of silently creating one.
    entries = list_entries(source_folder)
    requested_source = None
    if source_file and not force_new:
        raw_source = str(source_file)
        candidate = os.path.basename(raw_source)
        parsed = anchor_store.parse_filename(candidate)
        exact_path = DATA_DIR / source_folder / candidate
        if candidate != raw_source or not parsed or parsed["name"] != name or not exact_path.is_file():
            return {"ok": False, "error": "source-file-not-found", "sourceFolder": source_folder,
                    **archive, "message": f'Selected source file "{raw_source}" is not available '
                                          f'for "{name}" in source folder "{source_folder}".'}
        requested_source = candidate
    latest = requested_source or anchor_store.pick_latest(entries, name)
    if not force_new and latest is None:
        return {"ok": False, "error": "no-continue-file", "sourceFolder": source_folder, **archive,
                "message": f'No existing file for "{name}" in source folder "{source_folder}" to '
                           f'continue. Choose "Start new file" to begin one (or pick another source folder).'}

    result = {"ok": True, "sourceFolder": source_folder, "destination": destination, **archive}

    if destination == "test":
        # Trial: Continue seeds from the source's latest file and appends (a multi-session
        # file built on the source's latest); Start New writes a fresh single-session trial.
        seed = None if force_new else latest
        sub = "test_" + stamp + (("_" + _slug(test_description)) if test_description else "")
        out_filename = anchor_store.to_multi_name(seed) if seed else individual_name
        out_local = DATA_DIR / "test" / sub / out_filename
        out_local.parent.mkdir(parents=True, exist_ok=True)
        if seed:
            _seed_then_append(seed, source_folder, tmp, out_local)
            result["seededFrom"] = seed
        else:
            out_local.write_bytes(raw_bytes)
        result.update({"action": "test-run", "filename": out_filename, "subfolder": sub, "localPath": str(out_local)})
        return result

    # destination == "source": create a new file, or append into the existing one.
    if requested_source:
        parsed = anchor_store.parse_filename(requested_source)
        filenames = [fn for fn, _modified in entries]
        out_filename = requested_source if parsed["multi"] else anchor_store.next_multi_name(
            filenames, name, parsed["date"])
        plan = {"action": "append", "target": requested_source, "filename": out_filename}
    else:
        plan = anchor_store.resolve_save(source_folder, name, stamp, entries, force_new=force_new)
    out_filename = plan["filename"]
    out_local = DATA_DIR / source_folder / out_filename
    out_local.parent.mkdir(parents=True, exist_ok=True)
    if plan["action"] == "create":
        out_local.write_bytes(raw_bytes)
    else:
        _fetch_into(source_folder, plan["target"], out_local)   # bring the target down
        backup = _backup_source_file(out_local, plan["target"], stamp)   # pre-change backup
        if backup:
            result.update(backup)
        anchor_store.append_session(str(out_local), str(tmp))
    # "Use internal" consumes the list it ran: pop it off the accumulated source file (retained
    # lists are kept + usage-bumped; non-retained are deleted and the rest reindexed to 1..N).
    # Only for destination 'source' — a test trial must never mutate the real file's lists.
    if consumed_problem_list_id is not None:
        result["consumedProblemList"] = _consume_list(out_local, consumed_problem_list_id)
    # Persist the learner's targeted-practice config (targets / filler / params) into their
    # accumulated file so it prefills next time — only for destination 'source'.
    if targeted_config is not None:
        result["targetedConfig"] = _write_targeted_config(out_local, name, targeted_config)
    if visual_config is not None:
        result["visualConfig"] = _write_visual_config(out_local, name, visual_config)
    # Auto-generate the machine "quick practice" sets (21 rows: 3 ops x 7) from the learner's
    # fresh fluency — regenerated after every saved quiz. Only for destination 'source'.
    result["quickPractice"] = _regenerate_quick_practice(out_local, name)
    result.update({"action": plan["action"], "target": plan.get("target"), "filename": out_filename, "localPath": str(out_local)})

    # If a single-session target was renamed to the multi form, drop the stale old copy.
    if plan["action"] == "append" and plan["target"] and plan["target"] != out_filename:
        _delete_old(source_folder, plan["target"], result)
    return result


def _fetch_into(folder, filename, dest_local):
    """Copy the target file into dest_local from the local _data/<folder> mirror."""
    local = _local_find(folder, filename)
    if local and local.resolve() != dest_local.resolve():
        dest_local.write_bytes(local.read_bytes())


def _backup_source_file(src_local, original_name, stamp):
    """Before an append modifies a source file, copy the existing (unmodified) file to
    BACKUP_ROOT/<stem>_backup_<stamp><ext>. `src_local` already holds the existing file's
    bytes (fetched just before the append). Best-effort S3 upload mirrors the same snapshot
    under ANCHOR_S3_BACKUP_BASE."""
    try:
        src = Path(src_local)
        if not src.exists() or src.stat().st_size == 0:
            return None
        BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
        stem, ext = Path(original_name).stem, Path(original_name).suffix
        backup_path = BACKUP_ROOT / f"{stem}_backup_{stamp}{ext}"
        backup_path.write_bytes(src.read_bytes())
        out = {"backup": str(backup_path)}
        key = f"{S3_BACKUP_BASE}/{backup_path.name}"
        try:
            out["backupS3Uri"] = s3_upload(backup_path, key)
        except Exception as exc:
            out["backupS3Error"] = str(exc)
        return out
    except Exception as exc:
        return {"backupError": str(exc)}
def clone_user(folder, source_user, target_user, source_filename=None):
    """Clone source_user's latest per-person file in _data/<folder> as target_user.
    Wraps tools/clone_user_file.py with force=True, but first snapshots the target user's
    existing file(s) into BACKUP_ROOT so the overwrite is reversible. The source user's
    file is never modified."""
    folder_dir = DATA_DIR / folder
    if not folder_dir.is_dir():
        return {"ok": False, "error": f"folder not found: {folder}"}
    stamp = time.strftime("%Y-%m-%d_%H%M%S")
    backups = []
    for fn in clone_user_file.files_for_user(folder_dir, target_user):
        b = _backup_source_file(folder_dir / fn, fn, stamp)
        if not b or b.get("backupError") or not b.get("backup"):
            return {"ok": False, "error": f"target backup failed for {fn}",
                    "backupDetails": b, "backups": backups}
        backups.append(b)
    result = clone_user_file.clone_user_file(
        folder_dir, source_user, target_user, force=True, source_filename=source_filename)
    if result.get("ok"):
        result["folder"] = folder
        result["backups"] = backups
    return result

def _seed_then_append(seed_name, seed_folder, individual_tmp, out_local):
    _fetch_into(seed_folder, seed_name, out_local)
    anchor_store.append_session(str(out_local), str(individual_tmp))


def _consume_list(local_path, problem_list_id):
    """Pop the just-run internal list from the accumulated source file. Returns the store's
    summary ({action: retained|deleted|missing, ...}) or an {error} dict; never raises."""
    try:
        conn = problem_list_store.connect(str(local_path))
        try:
            return problem_list_store.consume_problem_list(conn, problem_list_id)
        finally:
            conn.close()
    except Exception as exc:
        return {"action": "error", "error": str(exc), "problem_list_id": problem_list_id}


def _regenerate_quick_practice(local_path, user):
    """Recompute + replace the user's 21 quick-practice rows in a just-saved per-person file
    (best-effort). Returns the store's summary or an {error} dict; never raises."""
    try:
        conn = quick_practice_store.connect(str(local_path))
        try:
            profile = profile_store.get_config(conn, user)
            return quick_practice_store.regenerate_for_user(
                conn, user, thresholds=profile.get("thresholds"))
        finally:
            conn.close()
    except Exception as exc:
        return {"error": str(exc), "user": user}


def _delete_old(folder, filename, result):
    old_local = _local_find(folder, filename)
    if old_local and old_local.exists():
        try:
            old_local.unlink()
        except Exception:
            pass


def _count_sessions(path, user):
    """Count this user's sessions in a .sqlite (for the load endpoint's confirmation text)."""
    try:
        c = sqlite3.connect(str(path))
        try:
            n = c.execute("SELECT COUNT(*) FROM Sessions WHERE user_name = ?", (user,)).fetchone()[0]
        finally:
            c.close()
        return int(n)
    except Exception:
        return None


def _problem_lists_for(path, user):
    """The user's internal problem lists (ordered) from a .sqlite, for the page's display +
    the "Use internal" run. Reads from a throwaway temp copy; returns [] on any error."""
    try:
        conn = problem_list_store.connect(str(path))
        try:
            return problem_list_store.fetch_problem_lists(conn, user_name=user)
        finally:
            conn.close()
    except Exception:
        return []


def _targeted_config_for(path, user):
    """The user's targeted-practice config from a .sqlite (or None when unset), for the
    page to prefill the target fields + params + filler. Returns None on any error."""
    try:
        conn = targeted_store.connect(str(path))
        try:
            return targeted_store.get_config(conn, user)
        finally:
            conn.close()
    except Exception:
        return None
def _visual_config_for(path, user):
    """The user's visual-practice config from a .sqlite (or None when unset), for the
    page to prefill the visual target fields + params + filler. Returns None on any error."""
    try:
        conn = visual_store.connect(str(path))
        try:
            return visual_store.get_config(conn, user)
        finally:
            conn.close()
    except Exception:
        return None


def _visual_config_for(path, user):
    """The user's visual-practice config from a .sqlite (or None when unset), for the
    page to prefill the visual target fields + params + filler. Returns None on any error."""
    try:
        conn = visual_store.connect(str(path))
        try:
            return visual_store.get_config(conn, user)
        finally:
            conn.close()
    except Exception:
        return None


def _fluency_feast_for(path, user):
    """The user's saved Fluency-feast preset from a .sqlite (or None when unset), for the kid
    pop-up + the editor to read. Returns None on any error."""
    try:
        conn = fluency_feast_store.connect(str(path))
        try:
            return fluency_feast_store.get_config(conn, user)
        finally:
            conn.close()
    except Exception:
        return None


def _profile_for(path, user):
    """The user's per-file profile (display/UX flags) from a .sqlite, with code defaults baked
    in. Returns the defaults on any error so the page always has a usable value."""
    try:
        conn = profile_store.connect(str(path))
        try:
            return profile_store.get_config(conn, user)
        finally:
            conn.close()
    except Exception:
        return {"showFluencyPercent": profile_store.DEFAULT_SHOW_FLUENCY_PERCENT, "updatedAt": None}


def _quick_practice_for(path, user):
    """The user's auto-generated quick-practice sets ({operation: [items]}) from a .sqlite,
    for display / external readers. Returns {} on any error."""
    try:
        conn = quick_practice_store.connect(str(path))
        try:
            return quick_practice_store.fetch_for_user(conn, user)
        finally:
            conn.close()
    except Exception:
        return {}


def _safe_subfolder(subfolder):
    """A single test-run subfolder name (one path segment under _data/<folder>/)."""
    s = str(subfolder or "").strip()
    if not s or "/" in s or "\\" in s or s in (".", ".."):
        return ""
    return s


def _resolve_user_db_path(folder, user, filename=None, subfolder=None):
    """Local Path for a learner's per-person .sqlite: explicit `filename` (+ optional test
    `subfolder`) when the caller knows which file to open; else the most-recent lineage via
    pick_latest."""
    user = _resolve_user(user)
    if filename:
        fn = os.path.basename(filename)
        sub = _safe_subfolder(subfolder)
        if sub:
            return DATA_DIR / folder / sub / fn
        top_level = DATA_DIR / folder / fn
        if top_level.is_file():
            return top_level
        return _local_find(folder, fn)
    target = anchor_store.pick_latest(list_entries(folder), user)
    if not target:
        return None
    tmp = Path(tempfile.mkdtemp()) / target
    _fetch_into(folder, target, tmp)
    return tmp if tmp.exists() else None


def latest_user_db(folder, user, filename=None, subfolder=None):
    """Resolve + return the learner's per-person .sqlite in `folder` so the page can auto-load
    it on name entry ("Continue latest") or after a finished quiz (optional explicit
    `filename` / test `subfolder`). Returns base64 bytes + session count + internal problem
    lists, or found=False when they have no file yet."""
    path = _resolve_user_db_path(folder, user, filename=filename, subfolder=subfolder)
    if not path:
        return {"ok": True, "found": False, "folder": folder, "user": user}
    raw = path.read_bytes()
    out = {"ok": True, "found": True, "folder": folder, "user": user, "filename": path.name,
           "sessionCount": _count_sessions(path, user), "problemLists": _problem_lists_for(path, user),
           "targetedConfig": _targeted_config_for(path, user),
           "visualConfig": _visual_config_for(path, user),
           "fluencyFeast": _fluency_feast_for(path, user),
           "profile": _profile_for(path, user),
           "quickPractice": _quick_practice_for(path, user),
           "base64": base64.b64encode(raw).decode()}
    sub = _safe_subfolder(subfolder)
    if sub:
        out["subfolder"] = sub
    return out


def _resolve_user_file(folder, user):
    """The local Path of the learner's most-recent per-person file in `folder`, or None. This
    is the file the problem-list editor reads from and writes to (the same file "Use internal"
    runs and the next quiz appends to — one source of truth)."""
    user = _resolve_user(user)
    target = anchor_store.pick_latest(list_entries(folder), user)
    if not target:
        return None
    return _local_find(folder, target)


def _editor_target(folder, user, filename=None):
    """The file the problem-list editor reads/writes. When the caller names a specific file
    (the analysis page loads one explicitly), target THAT exact file so the list lands where
    the user is looking; otherwise the user's latest lineage in the folder (anchor's model)."""
    if filename:
        path = _local_find(folder, os.path.basename(filename))
        if path:
            return path
    return _resolve_user_file(folder, user)


def resolve_editor_target(user, filename=None):
    """Best on-disk target when the analysis page loads a .sqlite by basename and the same name
    exists in multiple folders (e.g. tlkids vs an old test-trial copy). Prefers non-test
    folders, then the copy with the most sessions for this user, then newest mtime."""
    if not user:
        return {"ok": True, "found": False, "user": ""}
    if filename:
        basename = os.path.basename(filename)
        candidates = []
        for folder in data_folders():
            path = _local_find(folder, basename)
            if not path or not path.exists():
                continue
            try:
                mtime = path.stat().st_mtime
            except Exception:
                mtime = 0
            candidates.append({"folder": folder, "path": path, "mtime": mtime,
                               "sessionCount": _count_sessions(path, user)})
        if candidates:
            candidates.sort(key=lambda c: (1 if c["folder"] == "test" else 0,
                                           -c["sessionCount"], -c["mtime"]))
            best = candidates[0]
            rel = str(best["path"].relative_to(DATA_DIR))
            return {"ok": True, "found": True, "folder": best["folder"], "user": user,
                    "file": basename, "relativePath": rel}
    for folder in sorted(data_folders(), key=lambda f: (1 if f == "test" else 0, f)):
        path = _resolve_user_file(folder, user)
        if path:
            rel = str(path.relative_to(DATA_DIR))
            return {"ok": True, "found": True, "folder": folder, "user": user,
                    "file": path.name, "relativePath": rel}
    return {"ok": True, "found": False, "user": user, "file": os.path.basename(filename or "")}


def problem_lists_view(folder, user, filename=None):
    """{ok, folder, user, file?, problemLists} for the editor's read — the user's lists in the
    named file (or the folder's latest file). Empty list + found=False when no file yet."""
    path = _editor_target(folder, user, filename)
    if not path:
        return {"ok": True, "found": False, "folder": folder, "user": user, "problemLists": []}
    return {"ok": True, "found": True, "folder": folder, "user": user, "file": path.name,
            "problemLists": _problem_lists_for(path, user)}


def edit_problem_lists(folder, user, action, payload):
    """Apply one editor mutation to the target file in `folder` (the named file, or the latest
    auto-save target), then return the fresh list view. Actions: save-items, rename, set-retain,
    reorder, create, delete. Editing requires an existing per-person file (created by a quiz /
    Start New)."""
    path = _editor_target(folder, user, payload.get("file"))
    if not path:
        return {"ok": False, "error": "no-file", "folder": folder, "user": user,
                "message": f'No file for "{user}" in "{folder}" yet. Run a quiz (or Start New) to '
                           f'create one, then add lists.'}
    conn = problem_list_store.connect(str(path))
    try:
        if action == "save-items":
            problems = _parse_items_lenient(payload.get("text", ""))
            problem_list_store.replace_list_items(conn, int(payload["problemListId"]), problems)
        elif action == "rename":
            problem_list_store.rename_list(conn, int(payload["problemListId"]), payload.get("listName", ""))
        elif action == "set-retain":
            problem_list_store.set_retain(conn, int(payload["problemListId"]), bool(payload.get("retain")))
        elif action == "reorder":
            problem_list_store.reorder_lists(conn, user, [int(x) for x in (payload.get("order") or [])])
        elif action == "create":
            problem_list_store.create_list(conn, user, payload.get("listName") or "New list",
                                           problems=_parse_items_lenient(payload.get("text", "")),
                                           source=payload.get("source") or "editor",
                                           retain=bool(payload.get("retain", True)))
        elif action == "delete":
            problem_list_store.delete_list(conn, int(payload["problemListId"]))
        else:
            return {"ok": False, "error": "unknown-action", "action": action}
        lists = problem_list_store.fetch_problem_lists(conn, user_name=user)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "folder": folder, "user": user}
    finally:
        conn.close()
    return {"ok": True, "folder": folder, "user": user, "file": path.name, "problemLists": lists}


def targeted_config_view(folder, user, filename=None):
    """{ok, folder, user, file?, targetedConfig} — the user's targeted-practice config in the
    named file (or the folder's latest), null + found=False when no file yet."""
    path = _editor_target(folder, user, filename)
    if not path:
        return {"ok": True, "found": False, "folder": folder, "user": user, "targetedConfig": None}
    return {"ok": True, "found": True, "folder": folder, "user": user, "file": path.name,
            "targetedConfig": _targeted_config_for(path, user)}


def edit_targeted_config(folder, user, payload):
    """Write the user's targeted-practice config (targets / filler / params) to the named
    file (or the latest auto-save target). Requires an existing per-person file."""
    path = _editor_target(folder, user, payload.get("file"))
    if not path:
        return {"ok": False, "error": "no-file", "folder": folder, "user": user,
                "message": f'No file for "{user}" in "{folder}" yet. Run a quiz (or Start New) to '
                           f'create one, then set targets/filler.'}
    conn = targeted_store.connect(str(path))
    try:
        cfg = targeted_store.set_config(
            conn, user,
            targets=payload.get("targets"),
            filler=payload.get("filler"),
            graduation_streak=payload.get("graduationStreak"),
            fast_ms=payload.get("fastMs"),
            percent_target=payload.get("percentTarget"),
            reward_image=payload.get("rewardImage"),
            completion_image=payload.get("completionImage"))
    except Exception as exc:
        return {"ok": False, "error": str(exc), "folder": folder, "user": user}
    finally:
        conn.close()
    return {"ok": True, "folder": folder, "user": user, "file": path.name, "targetedConfig": cfg}


def visual_config_view(folder, user, filename=None):
    """{ok, folder, user, file?, visualConfig} — the user's visual-practice config in the
    folder's latest file (visualConfig null + found=False when they have no file yet)."""
    path = _editor_target(folder, user, filename)
    if not path:
        return {"ok": True, "found": False, "folder": folder, "user": user, "visualConfig": None}
    return {"ok": True, "found": True, "folder": folder, "user": user, "file": path.name,
            "visualConfig": _visual_config_for(path, user)}
def edit_visual_config(folder, user, payload):
    """Write the user's visual-practice config (targets / filler / params) to their latest
    file in `folder` — the same auto-save target as the problem-list editor. Requires an
    existing per-person file (created by a quiz / Start New)."""
    path = _editor_target(folder, user, payload.get("file"))
    if not path:
        return {"ok": False, "error": "no-file", "folder": folder, "user": user,
                "message": f'No file for "{user}" in "{folder}" yet. Run a quiz (or Start New) to '
                           f'create one, then set visual targets/filler.'}
    conn = visual_store.connect(str(path))
    try:
        cfg = visual_store.set_config(
            conn, user,
            targets=payload.get("targets"),
            filler=payload.get("filler"),
            fast_ms=payload.get("fastMs"),
            retrievals_to_clear=payload.get("retrievalsToClear"),
            hesitation_ms=payload.get("hesitationMs"))
    except Exception as exc:
        return {"ok": False, "error": str(exc), "folder": folder, "user": user}
    finally:
        conn.close()
    return {"ok": True, "folder": folder, "user": user, "file": path.name, "visualConfig": cfg}


def fluency_feast_view(folder, user, filename=None):
    """{ok, folder, user, file?, fluencyFeast} — the user's Fluency-feast preset in the named
    file (or the folder's latest), null + found=False when no file yet."""
    path = _editor_target(folder, user, filename)
    if not path:
        return {"ok": True, "found": False, "folder": folder, "user": user, "fluencyFeast": None}
    return {"ok": True, "found": True, "folder": folder, "user": user, "file": path.name,
            "fluencyFeast": _fluency_feast_for(path, user)}


def edit_fluency_feast(folder, user, payload):
    """Write the user's Fluency-feast preset (count / session scope / category mix) to the named
    file (or the latest auto-save target). Requires an existing per-person file."""
    path = _editor_target(folder, user, payload.get("file"))
    if not path:
        return {"ok": False, "error": "no-file", "folder": folder, "user": user,
                "message": f'No file for "{user}" in "{folder}" yet. Run a quiz (or Start New) to '
                           f'create one, then save a feast preset.'}
    session = payload.get("session") or {}
    conn = fluency_feast_store.connect(str(path))
    try:
        cfg = fluency_feast_store.set_config(
            conn, user,
            count=payload.get("count"),
            operation=payload.get("operation"),
            session_mode=session.get("mode"),
            session_n=session.get("n"),
            session_since=session.get("since"),
            mix=payload.get("mix"))
    except Exception as exc:
        return {"ok": False, "error": str(exc), "folder": folder, "user": user}
    finally:
        conn.close()
    return {"ok": True, "folder": folder, "user": user, "file": path.name, "fluencyFeast": cfg}


def profile_view(folder, user, filename=None):
    """{ok, folder, user, file?, profile} — the user's per-file profile in the named file (or
    the folder's latest). Defaults (found=False) when no file yet."""
    path = _editor_target(folder, user, filename)
    if not path:
        return {"ok": True, "found": False, "folder": folder, "user": user,
                "profile": {"showFluencyPercent": profile_store.DEFAULT_SHOW_FLUENCY_PERCENT, "updatedAt": None}}
    return {"ok": True, "found": True, "folder": folder, "user": user, "file": path.name,
            "profile": _profile_for(path, user)}


def edit_profile(folder, user, payload):
    """Write the user's per-file profile flags (currently showFluencyPercent) to the named file
    (or the latest auto-save target). Requires an existing per-person file."""
    path = _editor_target(folder, user, payload.get("file"))
    if not path:
        return {"ok": False, "error": "no-file", "folder": folder, "user": user,
                "message": f'No file for "{user}" in "{folder}" yet. Run a quiz (or Start New) to '
                           f'create one, then save profile settings.'}
    conn = profile_store.connect(str(path))
    try:
        cfg = profile_store.set_config(
            conn, user,
            show_fluency_percent=payload.get("showFluencyPercent"),
            thresholds=payload.get("thresholds"))
    except Exception as exc:
        return {"ok": False, "error": str(exc), "folder": folder, "user": user}
    finally:
        conn.close()
    rel = str(path.relative_to(DATA_DIR))
    return {"ok": True, "folder": folder, "user": user, "file": path.name,
            "relativePath": rel, "profile": cfg}


def clone_user(folder, source_user, target_user, source_filename=None):
    """Clone source_user's latest per-person file in _data/<folder> as target_user
    (the dragon game's "Clone Kid1's game" and any other tester workflow). When
    source_filename is given, clone that exact top-level file instead of the latest.
    Wraps tools/clone_user_file.py with force=True, but first snapshots the target user's
    existing file(s) into BACKUP_ROOT so the overwrite is reversible. Also copies
    the Game Master snapshot JSON when present so the parent dashboard matches.
    The source user's file and GM data are never modified."""
    folder_dir = DATA_DIR / folder
    if not folder_dir.is_dir():
        return {"ok": False, "error": f"folder not found: {folder}"}
    source_user = _resolve_user(source_user)
    target_user = _resolve_user(target_user)
    stamp = time.strftime("%Y-%m-%d_%H%M%S")
    backups = []
    for fn in clone_user_file.files_for_user(folder_dir, target_user):
        b = _backup_source_file(folder_dir / fn, fn, stamp)
        if not b or b.get("backupError") or not b.get("backup"):
            return {"ok": False, "error": f"target backup failed for {fn}",
                    "backupDetails": b, "backups": backups}
        backups.append(b)
    result = clone_user_file.clone_user_file(
        folder_dir, source_user, target_user, force=True, source_filename=source_filename)
    if result.get("ok"):
        result["folder"] = folder
        result["backups"] = backups
        result["dragon_gm"] = clone_dragon_gm_state(folder, source_user, target_user)
        result["dragon_world"] = clone_dragon_world_state(folder, source_user, target_user)
    return result


def clone_dragon_gm_state(folder, source_user, target_user):
    """Copy source's GM snapshot onto the target (best-effort). Messages are not cloned."""
    src = _gm_dir(folder) / f"{source_user}_state.json"
    dst = _gm_dir(folder) / f"{target_user}_state.json"
    if not src.is_file():
        if dst.is_file():
            try:
                dst.unlink()
            except OSError:
                pass
        return {"copied": False}
    data = _gm_read_json(src, None)
    if data is None:
        return {"copied": False}
    state = data.get("state") or {}
    if isinstance(state, dict):
        state = dict(state)
        if "user" in state:
            state["user"] = target_user
    payload = {"updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"), "state": state}
    dst.write_text(json.dumps(payload))
    return {"copied": True}


def clone_dragon_world_state(folder, source_user, target_user):
    """Copy source's full dragon-world save onto the target (best-effort)."""
    import dragon_world_store as dws
    return dws.clone_dragon_world(DATA_DIR, folder, source_user, target_user, sqlite_backup_root=BACKUP_ROOT)


def dragon_world_view(folder, user):
    import dragon_world_store as dws
    return dws.dragon_world_view(DATA_DIR, folder, _resolve_user(user))


def save_dragon_world(folder, user, game_state):
    import dragon_world_store as dws
    return dws.save_dragon_world(DATA_DIR, folder, _resolve_user(user), game_state, sqlite_backup_root=BACKUP_ROOT)


DRAGON_DISPLAY_NAMES_FILE = dragon_display_names.DISPLAY_NAMES_FILE


def dragon_display_names_view():
    return dragon_display_names.view()


def _write_targeted_config(local_path, user, targeted_config):
    """Persist targeted config; return an error object when the session saved but config did not."""
    if not targeted_config:
        return None
    try:
        conn = targeted_store.connect(str(local_path))
        try:
            return targeted_store.set_config(
                conn, user,
                targets=targeted_config.get("targets"),
                filler=targeted_config.get("filler"),
                graduation_streak=targeted_config.get("graduationStreak"),
                fast_ms=targeted_config.get("fastMs"),
                percent_target=targeted_config.get("percentTarget"),
                reward_image=targeted_config.get("rewardImage"),
                completion_image=targeted_config.get("completionImage"))
        finally:
            conn.close()
    except Exception as exc:
        return {"error": str(exc), "user": user}
def _write_visual_config(local_path, user, visual_config):
    """Persist visual config; return an error object when the session saved but config did not."""
    if not visual_config:
        return None
    try:
        conn = visual_store.connect(str(local_path))
        try:
            return visual_store.set_config(
                conn, user,
                targets=visual_config.get("targets"),
                filler=visual_config.get("filler"),
                fast_ms=visual_config.get("fastMs"),
                retrievals_to_clear=visual_config.get("retrievalsToClear"),
                hesitation_ms=visual_config.get("hesitationMs"))
        finally:
            conn.close()
    except Exception as exc:
        return {"error": str(exc), "user": user}


def _parse_items_lenient(text):
    """Parse editor textarea text into problems; blank/ whitespace -> [] (an emptied list is
    allowed). A non-blank line that can't be parsed raises (the editor shows the error)."""
    if not str(text or "").strip():
        return []
    return problem_list_store.parse_problem_list_text(text)


### Dragon Game Master sync (game <-> parent phone dashboard)
# The game POSTs a state snapshot at load + every burst end; the GM page polls
# it and can post messages back ("From the Dragon Keeper") that the game shows
# in the story overlay. Everything lives as JSON under the gitignored
# _data/<folder>/dragon-gm/ — no PII beyond the learner's first name.
def _gm_dir(folder):
    d = DATA_DIR / folder / "dragon-gm"
    d.mkdir(parents=True, exist_ok=True)
    return d
def _gm_read_json(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default
def dragon_state_view(folder, user):
    """The game's last-posted snapshot for the GM page (found=False before the first post)."""
    user = _resolve_user(user)
    path = _gm_dir(folder) / f"{user}_state.json"
    if not path.is_file():
        return {"ok": True, "found": False, "folder": folder, "user": user}
    data = _gm_read_json(path, None)
    if data is None:
        return {"ok": True, "found": False, "folder": folder, "user": user}
    return {"ok": True, "found": True, "folder": folder, "user": user,
            "updatedAt": data.get("updatedAt"), "state": data.get("state")}
def save_dragon_state(folder, user, snapshot):
    """Persist the game's snapshot (server timestamp wins for staleness display).

    Before overwrite: snapshot the previous file under _BACKUP/.../dragon-gm-snapshots/.
    If the incoming snapshot looks wiped vs the on-disk one (empty signs / 0 gems
    while the file still has real progress), merge-preserve the richer world fields
    so a blank localStorage cannot erase the kid's nest again.
    """
    user = _resolve_user(user)
    import dragon_progress_guard as dpg
    path = _gm_dir(folder) / f"{user}_state.json"
    existing = _gm_read_json(path, None) if path.is_file() else None
    existing_state = (existing or {}).get("state") if isinstance(existing, dict) else None
    incoming = snapshot if isinstance(snapshot, dict) else {}
    merged, preserved = dpg.preserve_world_progress(existing_state, incoming)
    backup = dpg.backup_json_file(path, "dragon-gm", sqlite_backup_root=BACKUP_ROOT)
    payload = {"updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"), "state": merged}
    path.write_text(json.dumps(payload))
    out = {"ok": True, "folder": folder, "user": user, "updatedAt": payload["updatedAt"]}
    if backup:
        out["backup"] = backup
    if preserved:
        out["preservedWorldProgress"] = True
    return out
def dragon_messages_view(folder, user, unread_only=False):
    """GM messages for the learner: full history for the dashboard, unread for the game."""
    user = _resolve_user(user)
    path = _gm_dir(folder) / f"{user}_messages.json"
    data = _gm_read_json(path, {"nextId": 1, "messages": []})
    messages = data.get("messages", [])
    if unread_only:
        messages = [m for m in messages if not m.get("read")]
    return {"ok": True, "folder": folder, "user": user, "messages": messages}
def post_dragon_message(folder, user, text, sender):
    """Append a GM message; the game shows unread ones after the next quiz."""
    user = _resolve_user(user)
    text = str(text or "").strip()
    if not text:
        return {"ok": False, "error": "text required"}
    path = _gm_dir(folder) / f"{user}_messages.json"
    data = _gm_read_json(path, {"nextId": 1, "messages": []})
    msg = {"id": data["nextId"], "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "from": str(sender or "").strip() or "The Dragon Keeper",
           "text": text[:500], "read": False}
    data["messages"].append(msg)
    data["nextId"] += 1
    data["messages"] = data["messages"][-100:]   # keep the file small
    path.write_text(json.dumps(data))
    return {"ok": True, "folder": folder, "user": user, "message": msg}
def mark_dragon_messages_read(folder, user, ids):
    """The game acks the messages it showed."""
    user = _resolve_user(user)
    path = _gm_dir(folder) / f"{user}_messages.json"
    data = _gm_read_json(path, {"nextId": 1, "messages": []})
    wanted = {int(i) for i in (ids or [])}
    marked = 0
    for m in data.get("messages", []):
        if m.get("id") in wanted and not m.get("read"):
            m["read"] = True
            marked += 1
    path.write_text(json.dumps(data))
    return {"ok": True, "folder": folder, "user": user, "marked": marked}
def dragon_zoomie_lines_view(folder, user):
    """GM-edited zoomie dialogue pools. Missing/empty bands fall back in-game."""
    user = _resolve_user(user)
    path = _gm_dir(folder) / f"{user}_zoomie_lines.json"
    data = _gm_read_json(path, {}) if path.is_file() else {}
    bands = data.get("bands") if isinstance(data, dict) else {}
    if not isinstance(bands, dict):
        bands = {}
    return {"ok": True, "folder": folder, "user": user,
            "bands": bands, "updatedAt": data.get("updatedAt") if isinstance(data, dict) else None}
def save_dragon_zoomie_lines(folder, user, bands):
    """Persist GM-edited zoomie dialogue. Empty bands are omitted to restore defaults."""
    user = _resolve_user(user)
    if not isinstance(bands, dict):
        return {"ok": False, "error": "bands must be an object"}
    cleaned_by_band = {}
    for raw_band, raw_lines in bands.items():
        if isinstance(raw_band, bool):
            return {"ok": False, "error": f"invalid zoomie band: {raw_band}"}
        if isinstance(raw_band, int):
            band = raw_band
        elif isinstance(raw_band, str) and re.fullmatch(r"\d+", raw_band.strip()):
            band = int(raw_band)
        else:
            return {"ok": False, "error": f"invalid zoomie band: {raw_band}"}
        if band < 81 or band > 89:
            return {"ok": False, "error": f"invalid zoomie band: {raw_band}"}
        if not isinstance(raw_lines, list):
            return {"ok": False, "error": f"band {band} must be a list of strings"}
        lines = []
        for line in raw_lines:
            if not isinstance(line, str):
                return {"ok": False, "error": f"band {band} lines must be strings"}
            text = line.strip()
            if text:
                lines.append(text[:400])
        if lines:
            cleaned_by_band[band] = lines[:8]
    saved = {str(band): cleaned_by_band[band] for band in sorted(cleaned_by_band)}
    updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    payload = {"updatedAt": updated_at, "bands": saved}
    path = _gm_dir(folder) / f"{user}_zoomie_lines.json"
    path.write_text(json.dumps(payload))
    return {"ok": True, "bands": saved, "updatedAt": updated_at}
def dragon_growth_spurt_lines_view(folder, user):
    """GM-edited growth spurt dialogue pools. Missing/empty bands fall back in-game."""
    user = _resolve_user(user)
    path = _gm_dir(folder) / f"{user}_growth_spurt_lines.json"
    data = _gm_read_json(path, {}) if path.is_file() else {}
    bands = data.get("bands") if isinstance(data, dict) else {}
    if not isinstance(bands, dict):
        bands = {}
    return {"ok": True, "folder": folder, "user": user,
            "bands": bands, "updatedAt": data.get("updatedAt") if isinstance(data, dict) else None}
def save_dragon_growth_spurt_lines(folder, user, bands):
    """Persist GM-edited growth spurt dialogue. Empty bands are omitted to restore defaults."""
    user = _resolve_user(user)
    if not isinstance(bands, dict):
        return {"ok": False, "error": "bands must be an object"}
    cleaned_by_band = {}
    for raw_band, raw_lines in bands.items():
        if isinstance(raw_band, bool):
            return {"ok": False, "error": f"invalid growth spurt band: {raw_band}"}
        if isinstance(raw_band, int):
            band = raw_band
        elif isinstance(raw_band, str) and re.fullmatch(r"\d+", raw_band.strip()):
            band = int(raw_band)
        else:
            return {"ok": False, "error": f"invalid growth spurt band: {raw_band}"}
        if band < 91 or band > 100:
            return {"ok": False, "error": f"invalid growth spurt band: {raw_band}"}
        if not isinstance(raw_lines, list):
            return {"ok": False, "error": f"band {band} must be a list of strings"}
        lines = []
        for line in raw_lines:
            if not isinstance(line, str):
                return {"ok": False, "error": f"band {band} lines must be strings"}
            text = line.strip()
            if text:
                lines.append(text[:400])
        if lines:
            cleaned_by_band[band] = lines[:8]
    saved = {str(band): cleaned_by_band[band] for band in sorted(cleaned_by_band)}
    updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    payload = {"updatedAt": updated_at, "bands": saved}
    path = _gm_dir(folder) / f"{user}_growth_spurt_lines.json"
    path.write_text(json.dumps(payload))
    return {"ok": True, "bands": saved, "updatedAt": updated_at}


def dragon_handoff_view(folder, user, device_id="", device_type=""):
    return dragon_handoff.dragon_handoff_view(DATA_DIR, folder, _resolve_user(user), device_id, device_type)


def dragon_handoff_action(folder, user, action, payload):
    return dragon_handoff.dragon_handoff_action(DATA_DIR, folder, _resolve_user(user), action, payload)


class Handler(http.server.SimpleHTTPRequestHandler):
    # HTTP/1.1 keep-alive: browsers reuse a few connections for the dragon ES-module
    # graph instead of opening ~40 short-lived TCP sockets (LAN RST flakiness).
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_DIR), **kwargs)

    def end_headers(self):
        path = urlparse(self.path).path
        # API JSON must never be cached: a stale /api/latest-user-db after a quiz
        # save would overwrite the browser's newer IndexedDB copy on Continue.
        if path.startswith('/api/'):
            self.send_header('Cache-Control', 'no-store')
        elif path.endswith(('.html', '.js', '.mjs', '.css')):
            self.send_header('Cache-Control', 'no-cache, must-revalidate')
        super().end_headers()

    def copyfile(self, source, outputfile):
        """Ignore client disconnects mid-transfer (common under parallel module loads)."""
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            self.close_connection = True

    def _send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        static_path = _normalize_static_path(parsed.path)
        if static_path != parsed.path:
            rest = parsed.query
            self.path = static_path + (f"?{rest}" if rest else "")
            parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            return self._send_json(200, {"ok": True, "bucket": BUCKET, "singleSessionBase": f"{S3_SINGLE_SESSION_BASE}/", "backupBase": f"{S3_BACKUP_BASE}/"})
        if parsed.path == "/api/data-folders":
            return self._send_json(200, {"ok": True, "folders": data_folders()})
        if parsed.path == "/api/list":
            folder = _safe_folder(parse_qs(parsed.query).get("folder", ["real"])[0])
            if not folder:
                return self._send_json(400, {"ok": False, "error": "folder required"})
            return self._send_json(200, {"ok": True, "folder": folder, "files": list_filenames(folder)})
        if parsed.path == "/api/folder-users":
            folder = _safe_folder(parse_qs(parsed.query).get("folder", ["real"])[0])
            if not folder:
                return self._send_json(400, {"ok": False, "error": "folder required"})
            return self._send_json(200, folder_users(folder))
        if parsed.path == "/api/latest-user-db":
            q = parse_qs(parsed.query)
            folder = _safe_folder(q.get("folder", ["real"])[0])
            user = os.path.basename(q.get("user", [""])[0])   # guard path traversal
            file_hint = q.get("file", [None])[0]
            subfolder = q.get("subfolder", [None])[0]
            if not folder:
                return self._send_json(400, {"ok": False, "error": "folder required"})
            if not user:
                return self._send_json(400, {"ok": False, "error": "user required"})
            try:
                return self._send_json(200, latest_user_db(folder, user, filename=file_hint, subfolder=subfolder))
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if parsed.path == "/api/problem-lists":
            q = parse_qs(parsed.query)
            folder = _safe_folder(q.get("folder", ["real"])[0])
            user = os.path.basename(q.get("user", [""])[0])
            file_hint = q.get("file", [None])[0]
            if not folder or not user:
                return self._send_json(400, {"ok": False, "error": "folder and user required"})
            try:
                return self._send_json(200, problem_lists_view(folder, user, filename=file_hint))
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if parsed.path == "/api/targeted-config":
            q = parse_qs(parsed.query)
            folder = _safe_folder(q.get("folder", ["real"])[0])
            user = os.path.basename(q.get("user", [""])[0])
            file_hint = q.get("file", [None])[0]
            if not folder or not user:
                return self._send_json(400, {"ok": False, "error": "folder and user required"})
            try:
                return self._send_json(200, targeted_config_view(folder, user, filename=file_hint))
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if parsed.path == "/api/visual-config":
            q = parse_qs(parsed.query)
            folder = _safe_folder(q.get("folder", ["real"])[0])
            user = os.path.basename(q.get("user", [""])[0])
            file_hint = q.get("file", [None])[0]
            if not folder or not user:
                return self._send_json(400, {"ok": False, "error": "folder and user required"})
            try:
                return self._send_json(200, visual_config_view(folder, user, filename=file_hint))
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if parsed.path == "/api/fluency-feast-config":
            q = parse_qs(parsed.query)
            folder = _safe_folder(q.get("folder", ["real"])[0])
            user = os.path.basename(q.get("user", [""])[0])
            file_hint = q.get("file", [None])[0]
            if not folder or not user:
                return self._send_json(400, {"ok": False, "error": "folder and user required"})
            try:
                return self._send_json(200, fluency_feast_view(folder, user, filename=file_hint))
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if parsed.path == "/api/profile":
            q = parse_qs(parsed.query)
            folder = _safe_folder(q.get("folder", ["real"])[0])
            user = os.path.basename(q.get("user", [""])[0])
            file_hint = q.get("file", [None])[0]
            if not folder or not user:
                return self._send_json(400, {"ok": False, "error": "folder and user required"})
            try:
                return self._send_json(200, profile_view(folder, user, filename=file_hint))
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if parsed.path == "/api/dragon-display-names":
            try:
                return self._send_json(200, dragon_display_names_view())
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if parsed.path == "/api/dragon-state":
            q = parse_qs(parsed.query)
            folder = _safe_folder(q.get("folder", ["tlkids"])[0])
            user = os.path.basename(q.get("user", [""])[0])
            if not folder or not user:
                return self._send_json(400, {"ok": False, "error": "folder and user required"})
            try:
                return self._send_json(200, dragon_state_view(folder, user))
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if parsed.path == "/api/dragon-world":
            q = parse_qs(parsed.query)
            folder = _safe_folder(q.get("folder", ["tlkids"])[0])
            user = os.path.basename(q.get("user", [""])[0])
            if not folder or not user:
                return self._send_json(400, {"ok": False, "error": "folder and user required"})
            try:
                return self._send_json(200, dragon_world_view(folder, user))
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if parsed.path == "/api/dragon-messages":
            q = parse_qs(parsed.query)
            folder = _safe_folder(q.get("folder", ["tlkids"])[0])
            user = os.path.basename(q.get("user", [""])[0])
            unread = q.get("unread", ["0"])[0] in ("1", "true")
            if not folder or not user:
                return self._send_json(400, {"ok": False, "error": "folder and user required"})
            try:
                return self._send_json(200, dragon_messages_view(folder, user, unread_only=unread))
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if parsed.path == "/api/dragon-zoomies":
            q = parse_qs(parsed.query)
            folder = _safe_folder(q.get("folder", ["tlkids"])[0])
            user = os.path.basename(q.get("user", [""])[0])
            if not folder or not user:
                return self._send_json(400, {"ok": False, "error": "folder and user required"})
            try:
                return self._send_json(200, dragon_zoomie_lines_view(folder, user))
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if parsed.path == "/api/dragon-growth-spurt":
            q = parse_qs(parsed.query)
            folder = _safe_folder(q.get("folder", ["tlkids"])[0])
            user = os.path.basename(q.get("user", [""])[0])
            if not folder or not user:
                return self._send_json(400, {"ok": False, "error": "folder and user required"})
            try:
                return self._send_json(200, dragon_growth_spurt_lines_view(folder, user))
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if parsed.path == "/api/dragon-handoff":
            q = parse_qs(parsed.query)
            folder = _safe_folder(q.get("folder", ["tlkids"])[0])
            user = os.path.basename(q.get("user", [""])[0])
            device_id = str(q.get("deviceId", [""])[0])
            device_type = str(q.get("deviceType", ["desktop"])[0])
            if not folder or not user:
                return self._send_json(400, {"ok": False, "error": "folder and user required"})
            try:
                return self._send_json(200, dragon_handoff_view(folder, user, device_id, device_type))
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if parsed.path == "/api/resolve-editor-target":
            q = parse_qs(parsed.query)
            user = os.path.basename(q.get("user", [""])[0])
            file_hint = q.get("file", [None])[0]
            if not user:
                return self._send_json(400, {"ok": False, "error": "user required"})
            try:
                return self._send_json(200, resolve_editor_target(user, filename=file_hint))
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if parsed.path == "/favicon.ico":
            icon = APP_DIR / "icons" / "favicon-anchor.svg"
            if icon.is_file():
                body = icon.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/problem-lists":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length))
                folder = _safe_folder(payload.get("folder") or "")
                user = os.path.basename(str(payload.get("user") or ""))
                action = str(payload.get("action") or "")
                if not folder or not user:
                    return self._send_json(400, {"ok": False, "error": "folder and user required"})
                result = edit_problem_lists(folder, user, action, payload)
                return self._send_json(200 if result.get("ok") else 400, result)
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if path == "/api/targeted-config":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length))
                folder = _safe_folder(payload.get("folder") or "")
                user = os.path.basename(str(payload.get("user") or ""))
                if not folder or not user:
                    return self._send_json(400, {"ok": False, "error": "folder and user required"})
                result = edit_targeted_config(folder, user, payload)
                return self._send_json(200 if result.get("ok") else 400, result)
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if path == "/api/visual-config":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length))
                folder = _safe_folder(payload.get("folder") or "")
                user = os.path.basename(str(payload.get("user") or ""))
                if not folder or not user:
                    return self._send_json(400, {"ok": False, "error": "folder and user required"})
                result = edit_visual_config(folder, user, payload)
                return self._send_json(200 if result.get("ok") else 400, result)
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if path == "/api/fluency-feast-config":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length))
                folder = _safe_folder(payload.get("folder") or "")
                user = os.path.basename(str(payload.get("user") or ""))
                if not folder or not user:
                    return self._send_json(400, {"ok": False, "error": "folder and user required"})
                result = edit_fluency_feast(folder, user, payload)
                return self._send_json(200 if result.get("ok") else 400, result)
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if path == "/api/profile":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length))
                folder = _safe_folder(payload.get("folder") or "")
                user = os.path.basename(str(payload.get("user") or ""))
                if not folder or not user:
                    return self._send_json(400, {"ok": False, "error": "folder and user required"})
                result = edit_profile(folder, user, payload)
                return self._send_json(200 if result.get("ok") else 400, result)
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if path == "/api/dragon-state":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length))
                folder = _safe_folder(payload.get("folder") or "")
                user = os.path.basename(str(payload.get("user") or ""))
                if not folder or not user:
                    return self._send_json(400, {"ok": False, "error": "folder and user required"})
                result = save_dragon_state(folder, user, payload.get("state") or {})
                return self._send_json(200, result)
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if path == "/api/dragon-world":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length))
                folder = _safe_folder(payload.get("folder") or "")
                user = os.path.basename(str(payload.get("user") or ""))
                if not folder or not user:
                    return self._send_json(400, {"ok": False, "error": "folder and user required"})
                result = save_dragon_world(folder, user, payload.get("gameState") or payload.get("state") or {})
                return self._send_json(200 if result.get("ok") else 400, result)
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if path == "/api/dragon-messages":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length))
                folder = _safe_folder(payload.get("folder") or "")
                user = os.path.basename(str(payload.get("user") or ""))
                action = str(payload.get("action") or "send")
                if not folder or not user:
                    return self._send_json(400, {"ok": False, "error": "folder and user required"})
                if action == "send":
                    result = post_dragon_message(folder, user, payload.get("text"), payload.get("from"))
                elif action == "mark-read":
                    result = mark_dragon_messages_read(folder, user, payload.get("ids"))
                else:
                    result = {"ok": False, "error": "action must be send|mark-read"}
                return self._send_json(200 if result.get("ok") else 400, result)
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if path == "/api/dragon-zoomies":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length))
                folder = _safe_folder(payload.get("folder") or "")
                user = os.path.basename(str(payload.get("user") or ""))
                if not folder or not user:
                    return self._send_json(400, {"ok": False, "error": "folder and user required"})
                result = save_dragon_zoomie_lines(folder, user, payload.get("bands"))
                return self._send_json(200 if result.get("ok") else 400, result)
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if path == "/api/dragon-growth-spurt":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length))
                folder = _safe_folder(payload.get("folder") or "")
                user = os.path.basename(str(payload.get("user") or ""))
                if not folder or not user:
                    return self._send_json(400, {"ok": False, "error": "folder and user required"})
                result = save_dragon_growth_spurt_lines(folder, user, payload.get("bands"))
                return self._send_json(200 if result.get("ok") else 400, result)
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if path == "/api/dragon-handoff":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length))
                folder = _safe_folder(payload.get("folder") or "")
                user = os.path.basename(str(payload.get("user") or ""))
                action = str(payload.get("action") or "")
                if not folder or not user:
                    return self._send_json(400, {"ok": False, "error": "folder and user required"})
                result = dragon_handoff_action(folder, user, action, payload)
                return self._send_json(200 if result.get("ok") else 400, result)
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if path == "/api/clone-user-file":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length))
                folder = _safe_folder(payload.get("folder") or "")
                source = os.path.basename(str(payload.get("sourceUser") or ""))
                target = os.path.basename(str(payload.get("targetUser") or ""))
                source_file = payload.get("sourceFile")
                if not folder or not source or not target:
                    return self._send_json(400, {"ok": False, "error": "folder, sourceUser, targetUser required"})
                result = clone_user(folder, source, target, source_filename=source_file)
                return self._send_json(200 if result.get("ok") else 400, result)
            except Exception as exc:
                return self._send_json(500, {"ok": False, "error": str(exc)})
        if path != "/api/save-run":
            return self._send_json(404, {"ok": False, "error": "unknown endpoint"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            source_folder = _safe_folder(payload.get("sourceFolder") or "real")
            destination = payload.get("destination", "source")
            if not source_folder:
                return self._send_json(400, {"ok": False, "error": "sourceFolder required"})
            if destination not in ("source", "test"):
                return self._send_json(400, {"ok": False, "error": "destination must be source|test"})
            name = os.path.basename(str(payload.get("name") or "Guest"))   # guard path traversal
            stamp = str(payload["stamp"])
            raw = base64.b64decode(payload["base64"])
            force_new = bool(payload.get("forceNew"))
            consumed = payload.get("consumedProblemListId")
            consumed = int(consumed) if consumed not in (None, "") else None
            result = save_run(source_folder, destination, name, stamp,
                              payload.get("testDescription", ""), raw,
                              force_new=force_new,
                              consumed_problem_list_id=consumed,
                              targeted_config=payload.get("targetedConfig"),
                              visual_config=payload.get("visualConfig"),
                              source_file=payload.get("sourceFile"))
            return self._send_json(200, result)
        except Exception as exc:
            return self._send_json(500, {"ok": False, "error": str(exc)})


if __name__ == "__main__":
    # Re-running this script restarts: free the port if a prior server is still up.
    _free_port(PORT)
    print(f"Anchor dev server (bind {BIND}): http://127.0.0.1:{PORT}/anchor.html  (serving {APP_DIR})")
    print(f"  Dragon game: http://127.0.0.1:{PORT}/dragon/index.html")
    print(f"  Dragon Game Master: http://127.0.0.1:{PORT}/dragon/gm.html")
    lan = _lan_ip()
    if lan and BIND != "127.0.0.1":
        print(f"  On your phone/tablet (same Wi-Fi): http://{lan}:{PORT}/anchor.html")
        print(f"  Dragon game on iPad/phone: http://{lan}:{PORT}/dragon/index.html")
        print(f"    (short URL also works: http://{lan}:{PORT}/dragon/index)")
        print(f"  Game Master on your phone: http://{lan}:{PORT}/dragon/gm.html")
    if S3_DISABLED:
        print(f"Backup broker -> S3 DISABLED (ANCHOR_S3_DISABLE=1)   ·   local mirror {DATA_DIR}   ·   snapshots {BACKUP_ROOT}")
    else:
        print(f"Backup broker -> singles s3://{BUCKET}/{S3_SINGLE_SESSION_BASE}/   ·   snapshots s3://{BUCKET}/{S3_BACKUP_BASE}/   ·   local mirror {DATA_DIR}   ·   snapshots {BACKUP_ROOT}")
    _start_sleep_guard()
    dragon_display_names.ensure_local_file()
    models = dragon_assets.ensure_local_models()
    if models.get("ok"):
        if models.get("copied"):
            print(f"  Dragon models: copied {', '.join(models['copied'])} → {models['runtimeDir']}")
        else:
            print(f"  Dragon models: ready ({len(models.get('present') or [])} GLBs in {models['runtimeDir']})")
    else:
        print(f"  Dragon models: WARNING — {models.get('error')} ({models.get('approvedDir')})")
        print("    Game will fall back to the procedural purple dragon until Pipa GLBs are available.")
    # Threading + large listen backlog + HTTP/1.1 keep-alive:
    # Chrome opens many parallel connections for the dragon ES-module graph (~40
    # files). Plain TCPServer is single-threaded; the default listen backlog (5)
    # also overflows under that burst and the OS RSTs the extras — LAN clients
    # then see ERR_CONNECTION_RESET and "Dragon Nest / Loading…" never finishes.
    class _DevHttpServer(http.server.ThreadingHTTPServer):
        allow_reuse_address = True
        request_queue_size = 128
        daemon_threads = True
    try:
        with _DevHttpServer((BIND, PORT), Handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nstopped")
    finally:
        _stop_sleep_guard()
