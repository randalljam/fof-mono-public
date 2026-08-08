"""Collect OpenSpec store state across worktrees."""

import re
from pathlib import Path

### Parsing
def count_tasks(text):
    done = 0
    total = 0
    for line in text.splitlines():
        if re.match(r"^\s*-\s+\[[xX]\]", line):
            done += 1
            total += 1
        elif re.match(r"^\s*-\s+\[ \]", line):
            total += 1
    return total, done
def archived_date(name):
    match = re.match(r"^(\d{4}-\d{2}-\d{2})-", name)
    if match:
        return match.group(1)
    return None

### Gathering
def relative_app_slug(store_path, worktree_path):
    rel = store_path.relative_to(Path(worktree_path) / "apps")
    return "/".join(rel.parts[:-1])
def spec_domains(store_path):
    specs_dir = store_path / "specs"
    if not specs_dir.exists():
        return []
    return sorted(path.name for path in specs_dir.iterdir() if path.is_dir())
def spec_files(store_path):
    specs_dir = store_path / "specs"
    if not specs_dir.exists():
        return []
    files = []
    for path in sorted(specs_dir.iterdir()):
        spec_path = path / "spec.md"
        if path.is_dir() and spec_path.exists():
            files.append({"domain": path.name, "path": str(spec_path.resolve())})
    return files
def change_artifacts(change_path):
    artifacts = []
    for name in ("proposal.md", "design.md", "tasks.md"):
        if (change_path / name).exists():
            artifacts.append(name)
    specs_dir = change_path / "specs"
    if specs_dir.exists():
        for path in sorted(specs_dir.iterdir()):
            if path.is_dir():
                artifacts.append("specs/" + path.name)
    return artifacts
def parse_change(change_path):
    tasks_path = change_path / "tasks.md"
    tasks_total = 0
    tasks_done = 0
    if tasks_path.exists():
        tasks_total, tasks_done = count_tasks(tasks_path.read_text(encoding="utf-8", errors="replace"))
    return {
        "name": change_path.name,
        "path": str(change_path.resolve()),
        "artifacts": change_artifacts(change_path),
        "tasks_total": tasks_total,
        "tasks_done": tasks_done,
    }
def active_changes(store_path):
    changes_dir = store_path / "changes"
    if not changes_dir.exists():
        return []
    changes = []
    for path in sorted(changes_dir.iterdir()):
        if path.is_dir() and path.name != "archive":
            changes.append(parse_change(path))
    return changes
def archived_changes(store_path):
    archive_dir = store_path / "changes/archive"
    if not archive_dir.exists():
        return []
    return [{"name": path.name, "date": archived_date(path.name), "path": str(path.resolve())} for path in sorted(archive_dir.iterdir()) if path.is_dir()]
def find_openspec_stores(worktree_path):
    root = Path(worktree_path)
    stores = set(root.glob("apps/*/openspec"))
    stores.update(root.glob("apps/*/*/openspec"))
    return sorted(path for path in stores if path.is_dir())
def collect_specs(repo_root, worktrees=None):
    items = []
    for worktree in worktrees or []:
        if worktree.get("missing"):
            continue
        path = worktree.get("path")
        if not path or not Path(path).exists():
            continue
        for store in find_openspec_stores(path):
            items.append({
                "worktree": path,
                "branch": worktree.get("branch"),
                "app": relative_app_slug(store, path),
                "store_path": str(store),
                "spec_domains": spec_domains(store),
                "spec_files": spec_files(store),
                "changes": active_changes(store),
                "archived": archived_changes(store),
            })
    return items
