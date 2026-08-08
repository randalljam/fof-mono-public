#!/usr/bin/env python3
"""Apply publish-time string replacements to a snapshot stage directory.

Usage: apply_replacements.py --root DIR --pairs FILE

Pairs file: one rule per line, `find==>replace`. Literal by default; a
`regex:` prefix makes the find side a Python regex (e.g. word-boundary name
swaps). Applied to the STAGE COPY only — the private tree is never modified.
The pairs file contains sensitive strings, so it must stay on the snapshot
exclude list.
"""
import argparse
import re
import sys
from pathlib import Path

MAX_BYTES = 2 * 1024 * 1024
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__"}

### Rules
def load_rules(path):
    """Return [(label, compiled_regex, replacement)] from a pairs file."""
    rules = []
    for raw in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip() or "==>" not in line:
            continue
        find, replacement = line.split("==>", 1)
        if find.startswith("regex:"):
            rules.append((find, re.compile(find[len("regex:"):]), replacement))
        else:
            rules.append((find, re.compile(re.escape(find)), replacement))
    return rules
def is_text_file(path):
    try:
        if path.stat().st_size > MAX_BYTES:
            return False
        head = path.open("rb").read(4096)
    except OSError:
        return False
    return b"\x00" not in head

### Main
def main():
    parser = argparse.ArgumentParser(description="Apply publish-time replacements to a stage dir")
    parser.add_argument("--root", required=True)
    parser.add_argument("--pairs", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    rules = load_rules(args.pairs)
    if not rules:
        print("replacements: no rules loaded from", args.pairs)
        return 0
    counts = {label: 0 for label, _, _ in rules}
    files_changed = 0
    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_symlink() or not path.is_file() or not is_text_file(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        new_text = text
        for label, pattern, replacement in rules:
            new_text, n = pattern.subn(replacement, new_text)
            counts[label] += n
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            files_changed += 1
    total = sum(counts.values())
    print("replacements: {0} substitution(s) across {1} file(s)".format(total, files_changed))
    for label, _, _ in rules:
        if counts[label]:
            print("  {0}: {1}".format(label if not label.startswith("regex:") else label[:60], counts[label]))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
