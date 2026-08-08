#!/usr/bin/env python3
"""Export Webflow CMS corpus manifests for the Focus on Foundations Astro site."""
import json
import os
import re
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.webflow_api import (
    SITE_ID_FOF,
    FDA_C19_TOWNHALLS_ID,
    SOVEREIGN_CHILD_ID,
    webflow_cms_list_items,
    _webflow_headers,
)
import requests

WEBFLOW_BASE = "https://floodlamp-8c9d00d6ef3e90c375de806594d04.webflow.io"
OUTPUT_DIR = os.path.join(REPO_ROOT, "apps/focusonfoundations/web/src/corpus")
PV_EVAC_MD_DIR = os.path.join(OUTPUT_DIR, "pv-evac")

COLLECTIONS = {
    "deutsch": {
        "collection_id": "67a249cf5625c057b2fd345c",
        "corpus_key": "deutsch",
        "old_path_prefix": "/deutsch-transcripts",
        "viewer_variant": "generic",
    },
    "fda-town-halls": {
        "collection_id": FDA_C19_TOWNHALLS_ID,
        "corpus_key": "fda-town-halls",
        "old_path_prefix": "/fda-c19-townhalls",
        "viewer_variant": "fda",
    },
    "sovereign-child-index": {
        "collection_id": "68bf0edd549d72aa1a32bf7f",
        "corpus_key": "sovereign-child",
        "old_path_prefix": "/sovereign-child-index",
        "viewer_variant": "generic",
    },
    "sovereign-child-book": {
        "collection_id": SOVEREIGN_CHILD_ID,
        "corpus_key": "sovereign-child",
        "old_path_prefix": "/sovereign-child",
        "viewer_variant": "generic",
    },
}

LINK_FIELDS = [
    "s3-transcript-html-url",
    "s3-qa-html-url",
    "s3-transcript-md-url",
    "s3-qa-md-url",
    "youtube-url",
    "spotify-url",
    "fda-hosted-pdf-url",
    "fda-hosted-slides-url",
    "link-youtube",
    "link-spotify",
    "link-fda-pdf",
    "link-fda-slides",
    "link youtube",
    "link spotify",
]

def _link_value(field_data, *keys):
    for key in keys:
        val = field_data.get(key)
        if val:
            if isinstance(val, dict):
                return val.get("url") or val.get("href") or ""
            return str(val)
    return ""

def _normalize_item(field_data, meta):
    slug = field_data.get("slug") or ""
    name = field_data.get("name") or slug
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})", name)
    sort_date = date_match.group(1) if date_match else name
    item = {
        "name": name,
        "slug": slug,
        "sortDate": sort_date,
        "corpusKey": meta["corpus_key"],
        "oldPathPrefix": meta["old_path_prefix"],
        "oldPath": f"{meta['old_path_prefix']}/{slug}",
        "newPath": f"/transcripts/{meta['corpus_key']}/{slug}/",
        "viewerVariant": meta["viewer_variant"],
        "transcriptHtmlUrl": _link_value(field_data, "s3-transcript-html-url"),
        "qaHtmlUrl": _link_value(field_data, "s3-qa-html-url"),
        "transcriptMdUrl": _link_value(field_data, "s3-transcript-md-url"),
        "qaMdUrl": _link_value(field_data, "s3-qa-md-url"),
        "youtubeUrl": _link_value(
            field_data,
            "youtube-url",
            "youtube-url-3",
            "link-youtube",
            "link youtube",
        ),
        "spotifyUrl": _link_value(field_data, "spotify-url", "link-spotify", "link spotify"),
        "fdaPdfUrl": _link_value(
            field_data,
            "fda-hosted-pdf-url",
            "pdf-url",
            "link-fda-pdf",
        ),
        "fdaSlidesUrl": _link_value(
            field_data,
            "fda-hosted-slides-url",
            "slides-url",
            "link-fda-slides",
        ),
        "presentationUrl": _link_value(field_data, "presentation-url"),
    }
    markdown_raw = (
        field_data.get("md-mod-text")
        or field_data.get("markdown")
        or field_data.get("markdown-attr")
        or field_data.get("transcript-markdown")
        or ""
    )
    if markdown_raw:
        item["markdown"] = markdown_raw
    return item

def _list_site_collections(site_id):
    response = requests.get(
        f"https://api.webflow.com/v2/sites/{site_id}/collections",
        headers=_webflow_headers(),
    )
    response.raise_for_status()
    return response.json().get("collections", [])

def _find_pv_evac_collection_id():
    for coll in _list_site_collections(SITE_ID_FOF):
        slug = (coll.get("slug") or "").lower()
        name = (coll.get("displayName") or coll.get("name") or "").lower()
        if "pv-evac" in slug or "pv evac" in name or slug == "pv-evac-docs":
            return coll["id"], coll.get("slug")
    for coll in _list_site_collections(SITE_ID_FOF):
        if "evac" in (coll.get("slug") or "").lower():
            return coll["id"], coll.get("slug")
    return None, None

def export_collection(key, meta):
    items_raw = webflow_cms_list_items(meta["collection_id"], include_archived=False, verbose=False)
    if not items_raw:
        print(f"WARNING: no items for {key} ({meta['collection_id']})")
        return []
    items = []
    for raw in items_raw:
        if raw.get("isArchived") or raw.get("isDraft"):
            continue
        field_data = raw.get("fieldData") or {}
        items.append(_normalize_item(field_data, meta))
    items.sort(key=lambda x: x["sortDate"])
    return items

def export_pv_evac():
    collection_id, collection_slug = _find_pv_evac_collection_id()
    if not collection_id:
        raise RuntimeError("Could not find PV evac Webflow collection")
    print(f"PV evac collection: {collection_id} ({collection_slug})")
    meta = {
        "collection_id": collection_id,
        "corpus_key": "pv-evacuation",
        "old_path_prefix": "/pv-evac-docs",
        "viewer_variant": "van11y",
    }
    items_raw = webflow_cms_list_items(collection_id, include_archived=False, verbose=False)
    items = []
    os.makedirs(PV_EVAC_MD_DIR, exist_ok=True)
    for raw in items_raw or []:
        if raw.get("isArchived") or raw.get("isDraft"):
            continue
        field_data = raw.get("fieldData") or {}
        item = _normalize_item(field_data, meta)
        md = item.pop("markdown", None) or field_data.get("markdown-content") or ""
        if not md:
            for k, v in field_data.items():
                if "markdown" in k.lower() and isinstance(v, str) and len(v) > 200:
                    md = v
                    break
        if md:
            md_path = os.path.join(PV_EVAC_MD_DIR, f"{item['slug']}.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md.replace("<<NL>>", "\n"))
            item["markdownFile"] = f"pv-evac/{item['slug']}.md"
        items.append(item)
    items.sort(key=lambda x: x["sortDate"])
    return items

def write_manifest(filename, items):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(items)} items -> {path}")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    deutsch = export_collection("deutsch", COLLECTIONS["deutsch"])
    fda = export_collection("fda-town-halls", COLLECTIONS["fda-town-halls"])
    sov_index = export_collection("sovereign-child-index", COLLECTIONS["sovereign-child-index"])
    sov_book = export_collection("sovereign-child-book", COLLECTIONS["sovereign-child-book"])
    sovereign = sov_index + sov_book
    sovereign.sort(key=lambda x: x["sortDate"])
    pv = export_pv_evac()
    write_manifest("corpus-deutsch.json", deutsch)
    write_manifest("corpus-fda-town-halls.json", fda)
    write_manifest("corpus-sovereign-child.json", sovereign)
    write_manifest("corpus-pv-evacuation.json", pv)
    print("\nCounts:", len(deutsch), len(fda), len(sov_index), "+", len(sov_book), "sov", len(pv), "pv")

if __name__ == "__main__":
    main()
