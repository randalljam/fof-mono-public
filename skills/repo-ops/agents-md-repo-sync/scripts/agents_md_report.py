#!/usr/bin/env python3
"""Build / verify / log agents-md-repo-sync run reports.

Usage:
    # Verify all listed tips match origin/main on root AGENTS.md (exit 1 if not)
    .venv/bin/python3 skills/repo-ops/agents-md-repo-sync/scripts/agents_md_report.py verify
    .venv/bin/python3 skills/repo-ops/agents-md-repo-sync/scripts/agents_md_report.py verify \\
        --branches feature/foo,feature/bar

    # Prepend a markdown report entry to the skill-tracked run log
    .venv/bin/python3 skills/repo-ops/agents-md-repo-sync/scripts/agents_md_report.py write-log \\
        --report-file /tmp/agents-md-repo-sync-report.md
"""
import argparse
import os
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from agents_md_inventory import (
    _git,
    _remote_branch_names,
    _repo_root,
    default_candidate_branches,
    inventory_rows,
)

LOG_REL = "skills/repo-ops/agents-md-repo-sync/run-log.md"
PT = ZoneInfo("America/Los_Angeles")

### Helpers: time + paths
def pacific_stamp():
    """Return YYYY-MM-DD_HHMM in America/Los_Angeles."""
    return datetime.now(PT).strftime("%Y-%m-%d_%H%M")
def resolve_log_path(repo_root):
    """Return absolute path for the git-tracked skill run log."""
    return os.path.join(repo_root, LOG_REL)
def list_non_root_agents_md(ref="origin/main"):
    """Return sorted repo-relative paths of tracked non-root AGENTS.md at ref."""
    rc, out, _ = _git(["ls-tree", "-r", "--name-only", ref])
    if rc != 0 or not out:
        return []
    paths = []
    for line in out.splitlines():
        path = line.strip()
        if not path or path == "AGENTS.md":
            continue
        if path.rsplit("/", 1)[-1] == "AGENTS.md":
            paths.append(path)
    return sorted(paths)

### Helpers: verify
def verify_tips_match_main(branch_names, main_ref="origin/main"):
    """Return (ok, rows, mismatches).

    ok is True only when every named tip's root AGENTS.md matches main byte-for-byte.
    """
    branch_refs = []
    missing_refs = []
    for name in branch_names:
        ref = f"origin/{name}"
        rc, _, _ = _git(["rev-parse", "--verify", "--quiet", ref])
        if rc != 0:
            missing_refs.append(name)
            continue
        branch_refs.append((name, ref))
    rows = inventory_rows(main_ref, branch_refs)
    mismatches = []
    for row in rows:
        if row["name"] == "main":
            continue
        if row["class"] != "match":
            mismatches.append(row)
    for name in missing_refs:
        mismatches.append({
            "name": name,
            "ref": f"origin/{name}",
            "exists": False,
            "sha12": "-",
            "class": "missing-ref",
            "commits": [],
        })
    ok = len(mismatches) == 0 and len(branch_refs) > 0
    if len(branch_names) == 0:
        ok = False
    return ok, rows, mismatches
def format_verify_section(ok, rows, mismatches):
    """Return markdown lines for the verification block."""
    main_row = next((r for r in rows if r["name"] == "main"), None)
    tip_rows = [r for r in rows if r["name"] != "main"]
    matched = [r for r in tip_rows if r["class"] == "match"]
    lines = []
    lines.append(f"- Canonical root SHA-256 (12): `{main_row['sha12'] if main_row else '-'}`")
    lines.append(f"- Tips checked: {len(tip_rows)}")
    lines.append(f"- Tips matching `origin/main`: {len(matched)}")
    if ok:
        lines.append("- **Verification: PASS** — every confirmed tip matches `origin/main` on root `AGENTS.md`")
    else:
        lines.append("- **Verification: FAIL** — not every tip matches")
        for row in mismatches:
            lines.append(f"  - `{row['name']}`: class `{row['class']}`, sha12 `{row['sha12']}`")
    return lines

### Helpers: report body
def format_run_report(meta):
    """Build a full markdown report entry from a meta dict.

    Expected keys (all optional except stamp/runner when writing):
      stamp, runner, phase_a_note, canonical_sha12,
      promoted (list of {branch, note}),
      demoted (list of {branch, topic, scoped_path, created, commit, pushed}),
      fanout_main_only (list of {branch, action, commit}),
      non_root_agents_md (list of paths; if None, omit section; if [] show empty note),
      fanout_other (list of {branch, note}),
      skipped (list of {branch, reason}),
      verify_ok, verify_lines (list[str])
    """
    stamp = meta.get("stamp") or pacific_stamp()
    lines = []
    lines.append(f"## {stamp} — agents-md-repo-sync")
    lines.append("")
    lines.append(f"- Run by: {meta.get('runner', '(unknown)')}")
    lines.append(f"- Phase A: {meta.get('phase_a_note', 'none (fan-out only)')}")
    if meta.get("canonical_sha12"):
        lines.append(f"- Canonical root SHA-256 (12): `{meta['canonical_sha12']}`")
    lines.append("")
    verify_lines = meta.get("verify_lines") or []
    if verify_lines:
        lines.append("### Verification")
        lines.append("")
        lines.extend(verify_lines)
        lines.append("")
    promoted = meta.get("promoted") or []
    if promoted:
        lines.append("### Promoted into root `AGENTS.md`")
        lines.append("")
        for item in promoted:
            lines.append(f"- `{item['branch']}`: {item['note']}")
        lines.append("")
    demoted = meta.get("demoted") or []
    if demoted:
        lines.append("### Demoted to scoped `AGENTS.md` (committed + pushed on tip)")
        lines.append("")
        for item in demoted:
            created = "created" if item.get("created") else "updated"
            commit = item.get("commit") or "?"
            pushed = "pushed" if item.get("pushed") else "NOT pushed"
            lines.append(
                f"- `{item['branch']}`: moved {item.get('topic', '(topic)')} → "
                f"`{item['scoped_path']}` ({created}); root synced; "
                f"commit `{commit}` ({pushed})"
            )
        lines.append("")
    fanout_main_only = meta.get("fanout_main_only") or []
    if fanout_main_only:
        lines.append("### Fan-out only — no branch `AGENTS.md` changes since fork")
        lines.append("")
        lines.append(
            "These tips had no root `AGENTS.md` edits for the life of the branch "
            "(relative to the fork from main). They only received the current "
            "`origin/main` file."
        )
        lines.append("")
        for item in fanout_main_only:
            action = item.get("action", "updated")
            commit = item.get("commit")
            if commit:
                lines.append(f"- `{item['branch']}`: {action} (`{commit}`)")
            else:
                lines.append(f"- `{item['branch']}`: {action}")
        lines.append("")
    if "non_root_agents_md" in meta:
        lines.append("### Inventory — non-root `AGENTS.md` files")
        lines.append("")
        paths = meta.get("non_root_agents_md") or []
        if paths:
            for path in paths:
                lines.append(f"- `{path}`")
        else:
            lines.append("- (none tracked at the inventory ref)")
        lines.append("")
    fanout_other = meta.get("fanout_other") or []
    if fanout_other:
        lines.append("### Other tip updates")
        lines.append("")
        for item in fanout_other:
            lines.append(f"- `{item['branch']}`: {item['note']}")
        lines.append("")
    skipped = meta.get("skipped") or []
    if skipped:
        lines.append("### Skipped")
        lines.append("")
        for item in skipped:
            lines.append(f"- `{item['branch']}`: {item['reason']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
def prepend_log(log_path, report_md):
    """Prepend report_md to log_path (create file/dir if needed). Newest entry on top."""
    parent = os.path.dirname(log_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    existing = ""
    if os.path.isfile(log_path):
        with open(log_path, encoding="utf-8") as f:
            existing = f.read()
    header = "# agents-md-repo-sync run log\n\nNewest entry first.\n\n"
    body_existing = existing
    if existing.startswith("# agents-md-repo-sync run log"):
        # strip header so we don't duplicate it
        parts = existing.split("\n", 3)
        # keep everything after the intro block
        idx = existing.find("## ")
        body_existing = existing[idx:] if idx >= 0 else ""
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(report_md)
        if body_existing and not body_existing.startswith("\n"):
            f.write("\n")
        f.write(body_existing if body_existing.startswith("## ") or not body_existing else body_existing)

### CLI
def _resolve_branch_names(branches_csv):
    """Parse --branches or default candidate list."""
    if branches_csv and branches_csv.strip():
        return [b.strip() for b in branches_csv.split(",") if b.strip()]
    return default_candidate_branches(_remote_branch_names())
def cmd_verify(args):
    """Verify tips match main; print a short markdown verify block to stdout for agents."""
    if not args.no_fetch:
        rc, _, err = _git(["fetch", "origin", "--prune"])
        if rc != 0:
            print(f"WARNING: git fetch failed: {err}", file=sys.stderr)
    names = _resolve_branch_names(args.branches)
    ok, rows, mismatches = verify_tips_match_main(names)
    lines = format_verify_section(ok, rows, mismatches)
    # Agent-facing: write verify block to stdout (not a noisy table dump)
    print("\n".join(lines))
    return 0 if ok else 1
def cmd_write_log(args):
    """Prepend a report file's contents to the run log."""
    root = _repo_root()
    if not root:
        print("ERROR: not inside a git repository", file=sys.stderr)
        return 2
    report_path = args.report_file
    if not report_path or not os.path.isfile(report_path):
        print("ERROR: --report-file must point to an existing markdown file", file=sys.stderr)
        return 2
    with open(report_path, encoding="utf-8") as f:
        report_md = f.read()
    if not report_md.strip().startswith("## "):
        print("ERROR: report must start with a ## heading (run entry)", file=sys.stderr)
        return 2
    log_path = args.log_path or resolve_log_path(root)
    prepend_log(log_path, report_md if report_md.endswith("\n") else report_md + "\n")
    # Return the log path for the agent (stdout = path only)
    print(log_path)
    return 0
def main(argv=None):
    """CLI entry."""
    ap = argparse.ArgumentParser(description="Verify and log agents-md-repo-sync runs.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("verify", help="verify all tips match origin/main on AGENTS.md")
    v.add_argument("--no-fetch", action="store_true")
    v.add_argument("--branches", default="", help="comma-separated branch names")
    v.set_defaults(func=cmd_verify)

    w = sub.add_parser("write-log", help="prepend a report markdown file to the run log")
    w.add_argument("--report-file", required=True, help="path to the report entry markdown")
    w.add_argument("--log-path", default="",
                    help="override log path (default skills/repo-ops/agents-md-repo-sync/run-log.md)")
    w.set_defaults(func=cmd_write_log)

    args = ap.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())
