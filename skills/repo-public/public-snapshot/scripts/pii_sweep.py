#!/usr/bin/env python3
"""Heuristic PII/secret sweep over a directory tree before publishing.

Usage:
  pii_sweep.py --root DIR [--terms FILE] [--allowlist FILE] [--report FILE]

Scans text files for emails, IPs, phone-shaped strings, AWS keys/ARNs/account
IDs, secret-looking assignments, street-address shapes, and any personal terms
supplied via --terms (one per line; keep that file local-only). Exits 1 when
unsuppressed findings remain. Heuristic gate — a clean run is necessary, not
sufficient; a human still reviews before publishing.
"""
import argparse
import re
import sys
from pathlib import Path

MAX_BYTES_DEFAULT = 2 * 1024 * 1024
PRINT_CAP_PER_CATEGORY = 40
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".pytest_cache"}
PATTERNS = [
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("ipv4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("phone", re.compile(r"\b(?:\+1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}\b")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("aws-arn", re.compile(r"arn:aws:[^\s\"']+")),
    ("secret-assignment", re.compile(r"(?i)\b(secret|token|api_?key|hmac_?key|password)\b\s*[:=]\s*[\"'][^\"']{12,}")),
    ("street-address", re.compile(r"\b\d{2,5}\s+[A-Z][a-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Court|Ct|Way|Place|Pl)\b")),
]
ACCOUNT_ID_RE = re.compile(r"\b\d{12}\b")
ACCOUNT_CONTEXT_RE = re.compile(r"(?i)aws|account|arn")

### File scanning
def load_lines(path):
    """Return stripped, non-comment lines from a list file."""
    entries = []
    for raw in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            entries.append(line)
    return entries
def is_text_file(path, max_bytes):
    """Cheap binary/size filter: skip large files and NUL-containing heads."""
    try:
        if path.stat().st_size > max_bytes:
            return False
        head = path.open("rb").read(4096)
    except OSError:
        return False
    return b"\x00" not in head
def iter_files(root):
    """Yield files under root, pruning skip dirs and symlinks."""
    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_symlink() or not path.is_file():
            continue
        yield path
def scan_line(line, term_res):
    """Return (category, matched-text) pairs found in one line."""
    hits = []
    for name, pattern in PATTERNS:
        for m in pattern.finditer(line):
            hits.append((name, m.group(0)))
    if ACCOUNT_CONTEXT_RE.search(line):
        for m in ACCOUNT_ID_RE.finditer(line):
            hits.append(("aws-account-id", m.group(0)))
    for term, term_re in term_res:
        if term_re.search(line):
            hits.append(("personal-term", term))
    return hits

### Main
def main():
    parser = argparse.ArgumentParser(description="Heuristic PII/secret sweep")
    parser.add_argument("--root", required=True, help="Directory tree to scan")
    parser.add_argument("--terms", help="Local-only personal terms file (one term per line)")
    parser.add_argument("--allowlist", help="Benign substrings to suppress (match text or path)")
    parser.add_argument("--report", help="Also write the full report to this file")
    parser.add_argument("--max-bytes", type=int, default=MAX_BYTES_DEFAULT)
    parser.add_argument("--reveal-terms", action="store_true", help="Show matched personal terms instead of <term> (local reports only)")
    parser.add_argument("--print-cap", type=int, default=PRINT_CAP_PER_CATEGORY, help="Max rows printed per category")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        print("error: not a directory:", root, file=sys.stderr)
        return 2
    # Allowlist entries: substring match against matched text or file path;
    # a leading '=' means exact match against the matched text only.
    raw_allow = load_lines(args.allowlist) if args.allowlist else []
    allow = [a for a in raw_allow if not a.startswith("=")]
    allow_exact = {a[1:] for a in raw_allow if a.startswith("=")}
    terms = load_lines(args.terms) if args.terms else []
    # Word-boundary match by default; a trailing '*' makes it a prefix match
    # (for key/token prefixes). Case-insensitive either way.
    term_res = []
    for t in terms:
        if t.endswith("*"):
            term_res.append((t, re.compile(r"\b" + re.escape(t[:-1]), re.IGNORECASE)))
        else:
            term_res.append((t, re.compile(r"\b" + re.escape(t) + r"\b", re.IGNORECASE)))
    findings = {}
    scanned = 0
    for path in iter_files(root):
        if not is_text_file(path, args.max_bytes):
            continue
        rel = str(path.relative_to(root))
        if any(a in rel for a in allow):
            continue
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for category, match in scan_line(line, term_res):
                if match in allow_exact or any(a in match for a in allow):
                    continue
                findings.setdefault(category, []).append((rel, lineno, match))
    out_lines = []
    total = 0
    for category in sorted(findings):
        rows = findings[category]
        total += len(rows)
        out_lines.append("== {0} ({1}) ==".format(category, len(rows)))
        for rel, lineno, match in rows[:args.print_cap]:
            shown = match if category != "personal-term" or args.reveal_terms else "<term>"
            out_lines.append("  {0}:{1}: {2}".format(rel, lineno, shown[:80]))
        if len(rows) > args.print_cap:
            out_lines.append("  ... +{0} more".format(len(rows) - args.print_cap))
    report = "\n".join(out_lines)
    if report:
        print(report)
    if args.report:
        Path(args.report).write_text(report + "\n", encoding="utf-8")
        print("report written:", args.report)
    print("pii sweep: {0} file(s) scanned, {1} finding(s) in {2} categor(ies)".format(scanned, total, len(findings)))
    return 1 if total else 0
if __name__ == "__main__":
    raise SystemExit(main())
