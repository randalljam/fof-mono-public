#!/usr/bin/env python3
"""Helper: list commits on a branch with paths for extraction planning."""
import argparse
import subprocess
import sys
from pathlib import Path

DEFAULT_REPO = Path("/Users/randytrue/Documents/Code/fof-mono")


def run_out(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout)
        sys.stderr.write(r.stderr)
        raise SystemExit(r.returncode)
    return r.stdout.strip()


def commit_paths(repo, sha):
    names = run_out(["git", "show", "--name-only", "--format=", sha], cwd=repo).splitlines()
    return [n for n in names if n.strip()]


def main():
    p = argparse.ArgumentParser(description="List branch commits with touched paths")
    p.add_argument("--repo", default=str(DEFAULT_REPO))
    p.add_argument("--base", required=True)
    p.add_argument("--branch", required=True)
    p.add_argument("--scope-prefix", default=None, help="e.g. (math-quiz)")
    p.add_argument("--include-path", action="append", default=[], help="path prefix; commit must touch only these (if set)")
    p.add_argument("--exclude-path", action="append", default=[], help="path prefix; if touched, flag as mixed")
    args = p.parse_args()
    repo = args.repo
    tip = run_out(["git", "rev-parse", args.branch], cwd=repo)
    shas = run_out(["git", "rev-list", "--reverse", f"{args.base}..{tip}"], cwd=repo).splitlines()
    for sha in shas:
        subj = run_out(["git", "log", "-1", "--format=%s", sha], cwd=repo)
        paths = commit_paths(repo, sha)
        tops = sorted({p.split("/")[0] if "/" not in p else "/".join(p.split("/")[:2]) for p in paths})
        scope_ok = (not args.scope_prefix) or (args.scope_prefix in subj)
        mixed = False
        for pref in args.exclude_path:
            if any(p.startswith(pref) for p in paths):
                mixed = True
        if args.include_path:
            only = all(any(p.startswith(ip) for ip in args.include_path) for p in paths)
            if not only:
                mixed = True
        tag = "EXTRACT" if scope_ok and not mixed else ("MIXED" if mixed else "SKIP")
        print(f"{sha[:7]}\t{tag}\t{subj}")
        for t in tops[:6]:
            print(f"  {t}")
        if len(tops) > 6:
            print(f"  ... +{len(tops)-6} more")


if __name__ == "__main__":
    main()
