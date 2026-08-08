"""Work inventory: group every corpus file in the deutsch manifest into works.

A work = one real-world content item (interview, talk, book, essay...). Files join a
work by base name (filename minus known suffixes); raw-stage folders contribute
inventory-only works. Archive/dupe folders are excluded per docs/graph-spec.md."""
import json
import os
import re
from . import ids

MANIFEST_RELPATH = "manifests/deutsch.manifest.jsonl"
### Folder classification: (prefix under data/deutsch/, collection, kind, layer)
FOLDER_RULES = [
    ("f8_done_qafixed_and_vrb/", "f8_done", "interview", 3),
    ("f8_qafixed_talks/", "talks", "talk", 3),
    ("f8_vrb_talks_only/", "talks_vrb", "talk", 1),
    ("interviews_print_web/", "print_web", "interview", 1),
    ("f9_raw/", "raw", "interview", 0),
    ("f2_work_in_progress/", "pipeline", "interview", 0),
    ("f4_needs_prepqa/", "pipeline", "interview", 0),
    ("f5_run_qa_now/", "pipeline", "interview", 0),
    ("f6_needs_qafixed/", "pipeline", "interview", 0),
]
EXCLUDED_DIRS = ("fx_archive/", "f9_prev", "dd_top-stars_new copy/", "dd_test_files/", "dev-eval/", "dev-multi-q/", "f9_process/", "f7_no-link-copy/")
TOPSTARS_DIR = "dd_top-stars_qa-multi/"

### Manifest loading
def load_manifest(repo_root):
    """Read manifests/deutsch.manifest.jsonl -> list of row dicts."""
    path = os.path.join(repo_root, MANIFEST_RELPATH)
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]
def manifest_sha_index(rows):
    """repo_path -> sha256 for provenance pinning."""
    return {r["repo_path"]: r["sha256"] for r in rows}

### Work grouping
def classify_path(repo_path):
    """Return (collection, kind, layer) for a data/deutsch file path, or None to skip."""
    rel = repo_path[len("data/deutsch/"):]
    for prefix in EXCLUDED_DIRS:
        if rel.startswith(prefix):
            return None
    for prefix, collection, kind, layer in FOLDER_RULES:
        if rel.startswith(prefix):
            return collection, kind, layer
    return None
def normalize_title_tokens(base_name):
    """Token set for fuzzy same-work matching across renamed pipeline stages."""
    title = ids.title_from_base_name(base_name).lower()
    stop = {"with", "the", "a", "an", "of", "on", "and", "interview", "podcast", "by"}
    return {t for t in re.findall(r"[a-z0-9]+", title) if t not in stop}
def jaccard(a, b):
    """Jaccard similarity of two sets."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
def build_inventory(rows):
    """Group manifest rows into works.
    Returns dict base_name -> {base_name, collection, kind, layer_max, formats{suffix: path}}.
    Processed collections (f8*, talks) claim identity first; raw/pipeline files then join an
    existing work when the date matches and title tokens overlap (Jaccard >= 0.5), else they
    create an inventory-only work."""
    works = {}
    deferred = []
    for row in rows:
        path = row["repo_path"]
        if not path.startswith("data/deutsch/") or not path.endswith((".md", ".json")):
            continue
        cls = classify_path(path)
        if cls is None:
            continue
        collection, kind, layer = cls
        base, suffix = ids.split_base_name(os.path.basename(path))
        entry = (base, suffix or "text", path, collection, kind, layer)
        if collection in ("raw", "pipeline"):
            deferred.append(entry)
        else:
            _add_file(works, *entry)
    date_index = {}
    for base, w in works.items():
        d = ids.date_from_base_name(base)
        if d:
            date_index.setdefault(d, []).append(base)
    for base, suffix, path, collection, kind, layer in deferred:
        target = base if base in works else None
        if target is None:
            d = ids.date_from_base_name(base)
            tokens = normalize_title_tokens(base)
            best, best_sim = None, 0.0
            for cand in date_index.get(d, []):
                sim = jaccard(tokens, normalize_title_tokens(cand))
                if sim > best_sim:
                    best, best_sim = cand, sim
            if best_sim >= 0.5:
                target = best
        if target is not None:
            _add_file(works, target, suffix, path, works[target]["collection"], works[target]["kind"], layer)
        else:
            _add_file(works, base, suffix, path, collection, kind, layer)
            d = ids.date_from_base_name(base)
            if d:
                date_index.setdefault(d, []).append(base)
    return works
def _add_file(works, base, suffix, path, collection, kind, layer):
    """Attach one file to a work, creating the work if new."""
    w = works.setdefault(base, {"base_name": base, "collection": collection, "kind": kind, "layer_max": 0, "formats": {}})
    if suffix in w["formats"]:
        key = suffix
        n = 2
        while "%s-%d" % (key, n) in w["formats"]:
            n += 1
        suffix = "%s-%d" % (key, n)
    w["formats"][suffix] = path
    w["layer_max"] = max(w["layer_max"], layer)
def topstars_paths(rows):
    """base_name -> repo path of the work's _qa-topstars.md selection file."""
    out = {}
    for row in rows:
        path = row["repo_path"]
        rel = path[len("data/deutsch/"):] if path.startswith("data/deutsch/") else ""
        if rel.startswith(TOPSTARS_DIR) and path.endswith("_qa-topstars.md"):
            base, _ = ids.split_base_name(os.path.basename(path))
            out[base] = path
    return out
