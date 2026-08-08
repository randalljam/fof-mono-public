#!/usr/bin/env python3
"""Reword commit messages on a branch without changing trees or dates."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from git_history_backup import backup_repo, DEFAULT_REPO


def run(cmd, cwd=None, check=True):
    print("+", " ".join(cmd))
    r = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if check and r.returncode != 0:
        sys.stderr.write(r.stdout)
        sys.stderr.write(r.stderr)
        raise SystemExit(r.returncode)
    return r


def run_out(cmd, cwd=None):
    return run(cmd, cwd=cwd).stdout.strip()


def load_map(path):
    mapping = {}
    full_by_short = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" not in line:
            raise SystemExit(f"map line must be old-sha<TAB>message: {line!r}")
        sha, msg = line.split("\t", 1)
        sha = sha.strip()
        msg = msg.strip()
        if not msg:
            raise SystemExit(f"empty message for {sha}")
        mapping[sha] = msg
        full_by_short[sha[:7]] = sha
    return mapping, full_by_short


def resolve_message(sha, mapping, full_by_short):
    if sha in mapping:
        return mapping[sha]
    short = sha[:7]
    if short in mapping:
        return mapping[short]
    if short in full_by_short and full_by_short[short] in mapping:
        return mapping[full_by_short[short]]
    return None


def check_preconditions(repo, branch, skip_remote=False):
    cur = run_out(["git", "branch", "--show-current"], cwd=repo)
    if cur != branch:
        raise SystemExit(f"expected branch {branch}, on {cur}")
    if branch in ("main", "master"):
        raise SystemExit("refusing to rewrite main")
    dirty = run_out(["git", "status", "--porcelain"], cwd=repo)
    if dirty:
        raise SystemExit("working tree not clean")
    if skip_remote:
        return
    run(["git", "fetch", "origin", "--prune"], cwd=repo)
    local = run_out(["git", "rev-parse", branch], cwd=repo)
    remote = run_out(["git", "rev-parse", f"origin/{branch}"], cwd=repo)
    if local != remote:
        raise SystemExit(f"local {branch} != origin/{branch}")
    wt = run(["git", "worktree", "list"], cwd=repo, check=False)
    hits = []
    for line in wt.stdout.splitlines():
        if f"[{branch}]" in line:
            hits.append(line.strip())
    if len(hits) > 1:
        raise SystemExit(f"branch checked out in multiple worktrees:\n" + "\n".join(hits))


def commit_fields(repo, sha):
    fmt = "%T%n%P%n%an%n%ae%n%at%n%cn%n%ce%n%ct%n%B"
    r = run(["git", "log", "-1", f"--format={fmt}", sha], cwd=repo)
    parts = r.stdout.split("\n", 8)
    if len(parts) < 9:
        raise SystemExit(f"could not read commit {sha}")
    tree, parents, an, ae, at_, cn, ce, ct, body = parts
    parent_list = [p for p in parents.split() if p]
    return {
        "tree": tree.strip(),
        "parents": parent_list,
        "author": f"{an} <{ae}>",
        "author_date": at_.strip(),
        "committer": f"{cn} <{ce}>",
        "committer_date": ct.strip(),
        "body": body.rstrip("\n"),
    }


def lineage_records_in_range(repo, base, branch):
    output = run_out(
        ["git", "log", "--first-parent", "--format=%H%x00%B%x00", f"{base}..{branch}"],
        cwd=repo,
    )
    records = []
    parts = output.split("\x00")
    for idx in range(0, len(parts) - 1, 2):
        sha = parts[idx].strip()
        message = parts[idx + 1]
        if sha and "Record-Type: branch-lineage" in message.splitlines():
            records.append(sha)
    return records


def commit_tree(repo, tree, parents, author, author_date, committer, committer_date, message):
    cmd = ["git", "commit-tree", tree, "-m", message]
    an, ae = author.rsplit(" <", 1)
    ae = ae.rstrip(">")
    cn, ce = committer.rsplit(" <", 1)
    ce = ce.rstrip(">")
    env = {
        **dict(os.environ),
        "GIT_AUTHOR_NAME": an,
        "GIT_AUTHOR_EMAIL": ae,
        "GIT_AUTHOR_DATE": author_date,
        "GIT_COMMITTER_NAME": cn,
        "GIT_COMMITTER_EMAIL": ce,
        "GIT_COMMITTER_DATE": committer_date,
    }
    for p in parents:
        cmd.extend(["-p", p])
    print("+", " ".join(cmd))
    r = subprocess.run(cmd, cwd=repo, text=True, capture_output=True, env=env)
    if r.returncode != 0:
        sys.stderr.write(r.stdout)
        sys.stderr.write(r.stderr)
        raise SystemExit(r.returncode)
    return r.stdout.strip()


def rebuild_branch(repo, branch, base, mapping, full_by_short):
    old_tip = run_out(["git", "rev-parse", branch], cwd=repo)
    shas = run_out(["git", "rev-list", "--reverse", f"{base}..{old_tip}"], cwd=repo).splitlines()
    if not shas:
        raise SystemExit(f"no commits between {base} and {old_tip}")
    parent = base
    new_shas = []
    for sha in shas:
        fields = commit_fields(repo, sha)
        new_msg = resolve_message(sha, mapping, full_by_short)
        if new_msg is None:
            new_msg = fields["body"]
        elif "\n" in fields["body"]:
            rest = fields["body"].split("\n", 1)[1]
            if rest.strip():
                new_msg = new_msg + "\n\n" + rest
        new_sha = commit_tree(
            repo,
            fields["tree"],
            [parent],
            fields["author"],
            fields["author_date"],
            fields["committer"],
            fields["committer_date"],
            new_msg,
        )
        new_shas.append(new_sha)
        parent = new_sha
    run(["git", "update-ref", f"refs/heads/{branch}", parent], cwd=repo)
    new_tip = parent
    if run(["git", "diff", old_tip, new_tip], cwd=repo, check=False).stdout.strip():
        raise SystemExit("tree changed after reword — aborting")
    if len(new_shas) != len(shas):
        raise SystemExit("commit count mismatch")
    print(f"OLD_TIP={old_tip}")
    print(f"NEW_TIP={new_tip}")
    print(f"COMMITS={len(new_shas)}")
    return old_tip, new_tip


def verify_messages(repo, base, mapping, full_by_short):
    shas = run_out(["git", "rev-list", f"{base}..HEAD"], cwd=repo).splitlines()
    for sha in shas:
        subj = run_out(["git", "log", "-1", "--format=%s", sha], cwd=repo)
        expected = resolve_message(sha, mapping, full_by_short)
        if expected and subj != expected.split("\n")[0]:
            raise SystemExit(f"message mismatch {sha[:7]}: got {subj!r} expected {expected.split(chr(10))[0]!r}")


def main():
    p = argparse.ArgumentParser(description="Reword branch commits preserving trees and dates")
    p.add_argument("--repo", default=str(DEFAULT_REPO))
    p.add_argument("--branch", required=True)
    p.add_argument("--base", required=True, help="fork-base (first parent), e.g. merge-base with main")
    p.add_argument("--map", required=True, help="TSV: old-sha<TAB>new subject")
    p.add_argument("--backup", action="store_true")
    p.add_argument("--push", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--skip-remote-check", action="store_true", help="for local test repos without origin")
    args = p.parse_args()
    repo = args.repo
    mapping, full_by_short = load_map(args.map)
    check_preconditions(repo, args.branch, skip_remote=args.skip_remote_check)
    lineage_records = lineage_records_in_range(repo, args.base, args.branch)
    if lineage_records:
        raise SystemExit(
            "refusing to recreate branch-lineage record(s): "
            + ", ".join(lineage_records)
            + "; use the branch-lineage-record rewrite-map and supersession workflow"
        )
    if args.backup:
        backup_repo(repo)
    if args.dry_run:
        print("dry-run: preconditions ok, map loaded", len(mapping), "entries")
        return
    old_tip, new_tip = rebuild_branch(repo, args.branch, args.base, mapping, full_by_short)
    verify_messages(repo, args.base, mapping, full_by_short)
    print("verification: git diff old new is empty")
    if args.push:
        r = run(["git", "push", "--force-with-lease", "origin", args.branch], cwd=repo)
        sys.stdout.write(r.stdout)
        sys.stderr.write(r.stderr)


if __name__ == "__main__":
    main()
