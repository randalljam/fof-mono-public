#!/usr/bin/env python3
"""Mirror + bundle backup per docs/git/git-history-deletion-RUNBOOK.md §2."""
import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_BACKUP_DIR = Path("/Users/randytrue/Documents/Code/_BACKUP/fof-mono_git-history")
DEFAULT_REPO = Path("/Users/randytrue/Documents/Code/fof-mono")


def run(cmd, cwd=None, check=True):
    print("+", " ".join(cmd))
    r = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if check and r.returncode != 0:
        sys.stderr.write(r.stdout)
        sys.stderr.write(r.stderr)
        raise SystemExit(r.returncode)
    return r


def find_git_common(repo):
    r = run(["git", "rev-parse", "--git-common-dir"], cwd=repo)
    gd = Path(r.stdout.strip())
    if not gd.is_absolute():
        gd = (Path(repo) / gd).resolve()
    return gd


def backup_repo(repo, backup_dir, stamp=None):
    repo = Path(repo).resolve()
    if stamp is None:
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    mirror = backup_dir / f"fof-mono-backup-{stamp}.git"
    bundle = backup_dir / f"fof-mono-backup-{stamp}.bundle"
    if mirror.exists() or bundle.exists():
        raise SystemExit(f"backup artifacts already exist for stamp {stamp}")
    gd = find_git_common(repo)
    run(["git", "clone", "--mirror", str(gd), str(mirror)])
    run(["git", "bundle", "create", str(bundle), "--all"], cwd=mirror)
    run(["git", "bundle", "verify", str(bundle)])
    refs = run(["git", "show-ref"], cwd=mirror).stdout.strip().splitlines()
    print(f"BACKUP_STAMP={stamp}")
    print(f"MIRROR={mirror}")
    print(f"BUNDLE={bundle}")
    print(f"REFS={len(refs)}")
    return {"stamp": stamp, "mirror": mirror, "bundle": bundle, "ref_count": len(refs)}


def main():
    p = argparse.ArgumentParser(description="Create mirror + bundle git history backup")
    p.add_argument("--repo", default=str(DEFAULT_REPO))
    p.add_argument("--backup-dir", default=str(DEFAULT_BACKUP_DIR))
    p.add_argument("--stamp", default=None)
    args = p.parse_args()
    backup_repo(args.repo, args.backup_dir, args.stamp)


if __name__ == "__main__":
    main()
