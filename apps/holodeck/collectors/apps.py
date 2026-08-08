"""Collect app registry and filesystem facts."""

import subprocess
from pathlib import Path

import yaml

UMBRELLAS = {"minecraft", "family", "games", "qrag", "education", "transcription"}
REGISTRY_FIELDS = {"name", "purpose", "kind", "stage", "spec_stage", "dev_command", "port", "local_url", "test_command", "deploy", "notes", "tags"}

### Parsing
def discover_app_slugs_from_names(first_level, second_level_by_umbrella):
    slugs = set()
    for name in first_level:
        if name in UMBRELLAS:
            children = second_level_by_umbrella.get(name, [])
            if children:
                for child in children:
                    slugs.add(name + "/" + child)
            else:
                slugs.add(name)
        else:
            slugs.add(name)
    return sorted(slugs)
def app_slug_for_path(path, discovered_slugs):
    rel = str(path).replace("\\", "/")
    if rel.startswith("./"):
        rel = rel[2:]
    if not rel.startswith("apps/"):
        return None
    app_rel = rel[len("apps/"):]
    matches = []
    for slug in discovered_slugs:
        if app_rel == slug or app_rel.startswith(slug + "/"):
            matches.append(slug)
    if not matches:
        return None
    return sorted(matches, key=len, reverse=True)[0]
def app_slugs_for_paths(paths, discovered_slugs):
    slugs = set()
    for path in paths:
        slug = app_slug_for_path(path, discovered_slugs)
        if slug:
            slugs.add(slug)
    return sorted(slugs)
def registry_by_slug(registry_apps):
    by_slug = {}
    for item in registry_apps or []:
        slug = item.get("slug")
        if slug:
            by_slug[slug] = item
    return by_slug
def merge_registry_apps(registry_apps, discovered_slugs):
    registry = registry_by_slug(registry_apps)
    all_slugs = sorted(set(discovered_slugs) | set(registry))
    merged = []
    for slug in all_slugs:
        registered = slug in registry
        item = {"slug": slug}
        if registered:
            for key, value in registry[slug].items():
                if key == "slug" or key in REGISTRY_FIELDS:
                    item[key] = value
        item["path"] = "apps/" + slug
        item["registered"] = registered
        merged.append(item)
    return merged
def parse_registry_yaml(text):
    loaded = yaml.safe_load(text) or {}
    return loaded.get("apps") or []

### Filesystem
def discover_app_slugs(apps_dir):
    first_level = []
    second_level = {}
    for child in sorted(Path(apps_dir).iterdir()):
        if child.is_dir():
            first_level.append(child.name)
            if child.name in UMBRELLAS:
                second_level[child.name] = [grand.name for grand in sorted(child.iterdir()) if grand.is_dir()]
    return discover_app_slugs_from_names(first_level, second_level)
def has_readme(app_path):
    if not app_path.exists():
        return False
    for child in app_path.iterdir():
        if child.is_file() and child.name.lower().startswith("readme") and child.suffix.lower() == ".md":
            return True
    return False
def has_tests(app_path):
    if not app_path.exists():
        return False
    for path in app_path.rglob("*"):
        try:
            rel = path.relative_to(app_path)
        except ValueError:
            continue
        if len(rel.parts) > 3:
            continue
        if path.is_dir() and path.name == "tests":
            return True
        if path.is_file() and (path.name.startswith("test_") and path.suffix == ".py" or path.name.endswith(".test.mjs")):
            return True
    return False
def has_root_html(app_path):
    if not app_path.exists():
        return False
    return any(path.is_file() and path.suffix.lower() == ".html" for path in app_path.iterdir())
def has_root_python(app_path):
    if not app_path.exists():
        return False
    return any(path.is_file() and path.suffix == ".py" for path in app_path.iterdir())
def only_root_markdown(app_path):
    if not app_path.exists():
        return False
    children = list(app_path.iterdir())
    files = [path for path in children if path.is_file()]
    dirs = [path for path in children if path.is_dir()]
    return bool(files) and not dirs and all(path.suffix.lower() == ".md" for path in files)
def infer_app_kind(app_path):
    app_path = Path(app_path)
    if (app_path / ".chalice").is_dir():
        return "chalice"
    if (app_path / "fly.toml").is_file():
        return "web"
    if has_root_html(app_path) or (app_path / "package.json").is_file():
        return "web"
    if has_root_python(app_path):
        return "cli"
    if only_root_markdown(app_path):
        return "docs"
    return "scripts"
def app_flags(app_path):
    return {
        "has_readme": has_readme(app_path),
        "has_tests": has_tests(app_path),
        "has_agents_md": (app_path / "AGENTS.md").exists(),
        "openspec": (app_path / "openspec").is_dir(),
    }

### Git
def run_git(repo_root, args, timeout=15):
    return subprocess.run(
        ["git", "-C", str(repo_root)] + args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
def git_last_commit_date(repo_root, rel_path):
    command = run_git(repo_root, ["log", "-1", "--format=%cI", "--", rel_path])
    if command.returncode == 0 and command.stdout.strip():
        return command.stdout.strip()
    return None
def git_commits_30d(repo_root, rel_path):
    command = run_git(repo_root, ["rev-list", "--count", "--since=30.days", "HEAD", "--", rel_path])
    if command.returncode == 0 and command.stdout.strip().isdigit():
        return int(command.stdout.strip())
    return 0

### Gathering
def collect_apps(repo_root):
    repo_root = Path(repo_root)
    registry_path = repo_root / "apps/holodeck/registry.yaml"
    registry_apps = parse_registry_yaml(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else []
    discovered = discover_app_slugs(repo_root / "apps")
    apps = merge_registry_apps(registry_apps, discovered)
    for item in apps:
        app_path = repo_root / item["path"]
        if not item.get("kind"):
            item["kind"] = infer_app_kind(app_path)
        item.update(app_flags(app_path))
        item["last_commit_date"] = git_last_commit_date(repo_root, item["path"])
        item["commits_30d"] = git_commits_30d(repo_root, item["path"])
    return apps
