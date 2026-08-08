"""Rsync status checks, preview/apply sync, and log writing."""
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from server import config as app_config
from server import mods as mods_ops
from server import remote as remote_ops

RSYNC_CHANGE_PREFIXES = (">", "<", "*deleting", "c", "h", "p", "o", "g", "t", "s")
HIDE_RSYNC_TIMESTAMP_ONLY_PREVIEW = True


def _rsync_itemize_parts(line):
    """Return (xfer, item_type, attrs) for one rsync --itemize-changes line."""
    stripped = line.strip()
    token = stripped.split(None, 1)[0]
    if len(token) < 3:
        return None
    xfer = token[0]
    item_type = token[1]
    attrs = token[2:]
    if item_type not in "fdLDS":
        return None
    return xfer, item_type, attrs


def _rsync_itemize_is_timestamp_only(line):
    """Return True for rsync itemize lines that only adjust timestamps/metadata."""
    stripped = line.strip()
    if not stripped or stripped.startswith("*deleting"):
        return False
    if stripped.startswith("sending incremental file list"):
        return False
    if stripped.startswith("building file list"):
        return False
    if stripped.startswith("total:"):
        return False
    if stripped.startswith("sent "):
        return False
    parts = _rsync_itemize_parts(stripped)
    if not parts:
        return False
    _xfer, item_type, attrs = parts
    if "+" in attrs:
        return False
    if "c" in attrs or "s" in attrs:
        return False
    non_dot = attrs.replace(".", "")
    if non_dot == "t":
        return True
    if item_type == "d" and non_dot in ("", "t"):
        return True
    return False


def filter_rsync_preview_output(output, hide_timestamp_only=HIDE_RSYNC_TIMESTAMP_ONLY_PREVIEW):
    """Drop timestamp-only rsync itemize lines from dry-run preview text."""
    if not output:
        return output
    if not hide_timestamp_only:
        return output
    kept = []
    for line in output.splitlines():
        if _rsync_itemize_is_timestamp_only(line):
            continue
        kept.append(line)
    filtered = "\n".join(kept).strip("\n")
    if not filtered and output.strip():
        return "(no file adds, deletes, or content changes)"
    return filtered


def parse_rsync_dry_run_output(output):
    """Return True if rsync dry-run output indicates changes."""
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("sending incremental file list"):
            continue
        if stripped.startswith("building file list"):
            continue
        if stripped.startswith("total:"):
            continue
        if stripped.startswith("sent "):
            continue
        if re.match(r"^[><*chpgot]", stripped):
            return True
        if stripped.startswith("*deleting"):
            return True
    return False


def instance_status_detail(computer, instance_name, reachability=None):
    """Return {state, mods_diff?} for one instance on one computer."""
    cfg = app_config.load_config()
    instances_dir = cfg["paths"]["instances_dir"]
    local_present = os.path.isdir(os.path.join(instances_dir, instance_name))
    if computer.get("role") == "master":
        state = "present" if local_present else "missing"
        return {"state": state}
    state = reachability.get(computer["id"]) if reachability else remote_ops.check_reachability(computer)
    if state == "unconfigured":
        return {"state": "unconfigured"}
    if state == "offline":
        return {"state": "unreachable"}
    if not local_present:
        return {"state": "missing"}
    if not remote_ops.remote_has_instance(computer, instance_name):
        return {"state": "missing"}
    local_jars = mods_ops.local_mod_jars(instance_name, instances_dir)
    remote_jars = mods_ops.remote_mod_jars(computer, instance_name)
    mod_state, mods_diff = mods_ops.compare_mod_jars(local_jars, remote_jars)
    detail = {"state": mod_state}
    if mods_diff:
        detail["mods_diff"] = mods_diff
    return detail


def instance_status(computer, instance_name, reachability=None):
    """Return a matrix cell state string for one instance on one computer."""
    return instance_status_detail(computer, instance_name, reachability)["state"]


def status_for_instances(instance_names, computer_ids=None, reachability=None):
    """Build status strings and mods diff detail for many instances."""
    cfg = app_config.load_config()
    reachability = reachability or remote_ops.check_all_reachability(computer_ids)
    computers = []
    selected = set(computer_ids) if computer_ids else None
    for computer in cfg["computers"]:
        if computer.get("role") != "target":
            continue
        if selected and computer["id"] not in selected:
            continue
        computers.append(computer)
    status = {name: {} for name in instance_names}
    mods_detail = {name: {} for name in instance_names}
    futures = {}
    with ThreadPoolExecutor(max_workers=12) as pool:
        for instance_name in instance_names:
            for computer in computers:
                key = (instance_name, computer["id"])
                futures[pool.submit(instance_status_detail, computer, instance_name, reachability)] = key
        for future in as_completed(futures):
            instance_name, computer_id = futures[future]
            try:
                detail = future.result()
            except Exception:
                status[instance_name][computer_id] = "unknown"
                continue
            status[instance_name][computer_id] = detail["state"]
            if detail.get("mods_diff"):
                mods_detail[instance_name][computer_id] = detail["mods_diff"]
    return {"status": status, "mods_detail": mods_detail}


def build_matrix(local_instances, status_payload=None):
    """Build matrix rows from local host4 instances only."""
    status_payload = status_payload or {}
    instance_names = [row["name"] for row in local_instances]
    return {
        "rows": list(local_instances),
        "status": status_payload.get("status") or {},
        "mods_detail": status_payload.get("mods_detail") or {},
        "local_mods": mods_ops.local_mods_map(instance_names),
    }


def _rsync_base_args(dry_run=True):
    """Shared rsync argv prefix for instance and icon sync."""
    args = [
        "rsync",
        "-az",
        "--delete",
        "--human-readable",
        "--itemize-changes",
        "-e", remote_ops.rsync_ssh_shell(),
    ]
    if dry_run:
        args.append("--dry-run")
    return args


def _rsync_mods_jars(computer, instance_name, dry_run=True):
    """Run rsync for mod .jar files only under minecraft/mods/."""
    cfg = app_config.load_config()
    source_mods = os.path.join(cfg["paths"]["instances_dir"], instance_name, "minecraft", "mods")
    if not os.path.isdir(source_mods):
        return False, "", "local mods folder not found"
    remote_mods = (
        cfg["paths"]["remote_instances_dir"]
        + "/"
        + instance_name
        + "/"
        + mods_ops.MODS_SUBPATH
        + "/"
    )
    args = [
        "rsync",
        "-az",
        "--delete",
        "--human-readable",
        "--itemize-changes",
        "-e", remote_ops.rsync_ssh_shell(),
        "--include=*.jar",
        "--exclude=*",
    ]
    if dry_run:
        args.append("--dry-run")
    args.append(source_mods + os.sep)
    args.append(remote_ops.rsync_remote_dest(computer, remote_mods))
    try:
        completed = subprocess.run(args, capture_output=True, text=True, timeout=600, check=False)
        return completed.returncode == 0, completed.stdout, completed.stderr
    except (subprocess.TimeoutExpired, OSError) as err:
        return False, "", str(err)


def _replace_superseded_mod_jars(computer, instance_name, dry_run=True):
    """Delete older same-mod jars on the target before syncing the local version."""
    local_jars = mods_ops.local_mod_jars(instance_name)
    remote_jars = mods_ops.remote_mod_jars(computer, instance_name)
    replacements = mods_ops.superseded_replacements(local_jars, remote_jars)
    if not replacements:
        return True, "", ""
    lines = ["Replacing older mod versions:"]
    for row in replacements:
        lines.append("  " + row["remote_jar"] + " → " + row["local_jar"])
    if dry_run:
        lines.append("(dry-run: old jars would be deleted and verified before sync)")
        return True, "\n".join(lines), ""
    for row in replacements:
        ok, message = remote_ops.delete_remote_mod_jar(computer, instance_name, row["remote_jar"])
        lines.append("  " + message)
        if not ok:
            return False, "\n".join(lines), message
    return True, "\n".join(lines), ""


def _sync_mods_jars(computer, instance_name, dry_run=True):
    """Replace superseded jars, then rsync local mod jars to the target."""
    ok, replace_out, replace_err = _replace_superseded_mod_jars(computer, instance_name, dry_run=dry_run)
    if not ok:
        return False, replace_out, replace_err
    ok, rsync_out, rsync_err = _rsync_mods_jars(computer, instance_name, dry_run=dry_run)
    parts = []
    if replace_out:
        parts.append(replace_out)
    if rsync_out:
        parts.append(rsync_out)
    stdout = "\n".join(parts)
    stderr = rsync_err or replace_err
    return ok, stdout, stderr


def _ensure_remote_mods_dir(computer, instance_name):
    """Create remote minecraft/mods before a real mod-jar sync."""
    cfg = app_config.load_config()
    remote_mods = (
        cfg["paths"]["remote_instances_dir"]
        + "/"
        + instance_name
        + "/"
        + mods_ops.MODS_SUBPATH
    )
    command = 'mkdir -p "$HOME/' + remote_mods + '"'
    args = ["ssh"] + remote_ops.ssh_command_args() + [remote_ops.ssh_target(computer), command]
    ok, _, stderr = remote_ops._run_command(args)
    if not ok:
        return False, stderr
    return True, ""


def _rsync_instance(computer, instance_name, dry_run=True, update_existing=True):
    """Run rsync for one instance to one target."""
    cfg = app_config.load_config()
    source_dir = os.path.join(cfg["paths"]["instances_dir"], instance_name)
    if not os.path.isdir(source_dir):
        return False, "", "local instance not found"
    if not update_existing and not dry_run:
        if remote_ops.remote_has_instance(computer, instance_name):
            return True, "Skipping existing target instance: " + instance_name, ""
    remote_path = cfg["paths"]["remote_instances_dir"] + "/" + instance_name + "/"
    args = _rsync_base_args(dry_run=dry_run)
    args.extend(app_config.rsync_exclude_args())
    args.append(source_dir + os.sep)
    args.append(remote_ops.rsync_remote_dest(computer, remote_path))
    try:
        completed = subprocess.run(args, capture_output=True, text=True, timeout=600, check=False)
        return completed.returncode == 0, completed.stdout, completed.stderr
    except (subprocess.TimeoutExpired, OSError) as err:
        return False, "", str(err)


def _rsync_icons(computer, dry_run=True):
    """Sync the Prism icon library to a target."""
    cfg = app_config.load_config()
    icons_dir = cfg["paths"]["icons_dir"]
    if not os.path.isdir(icons_dir):
        return True, "Skipping Prism icon library sync; local folder not found", ""
    remote_path = cfg["paths"]["remote_icons_dir"] + "/"
    args = _rsync_base_args(dry_run=dry_run)
    args.append(icons_dir + os.sep)
    args.append(remote_ops.rsync_remote_dest(computer, remote_path))
    try:
        completed = subprocess.run(args, capture_output=True, text=True, timeout=600, check=False)
        return completed.returncode == 0, completed.stdout, completed.stderr
    except (subprocess.TimeoutExpired, OSError) as err:
        return False, "", str(err)


def _ensure_remote_dirs(computer):
    """Create remote instances/icons dirs before a real sync."""
    cfg = app_config.load_config()
    commands = [
        'mkdir -p "$HOME/' + cfg["paths"]["remote_instances_dir"] + '"',
        'mkdir -p "$HOME/' + cfg["paths"]["remote_icons_dir"] + '"',
    ]
    for command in commands:
        args = ["ssh"] + remote_ops.ssh_command_args() + [remote_ops.ssh_target(computer), command]
        ok, _, stderr = remote_ops._run_command(args)
        if not ok:
            return False, stderr
    return True, ""


def _instance_sync_mode(mods_only, exists_on_target):
    """Return mods_jars when updating an existing target instance in safe mode."""
    if mods_only and exists_on_target:
        return "mods_jars"
    return "full_instance"


def _instance_sync_heading(instance_name, mode):
    """Human-readable heading for one instance sync in preview/apply output."""
    if mode == "mods_jars":
        return "Mod jars only (instance exists on target): " + instance_name
    if mode == "full_instance":
        return "Full instance sync: " + instance_name
    return "Syncing instance: " + instance_name


def _target_skips_icon_sync(instance_names, computer, mods_only):
    """Skip icon sync when every instance push on this target is mods-only."""
    if not mods_only:
        return False
    for instance_name in instance_names:
        if not remote_ops.remote_has_instance(computer, instance_name):
            return False
    return bool(instance_names)


def preview_sync(instance_names, target_ids, sync_icons=True, update_existing=False, mods_only=False):
    """Dry-run sync for selected instances and targets."""
    cfg = app_config.load_config()
    targets = []
    for computer in cfg["computers"]:
        if computer.get("role") != "target":
            continue
        if computer["id"] not in target_ids:
            continue
        targets.append(computer)
    sections = []
    for computer in targets:
        block = ["Dry-run preview for " + computer["name"] + " (" + remote_ops.ssh_target(computer) + ")"]
        if mods_only:
            block.append("Mode: mod jars for existing instances; full sync for new instances on target")
        if sync_icons and not _target_skips_icon_sync(instance_names, computer, mods_only):
            ok, stdout, stderr = _rsync_icons(computer, dry_run=True)
            block.append(filter_rsync_preview_output(stdout))
            if stderr:
                block.append(stderr)
            if not ok:
                block.append("icon sync dry-run failed")
        for instance_name in instance_names:
            if not update_existing and remote_ops.remote_has_instance(computer, instance_name):
                block.append("Skipping existing target instance: " + instance_name)
                continue
            exists = remote_ops.remote_has_instance(computer, instance_name)
            mode = _instance_sync_mode(mods_only, exists)
            block.append(_instance_sync_heading(instance_name, mode if mods_only else "default"))
            if mode == "mods_jars":
                ok, stdout, stderr = _sync_mods_jars(computer, instance_name, dry_run=True)
            else:
                ok, stdout, stderr = _rsync_instance(computer, instance_name, dry_run=True, update_existing=update_existing)
            block.append(filter_rsync_preview_output(stdout))
            if stderr:
                block.append(stderr)
            if not ok:
                block.append("instance sync dry-run failed")
        sections.append("\n".join(block))
    return "\n\n".join(sections)


def apply_sync(instance_names, target_ids, sync_icons=True, update_existing=False, mods_only=False):
    """Run the real sync and return combined output."""
    cfg = app_config.load_config()
    targets = []
    for computer in cfg["computers"]:
        if computer.get("role") != "target":
            continue
        if computer["id"] not in target_ids:
            continue
        targets.append(computer)
    sections = []
    for computer in targets:
        block = ["Real sync for " + computer["name"] + " (" + remote_ops.ssh_target(computer) + ")"]
        if mods_only:
            block.append("Mode: mod jars for existing instances; full sync for new instances on target")
        ok, detail = _ensure_remote_dirs(computer)
        if not ok:
            block.append("Failed to prepare remote dirs: " + detail)
            sections.append("\n".join(block))
            continue
        if sync_icons and not _target_skips_icon_sync(instance_names, computer, mods_only):
            ok, stdout, stderr = _rsync_icons(computer, dry_run=False)
            block.append(stdout)
            if stderr:
                block.append(stderr)
        for instance_name in instance_names:
            if not update_existing and remote_ops.remote_has_instance(computer, instance_name):
                block.append("Skipping existing target instance: " + instance_name)
                continue
            exists = remote_ops.remote_has_instance(computer, instance_name)
            mode = _instance_sync_mode(mods_only, exists)
            block.append("")
            block.append(_instance_sync_heading(instance_name, mode if mods_only else "default"))
            if mode == "mods_jars":
                ok, detail = _ensure_remote_mods_dir(computer, instance_name)
                if not ok:
                    block.append("Failed to prepare remote mods dir: " + detail)
                    continue
                ok, stdout, stderr = _sync_mods_jars(computer, instance_name, dry_run=False)
            else:
                ok, stdout, stderr = _rsync_instance(computer, instance_name, dry_run=False, update_existing=update_existing)
            block.append(stdout)
            if stderr:
                block.append(stderr)
        sections.append("\n".join(block))
    output = "\n\n".join(sections)
    return output


def _targets_for_ids(target_ids):
    """Return target computer dicts for the given ids."""
    cfg = app_config.load_config()
    selected = set(target_ids)
    targets = []
    for computer in cfg["computers"]:
        if computer.get("role") != "target":
            continue
        if computer["id"] not in selected:
            continue
        targets.append(computer)
    return targets


def capture_mods_snapshot(instance_names, target_ids):
    """Capture remote mod jars per target/instance before or after a push."""
    snapshot = {}
    for computer in _targets_for_ids(target_ids):
        snapshot[computer["id"]] = {}
        for instance_name in instance_names:
            present = remote_ops.remote_has_instance(computer, instance_name)
            snapshot[computer["id"]][instance_name] = {
                "present": present,
                "jars": mods_ops.remote_mod_jars(computer, instance_name) if present else [],
                "local_jars": mods_ops.local_mod_jars(instance_name),
            }
    return snapshot


def append_sync_log(before_snapshot, after_snapshot, instance_names, target_ids, options):
    """Append a condensed push entry to prism-sync_log.md."""
    cfg = app_config.load_config()
    log_path = cfg["paths"]["log_file"]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
    lines = [
        "",
        "# Push - " + timestamp,
        "",
        "Instances: " + ", ".join(instance_names),
        "Mod jars only: " + ("yes" if options.get("mods_only") else "no"),
        "Push icons: " + ("yes" if options.get("sync_icons") else "no"),
        "",
    ]
    for computer in _targets_for_ids(target_ids):
        lines.append("## " + computer.get("label", computer["name"]))
        lines.append("")
        for instance_name in instance_names:
            before = (before_snapshot.get(computer["id"]) or {}).get(instance_name) or {}
            after = (after_snapshot.get(computer["id"]) or {}).get(instance_name) or {}
            local_jars = after.get("local_jars") or before.get("local_jars") or mods_ops.local_mod_jars(instance_name)
            lines.append("### " + instance_name)
            diff_lines = mods_ops.mods_push_diff_lines(
                before.get("jars") or [],
                after.get("jars") or [],
                local_jars,
                bool(before.get("present")),
            )
            lines.extend(diff_lines)
            lines.append("")
    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def _pull_mod_jar(computer, instance_name, jar_name):
    """Pull one mod jar from a target instance into local mods/."""
    cfg = app_config.load_config()
    mods_dir = os.path.join(cfg["paths"]["instances_dir"], instance_name, "minecraft", "mods")
    os.makedirs(mods_dir, exist_ok=True)
    local_path = os.path.join(mods_dir, jar_name)
    if os.path.isfile(local_path):
        return True, "Already local: " + jar_name
    remote_file = (
        cfg["paths"]["remote_instances_dir"]
        + "/"
        + instance_name
        + "/"
        + mods_ops.MODS_SUBPATH
        + "/"
        + jar_name
    )
    args = [
        "rsync",
        "-az",
        "-e", remote_ops.rsync_ssh_shell(),
        remote_ops.rsync_remote_file(computer, remote_file),
        mods_dir + os.sep,
    ]
    try:
        completed = subprocess.run(args, capture_output=True, text=True, timeout=600, check=False)
        if completed.returncode == 0:
            return True, "Pulled: " + jar_name
        detail = (completed.stderr or completed.stdout or "").strip()
        return False, "Failed " + jar_name + ": " + detail
    except (subprocess.TimeoutExpired, OSError) as err:
        return False, "Failed " + jar_name + ": " + str(err)


def apply_pull(instance_names, target_ids):
    """Pull remote-only mod jars from targets into local instances."""
    cfg = app_config.load_config()
    targets = _targets_for_ids(target_ids)
    sections = []
    for instance_name in instance_names:
        instance_dir = os.path.join(cfg["paths"]["instances_dir"], instance_name)
        if not os.path.isdir(instance_dir):
            sections.append("Missing local instance: " + instance_name)
            continue
        local_jars = set(mods_ops.local_mod_jars(instance_name))
        for computer in targets:
            if remote_ops.check_reachability(computer) != "online":
                continue
            if not remote_ops.remote_has_instance(computer, instance_name):
                continue
            remote_jars = mods_ops.remote_mod_jars(computer, instance_name)
            _, diff = mods_ops.compare_mod_jars(list(local_jars), remote_jars)
            if not diff:
                continue
            remote_only = diff.get("remote_only") or []
            if not remote_only:
                continue
            block = [computer.get("label", computer["name"]) + " / " + instance_name]
            for jar_name in remote_only:
                ok, message = _pull_mod_jar(computer, instance_name, jar_name)
                block.append(message)
                if ok and message.startswith("Pulled:"):
                    local_jars.add(jar_name)
            sections.append("\n".join(block))
    if not sections:
        return "Nothing to pull (no remote-only mod jars on selected targets)."
    return "\n\n".join(sections)
