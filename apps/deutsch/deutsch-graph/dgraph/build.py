"""Full deterministic graph build. See docs/graph-spec.md for the output contract."""
import hashlib
import json
import os
from . import GRAPH_BUILDER_VERSION
from . import ids
from . import inventory
from . import parse_books
from . import parse_corpus
from . import parse_terms
from . import parse_well

### Paths
def app_root():
    """apps/deutsch/deutsch-graph/"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def repo_root():
    """Monorepo root (3 levels above the app)."""
    return os.path.dirname(os.path.dirname(os.path.dirname(app_root())))
def graph_dir():
    """Committed graph output dir."""
    return os.path.join(app_root(), "graph")

### Overlays
def load_overlay_jsonl(name):
    """Load overlays/<name> (committed curation inputs); missing file -> []. Comment lines starting with # allowed."""
    path = os.path.join(app_root(), "overlays", name)
    if not os.path.exists(path):
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(json.loads(line))
    return out
def topic_merge_map():
    """Label-level topic merges from overlays/topics_merge.jsonl: {'from': label, 'to': label}."""
    return {row["from"].lower(): row["to"] for row in load_overlay_jsonl("topics_merge.jsonl")}

### Build steps
def read_local(root, rel_path):
    """Read a repo-relative corpus file; returns None when not fetched locally."""
    path = os.path.join(root, rel_path)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()
def resolve_topics(labels, merges, topic_surface):
    """Apply overlay merges, dedup case-insensitively, record surface forms; return topic ids."""
    out = []
    for label in labels:
        label = merges.get(label.lower(), label)
        tid = ids.topic_id(label)
        if not tid[len("topic:"):]:
            continue
        topic_surface.setdefault(tid, {})
        counts = topic_surface[tid]
        counts[label] = counts.get(label, 0) + 1
        if tid not in out:
            out.append(tid)
    return out
def parse_work_qa(root, work, merges, topic_surface, diagnostics):
    """Parse a work's _qafixed (+ _qa-multi, + _qa-topstars) into qa node dicts."""
    qafixed_path = work["formats"].get("qafixed")
    text = read_local(root, qafixed_path)
    if text is None:
        diagnostics.append("MISSING LOCAL FILE (run fetch): " + qafixed_path)
        return []
    quirks = []
    meta, blocks = parse_corpus.parse_qa_file(text, quirks)
    for quirk in quirks:
        diagnostics.append("data quirk in %s: %s" % (qafixed_path, quirk))
    if blocks is None:
        diagnostics.append("no '### qa' heading: " + qafixed_path)
        return []
    work["link_youtube"] = work.get("link_youtube") or meta.get("link youtube")
    multi_by_ts = {}
    qa_multi_path = work["formats"].get("qa-multi")
    if qa_multi_path:
        mtext = read_local(root, qa_multi_path)
        if mtext is not None:
            _, mblocks = parse_corpus.parse_qa_file(mtext)
            stem = os.path.splitext(os.path.basename(qa_multi_path))[0].replace(" ", "_")
            for mb in mblocks or []:
                mb["vector_id_base"] = "%s_%d" % (stem, mb["ordinal"])
                multi_by_ts.setdefault(mb["timestamp_sec"], []).append(mb)
    starred_ts = set()
    topstars_path = work["formats"].get("qa-topstars")
    if topstars_path:
        stext = read_local(root, topstars_path)
        if stext is not None:
            _, sblocks = parse_corpus.parse_qa_file(stext)
            starred_ts = {sb["timestamp_sec"] for sb in sblocks or [] if sb["timestamp_sec"] is not None}
    wslug = ids.work_slug(work["base_name"])
    qa_nodes = []
    for block in blocks:
        mates = multi_by_ts.get(block["timestamp_sec"], [])
        mate = mates.pop(0) if mates else None
        topics = resolve_topics(block["topics"], merges, topic_surface)
        qa_nodes.append({
            "id": ids.qa_id(wslug, block["ordinal"]),
            "type": "qa",
            "label": block["questions"][0][:120],
            "work": ids.work_id(work["base_name"]),
            "question": block["questions"][0],
            "questions_alt": (mate["questions"][1:] if mate and len(mate["questions"]) > 1 else block["questions"][1:]),
            "timestamp_sec": block["timestamp_sec"],
            "youtube_ts_url": block["youtube_ts_url"],
            "topics": topics,
            "stars": block["stars"],
            "starred": block["timestamp_sec"] in starred_ts,
            "answer_pointer": {"path": qafixed_path, "block": block["ordinal"]},
            "answer_chars": block["answer_chars"],
            "vector_id_base": mate["vector_id_base"] if mate else None,
        })
    return qa_nodes
def essay_work_nodes(root, rows, diagnostics):
    """Work nodes for essays/, papers/, and TCS posts."""
    works = []
    for row in sorted(rows, key=lambda r: r["repo_path"]):
        path = row["repo_path"]
        if path.startswith("data/deutsch/essays/") and path.endswith(".md"):
            rel = path[len("data/deutsch/essays/"):]
            if rel.startswith("tcs/"):
                kind, collection, by_dd = "tcs_post", "tcs", "/dd/" in path
            elif rel.startswith("about deutsch/"):
                kind, collection, by_dd = "about", "about", False
            else:
                kind, collection, by_dd = "essay", "essays", True
        elif path.startswith("data/deutsch/papers/"):
            kind, collection, by_dd = "paper", "papers", True
        else:
            continue
        base = os.path.splitext(os.path.basename(path))[0]
        info = {"link": None, "date": None, "publication": None}
        if path.endswith(".md"):
            text = read_local(root, path)
            if text is not None:
                info = parse_corpus.parse_essay(text)
        works.append({
            "id": ids.work_id(base), "type": "work", "kind": kind,
            "label": ids.title_from_base_name(base), "title": ids.title_from_base_name(base),
            "date": ids.date_from_base_name(base) or info["date"], "by_deutsch": by_dd,
            "base_name": base, "formats": {"text": path}, "link_youtube": None,
            "link": info["link"], "layer_max": 4 if kind != "paper" else 0,
            "qa_count": 0, "starred_count": 0, "collection": collection,
        })
    return works
### Deutsch Well categories
TOPICS_IMPORTANT_TO_CATEGORY = {
    "Brain": "Human Brain", "Computer": "Computers", "Creativity": "Creativity",
    "Explanation": "Explanations", "Knowledge": "Explanatory Knowledge", "Math": "Mathematics",
    "Mind": "Human Mind", "People": "People", "Philosophy": "Philosophy", "Problems": "Problems",
    "Progress": "Progress", "Reality": "Reality", "Science": "Science", "Truth": "Truth",
    "Universality": "Universality",
}
def topic_slug_variants(label):
    """Slug + naive singular/plural variants for automatic category->topic matching."""
    s = ids.slugify(label)
    out = {s}
    if s.endswith("s"):
        out.add(s[:-1])
    else:
        out.add(s + "s")
    return out
def build_well_layer(root, source_nodes, chapters, topic_ids, diagnostics):
    """Categories, claims, excerpts from the Deutsch Well vault + overlay additions.
    Returns (category_nodes, claim_nodes, excerpts_by_cat, category_topic_edges)."""
    works_by_base = {n["base_name"]: n for n in source_nodes}
    for row in load_overlay_jsonl("aliases.jsonl"):
        if row.get("type") == "work" and row["to"] in works_by_base:
            works_by_base.setdefault(row["from"], works_by_base[row["to"]])
    works_by_date = {}
    for n in source_nodes:
        d = ids.date_from_base_name(n["base_name"])
        if d:
            works_by_date.setdefault(d, []).append(n)
    chapters_by_key = {(c["number"], ids.slugify(c["title"])): c for c in chapters}
    overlay_bridge = {}
    for row in load_overlay_jsonl("category_topics.jsonl"):
        overlay_bridge.setdefault(row["category"], []).extend(row["topics"])
    extras = load_overlay_jsonl("categories_extra.jsonl")
    important = {t["term"]: t for t in parse_terms.load_terms(root, diagnostics)["important"]}
    important_by_cat = {}
    for term, row in important.items():
        cat_label = TOPICS_IMPORTANT_TO_CATEGORY.get(term)
        if cat_label:
            important_by_cat[cat_label] = row
        else:
            diagnostics.append("terms: Topics-Important entry with no category mapping (not imported): " + row["path"])
    category_nodes, claim_nodes, excerpts_by_cat, edges = [], [], {}, []
    def bridge_topics(label, extra_slugs):
        resolved, unresolved = [], []
        for slug in sorted(topic_slug_variants(label) | set(extra_slugs)):
            tid = "topic:" + slug
            if tid in topic_ids:
                if tid not in resolved:
                    resolved.append(tid)
            elif slug in extra_slugs:
                unresolved.append(slug)
        for slug in unresolved:
            diagnostics.append("well: unresolved bridge topic slug '%s' for category '%s'" % (slug, label))
        return resolved
    for cat in parse_well.load_well(root, diagnostics):
        cslug = ids.slugify(cat["label"])
        cid = "category:" + cslug
        topics = bridge_topics(cat["label"], overlay_bridge.get(cat["label"], []))
        imp = important_by_cat.get(cat["label"])
        cat_excerpts = []
        for claim_idx, claim in enumerate(cat["claims"]):
            clid = "claim:%s/%02d" % (cslug, claim_idx)
            claim_nodes.append({
                "id": clid, "type": "claim", "label": claim["text"][:120], "text": claim["text"],
                "category": cid, "excerpt_count": len(claim["excerpts"]), "path": claim["path"],
            })
            for exc_idx, exc in enumerate(claim["excerpts"]):
                work_id_ref, chapter_id_ref = parse_well.resolve_source_ref(exc["source_ref"], works_by_base, chapters_by_key, works_by_date)
                if exc["source_ref"] and not work_id_ref and not chapter_id_ref:
                    diagnostics.append("well: unresolved excerpt source '%s' (%s)" % (exc["source_ref"], exc["path"]))
                cat_excerpts.append({
                    "id": "excerpt:%s/%02d/%03d" % (cslug, claim_idx, exc_idx),
                    "type": "excerpt", "label": exc["text"][:80],
                    "claim": clid, "category": cid,
                    "text_preview": exc["text"][:240], "text_chars": len(exc["text"]),
                    "source_ref": exc["source_ref"], "source_work": work_id_ref,
                    "source_chapter": chapter_id_ref, "path": exc["path"],
                })
        if cat_excerpts:
            excerpts_by_cat[cslug] = cat_excerpts
        category_nodes.append({
            "id": cid, "type": "category", "label": cat["label"],
            "definition": (important_by_cat.get(cat["label"]) or {}).get("definition"),
            "origin": "deutsch-well-2023", "source_path": cat["path"],
            "claim_count": len(cat["claims"]), "excerpt_count": len(cat_excerpts),
            "topics": topics,
        })
        for tid in topics:
            edges.append({"src": cid, "dst": tid, "type": "category_topic"})
        if imp:
            important_by_cat.pop(cat["label"], None)
    for extra in extras:
        cslug = ids.slugify(extra["label"])
        cid = "category:" + cslug
        topics = bridge_topics(extra["label"], extra.get("topics", []))
        imp = important_by_cat.get(extra["label"])
        category_nodes.append({
            "id": cid, "type": "category", "label": extra["label"],
            "definition": imp["definition"] if imp else extra.get("definition"),
            "origin": "v0.2-addition", "source_path": None,
            "claim_count": 0, "excerpt_count": 0, "topics": topics,
        })
        for tid in topics:
            edges.append({"src": cid, "dst": tid, "type": "category_topic"})
    return (sorted(category_nodes, key=lambda n: n["id"]),
            sorted(claim_nodes, key=lambda n: n["id"]),
            excerpts_by_cat,
            sorted(edges, key=lambda e: (e["src"], e["dst"])))
def enrich_concepts(concepts, concept_edges, root, diagnostics, extra_inputs=None):
    """Add missing concepts from the terms collection (Terms - BOI / FOR / BOIxyz).
    Book-parsed concepts win; term-folder entries fill gaps, with chapter refs when stated."""
    terms = parse_terms.load_terms(root, diagnostics)
    if extra_inputs is not None:
        for rows_list in terms.values():
            extra_inputs.update(r["path"] for r in rows_list)
    seen = {c["id"] for c in concepts}
    plan = [("boi", "boi", "terms-boi"), ("for", "for", "terms-for"), ("boixyz", "boi", "terms-boixyz")]
    for key, book_code, source_tag in plan:
        for row in terms[key]:
            tid = ids.concept_id(book_code, row["term"])
            if not tid.split("/")[-1] or tid in seen:
                continue
            seen.add(tid)
            chapter_ref = None
            if row["chapter_num"]:
                chapter_ref = ids.chapter_id(book_code, row["chapter_num"])
            concepts.append({
                "id": tid, "type": "concept", "label": row["term"], "definition": row["definition"],
                "source_work": "work:" + book_code, "source_path": row["path"],
                "chapter": chapter_ref, "source": source_tag,
            })
            concept_edges.append({"src": tid, "dst": "work:" + book_code, "type": "concept_of"})
def build_graph(root=None, verbose=True):
    """Run the full build; returns the result dict written to disk by write_graph."""
    root = root or repo_root()
    diagnostics = []
    rows = inventory.load_manifest(root)
    sha_index = inventory.manifest_sha_index(rows)
    merges = topic_merge_map()
    topic_surface = {}
    works_map = inventory.build_inventory(rows)
    topstars = inventory.topstars_paths(rows)
    source_nodes, all_qa = [], {}
    for base in sorted(works_map):
        w = works_map[base]
        if base in topstars:
            w["formats"].setdefault("qa-topstars", topstars[base])
        node = {
            "id": ids.work_id(base), "type": "work", "kind": w["kind"],
            "label": ids.title_from_base_name(base), "title": ids.title_from_base_name(base),
            "date": ids.date_from_base_name(base), "by_deutsch": True,
            "base_name": base, "formats": w["formats"], "link_youtube": None, "link": None,
            "layer_max": w["layer_max"], "qa_count": 0, "starred_count": 0,
            "collection": w["collection"],
        }
        if "qafixed" in w["formats"]:
            qa_nodes = parse_work_qa(root, node, merges, topic_surface, diagnostics)
            node["qa_count"] = len(qa_nodes)
            node["starred_count"] = sum(1 for q in qa_nodes if q["starred"])
            if qa_nodes:
                all_qa[ids.work_slug(base)] = qa_nodes
        source_nodes.append(node)
    source_nodes.extend(essay_work_nodes(root, rows, diagnostics))
    book_works, chapters, concepts, chapter_edges, concept_edges = parse_books.build_book_nodes(root, diagnostics)
    source_nodes.extend(book_works)
    extra_inputs = set()
    enrich_concepts(concepts, concept_edges, root, diagnostics, extra_inputs)
    topic_nodes = build_topic_nodes(topic_surface, all_qa)
    work_topic_edges = build_work_topic_edges(all_qa)
    topic_ids = {t["id"] for t in topic_nodes}
    category_nodes, claim_nodes, excerpts_by_cat, category_topic_edges = build_well_layer(
        root, source_nodes, chapters, topic_ids, diagnostics)
    result = {
        "nodes": {
            "sources": sorted(source_nodes, key=lambda n: n["id"]),
            "topics": topic_nodes,
            "concepts": sorted(concepts, key=lambda n: n["id"]),
            "chapters": sorted(chapters, key=lambda n: n["id"]),
            "categories": category_nodes,
            "claims": claim_nodes,
        },
        "qa": all_qa,
        "excerpts": excerpts_by_cat,
        "edges": {
            "work_topic": work_topic_edges,
            "chapter_of": sorted(chapter_edges, key=lambda e: (e["src"], e["dst"])),
            "concept_of": sorted(concept_edges, key=lambda e: (e["src"], e["dst"])),
            "category_topic": category_topic_edges,
        },
        "diagnostics": diagnostics,
        "sha_index": sha_index,
        "extra_inputs": sorted(extra_inputs),
    }
    if verbose:
        for d in diagnostics:
            print("DIAG:", d)
    return result
def build_topic_nodes(topic_surface, all_qa):
    """Topic nodes with canonical label = most frequent surface form."""
    qa_counts, work_sets = {}, {}
    for wslug, qa_nodes in all_qa.items():
        for q in qa_nodes:
            for tid in q["topics"]:
                qa_counts[tid] = qa_counts.get(tid, 0) + 1
                work_sets.setdefault(tid, set()).add(q["work"])
    nodes = []
    for tid in sorted(topic_surface):
        surfaces = topic_surface[tid]
        label = sorted(surfaces.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        aliases = sorted(s for s in surfaces if s != label)
        nodes.append({
            "id": tid, "type": "topic", "label": label, "aliases": aliases,
            "qa_count": qa_counts.get(tid, 0), "work_count": len(work_sets.get(tid, ())),
        })
    return nodes
def build_work_topic_edges(all_qa):
    """Aggregate qa topics into weighted work->topic edges."""
    weights = {}
    for wslug, qa_nodes in all_qa.items():
        for q in qa_nodes:
            for tid in q["topics"]:
                key = (q["work"], tid)
                weights[key] = weights.get(key, 0) + 1
    return [{"src": src, "dst": dst, "type": "work_topic", "weight": w}
            for (src, dst), w in sorted(weights.items())]

### Output writing
def dump_jsonl(items, path):
    """Deterministic JSONL write (sorted keys, no timestamps)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, sort_keys=True, ensure_ascii=False, default=sorted) + "\n")
def file_sha256(path):
    """Direct sha256 for inputs missing from the manifest."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
def collect_inputs(result, root):
    """Every corpus path referenced by the built graph, pinned by manifest sha256.
    Unmanifested paths (e.g. deutsch-well_2023/, terms/ before their manifest rows land) are
    hashed directly and rolled up per top-level folder to keep build-manifest.json compact."""
    paths = set()
    for node in result["nodes"]["sources"]:
        paths.update(node["formats"].values())
    for ch in result["nodes"]["chapters"]:
        paths.add(ch["path"])
    for co in result["nodes"]["concepts"]:
        paths.add(co["source_path"])
    for excs in result["excerpts"].values():
        for e in excs:
            paths.add(e["path"])
    paths.update(result.get("extra_inputs", []))
    inputs = []
    rollups = {}
    for path in sorted(paths):
        sha = result["sha_index"].get(path)
        if sha is not None:
            inputs.append({"path": path, "sha256": sha})
            continue
        local = os.path.join(root, path)
        sha = file_sha256(local) if os.path.exists(local) else ""
        parts = path.split("/")
        rollup_dir = "/".join(parts[:3]) if len(parts) > 3 else path
        rollups.setdefault(rollup_dir, []).append(sha)
    for rollup_dir in sorted(rollups):
        shas = rollups[rollup_dir]
        combined = hashlib.sha256("".join(sorted(shas)).encode()).hexdigest()
        inputs.append({"dir": rollup_dir, "file_count": len(shas), "sha256_rollup": combined, "unmanifested": True})
    return inputs
def write_graph(result, out_dir=None, root=None):
    """Write nodes/edges/build-manifest/GRAPH.md under graph/."""
    out_dir = out_dir or graph_dir()
    root = root or repo_root()
    dump_jsonl(result["nodes"]["sources"], os.path.join(out_dir, "nodes", "sources.jsonl"))
    dump_jsonl(result["nodes"]["topics"], os.path.join(out_dir, "nodes", "topics.jsonl"))
    dump_jsonl(result["nodes"]["concepts"], os.path.join(out_dir, "nodes", "concepts.jsonl"))
    dump_jsonl(result["nodes"]["chapters"], os.path.join(out_dir, "nodes", "chapters.jsonl"))
    dump_jsonl(result["nodes"]["categories"], os.path.join(out_dir, "nodes", "categories.jsonl"))
    dump_jsonl(result["nodes"]["claims"], os.path.join(out_dir, "nodes", "claims.jsonl"))
    qa_dir = os.path.join(out_dir, "nodes", "qa")
    if os.path.isdir(qa_dir):
        for name in os.listdir(qa_dir):
            os.remove(os.path.join(qa_dir, name))
    for wslug in sorted(result["qa"]):
        dump_jsonl(result["qa"][wslug], os.path.join(qa_dir, wslug + ".jsonl"))
    exc_dir = os.path.join(out_dir, "nodes", "excerpts")
    if os.path.isdir(exc_dir):
        for name in os.listdir(exc_dir):
            os.remove(os.path.join(exc_dir, name))
    for cslug in sorted(result["excerpts"]):
        dump_jsonl(result["excerpts"][cslug], os.path.join(exc_dir, cslug + ".jsonl"))
    for name, edges in result["edges"].items():
        dump_jsonl(edges, os.path.join(out_dir, "edges", name + ".jsonl"))
    counts = graph_counts(result)
    manifest = {
        "builder_version": GRAPH_BUILDER_VERSION,
        "counts": counts,
        "inputs": collect_inputs(result, root),
        "diagnostics": sorted(set(result["diagnostics"])),
    }
    with open(os.path.join(out_dir, "build-manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    write_graph_md(result, counts, os.path.join(out_dir, "GRAPH.md"))
    return counts
def graph_counts(result):
    """Node/edge counts by type for the manifest and GRAPH.md."""
    counts = {"nodes": {}, "edges": {}}
    for name, nodes in result["nodes"].items():
        counts["nodes"][name] = len(nodes)
    counts["nodes"]["qa"] = sum(len(v) for v in result["qa"].values())
    counts["nodes"]["excerpts"] = sum(len(v) for v in result["excerpts"].values())
    for name, edges in result["edges"].items():
        counts["edges"][name] = len(edges)
    counts["edges"]["qa_derived"] = counts["nodes"]["qa"]
    return counts
def write_graph_md(result, counts, path):
    """Generated human summary; the PR-review surface for graph rebuilds."""
    lines = []
    lines.append("file: apps/deutsch/deutsch-graph/graph/GRAPH.md")
    lines.append("title: Deutsch Graph — generated build summary (do not hand-edit)")
    lines.append("")
    lines.append("Generated by `build_graph.py build` (builder v%s). Regenerate; never edit." % GRAPH_BUILDER_VERSION)
    lines.append("")
    lines.append("")
    lines.append("## Counts")
    lines.append("| Nodes | # |")
    lines.append("|---|---|")
    for name in sorted(counts["nodes"]):
        lines.append("| %s | %d |" % (name, counts["nodes"][name]))
    lines.append("")
    lines.append("| Edges | # |")
    lines.append("|---|---|")
    for name in sorted(counts["edges"]):
        lines.append("| %s | %d |" % (name, counts["edges"][name]))
    kinds = {}
    layers = {}
    for node in result["nodes"]["sources"]:
        kinds[node["kind"]] = kinds.get(node["kind"], 0) + 1
        layers[node["layer_max"]] = layers.get(node["layer_max"], 0) + 1
    lines.append("")
    lines.append("")
    lines.append("## Works by kind")
    lines.append("| Kind | # |")
    lines.append("|---|---|")
    for kind in sorted(kinds):
        lines.append("| %s | %d |" % (kind, kinds[kind]))
    lines.append("")
    lines.append("")
    lines.append("## Works by max digestion layer")
    lines.append("| Layer | # |")
    lines.append("|---|---|")
    for layer in sorted(layers):
        lines.append("| L%d | %d |" % (layer, layers[layer]))
    lines.append("")
    lines.append("")
    lines.append("## Categories (first-tier layer)")
    lines.append("| Category | Origin | Claims | Excerpts | Bridged topics |")
    lines.append("|---|---|---|---|---|")
    for c in result["nodes"]["categories"]:
        lines.append("| %s | %s | %d | %d | %d |" % (c["label"], c["origin"], c["claim_count"], c["excerpt_count"], len(c["topics"])))
    top = sorted(result["nodes"]["topics"], key=lambda t: (-t["qa_count"], t["id"]))[:30]
    lines.append("")
    lines.append("")
    lines.append("## Top 30 topics by QA count")
    lines.append("| Topic | QA items | Works |")
    lines.append("|---|---|---|")
    for t in top:
        lines.append("| %s | %d | %d |" % (t["label"], t["qa_count"], t["work_count"]))
    if result["diagnostics"]:
        lines.append("")
        lines.append("")
        lines.append("## Build diagnostics")
        for d in sorted(set(result["diagnostics"])):
            lines.append("- " + d)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
