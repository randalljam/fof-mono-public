#!/usr/bin/env python3
"""Session-start branch-discipline check (READ-ONLY).

Verifies you are on the intended working branch before any commit, per
AGENTS.md -> Branch discipline. Fetches remote-tracking refs (non-destructive)
and reports; it never switches branches, resets, commits, or pushes.

Usage:
    .venv/bin/python3 skills/repo-ops/session-start-check/scripts/session_start_check.py
    ... --no-fetch          # skip the fetch (offline / already fetched)
    ... --max-distance 25   # how far below HEAD to look for the real branch
"""
import argparse
import re
import subprocess

AUTO_BRANCH_RE = re.compile(r"^claude/")
DESCRIPTIVE_PREFIXES = ("feature/", "fix/", "refactor/", "cleanup/", "import/", "export/", "use/")

### Helpers: git
def _git(args):
    """Run a git command; return (returncode, stdout, stderr) all stripped."""
    proc = subprocess.run(["git"] + args, capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
def _current_branch():
    """Return the current branch name, or 'HEAD' when detached."""
    _, out, _ = _git(["rev-parse", "--abbrev-ref", "HEAD"])
    return out
def _remote_branches():
    """Return remote branch short names (origin/foo -> foo), minus HEAD."""
    _, out, _ = _git(["for-each-ref", "--format=%(refname:short)", "refs/remotes/origin"])
    names = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.endswith("/HEAD"):
            continue
        names.append(line[len("origin/"):] if line.startswith("origin/") else line)
    return names
def _local_branches():
    """Return local branch names."""
    _, out, _ = _git(["for-each-ref", "--format=%(refname:short)", "refs/heads"])
    return [l.strip() for l in out.splitlines() if l.strip()]
def _is_ancestor(ancestor, descendant):
    """True if <ancestor> is an ancestor of (or equal to) <descendant>."""
    rc, _, _ = _git(["merge-base", "--is-ancestor", ancestor, descendant])
    return rc == 0
def _distance(ref, head):
    """Number of commits in ref..head; None if unresolvable."""
    rc, out, _ = _git(["rev-list", "--count", f"{ref}..{head}"])
    if rc != 0:
        return None
    try:
        return int(out)
    except ValueError:
        return None

### Logic: classify + find candidates
def _is_descriptive(name):
    """True when the branch name uses a convention prefix (feature/, fix/, ...)."""
    return name.startswith(DESCRIPTIVE_PREFIXES)
def _find_candidates(current, max_distance):
    """Find descriptively-named branches at/just below HEAD (the likely real branch).

    Returns a sorted list of dicts: descriptive branches first, then closest to HEAD.
    """
    seen = set()
    refs = []
    for name in _remote_branches():
        if name in ("main", current) or AUTO_BRANCH_RE.match(name):
            continue
        refs.append(("origin/" + name, name))
    for name in _local_branches():
        if name in ("main", current) or AUTO_BRANCH_RE.match(name) or name in seen:
            continue
        refs.append((name, name))
    candidates = []
    for ref, name in refs:
        if not _is_ancestor(ref, "HEAD"):
            continue
        dist = _distance(ref, "HEAD")
        if dist is None or dist > max_distance:
            continue
        candidates.append({"ref": ref, "name": name, "distance": dist,
                           "descriptive": _is_descriptive(name)})
        seen.add(name)
    candidates.sort(key=lambda c: (not c["descriptive"], c["distance"]))
    return candidates

### Report
def _print_header(title):
    """Print a section header line."""
    print(f"\n=== {title} ===")
def main():
    """Run the read-only session-start check and print a verdict."""
    ap = argparse.ArgumentParser(description="Read-only session-start branch-discipline check.")
    ap.add_argument("--no-fetch", action="store_true", help="skip git fetch")
    ap.add_argument("--max-distance", type=int, default=25,
                    help="max commits below HEAD to search for the real branch")
    args = ap.parse_args()

    rc, root, err = _git(["rev-parse", "--show-toplevel"])
    if rc != 0:
        print("Not inside a git repository.")
        print(err)
        return 2

    if not args.no_fetch:
        _print_header("git fetch origin --prune")
        frc, fout, ferr = _git(["fetch", "origin", "--prune"])
        print(fout or "(no output)")
        if ferr:
            print(ferr)
        if frc != 0:
            print("WARNING: fetch failed — remote state may be stale.")

    current = _current_branch()
    is_auto = bool(AUTO_BRANCH_RE.match(current))

    _print_header("Current branch")
    print(current + ("   [claude/ auto-branch]" if is_auto else ""))
    _, head_line, _ = _git(["log", "-1", "--format=%h · %ad · %an · %s",
                            "--date=format:%Y-%m-%d %H:%M", "HEAD"])
    print("HEAD:", head_line)

    _print_header("Remote branches (origin)")
    remotes = _remote_branches()
    for name in sorted(remotes):
        print("  " + name)

    _print_header("Ancestry vs origin/main")
    mb_rc, mb, _ = _git(["merge-base", "origin/main", "HEAD"])
    if mb_rc != 0 or not mb:
        print("DISCONNECTED — no common ancestor with origin/main. STOP and investigate (possible history rewrite).")
    else:
        ahead = _distance(mb, "HEAD")
        behind = _distance("HEAD", "origin/main")
        print(f"Shared fork-base: {mb[:12]}")
        print(f"HEAD is {ahead} commit(s) ahead of the fork-base.")
        if behind and behind > 0:
            print(f"origin/main is {behind} commit(s) ahead of this branch — branch is behind main (normal; `git merge origin/main` to update).")
        else:
            print("Branch contains all of origin/main (up to date with main).")

    verdict = []
    if is_auto:
        cands = _find_candidates(current, args.max_distance)
        _print_header("Candidate real working branches (this is a claude/ auto-branch)")
        if cands:
            for c in cands[:6]:
                tag = "descriptive" if c["descriptive"] else "non-convention"
                at = "AT HEAD tip" if c["distance"] == 0 else f"{c['distance']} commits below HEAD"
                print(f"  {c['ref']}  ({tag}, {at})")
        else:
            print("  none found within the search window.")
        strong = [c for c in cands if c["descriptive"]]
        verdict.append("STOP — you are on a claude/ auto-branch.")
        verdict.append("Per AGENTS.md, NEVER push a claude/<random> auto-branch or open a PR from it,")
        verdict.append("unless the user has explicitly designated THIS branch as the working branch.")
        if len(strong) == 1:
            verdict.append(f"Likely intended working branch: {strong[0]['ref']}. Confirm with the user, then switch before committing.")
        elif len(strong) > 1:
            verdict.append("Multiple descriptive candidates above — ask the user which branch is the working branch.")
        else:
            verdict.append("No clear descriptive candidate — ask the user which branch to work on. Do not guess.")
    else:
        verdict.append(f"You are on '{current}'.")
        if _is_descriptive(current):
            verdict.append("This uses a convention prefix. Confirm it is the branch the user intends, then proceed.")
        elif current == "main":
            verdict.append("You are on main — do NOT commit here. Create/switch to a feature branch (ask the user).")
        else:
            verdict.append("Non-convention name — confirm it is the intended working branch before committing.")

    _print_header("VERDICT")
    for line in verdict:
        print("  " + line)
    print("\n(Read-only check — no branches were switched, reset, committed, or pushed.)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
