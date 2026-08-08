#!/usr/bin/env python3
"""Move dangling phrases across chapter boundaries in a YouTube transcript markdown file.

When description chapter timestamps split mid-sentence, trailing fragments at the end of
one chapter are prepended to the next so each chapter boundary falls between sentences.

Usage:
    python adjust_chapter_transitions.py path/to/transcript_yt.md
"""
import re
import sys

SENTENCE_END = re.compile(r'[.!?]["\']?\s*$')
CHAPTER_RE = re.compile(
    r'(### .+?\n)(\[[^\]]+\]\([^\)]+\)\n)(.*?)(?=\n### |\Z)',
    re.DOTALL,
)

def find_split_point(text):
    """Return index where trailing incomplete fragment starts, or None."""
    text = text.rstrip()
    if SENTENCE_END.search(text):
        return None
    last_end = -1
    for m in re.finditer(r'[.!?]["\']?(?:\s+|$)', text):
        last_end = m.end()
    if last_end == -1:
        return None
    fragment = text[last_end:].strip()
    if not fragment or SENTENCE_END.search(fragment):
        return None
    return last_end

def adjust_transitions(chapters):
    adjusted = 0
    for i in range(len(chapters) - 1):
        curr = chapters[i]
        nxt = chapters[i + 1]
        split = find_split_point(curr["text"])
        if split is None:
            continue
        fragment = curr["text"][split:].strip()
        curr["text"] = curr["text"][:split].rstrip()
        nxt["text"] = fragment + " " + nxt["text"].lstrip()
        adjusted += 1
    return chapters, adjusted

def parse_transcript(body):
    chapters = []
    for m in CHAPTER_RE.finditer(body):
        chapters.append({
            "heading": m.group(1).rstrip("\n"),
            "link": m.group(2).rstrip("\n"),
            "text": m.group(3).strip(),
        })
    return chapters

def render_transcript(chapters):
    lines = []
    for ch in chapters:
        lines.append(ch["heading"])
        lines.append(ch["link"])
        lines.append(ch["text"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

### CLI
def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <transcript_yt.md>", file=sys.stderr)
        sys.exit(1)
    path = sys.argv[1]
    with open(path) as f:
        content = f.read()
    marker = "## Transcript\n"
    if marker not in content:
        print(f"Error: no '{marker.strip()}' section in {path}", file=sys.stderr)
        sys.exit(1)
    idx = content.index(marker)
    header = content[:idx + len(marker)]
    body = content[idx + len(marker):]
    chapters = parse_transcript(body)
    if not chapters:
        print(f"Error: no chapters found in transcript section of {path}", file=sys.stderr)
        sys.exit(1)
    chapters, adjusted = adjust_transitions(chapters)
    with open(path, "w") as f:
        f.write(header + render_transcript(chapters))
    if adjusted:
        print(f"Adjusted {adjusted} chapter boundary(ies) in {path}")
    else:
        print(f"No chapter transitions to adjust in {path}")

if __name__ == "__main__":
    main()
