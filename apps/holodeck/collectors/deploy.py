"""Collect deploy surface facts."""

import json
import re
import tomllib
from pathlib import Path

import yaml

### Parsing
def parse_fly_toml(text):
    data = tomllib.loads(text)
    return data.get("app")
def parse_chalice_config(text):
    data = json.loads(text)
    return {"name": data.get("app_name"), "stages": sorted((data.get("stages") or {}).keys())}
def parse_registry_yaml(text):
    loaded = yaml.safe_load(text) or {}
    return loaded.get("apps") or []
def normalize_registry_deploy(app_slug, deploy_entry):
    kind = deploy_entry.get("target") or deploy_entry.get("kind")
    name = deploy_entry.get("name") or app_slug
    return {
        "surface": kind + ":" + name if kind and name else name,
        "kind": kind,
        "app_slug": app_slug,
        "name": name,
        "command": deploy_entry.get("command"),
        "url": deploy_entry.get("url"),
        "config_path": deploy_entry.get("config_path"),
        "last_deploy": deploy_entry.get("last_deploy"),
    }
def parse_chalice_last_deploy(log_text, app_name):
    if not log_text or not app_name:
        return None
    found = None
    date_pattern = re.compile(r"\b(\d{4}-\d{2}-\d{2}(?:[ T_]\d{2}:?\d{2}(?::?\d{2})?)?)\b")
    for line in log_text.splitlines():
        if app_name.lower() not in line.lower():
            continue
        match = date_pattern.search(line)
        if match:
            found = match.group(1)
    return found

### Discovery
def depth_ok(path, root, max_parts):
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    return len(rel.parts) <= max_parts
def app_slug_for_apps_config(path, repo_root):
    rel_parent = path.parent.parent.relative_to(Path(repo_root) / "apps")
    return "/".join(rel_parent.parts)
def registry_deploys(repo_root):
    path = Path(repo_root) / "apps/holodeck/registry.yaml"
    if not path.exists():
        return []
    deploys = []
    for app in parse_registry_yaml(path.read_text(encoding="utf-8")):
        slug = app.get("slug")
        for entry in app.get("deploy") or []:
            deploys.append(normalize_registry_deploy(slug, entry))
    return deploys
def fly_deploys(repo_root):
    repo_root = Path(repo_root)
    items = []
    for path in sorted((repo_root / "apps").rglob("fly.toml")):
        if not depth_ok(path, repo_root / "apps", 5):
            continue
        name = parse_fly_toml(path.read_text(encoding="utf-8", errors="replace"))
        if not name:
            continue
        slug = "/".join(path.parent.relative_to(repo_root / "apps").parts)
        items.append({
            "surface": "fly:" + name,
            "kind": "fly",
            "app_slug": slug,
            "name": name,
            "command": None,
            "url": None,
            "config_path": str(path.relative_to(repo_root)),
            "last_deploy": None,
        })
    return items
def chalice_config_paths(repo_root):
    repo_root = Path(repo_root)
    paths = []
    paths.extend(sorted((repo_root / "apps").rglob(".chalice/config.json")))
    shared = repo_root / "web-shared/aws_chalice"
    if shared.exists():
        paths.extend(sorted(shared.glob("*/.chalice/config.json")))
    return paths
def chalice_deploys(repo_root, log_text=None):
    repo_root = Path(repo_root)
    items = []
    for path in chalice_config_paths(repo_root):
        config = parse_chalice_config(path.read_text(encoding="utf-8", errors="replace"))
        name = config.get("name")
        if not name:
            continue
        app_slug = None
        try:
            path.relative_to(repo_root / "apps")
            app_slug = app_slug_for_apps_config(path, repo_root)
        except ValueError:
            app_slug = None
        items.append({
            "surface": "chalice:" + name,
            "kind": "chalice",
            "app_slug": app_slug,
            "name": name,
            "command": None,
            "url": None,
            "config_path": str(path.relative_to(repo_root)),
            "last_deploy": parse_chalice_last_deploy(log_text, name),
        })
    return items
def load_chalice_log(repo_root):
    path = Path(repo_root) / "web-shared/aws_chalice/chalicelib_mirror_deploy_composite_log.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")

### Gathering
def dedupe_deploys(items):
    deduped = {}
    order = []
    for item in items:
        key = (item.get("kind"), item.get("name"))
        if key not in deduped:
            deduped[key] = item
            order.append(key)
    return [deduped[key] for key in order]
def collect_deploy(repo_root):
    log_text = load_chalice_log(repo_root)
    registry = registry_deploys(repo_root)
    auto = fly_deploys(repo_root) + chalice_deploys(repo_root, log_text=log_text)
    return dedupe_deploys(registry + auto)
