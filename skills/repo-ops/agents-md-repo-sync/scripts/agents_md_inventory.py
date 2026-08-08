#!/usr/bin/env python3
"""Read-only inventory of root AGENTS.md across origin/main and branch tips.

Usage:
    .venv/bin/python3 skills/repo-ops/agents-md-repo-sync/scripts/agents_md_inventory.py
    ... --no-fetch
    ... --branches feature/foo,feature/bar
"""
import argparse
import hashlib
import subprocess
import sys

AGENTS_PATH = "AGENTS.md"
SKIP_REMOTE_NAMES = {"main", "HEAD", "origin"}

### Helpers: pure
def short_sha256(text):
    """Return the first 12 hex chars of SHA-256 over UTF-8 text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
def classify_agents_presence(main_text, branch_text):
    """Classify root AGENTS.md relationship between main and a branch tip.

    Returns one of: missing-both, missing-on-main, missing-on-branch, match,
    branch-only, main-only, diverged.
    """
    main_missing = main_text is None
    branch_missing = branch_text is None
    if main_missing and branch_missing:
        return "missing-both"
    if main_missing:
        return "missing-on-main"
    if branch_missing:
        return "missing-on-branch"
    if main_text == branch_text:
        return "match"
    # Presence of both with different content: caller may refine with ancestry,
    # but for tip-vs-tip content we only know they diverge.
    return "diverged"
def refine_classification(kind, main_blob_in_branch_history, branch_blob_in_main_history):
    """Refine a tip-vs-tip 'diverged' result using blob ancestry hints.

    main_blob_in_branch_history: True if the current main AGENTS.md blob is an
    ancestor blob reachable from the branch tip history for that path (approx:
    branch tip's merge-base..branch never replaced away from an older main, etc.).
    Practical tip-only refinement used by the CLI:
      - branch_only: branch differs and main's text is not equal; use when the
        branch tip content does not appear on main and main's content appears
        in the branch's history (branch advanced the file).
      - main_only: main differs and branch still has an older blob that main
        already moved past.
    If ancestry hints are unknown (None), keep 'diverged'.
    """
    if kind != "diverged":
        return kind
    if main_blob_in_branch_history is None or branch_blob_in_main_history is None:
        return "diverged"
    if main_blob_in_branch_history and not branch_blob_in_main_history:
        return "branch-only"
    if branch_blob_in_main_history and not main_blob_in_branch_history:
        return "main-only"
    return "diverged"
def default_candidate_branches(remote_names):
    """Return every remote branch tip except main/HEAD and harness scratch refs."""
    out = []
    for name in remote_names:
        if name in SKIP_REMOTE_NAMES:
            continue
        if name.startswith("claude/"):
            continue
        out.append(name)
    return sorted(set(out))

### Helpers: git
def _git(args, cwd=None):
    """Run git; return (returncode, stdout, stderr) stripped."""
    proc = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=cwd)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
def _repo_root():
    """Return the git toplevel path or None."""
    rc, out, _ = _git(["rev-parse", "--show-toplevel"])
    return out if rc == 0 else None
def _remote_branch_names():
    """Return origin branch short names without the origin/ prefix."""
    rc, out, err = _git(["for-each-ref", "--format=%(refname:short)", "refs/remotes/origin"])
    if rc != 0:
        raise RuntimeError(err or "failed to list remote branches")
    names = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.endswith("/HEAD"):
            continue
        names.append(line[len("origin/"):] if line.startswith("origin/") else line)
    return names
def _show_file(ref, path):
    """Return file text at ref:path, or None if missing."""
    rc, out, err = _git(["show", f"{ref}:{path}"])
    if rc != 0:
        if "does not exist" in err or "exists on disk" in err or "Path" in err:
            return None
        # Missing path often yields "fatal: path 'X' does not exist in 'Y'"
        if rc != 0 and ("does not exist" in err or err.startswith("fatal:")):
            return None
        return None
    return out
def _merge_base(a, b):
    """Return merge-base SHA or None."""
    rc, out, _ = _git(["merge-base", a, b])
    return out if rc == 0 and out else None
def _commits_touching(base, tip, path):
    """Return oneline commits in base..tip that touched path."""
    if not base:
        return []
    rc, out, _ = _git(["log", "--oneline", f"{base}..{tip}", "--", path])
    if rc != 0 or not out:
        return []
    return out.splitlines()
def _blob_appears_in_range(start, end, path, needle_text):
    """True if any commit in start..end (inclusive end via end's blob walk) has needle.

    Practical check: compare tip blobs along log for path; also compare start blob.
    """
    if needle_text is None:
        return False
    needle_hash = short_sha256(needle_text)
    for ref in (start, end):
        if not ref:
            continue
        text = _show_file(ref, path)
        if text is not None and short_sha256(text) == needle_hash:
            return True
    if not start:
        return False
    rc, out, _ = _git(["log", "--format=%H", f"{start}..{end}", "--", path])
    if rc != 0 or not out:
        return False
    for sha in out.splitlines():
        text = _show_file(sha.strip(), path)
        if text is not None and short_sha256(text) == needle_hash:
            return True
    return False

### Report
def inventory_rows(main_ref, branch_refs, path=AGENTS_PATH):
    """Build inventory row dicts for main + each branch ref.

    branch_refs: list of (display_name, git_ref) e.g. ("feature/foo", "origin/feature/foo").
    """
    main_text = _show_file(main_ref, path)
    rows = [{
        "name": "main",
        "ref": main_ref,
        "exists": main_text is not None,
        "sha12": short_sha256(main_text) if main_text is not None else "-",
        "class": "baseline",
        "commits": [],
    }]
    for name, ref in branch_refs:
        branch_text = _show_file(ref, path)
        kind = classify_agents_presence(main_text, branch_text)
        base = _merge_base(main_ref, ref)
        if kind == "diverged":
            main_in_branch = _blob_appears_in_range(base, ref, path, main_text)
            branch_in_main = _blob_appears_in_range(base, main_ref, path, branch_text)
            kind = refine_classification(kind, main_in_branch, branch_in_main)
        rows.append({
            "name": name,
            "ref": ref,
            "exists": branch_text is not None,
            "sha12": short_sha256(branch_text) if branch_text is not None else "-",
            "class": kind,
            "commits": _commits_touching(base, ref, path),
            "merge_base": base or "-",
        })
    return rows
def print_report(rows):
    """Print a human-readable inventory report."""
    print("=== AGENTS.md repo sync inventory (READ-ONLY) ===")
    print(f"path: {AGENTS_PATH}")
    print()
    print(f"{'branch':<42} {'sha12':<14} {'class':<16} commits-since-base")
    print("-" * 100)
    for row in rows:
        commits = row.get("commits") or []
        commit_note = f"{len(commits)}"
        if commits:
            commit_note += f" (latest: {commits[0]})"
        print(f"{row['name']:<42} {row['sha12']:<14} {row['class']:<16} {commit_note}")
    print()
    print("class legend: match | branch-only | main-only | diverged | missing-* | baseline")
    print("Next: classify branch-only/diverged diffs into promote vs demote-to-scoped (see skill README).")

### CLI
def main(argv=None):
    """CLI entry: fetch (optional), inventory, print."""
    ap = argparse.ArgumentParser(description="Inventory root AGENTS.md across branch tips.")
    ap.add_argument("--no-fetch", action="store_true", help="skip git fetch")
    ap.add_argument("--branches", default="",
                    help="comma-separated branch names (without origin/). Default: active convention branches")
    args = ap.parse_args(argv)

    root = _repo_root()
    if not root:
        print("ERROR: not inside a git repository", file=sys.stderr)
        return 2

    if not args.no_fetch:
        rc, _, err = _git(["fetch", "origin", "--prune"])
        if rc != 0:
            print(f"WARNING: git fetch failed: {err}", file=sys.stderr)

    rc, _, err = _git(["rev-parse", "--verify", "--quiet", "origin/main"])
    if rc != 0:
        print("ERROR: origin/main not found; fetch or set upstream", file=sys.stderr)
        return 2

    if args.branches.strip():
        names = [b.strip() for b in args.branches.split(",") if b.strip()]
    else:
        names = default_candidate_branches(_remote_branch_names())

    branch_refs = []
    for name in names:
        ref = f"origin/{name}"
        rc, _, _ = _git(["rev-parse", "--verify", "--quiet", ref])
        if rc != 0:
            print(f"WARNING: missing {ref}; skipping", file=sys.stderr)
            continue
        branch_refs.append((name, ref))

    rows = inventory_rows("origin/main", branch_refs)
    print_report(rows)
    return 0

if __name__ == "__main__":
    sys.exit(main())
