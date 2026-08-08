"""Graph-conditioned content generation pipeline for Deutsch Content Forge."""
import json
import re
from dgraph import divergence
from dgraph import grounding
from dgraph import llm_util
from ctools import config as ctools_config
from . import config
from . import render

CITE_RE = re.compile(r"\[((?:qa|concept|chapter|claim|excerpt|category|topic|work|book):[^\]\s]+)\]")
HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)

### Knobs
def _clamp_tone(value):
    """Normalize tone level."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = ctools_config.DEFAULT_TONE
    return value if value in ctools_config.TONES else ctools_config.DEFAULT_TONE
def _dedupe(items, limit=None):
    """Order-preserving string dedupe with optional cap."""
    out, seen = [], set()
    for item in items or []:
        if not isinstance(item, str) or not item.strip() or item in seen:
            continue
        seen.add(item)
        out.append(item)
        if limit and len(out) >= limit:
            break
    return out

### Routing
def _catalog_maps(catalog):
    """Exact-label maps for topic and category catalogs."""
    return ({t["label"]: t["id"] for t in catalog["topics"]},
            {c["label"]: c["id"] for c in catalog["categories"]})
def _labels_for_ids(graph, ids):
    """Resolve graph ids to labels."""
    return [graph["nodes"].get(node_id, {}).get("label", node_id) for node_id in ids]
def _fallback_prompt(description, catalog):
    """Prompt for the one forge-specific wider routing call."""
    topic_labels = ", ".join(t["label"] for t in catalog["topics"])
    category_labels = ", ".join(c["label"] for c in catalog["categories"])
    return (
        "Route this Content Forge description to a Deutsch graph context package. Use exact labels only. "
        "Pick up to 8 TOPICS from the topic catalog, up to 2 CATEGORIES from the category catalog, and up to 3 "
        "CONCEPT_NEEDLES for book-term lookup. Prefer labels directly needed to ground the requested content. "
        "Empty arrays are allowed when nothing fits.\n\nDESCRIPTION:\n%s\n\nTOPIC LABELS:\n%s\n\nCATEGORY LABELS:\n%s\n\n"
        "Return ONLY JSON: {\"topics\": [\"exact topic label\"], \"categories\": [\"exact category label\"], "
        "\"concept_needles\": [\"keyword\"]}"
    ) % (description, topic_labels, category_labels)
def _fallback_route(description, catalog, model=None, chat=None):
    """One wider routing call for forge when the shared router under-selects topics."""
    chat = chat or llm_util.chat
    topic_ids, category_ids = _catalog_maps(catalog)
    data = llm_util.json_from(chat([{"role": "user", "content": _fallback_prompt(description, catalog)}], model=model))
    if isinstance(data, dict) and "routes" in data and data["routes"]:
        data = data["routes"][0]
    if not isinstance(data, dict):
        data = {}
    topics = data.get("topics", [])
    categories = data.get("categories", [])
    needles = data.get("concept_needles", [])
    return {"topics": [topic_ids[label] for label in topics if label in topic_ids][:8] if isinstance(topics, list) else [],
            "categories": [category_ids[label] for label in categories if label in category_ids][:2] if isinstance(categories, list) else [],
            "concept_needles": _dedupe(needles, limit=3) if isinstance(needles, list) else []}
def _merge_route(first, extra):
    """Merge shared-router output with wider forge-router output."""
    topics = _dedupe(first.get("topics", []) + extra.get("topics", []), limit=8)
    categories = _dedupe(extra.get("categories", []), limit=2)
    needles = _dedupe(first.get("concept_needles", []) + extra.get("concept_needles", []), limit=3)
    return {"topics": topics, "categories": categories, "concept_needles": needles}
def route_description(description, graph, model=None, chat=None):
    """Route a freeform content description to graph topics, categories, and concept needles."""
    catalog = grounding.topic_catalog(graph)
    claim = {"id": "forge:description", "text": description, "quote": description}
    routes = divergence.route_claims([claim], catalog, model=model, chat=chat)
    first = routes[0] if routes else {"topics": [], "concept_needles": []}
    routing = {"topics": first.get("topics", []), "categories": [], "concept_needles": first.get("concept_needles", []),
               "fallback_used": False, "router_calls": 1}
    if len(routing["topics"]) < 4:
        extra = _fallback_route(description, catalog, model=model, chat=chat)
        merged = _merge_route(routing, extra)
        routing.update(merged)
        routing["fallback_used"] = True
        routing["router_calls"] = 2
    routing["topic_labels"] = _labels_for_ids(graph, routing["topics"])
    routing["category_labels"] = _labels_for_ids(graph, routing["categories"])
    return routing

### Grounding package
def _add_manifest_node(nodes, seen, node):
    """Append one retrieved node once."""
    node_id = node.get("id")
    if not node_id or node_id in seen:
        return
    seen.add(node_id)
    nodes.append(node)
def package_manifest(package):
    """Record source nodes retrieved into the prompt context package."""
    nodes, seen = [], set()
    for item in package.get("qa", []):
        _add_manifest_node(nodes, seen, {"id": item.get("id"), "type": "qa", "label": item.get("question", ""),
                                         "work": item.get("work_label", ""), "youtube_ts_url": item.get("youtube_ts_url", ""),
                                         "source_area": "qa"})
    for claim in package.get("claims", []):
        _add_manifest_node(nodes, seen, {"id": claim.get("id"), "type": "claim", "label": claim.get("claim", ""),
                                         "category": claim.get("category", ""), "source_area": "claim"})
        for excerpt in claim.get("excerpts", []):
            _add_manifest_node(nodes, seen, {"id": excerpt.get("id"), "type": "excerpt", "label": excerpt.get("text", ""),
                                             "claim": claim.get("id"), "source_area": "excerpt"})
    for concept in package.get("concepts", []):
        _add_manifest_node(nodes, seen, {"id": concept.get("id"), "type": "concept", "label": concept.get("label", ""),
                                         "definition": concept.get("definition", ""), "source_area": "concept"})
    counts = {}
    for node in nodes:
        counts[node["type"]] = counts.get(node["type"], 0) + 1
    return {"nodes": nodes, "node_ids": [node["id"] for node in nodes], "counts": counts,
            "corpus_available": bool(package.get("corpus_available"))}
def _grounding_text(package):
    """Render the grounding package as prompt source material."""
    parts = []
    for item in package.get("qa", []):
        parts.append("SOURCE %s\nWORK: %s\nQUESTION: %s\nANSWER: %s" % (
            item["id"], item.get("work_label", ""), item.get("question", ""),
            item.get("answer") or "(verbatim answer unavailable; use question and metadata only)"))
    for claim in package.get("claims", []):
        text = "SOURCE %s\nCLAIM: %s" % (claim["id"], claim.get("claim", ""))
        for excerpt in claim.get("excerpts", []):
            text += "\nEXCERPT %s: %s" % (excerpt.get("id"), excerpt.get("text", ""))
        parts.append(text)
    for concept in package.get("concepts", []):
        parts.append("SOURCE %s\nTERM: %s\nDEFINITION: %s" % (
            concept["id"], concept.get("label", ""), concept.get("definition") or ""))
    return "\n\n".join(parts) if parts else "(no Deutsch graph source material matched this description)"

### Generation
def _word_count(text):
    """Approximate prose word count."""
    return len(re.findall(r"\b[\w'-]+\b", text or ""))
def _system_prompt(fmt, length, tone, package):
    """Assemble the generation system prompt."""
    format_row = config.FORMATS[fmt]
    length_row = config.LENGTHS[length]
    tone_row = ctools_config.TONES[tone]
    return "\n\n".join([
        "You are Content Forge, a graph-conditioned drafting tool for new text based on Deutsch graph sources.",
        "FORMAT (%s): %s" % (format_row["label"], format_row["instruction"]),
        "LENGTH TARGET: about %d words. Stay close to the target and avoid padding." % length_row["words"],
        "TONE (%s): %s" % (tone_row["label"], tone_row["instruction"]),
        "CITATION DUTY: Use only the SOURCE blocks below for claims about David Deutsch's ideas. Ground every substantive section in these sources and cite node ids inline in square brackets, e.g. [qa:2013-06-25_nautilus-why-its-good-to-be-wrong:000]. If the selected sources do not cover part of the requested description, say that the selected graph sources do not cover it rather than inventing a Deutsch position. Output only the requested Markdown piece. Use ##-level section headings for every section.",
        "SOURCE MATERIAL:\n\n" + _grounding_text(package),
    ])
def _generate_once(description, system_prompt, model=None, chat=None):
    """Run one generation call."""
    chat = chat or llm_util.chat
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": "DESCRIPTION:\n" + description}]
    return chat(messages, model=model).strip()
def generate_piece(description, fmt, length, tone, package, model=None, chat=None):
    """Generate a piece, with one soft retry when the answer is far over target."""
    target = config.LENGTHS[length]["words"]
    system_prompt = _system_prompt(fmt, length, tone, package)
    piece = _generate_once(description, system_prompt, model=model, chat=chat)
    notes = []
    words = _word_count(piece)
    if words > int(target * 1.6):
        retry_prompt = system_prompt + "\n\nLENGTH REVISION: The previous draft was %d words, which is too long. Rewrite once at about %d words while preserving ## headings, inline citations, and honest gaps." % (words, target)
        piece = _generate_once(description, retry_prompt, model=model, chat=chat)
        new_words = _word_count(piece)
        if new_words > int(target * 1.6):
            notes.append({"type": "length", "note": "Kept the retry even though it remained over the soft length limit.", "target_words": target, "actual_words": new_words})
        else:
            notes.append({"type": "length", "note": "Regenerated once after the first draft exceeded the soft length limit.", "target_words": target, "first_words": words, "actual_words": new_words})
    return piece, notes

### Citation sidecar
def _resolve_citation(node_id, citation_index):
    """Normalize one graph citation entry for UI and sidecar rendering."""
    entry = citation_index.get(node_id, {})
    return {"id": node_id, "type": entry.get("type", ""), "label": entry.get("label", node_id),
            "work": entry.get("work_label") or entry.get("work") or "",
            "youtube_ts_url": entry.get("youtube_ts_url") or entry.get("url") or ""}
def _section_chunks(text):
    """Split markdown into sections keyed by ## headings."""
    matches = list(HEADING_RE.finditer(text or ""))
    if not matches:
        return [{"heading": "Untitled", "text": text or ""}]
    chunks = []
    if text[:matches[0].start()].strip():
        chunks.append({"heading": "Preamble", "text": text[:matches[0].start()].strip()})
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        chunks.append({"heading": match.group(1).strip(), "text": text[match.start():end].strip()})
    return chunks
def _clean_invalid_citations(text, citation_index):
    """Strip unknown graph citations from a markdown section."""
    invalid = []
    def repl(match):
        node_id = match.group(1)
        if node_id in citation_index:
            return match.group(0)
        invalid.append(node_id)
        return ""
    cleaned = CITE_RE.sub(repl, text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r" +\n", "\n", cleaned)
    return cleaned.strip(), invalid
def _section_body(text):
    """Section text without the heading line."""
    return HEADING_RE.sub("", text, count=1).strip()
def _valid_ids(text, citation_index):
    """Order-preserving valid citation ids in a text span."""
    ids = []
    for node_id in CITE_RE.findall(text):
        if node_id in citation_index and node_id not in ids:
            ids.append(node_id)
    return ids
def _retrieved_but_uncited(manifest, cited_ids):
    """Manifest nodes that were available to the model but not cited."""
    cited = set(cited_ids)
    return [node for node in manifest.get("nodes", []) if node.get("id") not in cited]
def build_sidecar(piece, citation_index, manifest, provenance, knobs, routing, notes):
    """Validate citations, strip invalid ids, and build the sidecar."""
    sections, cleaned_sections, invalid_rows, all_cited = [], [], [], []
    for chunk in _section_chunks(piece):
        cleaned, invalid = _clean_invalid_citations(chunk["text"], citation_index)
        ids = _valid_ids(cleaned, citation_index)
        all_cited.extend(ids)
        for node_id in invalid:
            invalid_rows.append({"section": chunk["heading"], "id": node_id})
        body = _section_body(cleaned)
        sections.append({"heading": chunk["heading"], "word_count": _word_count(CITE_RE.sub("", body)),
                         "cited_node_ids": ids, "citations": [_resolve_citation(node_id, citation_index) for node_id in ids],
                         "invalid_citations": _dedupe(invalid), "grounded": bool(ids)})
        cleaned_sections.append(cleaned)
    cleaned_piece = "\n\n".join(section for section in cleaned_sections if section).strip()
    manifest = dict(manifest)
    manifest["retrieved_but_uncited"] = _retrieved_but_uncited(manifest, all_cited)
    coverage = {"n_sections": len(sections), "n_grounded": len([s for s in sections if s["grounded"]]),
                "n_ungrounded": len([s for s in sections if not s["grounded"]]),
                "n_citations": sum(len(s["cited_node_ids"]) for s in sections),
                "n_invalid": len(invalid_rows)}
    sidecar = {"provenance": provenance, "knobs": knobs, "routing": routing, "sections": sections,
               "invalid_citations": invalid_rows, "context_package": manifest, "coverage": coverage,
               "notes": notes, "synthetic_content": render.DISCLOSURE}
    return cleaned_piece, sidecar

### Pipeline
def _source_name(description):
    """Stable short run label."""
    words = " ".join((description or "").split())
    return words[:80] if words else "content-forge"
def run(description, fmt=None, length=None, tone=None, model=None, chat=None, graph=None, citation_index=None, repo_root=None, generated_at=""):
    """Full forge pipeline from description to markdown plus citations sidecar."""
    if not (description or "").strip():
        raise ValueError("empty description")
    graph = graph or grounding.load_graph()
    citation_index = citation_index or grounding.citation_index(graph)
    repo_root = repo_root or config.REPO_ROOT
    fmt = config.clean_format(fmt)
    length = config.clean_length(length)
    tone = _clamp_tone(tone)
    routing = route_description(description, graph, model=model, chat=chat)
    package = grounding.build_grounding(graph, routing["topics"], routing["categories"], routing["concept_needles"], repo_root=repo_root)
    manifest = package_manifest(package)
    piece, notes = generate_piece(description, fmt, length, tone, package, model=model, chat=chat)
    tone_row = ctools_config.TONES[tone]
    provenance = {"description": description, "tool": "content-forge", "model": model or "", "generated_at": generated_at}
    knobs = {"format": fmt, "format_label": config.FORMATS[fmt]["label"], "length": length,
             "target_words": config.LENGTHS[length]["words"], "tone": tone, "tone_label": tone_row["label"]}
    cleaned_piece, sidecar = build_sidecar(piece, citation_index, manifest, provenance, knobs, routing, notes)
    markdown, sidecar_md = render.assemble(cleaned_piece, sidecar, provenance, knobs)
    return {"source_name": _source_name(description), "title": _source_name(description), "description": description,
            "generated_at": generated_at, "piece_markdown": cleaned_piece, "markdown": markdown,
            "sidecar_markdown": sidecar_md, "sidecar": sidecar, "routing": routing,
            "package_manifest": sidecar["context_package"], "coverage": sidecar["coverage"],
            "notes": notes, "knobs": knobs, "summary": sidecar["coverage"]}
def run_from_request(payload, state):
    """Server entry point: payload description -> full result dict."""
    description = payload.get("description") or ""
    return run(description, fmt=payload.get("format"), length=payload.get("length"), tone=payload.get("tone"),
               model=payload.get("model"), chat=state.get("chat"), graph=state.get("graph"), citation_index=state.get("citation_index"),
               repo_root=state.get("repo_root"), generated_at=state.get("generated_at", ""))
