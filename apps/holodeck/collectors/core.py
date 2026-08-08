"""Collect shared core module facts."""

import subprocess
from pathlib import Path

### Parsing
def is_decorative(line):
    stripped = line.strip().strip("#").strip()
    if not stripped.strip("=-*~_ "):
        return True
    return stripped.strip("= ").upper().startswith(("START OF FILE", "END OF FILE"))
def clean_description(line):
    line = line.strip()
    if line.startswith("#"):
        return line.lstrip("#").strip() or None
    for quote in ('"""', "'''"):
        if line.startswith(quote):
            rest = line[len(quote):]
            if quote in rest:
                rest = rest.split(quote, 1)[0]
            return rest.strip() or None
    return line.strip() or None
def first_description_from_text(text):
    lines = text.splitlines()[:15]
    in_docstring = False
    for line in lines:
        stripped = line.strip()
        if not stripped or is_decorative(stripped):
            continue
        if stripped.startswith("#"):
            return clean_description(stripped)
        if stripped.startswith('"""') or stripped.startswith("'''"):
            description = clean_description(stripped)
            if description:
                return description
            in_docstring = True
            continue
        if in_docstring:
            return stripped or None
    return None

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
def module_description(path):
    if path.is_dir():
        readme = path / "README.md"
        if readme.exists():
            return first_description_from_text(readme.read_text(encoding="utf-8", errors="replace"))
        return None
    return first_description_from_text(path.read_text(encoding="utf-8", errors="replace"))
def collect_core(repo_root):
    repo_root = Path(repo_root)
    items = []
    for path in sorted((repo_root / "core").glob("*.py")):
        if path.name == "__init__.py":
            continue
        rel_path = "core/" + path.name
        items.append({
            "module": path.stem,
            "description": module_description(path),
            "last_commit_date": git_last_commit_date(repo_root, rel_path),
            "commits_30d": git_commits_30d(repo_root, rel_path),
        })
    cron_path = repo_root / "core/cron"
    if cron_path.exists():
        items.append({
            "module": "cron",
            "description": module_description(cron_path),
            "last_commit_date": git_last_commit_date(repo_root, "core/cron"),
            "commits_30d": git_commits_30d(repo_root, "core/cron"),
        })
    return items
