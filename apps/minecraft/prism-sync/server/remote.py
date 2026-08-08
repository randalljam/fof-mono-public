"""SSH reachability checks and remote instance listing."""
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

from server import config as app_config

SSH_TIMEOUT_SECONDS = 3


def _run_command(args, timeout=SSH_TIMEOUT_SECONDS):
    """Run a subprocess and return (ok, stdout, stderr)."""
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return completed.returncode == 0, completed.stdout, completed.stderr
    except (subprocess.TimeoutExpired, OSError) as err:
        return False, "", str(err)


def ssh_target(computer):
    """Build user@host for a computer dict."""
    return computer["user"] + "@" + computer["host"]


def ssh_command_args():
    """Shared OpenSSH flags for non-interactive remote commands."""
    return [
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=" + str(SSH_TIMEOUT_SECONDS),
        "-o", "StrictHostKeyChecking=accept-new",
    ]


def rsync_ssh_shell():
    """Shell command rsync -e uses for remote sync and dry-run status checks."""
    return "ssh " + " ".join(ssh_command_args())


def check_reachability(computer):
    """Return online/offline/unconfigured for one computer."""
    if computer.get("role") == "master":
        return "online"
    if not computer.get("host") or not computer.get("user"):
        return "unconfigured"
    args = ["ssh"] + ssh_command_args() + [ssh_target(computer), "true"]
    ok, _, _ = _run_command(args)
    return "online" if ok else "offline"


def check_all_reachability(computer_ids=None):
    """Check reachability for selected computers in parallel."""
    cfg = app_config.load_config()
    selected = {}
    if computer_ids:
        selected = set(computer_ids)
    results = {}
    futures = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for computer in cfg["computers"]:
            if selected and computer["id"] not in selected:
                continue
            futures[pool.submit(check_reachability, computer)] = computer["id"]
        for future in as_completed(futures):
            computer_id = futures[future]
            try:
                results[computer_id] = future.result()
            except Exception:
                results[computer_id] = "offline"
    return results


def remote_instance_names(computer):
    """List Prism instance folder names on a remote Mac."""
    if computer.get("role") == "master":
        from server import prism as prism_ops
        return sorted(prism_ops.list_instance_names())
    cfg = app_config.load_config()
    remote_dir = cfg["paths"]["remote_instances_dir"]
    if not computer.get("host") or not computer.get("user"):
        return []
    command = (
        'for d in "$HOME/' + remote_dir + '"/*; do '
        'if [ -d "$d" ] && [ -f "$d/instance.cfg" ]; then basename "$d"; fi; done'
    )
    args = ["ssh"] + ssh_command_args() + [ssh_target(computer), command]
    ok, stdout, _ = _run_command(args, timeout=SSH_TIMEOUT_SECONDS + 5)
    if not ok:
        return []
    names = []
    for line in stdout.splitlines():
        name = line.strip()
        if name:
            names.append(name)
    return sorted(names, key=str.lower)


def list_remote_instances_for_targets(computer_ids=None, reachability=None):
    """Return {computer_id: [instance names]} for reachable targets."""
    reachability = reachability or {}
    rows = {}
    futures = {}
    targets = app_config.target_computers(enabled_only=False)
    selected = set(computer_ids) if computer_ids else None
    with ThreadPoolExecutor(max_workers=8) as pool:
        for computer in targets:
            if selected and computer["id"] not in selected:
                continue
            state = reachability.get(computer["id"])
            if state not in (None, "online") and reachability:
                rows[computer["id"]] = []
                continue
            if state == "offline" or state == "unconfigured":
                rows[computer["id"]] = []
                continue
            futures[pool.submit(remote_instance_names, computer)] = computer["id"]
        for future in as_completed(futures):
            computer_id = futures[future]
            try:
                rows[computer_id] = future.result()
            except Exception:
                rows[computer_id] = []
    return rows


def rsync_remote_dest(computer, relative_path):
    """Build a quoted rsync remote destination (handles spaces in paths)."""
    path = relative_path.rstrip("/") + "/"
    return ssh_target(computer) + ':"$HOME/' + path + '"'


def rsync_remote_file(computer, relative_file_path):
    """Build a quoted rsync remote source path for one file."""
    return ssh_target(computer) + ':"$HOME/' + relative_file_path + '"'


def remote_has_instance(computer, instance_name):
    """Return True if the remote instance folder exists."""
    cfg = app_config.load_config()
    remote_dir = cfg["paths"]["remote_instances_dir"]
    remote_instance = remote_dir + "/" + instance_name
    command = 'test -d "$HOME/' + remote_instance + '"'
    args = ["ssh"] + ssh_command_args() + [ssh_target(computer), command]
    ok, _, _ = _run_command(args)
    return ok


def _remote_mod_jar_relative(instance_name, jar_name):
    """Return repo-relative remote path to one mod jar."""
    cfg = app_config.load_config()
    return (
        cfg["paths"]["remote_instances_dir"]
        + "/"
        + instance_name
        + "/minecraft/mods/"
        + jar_name
    )


def remote_mod_jar_exists(computer, instance_name, jar_name):
    """Return True if a mod jar exists on the remote instance."""
    rel = _remote_mod_jar_relative(instance_name, jar_name)
    command = 'test -f "$HOME/' + rel + '"'
    args = ["ssh"] + ssh_command_args() + [ssh_target(computer), command]
    ok, _, _ = _run_command(args, timeout=SSH_TIMEOUT_SECONDS + 10)
    return ok


def delete_remote_mod_jar(computer, instance_name, jar_name):
    """Delete one remote mod jar and verify it is gone."""
    rel = _remote_mod_jar_relative(instance_name, jar_name)
    command = 'rm -f "$HOME/' + rel + '"'
    args = ["ssh"] + ssh_command_args() + [ssh_target(computer), command]
    ok, _, stderr = _run_command(args, timeout=SSH_TIMEOUT_SECONDS + 10)
    if not ok:
        detail = (stderr or "").strip() or "delete failed"
        return False, "Failed to delete " + jar_name + ": " + detail
    if remote_mod_jar_exists(computer, instance_name, jar_name):
        return False, "Verification failed: " + jar_name + " still present after delete"
    return True, "Deleted and verified: " + jar_name
