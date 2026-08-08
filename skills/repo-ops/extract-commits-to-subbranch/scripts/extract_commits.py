#!/usr/bin/env python3
"""Extract selected commits to a sub-branch; optionally squash-merge back to parent."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REWORD_DIR = SCRIPT_DIR.parent.parent / "reword-branch-commits" / "scripts"
sys.path.insert(0, str(REWORD_DIR))
from git_history_backup import backup_repo, DEFAULT_REPO
from reword_commits import (
    check_preconditions,
    commit_fields,
    commit_tree,
    run,
    run_out,
)


def parse_commits(spec, repo, branch, base):
    if Path(spec).exists():
        lines = [ln.strip() for ln in Path(spec).read_text().splitlines() if ln.strip() and not ln.startswith("#")]
    else:
        lines = [s.strip() for s in spec.split(",") if s.strip()]
    tip = run_out(["git", "rev-parse", branch], cwd=repo)
    all_shas = run_out(["git", "rev-list", f"{base}..{tip}"], cwd=repo).splitlines()
    full = {}
    for s in all_shas:
        full[s[:7]] = s
    out = []
    for item in lines:
        if len(item) >= 40:
            out.append(item)
        elif item[:7] in full:
            out.append(full[item[:7]])
        else:
            raise SystemExit(f"commit not on branch: {item}")
    return out, all_shas


def cherry_pick_chain(repo, branch, base, commits):
    run(["git", "checkout", "-B", branch, base], cwd=repo)
    for sha in commits:
        ad = run_out(["git", "log", "-1", "--format=%aI", sha], cwd=repo)
        env = {**os.environ, "GIT_COMMITTER_DATE": ad}
        print(f"+ cherry-pick {sha[:7]} (committer date = author date)")
        r = subprocess.run(["git", "cherry-pick", sha], cwd=repo, env=env, text=True, capture_output=True)
        if r.returncode != 0:
            sys.stderr.write(r.stdout)
            sys.stderr.write(r.stderr)
            raise SystemExit(r.returncode)


def rebuild_without(repo, branch, base, drop_set):
    old_tip = run_out(["git", "rev-parse", branch], cwd=repo)
    shas = run_out(["git", "rev-list", "--reverse", f"{base}..{old_tip}"], cwd=repo).splitlines()
    kept = [s for s in shas if s not in drop_set]
    parent = base
    for sha in kept:
        fields = commit_fields(repo, sha)
        new_sha = commit_tree(
            repo,
            fields["tree"],
            [parent],
            fields["author"],
            fields["author_date"],
            fields["committer"],
            fields["committer_date"],
            fields["body"],
        )
        parent = new_sha
    run(["git", "update-ref", f"refs/heads/{branch}", parent], cwd=repo)
    new_tip = parent
    diff = run(["git", "diff", old_tip, new_tip], cwd=repo, check=False).stdout.strip()
    if diff:
        print("NOTE: parent tip tree differs from pre-drop tip until squash-merge restores extracted changes")
    return old_tip, new_tip


def squash_merge_pr(repo, head_branch, base_branch, title, body):
    run(["git", "push", "-u", "origin", head_branch], cwd=repo)
    r = run(
        ["gh", "pr", "create", "--base", base_branch, "--head", head_branch, "--title", title, "--body", body],
        cwd=repo,
    )
    pr_url = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    pr_num = ""
    for part in pr_url.split("/"):
        if part.isdigit():
            pr_num = part
    if not pr_num:
        raise SystemExit(f"could not parse PR number from: {pr_url!r}")
    run(["gh", "pr", "merge", pr_num, "--squash", "--delete-branch"], cwd=repo)
    run(["git", "fetch", "origin", "--prune"], cwd=repo)
    run(["git", "checkout", base_branch], cwd=repo)
    run(["git", "pull", "origin", base_branch], cwd=repo)
    return pr_num, pr_url


def main():
    p = argparse.ArgumentParser(description="Extract commits to sub-branch and squash-merge back")
    p.add_argument("--repo", default=str(DEFAULT_REPO))
    p.add_argument("--source-branch", required=True)
    p.add_argument("--sub-branch", required=True)
    p.add_argument("--parent-base", required=True)
    p.add_argument("--commits", required=True, help="comma SHAs or file path")
    p.add_argument("--backup", action="store_true")
    p.add_argument("--push", action="store_true", help="push sub-branch and rewritten source")
    p.add_argument("--auto", action="store_true", help="skip pause; run squash PR immediately")
    p.add_argument("--squash-pr", action="store_true")
    p.add_argument("--pr-title", default=None)
    p.add_argument("--pr-body", default="Squash-merge extracted commits back to parent branch.")
    p.add_argument("--pre-tip-file", default=None, help="write pre-extraction source tip SHA here")
    p.add_argument("--skip-remote-check", action="store_true")
    args = p.parse_args()
    repo = args.repo
    check_preconditions(repo, args.source_branch, skip_remote=args.skip_remote_check)
    extract_shas, all_shas = parse_commits(args.commits, repo, args.source_branch, args.parent_base)
    drop_set = set(extract_shas)
    pre_tip = run_out(["git", "rev-parse", args.source_branch], cwd=repo)
    if args.pre_tip_file:
        Path(args.pre_tip_file).write_text(pre_tip + "\n")
    if args.backup:
        backup_repo(repo)
    cur = run_out(["git", "branch", "--show-current"], cwd=repo)
    cherry_pick_chain(repo, args.sub_branch, args.parent_base, extract_shas)
    if args.push:
        run(["git", "push", "-u", "origin", args.sub_branch], cwd=repo)
    run(["git", "checkout", args.source_branch], cwd=repo)
    old_tip, new_tip = rebuild_without(repo, args.source_branch, args.parent_base, drop_set)
    print(f"SOURCE_OLD_TIP={old_tip}")
    print(f"SOURCE_NEW_TIP={new_tip}")
    print(f"EXTRACTED={len(extract_shas)} commits on {args.sub_branch}")
    if args.push:
        run(["git", "push", "--force-with-lease", "origin", args.source_branch], cwd=repo)
    if args.pre_tip_file:
        print(f"INVARIANT: after squash, git diff {pre_tip} origin/{args.source_branch} should be empty")
    if not args.auto:
        print("\n=== PAUSE ===")
        print("Inspect git graph. Re-run with --auto --squash-pr to open squash PR into parent.")
        print(f"  git log --oneline --graph {args.parent_base}..{args.source_branch}")
        print(f"  git log --oneline {args.parent_base}..origin/{args.sub_branch}")
        return
    if args.squash_pr:
        title = args.pr_title or f"Extract commits onto {args.sub_branch}"
        pr_num, pr_url = squash_merge_pr(repo, args.sub_branch, args.source_branch, title, args.pr_body)
        post_tip = run_out(["git", "rev-parse", args.source_branch], cwd=repo)
        diff = run(["git", "diff", pre_tip, post_tip], cwd=repo, check=False).stdout.strip()
        if diff:
            raise SystemExit("tree-equality invariant FAILED after squash merge")
        print(f"SQUASH_PR={pr_num} {pr_url}")
        print("INVARIANT_OK tree unchanged at source tip")


if __name__ == "__main__":
    main()
