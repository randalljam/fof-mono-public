#!/usr/bin/env python3
"""Check and repair local-only file mounts across git worktrees."""

import argparse
import fnmatch
import hashlib
import os
import shutil
import subprocess
from datetime import datetime

DEFAULT_LOCAL_ROOT = "/Users/randytrue/Documents/Code/_LOCAL_FILES/fof-mono"
DISPOSABLE_PATTERNS = [
    ".git/*",
    ".DS_Store",
    "*.DS_Store",
    ".env",
    ".env.*",
    ".venv",
    ".venv/*",
    "node_modules/*",
    "*/node_modules/*",
    "__pycache__/*",
    "*.pyc",
    ".pytest_cache/*",
    ".mypy_cache/*",
    ".ruff_cache/*",
    "test-results/*",
    "playwright-report/*",
    "dist/*",
    "*/dist/*",
    "build/*",
    "*/build/*",
    "tmp/*",
    "temp/*",
    "cache/*",
    "agents/*/.hermes_sync_state.json",
    "apps/games/arnis-tile-cache/*",
    "apps/games/poly-files/*",
    "*/.gradle/*",
    "apps/minecraft/*/.gradle/*",
    "apps/minecraft/*/*/.gradle/*",
    "apps/minecraft/*/*/*/.gradle/*",
    "apps/minecraft/*/*/*/*/.gradle/*",
]

### Helpers: command execution
def run(cmd, cwd=None, check=True):
    """Run a command and return stdout."""
    proc = subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise SystemExit(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr}")
    return proc.stdout
def repo_root_from_script():
    """Return the repo root inferred from this script path."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def relpath(path, root):
    """Return path relative to root with forward slashes."""
    return os.path.relpath(path, root).replace(os.sep, "/")

### Helpers: config
def read_mounts(mounts_file):
    """Read repo-relative mount points from a text config file."""
    mounts = []
    with open(mounts_file, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            mounts.append(line.strip("/"))
    return mounts
def parse_worktrees(repo_root):
    """Return git worktree paths for the repo."""
    output = run(["git", "-C", repo_root, "worktree", "list", "--porcelain"])
    paths = []
    for line in output.splitlines():
        if line.startswith("worktree "):
            paths.append(line.split(" ", 1)[1])
    return paths
def path_is_under_mount(path, mounts):
    """Return true when a repo-relative path is under a configured mount."""
    path = path.strip("/")
    for mount in mounts:
        mount = mount.strip("/")
        if path == mount or path.startswith(mount + "/"):
            return True
    return False
def path_is_disposable(path):
    """Return true for ignored paths that are expected disposable noise."""
    path = path.strip("/")
    for pattern in DISPOSABLE_PATTERNS:
        if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern):
            return True
    return False

### Helpers: filesystem
def sha256_file(file_path):
    """Return sha256 for a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
def iter_real_files(root):
    """Yield file paths under a real directory, skipping .DS_Store."""
    if not os.path.isdir(root):
        return
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if filename == ".DS_Store":
                continue
            yield os.path.join(dirpath, filename)
def is_empty_tree(path):
    """Return true when a directory tree has no non-.DS_Store files."""
    if not os.path.isdir(path):
        return False
    for _ in iter_real_files(path):
        return False
    return True
def ensure_parent(path):
    """Create the parent directory for path."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
def copy_tree_contents(src, dst):
    """Copy directory contents, excluding .DS_Store."""
    os.makedirs(dst, exist_ok=True)
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        rel = os.path.relpath(dirpath, src)
        dst_dir = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(dst_dir, exist_ok=True)
        for filename in filenames:
            if filename == ".DS_Store":
                continue
            shutil.copy2(os.path.join(dirpath, filename), os.path.join(dst_dir, filename))
def backup_real_path(src, backup_root, worktree_path, mount):
    """Copy a real path to the sync backup area."""
    wt_name = os.path.basename(worktree_path.rstrip(os.sep)) or "worktree"
    backup_path = os.path.join(backup_root, wt_name, mount)
    if os.path.exists(backup_path):
        shutil.rmtree(backup_path)
    ensure_parent(backup_path)
    copy_tree_contents(src, backup_path)
    return backup_path

### Checks: mounts
def compare_real_dir_to_target(src, target):
    """Return conflict rows for files in src that differ from target."""
    conflicts = []
    for src_file in iter_real_files(src):
        rel = os.path.relpath(src_file, src)
        target_file = os.path.join(target, rel)
        if not os.path.exists(target_file):
            continue
        if not os.path.isfile(target_file):
            conflicts.append((rel, "target is not a regular file"))
            continue
        if sha256_file(src_file) != sha256_file(target_file):
            conflicts.append((rel, "sha256 differs"))
    return conflicts
def check_mount(worktree, local_root, mount, apply, backup_root):
    """Check one mount point and optionally repair it."""
    link_path = os.path.join(worktree, mount)
    target_path = os.path.join(local_root, mount)
    rows = []
    if os.path.islink(link_path):
        current = os.readlink(link_path)
        if current == target_path:
            rows.append(("ok", mount, f"linked -> {target_path}"))
            return rows
        rows.append(("fix", mount, f"relink from {current} -> {target_path}"))
        if apply:
            os.unlink(link_path)
            os.symlink(target_path, link_path)
        return rows
    if not os.path.exists(link_path):
        rows.append(("fix", mount, f"missing; link -> {target_path}"))
        if apply:
            os.makedirs(target_path, exist_ok=True)
            ensure_parent(link_path)
            os.symlink(target_path, link_path)
        return rows
    if os.path.isdir(link_path):
        conflicts = compare_real_dir_to_target(link_path, target_path)
        if conflicts:
            rows.append(("block", mount, f"real directory has {len(conflicts)} conflicting file(s)"))
            for rel, reason in conflicts[:10]:
                rows.append(("detail", mount, f"{rel}: {reason}"))
            return rows
        action = "empty real directory tree" if is_empty_tree(link_path) else "real directory with only new files"
        rows.append(("fix", mount, f"{action}; migrate then link -> {target_path}"))
        if apply:
            os.makedirs(target_path, exist_ok=True)
            backup_path = backup_real_path(link_path, backup_root, worktree, mount)
            copy_tree_contents(link_path, target_path)
            shutil.rmtree(link_path)
            os.symlink(target_path, link_path)
            rows.append(("backup", mount, f"copied original to {backup_path}"))
        return rows
    rows.append(("block", mount, "path exists but is not a directory or symlink"))
    return rows
def check_all_mounts(worktrees, local_root, mounts, apply):
    """Check all configured mounts across worktrees."""
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_root = os.path.join(local_root, "_sync-backups", stamp)
    all_rows = []
    for worktree in worktrees:
        all_rows.append(("worktree", "", worktree))
        for mount in mounts:
            all_rows.extend(check_mount(worktree, local_root, mount, apply, backup_root))
    return all_rows

### Checks: ignored files
def ignored_files(worktree):
    """Return ignored untracked files known to git."""
    output = run(["git", "-C", worktree, "ls-files", "--others", "--ignored", "--exclude-standard", "-z"])
    return [item for item in output.split("\0") if item]
def check_ignored_outside_mounts(worktrees, mounts, limit):
    """Return ignored files outside configured mounts, excluding disposable noise."""
    rows = []
    for worktree in worktrees:
        found = []
        for path in ignored_files(worktree):
            if path_is_under_mount(path, mounts) or path_is_disposable(path):
                continue
            found.append(path)
        rows.append(("worktree", "", worktree))
        if not found:
            rows.append(("ok", "ignored", "no ignored files outside configured mounts"))
            continue
        rows.append(("warn", "ignored", f"{len(found)} ignored file(s) outside configured mounts"))
        for path in found[:limit]:
            rows.append(("detail", "ignored", path))
        if len(found) > limit:
            rows.append(("detail", "ignored", f"... {len(found) - limit} more"))
    return rows

### Output
def print_rows(rows):
    """Print check rows."""
    failed = False
    for kind, mount, message in rows:
        if kind == "worktree":
            print(f"\n## {message}")
            continue
        label = kind.upper()
        prefix = f"{label}: {mount}" if mount else label
        print(f"{prefix}: {message}")
        if kind == "block":
            failed = True
    return failed
def main():
    """CLI entry point."""
    repo_root = repo_root_from_script()
    parser = argparse.ArgumentParser(description="Check/sync fof-mono local file mounts.")
    parser.add_argument("--repo-root", default=repo_root)
    parser.add_argument("--local-root", default=os.environ.get("FOF_MONO_LOCAL_FILES_ROOT", DEFAULT_LOCAL_ROOT))
    parser.add_argument("--mounts-file", default=os.path.join(repo_root, "scripts", "local_files_mounts.txt"))
    parser.add_argument("--worktree", action="append", help="Worktree to check; repeatable. Defaults to all worktrees.")
    parser.add_argument("--apply", action="store_true", help="Apply safe repairs/migrations. Default is dry-run.")
    parser.add_argument("--skip-ignored-scan", action="store_true", help="Skip ignored-file report outside mounts.")
    parser.add_argument("--ignored-limit", type=int, default=25)
    args = parser.parse_args()
    mounts = read_mounts(args.mounts_file)
    worktrees = args.worktree or parse_worktrees(args.repo_root)
    print("=== local files consistency check ===")
    print(f"mode:       {'apply' if args.apply else 'dry-run'}")
    print(f"repo root:  {args.repo_root}")
    print(f"local root: {args.local_root}")
    print(f"mounts:     {', '.join(mounts)}")
    print(f"worktrees:  {len(worktrees)}")
    rows = check_all_mounts(worktrees, args.local_root, mounts, args.apply)
    blocked = print_rows(rows)
    if not args.skip_ignored_scan:
        print("\n=== ignored files outside mounts ===")
        blocked = print_rows(check_ignored_outside_mounts(worktrees, mounts, args.ignored_limit)) or blocked
    if blocked:
        raise SystemExit(2)
if __name__ == "__main__":
    main()
