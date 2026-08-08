"""
Repo clone-size audit: tracked tree, shallow clone, and full clone per branch.

Reports megabytes (nearest 0.1 MB) for:
  - tracked MB — logical byte sum of git-tracked files at the branch tip
  - shallow clone MB — measured `git clone --depth 1 --single-branch` on disk
  - shallow .git MB — object database portion of that shallow clone
  - full clone MB — measured full `git clone` (same history for every branch)

Full-clone checkout size follows whichever branch HEAD points to after clone;
tracked MB is per branch. History bloat ≈ full .git MB − shallow .git MB.

Default temp clones go under `<repo>/data/_repo_size_audit_tmp/` (gitignored).

Run from repo root:
  `.venv/bin/python3 skills/repo-ops/repo-size-audit/scripts/repo_size_audit.py`
  `.venv/bin/python3 skills/repo-ops/repo-size-audit/scripts/repo_size_audit.py --branches main feature/minecraft-mod-forge --print-only`
  `.venv/bin/python3 skills/repo-ops/repo-size-audit/scripts/repo_size_audit.py --fast --print-only`
"""
import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime

### Helpers: formatting
def _bytes_to_mb(n):
    """Convert bytes to megabytes, one decimal place."""
    return round(n / (1024 * 1024), 1)
def _fmt_mb(n):
    """Format megabytes with one decimal and thousands separators."""
    return f"{n:,.1f}"
def _fmt_gb(n_mb):
    """Format megabytes as gigabytes when useful."""
    if n_mb >= 1024:
        return f"{round(n_mb / 1024, 2):,.2f} GB"
    return f"{_fmt_mb(n_mb)} MB"
def _timestamp():
    """Return a local timestamp for the generated report."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z").strip()

### Helpers: git
def _run(cmd, cwd=None):
    """Run a command and return stdout text."""
    return subprocess.check_output(cmd, cwd=cwd, text=True, stderr=subprocess.STDOUT)
def _resolve_ref(repo_root, branch):
    """
    Resolve a branch name to a git ref (prefer origin/<branch>).

    :param repo_root: str, absolute repo path.
    :param branch: str, branch name without remote prefix.
    :return ref: str, ref that exists locally.
    """
    for candidate in (f"origin/{branch}", branch):
        try:
            _run(["git", "-C", repo_root, "rev-parse", "--verify", candidate])
            return candidate
        except subprocess.CalledProcessError:
            continue
    raise SystemExit(f"Branch not found locally: {branch!r} (try git fetch origin)")
def _tracked_bytes(repo_root, ref):
    """Sum blob sizes for all paths in ref's tree."""
    out = _run(["git", "-C", repo_root, "ls-tree", "-r", "-l", ref])
    total = 0
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 4:
            total += int(parts[3])
    return total
def _du_mb(path):
    """Return on-disk size of path in megabytes (du -sk, one decimal)."""
    kb = int(_run(["du", "-sk", path]).split()[0])
    return round(kb / 1024, 1)
def _local_git_mb(repo_root):
    """Return .git directory size in the current checkout."""
    git_dir = os.path.join(repo_root, ".git")
    if not os.path.isdir(git_dir):
        return None
    return _du_mb(git_dir)

### Helpers: clone measurement
def _clone_dir(repo_root, tmp_base, label):
    """Return a sanitized clone destination path."""
    safe = label.replace("/", "_")
    return os.path.join(tmp_base, safe)
def _shallow_clone(repo_root, branch, dest):
    """Create a depth-1 single-branch clone."""
    url = f"file://{repo_root}"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    _run(["git", "clone", "--depth", "1", "--branch", branch, "--single-branch", url, dest])
def _full_clone(repo_root, dest):
    """Create a full-history clone."""
    url = f"file://{repo_root}"
    if os.path.exists(dest):
        shutil.rmtree(dest)
    _run(["git", "clone", url, dest])

### Main: audit
def audit_branches(repo_root, branches, measure_clones=True, tmp_base=None):
    """
    Build audit rows for each branch.

    :param repo_root: str, absolute repo path.
    :param branches: list[str], branch names.
    :param measure_clones: bool, run temp clones for shallow/full sizes.
    :param tmp_base: str or None, directory for temp clones.
    :return result: dict with rows, full_clone stats, local_git_mb.
    """
    if tmp_base is None:
        tmp_base = os.path.join(repo_root, "data", "_repo_size_audit_tmp")
    rows = []
    full_total_mb = None
    full_git_mb = None
    cleanup = measure_clones
    try:
        if measure_clones:
            os.makedirs(tmp_base, exist_ok=True)
            full_dest = _clone_dir(repo_root, tmp_base, "_full_clone")
            _full_clone(repo_root, full_dest)
            full_total_mb = _du_mb(full_dest)
            full_git_mb = _du_mb(os.path.join(full_dest, ".git"))
        for branch in branches:
            ref = _resolve_ref(repo_root, branch)
            tracked_mb = _bytes_to_mb(_tracked_bytes(repo_root, ref))
            shallow_total_mb = shallow_git_mb = None
            if measure_clones:
                shallow_dest = _clone_dir(repo_root, tmp_base, f"shallow-{branch}")
                _shallow_clone(repo_root, branch, shallow_dest)
                shallow_total_mb = _du_mb(shallow_dest)
                shallow_git_mb = _du_mb(os.path.join(shallow_dest, ".git"))
            rows.append({
                "branch": branch,
                "ref": ref,
                "tracked_mb": tracked_mb,
                "shallow_total_mb": shallow_total_mb,
                "shallow_git_mb": shallow_git_mb,
            })
    finally:
        if cleanup and os.path.isdir(tmp_base):
            shutil.rmtree(tmp_base, ignore_errors=True)
    return {
        "rows": rows,
        "full_total_mb": full_total_mb,
        "full_git_mb": full_git_mb,
        "local_git_mb": _local_git_mb(repo_root),
    }

### Main: output
def format_report(repo_root, result, measure_clones=True):
    """Format audit result as a text table."""
    lines = []
    lines.append(f"Repo: {repo_root}")
    lines.append(f"Generated at: {_timestamp()}")
    mode = "measured clones" if measure_clones else "fast (tracked + local .git only)"
    lines.append(f"Mode: {mode}")
    lines.append("")
    if measure_clones:
        header = (
            f"{'branch':<28}  {'tracked':>10}  {'shallow':>10}  {'shal .git':>10}  {'history*':>10}"
        )
        lines.append(header)
        lines.append("-" * len(header))
        for row in result["rows"]:
            hist = None
            if row["shallow_git_mb"] is not None and result["full_git_mb"] is not None:
                hist = round(result["full_git_mb"] - row["shallow_git_mb"], 1)
            hist_s = _fmt_mb(hist) if hist is not None else "n/a"
            lines.append(
                f"{row['branch']:<28}  "
                f"{_fmt_mb(row['tracked_mb']):>10}  "
                f"{_fmt_mb(row['shallow_total_mb']):>10}  "
                f"{_fmt_mb(row['shallow_git_mb']):>10}  "
                f"{hist_s:>10}"
            )
        lines.append("")
        ft = result["full_total_mb"]
        fg = result["full_git_mb"]
        lines.append(f"Full clone (all history):  {_fmt_mb(ft)} MB  ({_fmt_gb(ft)})")
        lines.append(f"  └─ .git object database: {_fmt_mb(fg)} MB  ({_fmt_gb(fg)})")
        lines.append(f"  └─ worktree at clone HEAD: {_fmt_mb(round(ft - fg, 1))} MB")
        lines.append("* history ≈ full .git − shallow .git (per branch shallow pack differs slightly)")
    else:
        header = f"{'branch':<28}  {'tracked MB':>12}  {'ref':>20}"
        lines.append(header)
        lines.append("-" * len(header))
        for row in result["rows"]:
            lines.append(
                f"{row['branch']:<28}  {_fmt_mb(row['tracked_mb']):>12}  {row['ref']:>20}"
            )
    lg = result["local_git_mb"]
    if lg is not None:
        lines.append("")
        lines.append(
            f"Local .git on this machine: {_fmt_mb(lg)} MB  ({_fmt_gb(lg)}) "
            f"— may exceed fresh-clone .git due to reflog, extra refs, or unpushed objects"
        )
    lines.append("")
    lines.append("Notes:")
    lines.append("  • tracked MB = git-tracked files only; .gitignore paths are not included")
    lines.append("  • shallow clone = `git clone --depth 1 --single-branch`")
    lines.append("  • full clone downloads the entire object database (all branches' history)")
    return "\n".join(lines)
def _history_mb(row, result):
    """Return estimated history overhead for a branch row."""
    if row["shallow_git_mb"] is None or result["full_git_mb"] is None:
        return None
    return round(result["full_git_mb"] - row["shallow_git_mb"], 1)
def format_markdown_report(repo_root, result, measure_clones=True, cmd=None, basename="current-repo-size-audit"):
    """Format the audit as a stable markdown report."""
    mode = "measured clones" if measure_clones else "fast (tracked + local .git only)"
    run_cmd = cmd or ".venv/bin/python3 skills/repo-ops/repo-size-audit/scripts/repo_size_audit.py"
    lines = [
        f"file: {basename}.md",
        "title: Current repo size audit",
        "",
        "## Repo Size Audit",
        f"Generated at: `{_timestamp()}`",
        f"Repo root: `{repo_root}`",
        f"Mode: `{mode}`",
        f"Generated by: `{run_cmd}`",
        "",
    ]
    if measure_clones:
        lines.extend([
            "### Results",
            "| Branch | Tracked files (active tree) | Shallow clone (`--depth 1`) | Full clone (all history) | History bloat in `.git`* |",
            "|--------|----------------------------:|----------------------------:|-------------------------:|-------------------------:|",
        ])
        for row in result["rows"]:
            hist = _history_mb(row, result)
            full = f"{_fmt_mb(result['full_total_mb'])} MB"
            lines.append(f"| **{row['branch']}** | **{_fmt_mb(row['tracked_mb'])} MB** | **{_fmt_mb(row['shallow_total_mb'])} MB** | **{full}** | **~{_fmt_mb(hist)} MB** |")
        lines.extend([
            "",
            "\\*History bloat ≈ full-clone `.git` minus shallow `.git`; per-branch shallow packs can differ slightly.",
            "",
            "### Full Clone Breakdown",
            "| Component | Size |",
            "|-----------|-----:|",
            f"| **Total download + checkout** | **{_fmt_mb(result['full_total_mb'])} MB** ({_fmt_gb(result['full_total_mb'])}) |",
            f"| `.git` object database (all branches, all history) | {_fmt_mb(result['full_git_mb'])} MB |",
            f"| Checked-out tracked files (worktree) | {_fmt_mb(round(result['full_total_mb'] - result['full_git_mb'], 1))} MB |",
            "",
            "### Shallow Clone Breakdown",
            "| Branch | Total | `.git` | Worktree (tracked files) |",
            "|--------|------:|-------:|-------------------------:|",
        ])
        for row in result["rows"]:
            worktree = round(row["shallow_total_mb"] - row["shallow_git_mb"], 1)
            lines.append(f"| {row['branch']} | {_fmt_mb(row['shallow_total_mb'])} MB | {_fmt_mb(row['shallow_git_mb'])} MB | ~{_fmt_mb(worktree)} MB |")
        max_tracked = max([row["tracked_mb"] for row in result["rows"]] or [0])
        max_history = max([_history_mb(row, result) or 0 for row in result["rows"]] or [0])
        lines.extend([
            "",
            "### Takeaways",
            f"1. A fresh full clone is **{_fmt_mb(result['full_total_mb'])} MB** ({_fmt_gb(result['full_total_mb'])}).",
            f"2. Active tracked content is at most **{_fmt_mb(max_tracked)} MB** across the audited branches.",
            f"3. Estimated history overhead is about **{_fmt_mb(max_history)} MB** over shallow clone `.git` size.",
        ])
    else:
        lines.extend([
            "### Results",
            "| Branch | Tracked files (active tree) | Ref |",
            "|--------|----------------------------:|-----|",
        ])
        for row in result["rows"]:
            lines.append(f"| **{row['branch']}** | **{_fmt_mb(row['tracked_mb'])} MB** | `{row['ref']}` |")
    if result["local_git_mb"] is not None:
        lines.extend([
            "",
            "### Local Checkout",
            f"Local `.git` on this machine is **{_fmt_mb(result['local_git_mb'])} MB** ({_fmt_gb(result['local_git_mb'])}). This may exceed fresh-clone `.git` size due to reflog, extra refs, or unpushed objects.",
        ])
    lines.extend([
        "",
        "### Notes",
        "- Tracked MB = git-tracked files only; `.gitignore` paths are not included.",
        "- Shallow clone = `git clone --depth 1 --single-branch`.",
        "- Full clone downloads the entire object database for the refs included in the clone.",
        "",
    ])
    return "\n".join(lines)
def write_report(repo_root, result, measure_clones, output_path=None, cmd=None):
    """Write markdown snapshot and return path."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    skill_dir = os.path.dirname(script_dir)
    path = output_path or os.path.join(skill_dir, "current-repo-size-audit.md")
    basename = os.path.splitext(os.path.basename(path))[0]
    content = format_markdown_report(repo_root, result, measure_clones=measure_clones, cmd=cmd, basename=basename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path

### CLI
def _parse_args(argv):
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Audit git clone sizes per branch (tracked tree, shallow, full)."
    )
    parser.add_argument(
        "repo_root",
        nargs="?",
        default=".",
        help="Path to repo root (default: cwd)",
    )
    parser.add_argument(
        "--branches",
        "-b",
        nargs="+",
        default=["main"],
        help="Branches to audit (default: main)",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip temp clones; report tracked bytes and local .git size only",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print table to stdout; do not write markdown file",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output markdown path (default: current report in skill folder)",
    )
    return parser.parse_args(argv)
if __name__ == "__main__":
    args = _parse_args(sys.argv[1:])
    repo_root = os.path.abspath(args.repo_root)
    measure_clones = not args.fast
    result = audit_branches(repo_root, args.branches, measure_clones=measure_clones)
    report = format_report(repo_root, result, measure_clones=measure_clones)
    if args.print_only:
        print(report)
    else:
        cmd = ".venv/bin/python3 skills/repo-ops/repo-size-audit/scripts/repo_size_audit.py " + " ".join(sys.argv[1:])
        path = write_report(repo_root, result, measure_clones, output_path=args.output, cmd=cmd.strip())
        print(report)
        print()
        print(f"Wrote {path}")
