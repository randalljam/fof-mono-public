#!/usr/bin/env python3
"""Mission-closeout fact gatherer (READ-ONLY).

Collects the facts an end-of-session approval packet needs and prints a packet
skeleton for the agent to fill in against real tool output. It changes nothing:
no commit, push, test run, or branch switch. The agent runs the tests and fills
the packet; this script just assembles the ground truth to fill it from.

Usage:
    .venv/bin/python3 skills/repo-ops/mission-closeout/scripts/closeout_summary.py
    ... --parent origin/main    # override the comparison base (default: origin/main)
"""
import argparse
import subprocess

### Helpers: git
def _git(args):
    """Run a git command; return (returncode, stdout, stderr) all stripped."""
    proc = subprocess.run(["git"] + args, capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
def _current_branch():
    """Return current branch name."""
    _, out, _ = _git(["rev-parse", "--abbrev-ref", "HEAD"])
    return out
def _distance(a, b):
    """Number of commits in a..b, or None."""
    rc, out, _ = _git(["rev-list", "--count", f"{a}..{b}"])
    try:
        return int(out) if rc == 0 else None
    except ValueError:
        return None

### Logic
def _resolve_parent(override):
    """Pick the comparison base: explicit override, else origin/main."""
    if override:
        return override, "override"
    return "origin/main", "default"
def _print_header(title):
    """Print a section header."""
    print(f"\n=== {title} ===")
def main():
    """Assemble closeout facts and print the approval-packet skeleton."""
    ap = argparse.ArgumentParser(description="Read-only mission-closeout fact gatherer.")
    ap.add_argument("--parent", default=None, help="comparison base (default: origin/main)")
    args = ap.parse_args()

    rc, _, err = _git(["rev-parse", "--show-toplevel"])
    if rc != 0:
        print("Not inside a git repository.")
        print(err)
        return 2

    current = _current_branch()
    parent, parent_reason = _resolve_parent(args.parent)

    _print_header("Branch & push state")
    print("Branch:", current)
    _, upstream, _ = _git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    if upstream:
        unpushed = _distance(upstream, "HEAD")
        print(f"Upstream: {upstream} ({unpushed} local commit(s) not yet pushed)")
    else:
        print("Upstream: none set (branch not published).")
    print(f"Comparison base: {parent}  ({parent_reason})")

    _print_header(f"Commits on this branch since {parent}")
    _, commits, _ = _git(["log", "--oneline", f"{parent}..HEAD"])
    print(commits or "(none)")

    _print_header(f"Diffstat since {parent}")
    _, stat, _ = _git(["diff", "--stat", f"{parent}...HEAD"])
    print(stat or "(no differences)")

    _print_header("Uncommitted changes (working tree)")
    _, dirty, _ = _git(["status", "--short"])
    if dirty:
        print(dirty)
        print("\nWARNING: uncommitted changes present. Commit or explain them before closing out.")
    else:
        print("(clean working tree)")

    _print_header("Files changed, by top-level area")
    _, names, _ = _git(["diff", "--name-only", f"{parent}...HEAD"])
    areas = {}
    for path in names.splitlines():
        top = path.split("/", 1)[0] if "/" in path else path
        areas[top] = areas.get(top, 0) + 1
    for top in sorted(areas):
        print(f"  {top}: {areas[top]} file(s)")
    if not areas:
        print("  (none)")

    _print_header("APPROVAL PACKET — fill this in against real tool output")
    print("""\
Lead with the outcome. Write for someone who did not watch you work.

What changed (2-4 plain bullets):
  - ...

What I verified (tests RUN with output — not 'should pass'):
  - ...
  # If tests could not run in this harness (e.g. cloud VM), say so explicitly and
  # leave the exact run command for local follow-up.

Risk (what could break; what you deliberately did NOT touch):
  - ...

The one decision for you:
  - [ ] merge? open a PR? approve a follow-up? nothing (branch pushed for review)?
""")

    _print_header("CLOSEOUT CHECKLIST")
    for item in [
        "Every claim above is backed by a tool result from this session (AGENTS.md verification rules).",
        "Tests written + run where testable; failures reported with output, not hidden.",
        "Commits use scoped conventional messages; one logical change per commit.",
        "Compound step: durable lesson learned written back as a rule / skill note / test, if any.",
        "Pushed only the intended branch — never a claude/<random> auto-branch (see session-start-check).",
    ]:
        print("  [ ] " + item)
    print("\n(Read-only — nothing was committed, pushed, tested, or switched by this script.)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
