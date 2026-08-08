#!/usr/bin/env python3
"""Copy .vscode/settings.json from main into a worktree, preserving title-bar colors.

Worktree Manager assigns a per-worktree title-bar color when it creates a checkout.
Bootstrap needs the full settings from main but must not overwrite those colors with
fof-mono's green title bar.
"""
import re
import shutil
import sys
from pathlib import Path

TITLEBAR_COLOR_LINE = re.compile(r'^\s*"titleBar\.[^"]+"\s*:')
WINDOW_TITLEBAR_STYLE_LINE = re.compile(r'^\s*"window\.titleBarStyle"\s*:')
COLOR_CUSTOMIZATIONS_OPEN = re.compile(r'"workbench\.colorCustomizations"\s*:\s*\{')


def _read_text(path):
    return Path(path).read_text(encoding="utf-8")


def _write_text(path, text):
    Path(path).write_text(text, encoding="utf-8")


def _split_lines(text):
    return text.splitlines()


def _extract_titlebar_color_lines(text):
    return [line for line in _split_lines(text) if TITLEBAR_COLOR_LINE.match(line)]


def _extract_window_titlebar_style_line(text):
    for line in _split_lines(text):
        if WINDOW_TITLEBAR_STYLE_LINE.match(line):
            return line
    return None


def _normalize_titlebar_color_line(line):
    stripped = line.strip()
    if not stripped.endswith(","):
        stripped = stripped + ","
    return "        " + stripped


def _remove_titlebar_overrides(lines):
    return [
        line
        for line in lines
        if not TITLEBAR_COLOR_LINE.match(line)
        and not WINDOW_TITLEBAR_STYLE_LINE.match(line)
    ]


def _merge_settings(main_path, dest_path):
    main_text = _read_text(main_path)
    dest_text = _read_text(dest_path)
    preserved_colors = _extract_titlebar_color_lines(dest_text)
    preserved_style = _extract_window_titlebar_style_line(dest_text)
    if not preserved_colors and preserved_style is None:
        _write_text(dest_path, main_text)
        return "copied"
    main_lines = _split_lines(main_text)
    style_insert_at = None
    for idx, line in enumerate(main_lines):
        if WINDOW_TITLEBAR_STYLE_LINE.match(line):
            style_insert_at = idx
            break
    lines = _remove_titlebar_overrides(main_lines)
    merged = []
    inserted_colors = False
    for line in lines:
        merged.append(line)
        if not inserted_colors and preserved_colors and COLOR_CUSTOMIZATIONS_OPEN.search(line):
            for color_line in preserved_colors:
                merged.append(_normalize_titlebar_color_line(color_line))
            inserted_colors = True
    if preserved_style is not None:
        if style_insert_at is not None:
            removed_before = sum(
                1
                for line in main_lines[:style_insert_at]
                if TITLEBAR_COLOR_LINE.match(line) or WINDOW_TITLEBAR_STYLE_LINE.match(line)
            )
            insert_at = style_insert_at - removed_before
            merged.insert(insert_at, preserved_style)
        else:
            merged.append(preserved_style)
    _write_text(dest_path, "\n".join(merged) + "\n")
    return "merged"


def main():
    if len(sys.argv) != 3:
        print("usage: worktree_copy_settings.py <main_settings> <dest_settings>", file=sys.stderr)
        sys.exit(1)
    main_path = Path(sys.argv[1])
    dest_path = Path(sys.argv[2])
    if not main_path.is_file():
        print(f"error: main settings not found: {main_path}", file=sys.stderr)
        sys.exit(1)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if not dest_path.is_file():
        shutil.copy2(main_path, dest_path)
        print("copied")
        return
    mode = _merge_settings(main_path, dest_path)
    print(mode)


if __name__ == "__main__":
    main()
