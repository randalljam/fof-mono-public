"""Shared divergence detection over external claims and Deutsch graph grounding."""
import json
import re
from . import grounding
from . import llm_util

VERDICTS = ("agree", "diverge", "no-position")

### Routing
def _chunks(items, size):
    """Yield fixed-size chunks."""
    for idx in range(0, len(items), size):
        yield idx, items[idx:idx + size]
def _claim_payload(claims):
    """Compact claim payload for prompts."""
    payload = []
    for claim in claims:
        payload.append({"id": claim.get("id"), "text": claim.get("text", ""),
                        "speaker": claim.get("speaker"), "quote": claim.get("quote", "")})
    return json.dumps(payload, ensure_ascii=True)
def route_claims(claims, catalog, model=None, chat=None):
    """Route claims to graph topic ids and concept lookup needles."""
    chat = chat or llm_util.chat
    topic_labels = ", ".join(t["label"] for t in catalog["topics"])
    topic_ids = {t["label"]: t["id"] for t in catalog["topics"]}
    routes = [{"topics": [], "concept_needles": []} for _ in claims]
    index_by_id = {claim.get("id"): idx for idx, claim in enumerate(claims) if claim.get("id")}
    for start, chunk in _chunks(claims, 20):
        prompt = (
            "Route each external claim to the Deutsch graph. For each claim, pick up to 3 TOPICS from this exact-label "
            "catalog, most relevant first, and up to 2 CONCEPT_NEEDLES for book-term lookup. Empty topics are allowed "
            "when nothing fits.\n\nTOPIC LABELS:\n%s\n\nCLAIMS JSON:\n%s\n\n"
            "Return ONLY JSON: {\"routes\": [{\"id\": \"clm:001\", \"topics\": [\"exact label\"], "
            "\"concept_needles\": [\"keyword\"]}]}"
        ) % (topic_labels, _claim_payload(chunk))
        data = llm_util.json_from(chat([{"role": "user", "content": prompt}], model=model))
        rows = data.get("routes", []) if isinstance(data, dict) else []
        for row_idx, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            claim_id = row.get("id") or row.get("claim_id")
            target = index_by_id.get(claim_id)
            if target is None and row_idx < len(chunk):
                target = start + row_idx
            if target is None or target >= len(routes):
                continue
            labels = row.get("topics", [])
            needles = row.get("concept_needles", [])
            routes[target] = {
                "topics": [topic_ids[label] for label in labels if label in topic_ids][:3] if isinstance(labels, list) else [],
                "concept_needles": [n for n in needles if isinstance(n, str) and n.strip()][:2] if isinstance(needles, list) else [],
            }
    return routes

### Judging
def _grounding_payload(claim):
    """Compact grounding payload for a claim judgment prompt."""
    items = []
    for item in claim.get("grounding", []):
        row = {"id": item.get("id")}
        for key in ("question", "answer", "claim", "definition", "label", "brief"):
            if item.get(key):
                row[key] = item.get(key)
        items.append(row)
    return items
def _judge_payload(claims):
    """Compact JSON payload for judge prompts."""
    payload = []
    for claim in claims:
        payload.append({"id": claim.get("id"), "text": claim.get("text", ""),
                        "quote": claim.get("quote", ""), "grounding": _grounding_payload(claim)})
    return json.dumps(payload, ensure_ascii=True)
def _clamp(value, low, high, default):
    """Float clamp with fallback."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = default
    return max(low, min(high, value))
def _two_sentences(text):
    """Keep at most two simple sentence spans."""
    if not isinstance(text, str):
        return ""
    parts = re.findall(r"[^.!?]+[.!?]?", text.strip())
    return " ".join(part.strip() for part in parts[:2]).strip()
def _default_judgment():
    """Neutral no-position judgment."""
    return {"verdict": "no-position", "deutsch_position": "", "citations": [], "confidence": 0.0, "note": ""}
def _sanitize_judgment(row, claim):
    """Validate one model judgment against allowed verdicts and grounding ids."""
    out = _default_judgment()
    if not isinstance(row, dict):
        return out
    verdict = row.get("verdict")
    out["verdict"] = verdict if verdict in VERDICTS else "no-position"
    out["deutsch_position"] = _two_sentences(row.get("deutsch_position", ""))
    allowed = {item.get("id") for item in claim.get("grounding", []) if item.get("id")}
    citations = row.get("citations", [])
    if isinstance(citations, list):
        out["citations"] = [cid for cid in citations if cid in allowed]
    out["confidence"] = _clamp(row.get("confidence"), 0.0, 1.0, 0.0)
    note = row.get("note", "")
    out["note"] = note.strip() if isinstance(note, str) else ""
    if out["verdict"] in ("agree", "diverge") and (not out["deutsch_position"] or not out["citations"]):
        out = _default_judgment()
        out["note"] = "Downgraded to no-position because the model judgment lacked grounded position text or citations."
    return out
def judge_claims(claims_with_grounding, model=None, chat=None):
    """Judge claim agreement/divergence against provided grounding only."""
    chat = chat or llm_util.chat
    judgments = [_default_judgment() for _ in claims_with_grounding]
    index_by_id = {claim.get("id"): idx for idx, claim in enumerate(claims_with_grounding) if claim.get("id")}
    for start, chunk in _chunks(claims_with_grounding, 8):
        prompt = (
            "Judge each external claim against ONLY the provided Deutsch graph sources. Return agree when the claim is "
            "substantially compatible with the sources, diverge when it conflicts, and no-position when the sources do "
            "not establish a Deutsch position. The deutsch_position must be no more than two sentences and grounded only "
            "in the provided sources. Citations must be source ids from that claim's grounding.\n\nCLAIMS JSON:\n%s\n\n"
            "Return ONLY JSON: {\"judgments\": [{\"id\": \"clm:001\", \"verdict\": \"agree|diverge|no-position\", "
            "\"deutsch_position\": \"...\", \"citations\": [\"qa:...\"], \"confidence\": 0.0, \"note\": \"...\"}]}"
        ) % _judge_payload(chunk)
        data = llm_util.json_from(chat([{"role": "user", "content": prompt}], model=model))
        rows = data.get("judgments", []) if isinstance(data, dict) else []
        for row_idx, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            claim_id = row.get("id") or row.get("claim_id")
            target = index_by_id.get(claim_id)
            if target is None and row_idx < len(chunk):
                target = start + row_idx
            if target is None or target >= len(judgments):
                continue
            judgments[target] = _sanitize_judgment(row, claims_with_grounding[target])
    return judgments

### Detection orchestration
def _brief_grounding(qa_items, concept_items):
    """Normalize grounding items for detection output and judge input."""
    out = []
    for item in qa_items:
        brief = item.get("answer") or item.get("question")
        out.append({"id": item["id"], "type": "qa", "question": item.get("question"),
                    "answer": item.get("answer"), "brief": grounding._trim(brief, 500)})
    for item in concept_items:
        brief = item.get("definition") or item.get("label")
        out.append({"id": item["id"], "type": "concept", "label": item.get("label"),
                    "definition": item.get("definition"), "brief": grounding._trim(brief, 500)})
    return out
def detect(graph, claims, repo_root=None, model=None, chat=None, per_topic=3):
    """Route, ground, and judge external claims against the Deutsch graph."""
    catalog = grounding.topic_catalog(graph)
    routes = route_claims(claims, catalog, model=model, chat=chat)
    enriched = []
    judge_inputs = []
    judge_targets = []
    for idx, claim in enumerate(claims):
        route = routes[idx] if idx < len(routes) else {"topics": [], "concept_needles": []}
        qa_items = grounding.qa_grounding(graph, route["topics"], per_topic=per_topic, repo_root=repo_root)
        concept_items = grounding.concept_grounding(graph, route["concept_needles"])
        item = dict(claim)
        item["topics"] = route["topics"]
        item["concept_needles"] = route["concept_needles"]
        item["grounding"] = _brief_grounding(qa_items, concept_items)
        if item["grounding"]:
            judge_targets.append(len(enriched))
            judge_inputs.append(item)
        else:
            item.update({"verdict": "no-position", "deutsch_position": "", "citations": [],
                         "confidence": 0.0, "note": "No matching Deutsch graph grounding."})
        enriched.append(item)
    if judge_inputs:
        judgments = judge_claims(judge_inputs, model=model, chat=chat)
        for target, judgment in zip(judge_targets, judgments):
            enriched[target].update(judgment)
    return enriched
