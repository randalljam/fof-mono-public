#!/usr/bin/env python3
"""Export selected consumer ChatGPT and Claude chats to markdown."""

import argparse
import glob
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from normalize import (
    parse_chatgpt_markdown_file,
    parse_chatgpt_share_html,
    parse_chatgpt_share_url,
    parse_claude_json_file,
    parse_pasted_markdown_file,
    repo_root,
)
from render_md import write_outputs

DEFAULT_LOCAL_ROOT = "/Users/randytrue/Documents/Code/_LOCAL_FILES/fof-mono"
def default_out_dir():
    root = os.environ.get("FOF_MONO_LOCAL_FILES_ROOT", DEFAULT_LOCAL_ROOT)
    return str(Path(root) / "consumer-chats")
def expand_paths(patterns):
    paths = []
    for pattern in patterns or []:
        matches = sorted(glob.glob(pattern))
        if matches:
            paths.extend(matches)
        elif Path(pattern).exists():
            paths.append(pattern)
        else:
            raise FileNotFoundError(f"No files matched: {pattern}")
    return paths
def collect_threads(args):
    threads = []
    for url in args.chatgpt_share or []:
        threads.append(parse_chatgpt_share_url(url))
    for path in expand_paths(args.chatgpt_html):
        threads.append(parse_chatgpt_share_html(path))
    for path in expand_paths(args.chatgpt_md):
        threads.append(parse_chatgpt_markdown_file(path))
    for path in expand_paths(args.pasted_md):
        threads.append(parse_pasted_markdown_file(path, source=args.pasted_source))
    for path in expand_paths(args.claude_json):
        threads.extend(parse_claude_json_file(path, select=args.select, ids=args.claude_id))
    if not threads:
        raise SystemExit("No input chats provided. Use --chatgpt-share, --chatgpt-html, --claude-json, or --pasted-md.")
    return threads
def build_parser():
    parser = argparse.ArgumentParser(description="Export selected consumer chats to markdown.")
    parser.add_argument("--chatgpt-share", action="append", default=[], help="ChatGPT share URL (repeatable)")
    parser.add_argument("--chatgpt-html", action="append", default=[], help="Saved ChatGPT share HTML file or glob")
    parser.add_argument("--chatgpt-md", action="append", default=[], help="Existing ChatGPT markdown export or glob")
    parser.add_argument("--claude-json", action="append", default=[], help="Claude browser export JSON or glob")
    parser.add_argument("--pasted-md", action="append", default=[], help="Pasted markdown in house format")
    parser.add_argument("--pasted-source", default="chatgpt", choices=["chatgpt", "claude"], help="Source label for --pasted-md")
    parser.add_argument("--select", default="", help="Comma-separated title/id substring filter for Claude JSON")
    parser.add_argument("--claude-id", action="append", default=[], help="Exact Claude conversation id (repeatable)")
    parser.add_argument("--combine", action="store_true", help="Also write one combined markdown file")
    parser.add_argument("--topic", default="", help="Combined file title/topic slug")
    parser.add_argument("--out-dir", default="", help=f"Output directory (default: {default_out_dir()})")
    return parser
def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    out_dir = args.out_dir or default_out_dir()
    threads = collect_threads(args)
    written = write_outputs(threads, out_dir, combine=args.combine, topic=args.topic or None)
    print(f"Repo root: {repo_root()}")
    print(f"Wrote {len(written)} file(s) to {out_dir}:")
    for path in written:
        print(f"  {path}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
