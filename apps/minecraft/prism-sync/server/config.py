"""Load computers.toml and expose resolved paths."""
import os
import sys
import tomllib

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG_PATH = os.path.join(APP_DIR, "computers.toml")
_config_cache = None


def expand_path(path):
    """Expand ~ and env vars in a path string."""
    return os.path.expanduser(os.path.expandvars(path))


def config_path():
    """Return the active config file path."""
    return os.environ.get("PRISM_SYNC_CONFIG", DEFAULT_CONFIG_PATH)


def load_config(force_reload=False):
    """Load and cache computers.toml."""
    global _config_cache
    if _config_cache is not None and not force_reload:
        return _config_cache
    path = config_path()
    with open(path, "rb") as handle:
        raw = tomllib.load(handle)
    paths = raw.get("paths", {})
    raw["paths"] = {
        "instances_dir": expand_path(paths.get("instances_dir", "")),
        "icons_dir": expand_path(paths.get("icons_dir", "")),
        "remote_instances_dir": paths.get("remote_instances_dir", ""),
        "remote_icons_dir": paths.get("remote_icons_dir", ""),
        "log_file": os.path.join(APP_DIR, paths.get("log_file", "_data/prism-sync_log.md")),
    }
    computers = sorted(raw.get("computers", []), key=lambda row: row.get("order", 0))
    raw["computers"] = computers
    raw["app_dir"] = APP_DIR
    _config_cache = raw
    return raw


def get_computer(computer_id):
    """Find a computer dict by id."""
    for computer in load_config()["computers"]:
        if computer["id"] == computer_id:
            return computer
    return None


def master_computer():
    """Return the master (source) computer entry."""
    for computer in load_config()["computers"]:
        if computer.get("role") == "master":
            return computer
    return None


def target_computers(enabled_only=False):
    """Return target computers sorted by order."""
    rows = []
    for computer in load_config()["computers"]:
        if computer.get("role") != "target":
            continue
        if enabled_only and not computer.get("enabled"):
            continue
        rows.append(computer)
    return rows


def rsync_exclude_args():
    """Build rsync --exclude= flags from config."""
    args = []
    for row in load_config().get("rsync_excludes", []):
        args.append("--exclude=" + row["path"])
    return args


def rsync_exclude_labels():
    """Short labels for the UI chips."""
    return [row["label"] for row in load_config().get("rsync_excludes", [])]


def instance_name_matches_filters(name, includes=None, excludes=None):
    """Return True if an instance name passes include/exclude filters."""
    cfg = load_config()
    exclude_patterns = excludes if excludes is not None else cfg["instance_filters"].get("excludes", [])
    include_patterns = includes if includes is not None else cfg["instance_filters"].get("includes", [])
    for pattern in exclude_patterns:
        if pattern and pattern in name:
            return False
    if not include_patterns:
        return True
    for pattern in include_patterns:
        if pattern and pattern in name:
            return True
    return False


def public_config():
    """Serialize config for the web UI."""
    cfg = load_config()
    return {
        "port": cfg.get("server", {}).get("port", 8765),
        "computers": [
            {
                "id": row["id"],
                "name": row["name"],
                "label": row.get("label", row["name"]),
                "host": row.get("host", ""),
                "user": row.get("user", ""),
                "role": row.get("role", "target"),
                "enabled": bool(row.get("enabled")),
                "order": row.get("order", 0),
            }
            for row in cfg["computers"]
        ],
        "instance_filters": cfg.get("instance_filters", {}),
        "rsync_exclude_labels": rsync_exclude_labels(),
        "rsync_excludes": [row["path"] for row in cfg.get("rsync_excludes", [])],
    }
