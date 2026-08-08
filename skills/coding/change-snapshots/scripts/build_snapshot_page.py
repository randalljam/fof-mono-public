#!/usr/bin/env python3
"""Build the change-snapshots index.html from a folder's manifest.json.

Usage: python3 build_snapshot_page.py <snapshot-folder>
Reads <folder>/manifest.json ({title, branch, commit, stamp, summary, items:
[{image, caption}]}) and writes <folder>/index.html — a phone-friendly page:
each screenshot full-width with its caption underneath. See the skill README
(skills/coding/change-snapshots/README.md) for the folder contract.
"""
import html
import json
import sys
from pathlib import Path

### Page template
PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, Arial, sans-serif; margin: 0; background: #f5f5f5; color: #222; }}
  .wrap {{ max-width: 640px; margin: 0 auto; padding: 16px; }}
  header {{ margin-bottom: 8px; }}
  h1 {{ font-size: 1.25rem; margin: 0 0 4px; }}
  .meta {{ color: #666; font-size: 0.85rem; }}
  .summary {{ margin: 8px 0 4px; font-size: 0.95rem; }}
  figure {{ margin: 20px 0; background: #fff; border: 1px solid #ddd; border-radius: 10px; padding: 10px; }}
  figure img {{ width: 100%; height: auto; border-radius: 6px; display: block; }}
  figcaption {{ margin-top: 8px; font-size: 0.95rem; color: #333; }}
  figcaption .n {{ font-weight: 700; margin-right: 6px; color: #00838f; }}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>{title}</h1>
  <div class="meta">{branch} · commit {commit} · {stamp}</div>
  <div class="summary">{summary}</div>
</header>
{figures}
</div>
</body>
</html>
"""
FIGURE = """<figure>
  <img src="{image}" alt="{caption}">
  <figcaption><span class="n">{n}</span>{caption}</figcaption>
</figure>"""

### Build
def build(folder):
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text())
    figures = []
    for i, item in enumerate(manifest.get("items", []), 1):
        image = folder / item["image"]
        if not image.is_file():
            raise SystemExit(f"missing image: {image}")
        figures.append(FIGURE.format(n=i, image=html.escape(item["image"]),
                                     caption=html.escape(item.get("caption", ""))))
    page = PAGE.format(
        title=html.escape(manifest.get("title", "Change snapshots")),
        branch=html.escape(manifest.get("branch", "")),
        commit=html.escape(manifest.get("commit", "")),
        stamp=html.escape(manifest.get("stamp", "")),
        summary=html.escape(manifest.get("summary", "")),
        figures="\n".join(figures))
    out = folder / "index.html"
    out.write_text(page)
    print(f"wrote {out} ({len(figures)} snapshot(s))")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    build(sys.argv[1])
