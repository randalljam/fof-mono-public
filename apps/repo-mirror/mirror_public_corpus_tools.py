"""
Copy newer/changed files from this repo (corpus-tools) into a sibling clone of
public-corpus-tools. Only relative paths that already exist in the public repo are
considered; nothing is added or removed in the public tree.

This file lives under apps/repo-mirror/; the private repo root
(corpus-tools) is two levels above this directory. Expects a local clone at
../public-corpus-tools next to that repository root (same parent folder as corpus-tools).

Run from the corpus-tools repo root (uses the project .venv):

    .venv/bin/python3 apps/repo-mirror/mirror_public_corpus_tools.py

Each copy is counted: a file is only copied when private and public content differ
(byte compare). After a run reports 0 copies, overlapping files already matched; Git
may still show many modified files versus the last commit if those copies happened in
an earlier run and you have not committed, or if you are looking at a different clone
than Public (target) above.
"""
import filecmp
import os
import shutil
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRIVATE_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
PUBLIC_ROOT = os.path.normpath(os.path.join(PRIVATE_ROOT, "..", "public-corpus-tools"))
LOG_PATH = os.path.join(SCRIPT_DIR, "public_corpus_tools_files_log.md")
TARGET_IGNORE_DIRS = {".git", ".vscode", ".venv", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache"}

### Helpers
def _is_junk_file(filename):
    """
    Return True if the file should be skipped when walking the public tree.

    :param filename: str, basename of the file.
    :return skip: bool, True to skip.
    """
    if filename == ".DS_Store":
        return True
    return False
def collect_public_files(public_root):
    """
    Walk the public repo and collect relative paths to files.

    :param public_root: str, absolute path to the public clone root.
    :return files: dict, relative path -> absolute path in public repo.
    """
    files = {}
    for dirpath, dirnames, filenames in os.walk(public_root):
        dirnames[:] = [d for d in dirnames if d not in TARGET_IGNORE_DIRS]
        rel_dir = os.path.relpath(dirpath, public_root)
        if rel_dir == ".":
            rel_dir = ""
        for filename in filenames:
            if _is_junk_file(filename):
                continue
            rel_path = os.path.join(rel_dir, filename) if rel_dir else filename
            files[rel_path] = os.path.join(dirpath, filename)
    return files
def sync_overlapping_paths(public_files):
    """
    For each file in the public tree, if the same relative path exists in the
    private repo and differs, copy from private to public.

    :param public_files: dict, relative path -> absolute path in public repo.
    :return result: tuple of (changes dict, stats dict). changes has keys
        'added', 'updated', 'deleted'. stats has 'public_total', 'only_in_public',
        'overlap', 'identical' (overlap minus copied).
    """
    updated = []
    only_in_public = 0
    for rel_path, pub_abs in sorted(public_files.items()):
        priv_abs = os.path.join(PRIVATE_ROOT, rel_path)
        if not os.path.isfile(priv_abs):
            only_in_public += 1
            continue
        if not filecmp.cmp(priv_abs, pub_abs, shallow=False):
            os.makedirs(os.path.dirname(pub_abs), exist_ok=True)
            shutil.copy2(priv_abs, pub_abs)
            updated.append(rel_path.replace("\\", "/"))
    overlap = len(public_files) - only_in_public
    identical = overlap - len(updated)
    stats = {
        "public_total": len(public_files),
        "only_in_public": only_in_public,
        "overlap": overlap,
        "identical": identical,
    }
    return {"added": [], "updated": updated, "deleted": []}, stats
def write_log(changes):
    """
    Prepend a timestamped sync summary to the log file (newest entries first).

    :param changes: dict with 'added', 'updated', 'deleted' lists of relative paths.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"# === {timestamp}  added: {len(changes['added'])}  updated: {len(changes['updated'])}  deleted: {len(changes['deleted'])} ==="
    lines = [header]
    for p in changes["added"]:
        lines.append(f"+ {p}")
    for p in changes["updated"]:
        lines.append(f"~ {p}")
    for p in changes["deleted"]:
        lines.append(f"- {p}")
    lines.append("")
    new_entry = "\n".join(lines) + "\n"
    existing = ""
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r") as f:
            existing = f.read()
    with open(LOG_PATH, "w") as f:
        f.write(new_entry + existing)
def main():
    """
    Run overlap-only sync from private repo into ../public-corpus-tools and append the log.
    """
    if not os.path.isdir(PUBLIC_ROOT):
        print(f"ERROR: public clone not found at {PUBLIC_ROOT}")
        print("Clone https://github.com/FocusOnFoundationsNonprofit/public-corpus-tools.git next to this repo.")
        return
    print(f"Private (source): {PRIVATE_ROOT}")
    print(f"Public (target):    {PUBLIC_ROOT}")
    print()
    public_files = collect_public_files(PUBLIC_ROOT)
    changes, stats = sync_overlapping_paths(public_files)
    write_log(changes)
    n = len(changes["updated"])
    print(
        f"Scanned {stats['public_total']} file(s) in the public clone. "
        f"{stats['overlap']} path(s) also exist in private; "
        f"{stats['only_in_public']} path(s) are only in public (skipped)."
    )
    if stats["overlap"] == 0:
        print("No overlapping paths to compare (nothing exists in both trees).")
    elif n == 0:
        print(
            f"This run copied 0 files: all {stats['identical']} overlapping file(s) "
            "already match private (byte-identical) before this run started."
        )
        print(
            "If your Git / Source Control view still lists many changes, that is usually "
            "files differing from the last commit (for example after an earlier mirror). "
            "Confirm the open folder matches Public (target) above."
        )
    else:
        print(
            f"Summary: {n} file(s) copied from private this run; "
            f"{stats['identical']} overlapping file(s) unchanged (already matched)."
        )
        print()
        print("Copied this run (same paths as in the log entry):")
        for p in changes["updated"]:
            print(f"  ~ {p}")
    print()
    print(f"Done. {n} file(s) copied this run.")
    print(f"Log: {LOG_PATH}")
if __name__ == "__main__":
    main()
