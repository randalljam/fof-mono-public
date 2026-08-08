"""Compare mod .jar filenames between local and remote Prism instances."""
import os
import re

from server import config as app_config
from server import remote as remote_ops

MODS_SUBPATH = "minecraft/mods"
MC_VERSION_IN_JAR_RE = re.compile(r"-\d+\.\d+(?:\.\d+)?(?:-\d+)?")


def mod_jar_slug(jar_name):
    """Return the mod identity prefix before the Minecraft version segment in a jar name."""
    base = jar_name[:-4] if jar_name.lower().endswith(".jar") else jar_name
    match = MC_VERSION_IN_JAR_RE.search(base)
    if match:
        return base[:match.start()].lower()
    return base.lower()


def superseded_replacements(local_jars, remote_jars):
    """Return remote jars replaced by a different local jar with the same mod slug."""
    local_set = set(local_jars)
    local_by_slug = {}
    for name in local_jars:
        local_by_slug[mod_jar_slug(name)] = name
    rows = []
    for remote_name in remote_jars:
        if remote_name in local_set:
            continue
        slug = mod_jar_slug(remote_name)
        local_name = local_by_slug.get(slug)
        if not local_name:
            continue
        rows.append({
            "slug": slug,
            "remote_jar": remote_name,
            "local_jar": local_name,
        })
    rows.sort(key=lambda row: row["remote_jar"].lower())
    return rows


def local_mod_jars(instance_name, instances_dir=None):
    """Return sorted .jar basenames under the local instance mods folder."""
    cfg = app_config.load_config()
    instances_dir = instances_dir or cfg["paths"]["instances_dir"]
    mods_dir = os.path.join(instances_dir, instance_name, "minecraft", "mods")
    if not os.path.isdir(mods_dir):
        return []
    names = []
    for entry in os.listdir(mods_dir):
        if not entry.lower().endswith(".jar"):
            continue
        path = os.path.join(mods_dir, entry)
        if os.path.isfile(path):
            names.append(entry)
    return sorted(names, key=str.lower)


def remote_mod_jars(computer, instance_name):
    """Return sorted .jar basenames on a remote instance mods folder."""
    cfg = app_config.load_config()
    if not computer.get("host") or not computer.get("user"):
        return []
    remote_mods = (
        cfg["paths"]["remote_instances_dir"]
        + "/"
        + instance_name
        + "/"
        + MODS_SUBPATH
    )
    command = (
        'if [ -d "$HOME/' + remote_mods + '" ]; then '
        'for f in "$HOME/' + remote_mods + '"/*.jar; do '
        '[ -f "$f" ] && basename "$f"; done; fi'
    )
    args = ["ssh"] + remote_ops.ssh_command_args() + [remote_ops.ssh_target(computer), command]
    ok, stdout, _ = remote_ops._run_command(args, timeout=remote_ops.SSH_TIMEOUT_SECONDS + 10)
    if not ok:
        return []
    names = []
    for line in stdout.splitlines():
        name = line.strip()
        if name.lower().endswith(".jar"):
            names.append(name)
    return sorted(names, key=str.lower)


def compare_mod_jars(local_jars, remote_jars):
    """Return (state, mods_diff_or_none). state is same_mods or different_mods."""
    local_set = set(local_jars)
    remote_set = set(remote_jars)
    if local_set == remote_set:
        return "same_mods", None
    return "different_mods", {
        "local_only": sorted(local_set - remote_set, key=str.lower),
        "remote_only": sorted(remote_set - local_set, key=str.lower),
    }


def local_mods_map(instance_names):
    """Return {instance_name: [jar basenames]} for local instances."""
    rows = {}
    for name in instance_names:
        rows[name] = local_mod_jars(name)
    return rows


def local_mods_tooltip_text(jars):
    """Format local mod jars for an instance-name tooltip."""
    lines = ["mods/ on host4:"]
    if not jars:
        lines.append("  (none)")
        return "\n".join(lines)
    for name in jars:
        lines.append("  " + name)
    return "\n".join(lines)


def jar_list_label(jars):
    """Format a jar list for log lines."""
    if not jars:
        return "(none)"
    return ", ".join(jars)


def mods_push_diff_lines(before_jars, after_jars, local_jars, instance_was_present):
    """Return condensed log lines for one instance push."""
    lines = []
    before_set = set(before_jars)
    after_set = set(after_jars)
    removed = sorted(before_set - after_set, key=str.lower)
    added = sorted(after_set - before_set, key=str.lower)
    if instance_was_present:
        lines.append("Target mods/ before: " + jar_list_label(before_jars))
    else:
        lines.append("Target before: (instance not present)")
    lines.append("Target mods/ after: " + jar_list_label(after_jars))
    lines.append("host4 mods/: " + jar_list_label(local_jars))
    if removed:
        lines.append("Removed from target (rsync --delete):")
        for name in removed:
            lines.append("  - " + name)
    if added:
        lines.append("Added to target:")
        for name in added:
            lines.append("  + " + name)
    if not removed and not added and before_set == after_set:
        lines.append("No mod jar changes.")
    return lines


def mods_diff_tooltip(mods_diff, local_label="host4", remote_label="target"):
    """Format mods_diff dict as multi-line tooltip text."""
    if not mods_diff:
        return ""
    lines = []
    local_only = mods_diff.get("local_only") or []
    remote_only = mods_diff.get("remote_only") or []
    if local_only:
        lines.append("Only on " + local_label + ":")
        for name in local_only:
            lines.append("  " + name)
    if remote_only:
        lines.append("Only on " + remote_label + ":")
        for name in remote_only:
            lines.append("  " + name)
    return "\n".join(lines)
