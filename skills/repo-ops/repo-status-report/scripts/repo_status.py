"""
Deterministic snapshot of immediate child folders under a scan path.

Default scan path is the repo root. Optional repo-relative folders scan their
own next-level children instead (same columns as the root report).

Reports, for each immediate child directory:
  - tracked file count and tracked size on disk (what git would carry)
  - working-tree file count and working-tree size on disk (what du -sh sees)

Megabyte sizes use one decimal place (commas for thousands where applicable).

Output (default): writes a stable markdown snapshot in the skill folder:
  skills/repo-ops/repo-status-report/current-repo-status-report.md

Use --print-only to skip the file and print the table to stdout instead.

Run from repo root:
  `.venv/bin/python3 skills/repo-ops/repo-status-report/scripts/repo_status.py .`
  `.venv/bin/python3 skills/repo-ops/repo-status-report/scripts/repo_status.py . --print-only`
  `.venv/bin/python3 skills/repo-ops/repo-status-report/scripts/repo_status.py . apps/math-quiz --print-only`
"""
import argparse
import os
import subprocess
import sys
from datetime import datetime

### Helpers: sizing
def _bytes_to_mb(n):
    """
    Convert a byte count to megabytes, one decimal place.

    :param n: int, byte count.
    :return mb: float, megabytes rounded to one decimal.
    """
    return round(n / (1024 * 1024), 1)
def _fmt_mb(n):
    """
    Format a megabyte value with one decimal and thousands separators.

    :param n: float, megabytes.
    :return s: str, formatted megabytes (e.g. "1,234.5" or "0.3").
    """
    return f"{n:,.1f}"

### Helpers: filesystem walks
def _walk_size(path):
    """
    Sum file sizes and count files under path, following no symlinks.

    :param path: str, directory path.
    :return result: tuple (file_count, total_bytes).
    """
    count = 0
    total = 0
    for root, dirs, files in os.walk(path, followlinks=False):
        for f in files:
            fp = os.path.join(root, f)
            try:
                st = os.lstat(fp)
            except OSError:
                continue
            if os.path.islink(fp):
                continue
            count += 1
            total += st.st_size
    return count, total
def _list_immediate_dirs(abs_base):
    """
    Return immediate child directories of abs_base, excluding .git.

    :param abs_base: str, absolute path to the directory to scan.
    :return dirs: list[str], sorted directory names.
    """
    entries = []
    for name in os.listdir(abs_base):
        if name == ".git":
            continue
        full = os.path.join(abs_base, name)
        if os.path.isdir(full) and not os.path.islink(full):
            entries.append(name)
    return sorted(entries)
def _list_root_dirs(repo_root):
    """
    Return immediate child directories of the repo root, excluding .git.

    :param repo_root: str, absolute path to the repo root.
    :return dirs: list[str], sorted directory names.
    """
    return _list_immediate_dirs(repo_root)

### Helpers: git
def _tracked_files_by_dir(repo_root):
    """
    Group `git ls-files` output by top-level directory.

    :param repo_root: str, absolute path to the repo root.
    :return mapping: dict, dirname -> list[str] of repo-relative paths.
    """
    return _tracked_files_under(repo_root, "")
def _tracked_files_under(repo_root, rel_base):
    """
    Group `git ls-files` paths by immediate child name under rel_base.

    rel_base "" uses repo-root grouping; otherwise only paths under rel_base.

    :param repo_root: str, absolute path to the repo root.
    :param rel_base: str, repo-relative directory to scan ("" for repo root).
    :return mapping: dict, dirname -> list[str] of repo-relative paths.
    """
    out = subprocess.check_output(["git", "-C", repo_root, "ls-files"], text=True)
    by_dir = {}
    base_files = []
    if not rel_base:
        for line in out.splitlines():
            if "/" in line:
                top = line.split("/", 1)[0]
                by_dir.setdefault(top, []).append(line)
            else:
                base_files.append(line)
    else:
        prefix = rel_base + "/"
        for line in out.splitlines():
            if line == rel_base:
                base_files.append(line)
            elif line.startswith(prefix):
                rest = line[len(prefix):]
                if "/" in rest:
                    top = rest.split("/", 1)[0]
                    by_dir.setdefault(top, []).append(line)
                else:
                    base_files.append(line)
    by_dir["<root files>"] = base_files
    return by_dir
def _sum_tracked(paths, repo_root):
    """
    Count and sum byte size of tracked files that still exist on disk.

    :param paths: list[str], repo-relative paths.
    :param repo_root: str, absolute path to the repo root.
    :return result: tuple (file_count, total_bytes).
    """
    count = 0
    total = 0
    for p in paths:
        fp = os.path.join(repo_root, p)
        try:
            st = os.lstat(fp)
        except OSError:
            continue
        if os.path.islink(fp):
            continue
        count += 1
        total += st.st_size
    return count, total

### Main
def _format_table_rows(rows):
    """
    Format report rows into a table string.

    :param rows: list[tuple], (name, tracked#, tracked MB, worktree#, worktree MB).
    :return table: str, formatted table text.
    """
    name_w = max(len(r[0]) for r in rows)
    lines = []
    lines.append(f"{'folder':<{name_w}}  {'tracked#':>9}  {'tracked MB':>12}  {'worktree#':>10}  {'worktree MB':>13}")
    lines.append("-" * (name_w + 2 + 9 + 2 + 12 + 2 + 10 + 2 + 13))
    tot_tr_n = tot_tr_mb = tot_wt_n = tot_wt_mb = 0
    for name, tn, tmb, wn, wmb in rows:
        lines.append(f"{name:<{name_w}}  {tn:>9,}  {_fmt_mb(tmb):>12}  {wn:>10,}  {_fmt_mb(wmb):>13}")
        tot_tr_n += tn
        tot_tr_mb += tmb
        tot_wt_n += wn
        tot_wt_mb += wmb
    lines.append("-" * (name_w + 2 + 9 + 2 + 12 + 2 + 10 + 2 + 13))
    lines.append(f"{'TOTAL':<{name_w}}  {tot_tr_n:>9,}  {_fmt_mb(round(tot_tr_mb, 1)):>12}  {tot_wt_n:>10,}  {_fmt_mb(round(tot_wt_mb, 1)):>13}")
    return "\n".join(lines)
def report_table(repo_root, rel_base=""):
    """
    Build a status table of immediate child folders under rel_base.

    rel_base "" scans the repo root; otherwise rel_base is repo-relative.

    :param repo_root: str, absolute path to the repo root.
    :param rel_base: str, repo-relative scan path (default: repo root).
    :return table: str, formatted table text.
    """
    abs_base = repo_root if not rel_base else os.path.join(repo_root, rel_base)
    dirs = _list_immediate_dirs(abs_base)
    tracked_map = _tracked_files_under(repo_root, rel_base)
    rows = []
    for d in dirs:
        wt_count, wt_bytes = _walk_size(os.path.join(abs_base, d))
        tr_count, tr_bytes = _sum_tracked(tracked_map.get(d, []), repo_root)
        rows.append((d, tr_count, _bytes_to_mb(tr_bytes), wt_count, _bytes_to_mb(wt_bytes)))
    rf_count, rf_bytes = _sum_tracked(tracked_map.get("<root files>", []), repo_root)
    rows.append(("<root files>", rf_count, _bytes_to_mb(rf_bytes), rf_count, _bytes_to_mb(rf_bytes)))
    return _format_table_rows(rows)
def default_output_path():
    """
    Return the default stable markdown report path in the skill folder.

    :return path: str, absolute path to current-repo-status-report.md.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    skill_dir = os.path.dirname(script_dir)
    return os.path.join(skill_dir, "current-repo-status-report.md")
def _timestamp():
    """Return a local timestamp for the generated report."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z").strip()
def format_markdown_snapshot(repo_root, table, title=None, scan_path=None, cmd=None, basename=None):
    """
    Wrap a report table in the standard plans markdown header.

    :param repo_root: str, absolute path to the repo root.
    :param table: str, formatted table text.
    :param title: str or None, document title.
    :param scan_path: str or None, repo-relative path shown in the section header.
    :param cmd: str or None, command line recorded in the markdown.
    :param basename: str or None, file: header basename without .md.
    :return md: str, full markdown document.
    """
    file_base = basename or "current-repo-status-report"
    doc_title = title or "Current repo status report"
    run_cmd = cmd or f".venv/bin/python3 skills/repo-ops/repo-status-report/scripts/repo_status.py {repo_root}"
    section = f"## Snapshot — `{scan_path}`\n" if scan_path else "## Repo Root\n"
    return (
        f"file: {file_base}.md\n"
        f"title: {doc_title}\n"
        "\n"
        f"{section}"
        f"Generated at: `{_timestamp()}`\n"
        f"Repo root: `{repo_root}`\n"
        f"Generated by `{run_cmd}`\n"
        "\n"
        "```\n"
        f"{table}\n"
        "```\n"
    )
def format_markdown_multi(repo_root, sections, title, basename, cmd):
    """
    Wrap multiple folder tables in one markdown document.

    :param repo_root: str, absolute path to the repo root.
    :param sections: list[tuple], (rel_base, table) pairs.
    :param title: str, document title.
    :param basename: str, file: header basename without .md.
    :param cmd: str, command line recorded in the markdown.
    :return md: str, full markdown document.
    """
    parts = [
        f"file: {basename}.md\n",
        f"title: {title}\n",
        "\n",
        f"Generated at: `{_timestamp()}`\n",
        f"Repo root: `{repo_root}`\n",
        f"Generated by `{cmd}`\n",
    ]
    for rel_base, table in sections:
        parts.append(f"\n## `{rel_base}`\n\n```\n{table}\n```\n")
    return "".join(parts)
def format_current_report(repo_root, root_table, apps_table, cmd, basename):
    """
    Wrap the default root and apps tables in one stable markdown report.

    :param repo_root: str, absolute path to the repo root.
    :param root_table: str, formatted repo root table.
    :param apps_table: str, formatted apps folder table.
    :param cmd: str, command line recorded in the markdown.
    :param basename: str, file: header basename without .md.
    :return md: str, full markdown document.
    """
    return (
        f"file: {basename}.md\n"
        "title: Current repo status report\n"
        "\n"
        "## Repo Root\n"
        f"Generated at: `{_timestamp()}`\n"
        f"Repo root: `{repo_root}`\n"
        f"Generated by `{cmd}`\n"
        "\n"
        "```\n"
        f"{root_table}\n"
        "```\n"
        "\n"
        "## Folders Under Apps\n"
        "```\n"
        f"{apps_table}\n"
        "```\n"
    )
def write_snapshot(repo_root, output_path=None, scan_folders=None):
    """
    Write a stable markdown snapshot and return its path.

    :param repo_root: str, absolute path to the repo root.
    :param output_path: str or None, optional override for output file.
    :param scan_folders: list[str] or None, repo-relative folders to scan.
    :return path: str, absolute path written.
    """
    path = output_path or default_output_path()
    basename = os.path.splitext(os.path.basename(path))[0]
    if scan_folders:
        sections = [(f, report_table(repo_root, rel_base=f)) for f in scan_folders]
        folder_args = " ".join(scan_folders)
        cmd = f".venv/bin/python3 skills/repo-ops/repo-status-report/scripts/repo_status.py {repo_root} {folder_args}"
        content = format_markdown_multi(
            repo_root,
            sections,
            title="Current repo status report",
            basename=basename,
            cmd=cmd,
        )
    else:
        cmd = f".venv/bin/python3 skills/repo-ops/repo-status-report/scripts/repo_status.py {repo_root}"
        content = format_current_report(repo_root, report_table(repo_root), report_table(repo_root, rel_base="apps"), cmd, basename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
def _parse_args(argv):
    """
    Parse CLI arguments.

    :param argv: list[str], arguments after the script name.
    :return args: argparse.Namespace.
    """
    parser = argparse.ArgumentParser(description="Report immediate child folder sizes in the repo.")
    parser.add_argument("repo_root", nargs="?", default=".", help="Path to repo root (default: cwd)")
    parser.add_argument(
        "scan_folders",
        nargs="*",
        help="Optional repo-relative folders to scan (default: repo root)",
    )
    parser.add_argument("--print-only", action="store_true", help="Print table to stdout; do not write a file")
    parser.add_argument("--output", "-o", help="Output markdown path (default: current report in skill folder)")
    return parser.parse_args(argv)
if __name__ == "__main__":
    args = _parse_args(sys.argv[1:])
    repo_root = os.path.abspath(args.repo_root)
    scan_folders = args.scan_folders or None
    if args.print_only:
        if scan_folders:
            for folder in scan_folders:
                print(f"## {folder}\n")
                print(report_table(repo_root, rel_base=folder))
                print()
        else:
            print(report_table(repo_root))
    else:
        path = write_snapshot(repo_root, output_path=args.output, scan_folders=scan_folders)
        print(f"Wrote {path}")
