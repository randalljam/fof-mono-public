"""Local Prism Launcher instance discovery and icon resolution."""
import os
import re

from server import config as app_config

ICON_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".svg")
DEFAULT_ICON_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10"
    b"\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x0cIDATx\x9cc``\x00\x00"
    b"\x00\x02\x00\x01\xe5\x27\xde\xfc\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _read_instance_cfg(instance_dir):
    """Parse iconKey from instance.cfg."""
    cfg_path = os.path.join(instance_dir, "instance.cfg")
    if not os.path.isfile(cfg_path):
        return {}
    data = {}
    with open(cfg_path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            match = re.match(r"^\s*iconKey\s*=\s*(.+?)\s*$", line)
            if match:
                data["iconKey"] = match.group(1)
            match = re.match(r"^\s*name\s*=\s*(.+?)\s*$", line)
            if match:
                data["display_name"] = match.group(1)
    return data


def _icon_path_for_key(icon_key, icons_dir):
    """Resolve iconKey to a file under the Prism icons library."""
    if not icon_key or not icons_dir or not os.path.isdir(icons_dir):
        return None
    candidates = [os.path.join(icons_dir, icon_key)]
    for ext in ICON_EXTENSIONS:
        candidates.append(os.path.join(icons_dir, icon_key + ext))
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    lowered = icon_key.lower()
    try:
        for filename in os.listdir(icons_dir):
            stem, ext = os.path.splitext(filename)
            if ext.lower() in ICON_EXTENSIONS and stem.lower() == lowered:
                return os.path.join(icons_dir, filename)
    except OSError:
        return None
    return None


def resolve_icon_path(instance_name, instances_dir=None, icons_dir=None):
    """Return the best icon file path for an instance."""
    cfg = app_config.load_config()
    instances_dir = instances_dir or cfg["paths"]["instances_dir"]
    icons_dir = icons_dir or cfg["paths"]["icons_dir"]
    instance_dir = os.path.join(instances_dir, instance_name)
    meta = _read_instance_cfg(instance_dir)
    icon_path = _icon_path_for_key(meta.get("iconKey"), icons_dir)
    if icon_path:
        return icon_path
    fallback = os.path.join(instance_dir, "minecraft", "icon.png")
    if os.path.isfile(fallback):
        return fallback
    return None


def read_icon_bytes(instance_name, instances_dir=None, icons_dir=None):
    """Return icon bytes or a tiny default PNG."""
    icon_path = resolve_icon_path(instance_name, instances_dir, icons_dir)
    if icon_path and os.path.isfile(icon_path):
        with open(icon_path, "rb") as handle:
            return handle.read()
    return DEFAULT_ICON_BYTES


def discover_local_instances(includes=None, excludes=None, instances_dir=None):
    """List local Prism instances that pass filters, sorted A→Z."""
    cfg = app_config.load_config()
    instances_dir = instances_dir or cfg["paths"]["instances_dir"]
    icons_dir = cfg["paths"]["icons_dir"]
    if not os.path.isdir(instances_dir):
        return []
    rows = []
    for entry in os.listdir(instances_dir):
        instance_dir = os.path.join(instances_dir, entry)
        if not os.path.isdir(instance_dir):
            continue
        if not os.path.isfile(os.path.join(instance_dir, "instance.cfg")):
            continue
        if not app_config.instance_name_matches_filters(entry, includes, excludes):
            continue
        meta = _read_instance_cfg(instance_dir)
        rows.append({
            "name": entry,
            "display_name": meta.get("display_name") or entry,
            "iconKey": meta.get("iconKey", ""),
            "has_icon": resolve_icon_path(entry, instances_dir, icons_dir) is not None,
            "section": "local",
        })
    rows.sort(key=lambda row: row["display_name"].lower())
    return rows


def list_instance_names(instances_dir=None):
    """Return every valid local instance folder name."""
    cfg = app_config.load_config()
    instances_dir = instances_dir or cfg["paths"]["instances_dir"]
    if not os.path.isdir(instances_dir):
        return set()
    names = set()
    for entry in os.listdir(instances_dir):
        instance_dir = os.path.join(instances_dir, entry)
        if os.path.isdir(instance_dir) and os.path.isfile(os.path.join(instance_dir, "instance.cfg")):
            names.add(entry)
    return names
