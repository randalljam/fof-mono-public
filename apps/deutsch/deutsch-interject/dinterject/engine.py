"""Pipeline for inserting clearly labeled virtual Deutsch interjections into external content."""
import json
import os
import re
from dgraph import claims as claim_service
from dgraph import divergence
from dgraph import grounding
from dgraph import llm_util
from ctools import config as ctools_config
from . import config
from . import render

QUOTE_RE = re.compile(r'"([^"]+)"')

### Helpers
def _clamp_tone(value):
    """Normalize tone level."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = ctools_config.DEFAULT_TONE
    return value if value in ctools_config.TONES else ctools_config.DEFAULT_TONE
def _clean_fidelity(value):
    """Normalize fidelity key."""
    return config.clean_fidelity(value)
def _chunks(items, size):
    """Yield fixed-size chunks."""
    for idx in range(0, len(items), size):
        yield items[idx:idx + size]
def _grounding_text(claim):
    """All grounding text for quote verification."""
    parts = []
    for item in claim.get("grounding", []):
        for key in ("answer", "question", "claim", "definition", "brief", "label"):
            if item.get(key):
                parts.append(item[key])
    return "\n".join(parts)
def _allowed_ids(claim):
    """Grounding ids allowed for a claim."""
    return {item.get("id") for item in claim.get("grounding", []) if item.get("id")}
def _citation_details(ids, citation_index):
    """Resolve citation ids for UI rendering."""
    out = []
    for cid in ids:
        entry = citation_index.get(cid, {"id": cid, "label": cid}) if citation_index else {"id": cid, "label": cid}
        item = dict(entry)
        item.setdefault("id", cid)
        out.append(item)
    return out
def _claim_payload(claims):
    """Compact generation payload."""
    rows = []
    for claim in claims:
        rows.append({"id": claim.get("id"), "speaker": claim.get("speaker"), "turn_index": claim.get("turn_index"),
                     "claim": claim.get("text"), "source_quote": claim.get("quote"), "verdict": claim.get("verdict"),
                     "deutsch_position": claim.get("deutsch_position"), "citations": claim.get("citations", []),
                     "grounding": claim.get("grounding", [])})
    return json.dumps(rows, ensure_ascii=True)
def _generation_prompt(claims, tone, fidelity):
    """Prompt for interjection generation."""
    tone_row = ctools_config.TONES[tone]
    fidelity_row = config.QUOTE_FIDELITY[fidelity]
    return (
        "Generate clearly labeled virtual David Deutsch interjections for the selected external claims. "
        "Use ONLY the provided Deutsch graph grounding for each claim. Do not invent positions, sources, or quotes. "
        "For agree verdicts, briefly mark the compatibility rather than manufacturing a disagreement. "
        "Tone: %s. %s Fidelity: %s. %s\n\nCLAIMS JSON:\n%s\n\n"
        "Return ONLY JSON: {\"interjections\": [{\"claim_id\": \"clm:001\", \"text\": \"...\", \"citations\": [\"qa:...\"]}]}"
    ) % (tone_row["label"], tone_row["instruction"], fidelity_row["label"], fidelity_row["instruction"], _claim_payload(claims))
def _sanitize_interjection(row, claim):
    """Validate one generated interjection and filter citations to claim grounding ids."""
    if not isinstance(row, dict):
        return None
    text = row.get("text", "")
    if not isinstance(text, str) or not text.strip():
        return None
    allowed = _allowed_ids(claim)
    requested = row.get("citations", [])
    if not isinstance(requested, list):
        requested = []
    citations = [cid for cid in requested if cid in allowed]
    if not citations:
        citations = [cid for cid in claim.get("citations", []) if cid in allowed]
    if not citations:
        return None
    return {"claim_id": claim["id"], "turn_index": claim.get("turn_index"), "verdict": claim.get("verdict"),
            "text": text.strip(), "citations": citations, "source_claim": claim.get("text", ""),
            "deutsch_position": claim.get("deutsch_position", "")}
def _word_count(text):
    """Approximate word count for quote-verification threshold."""
    return len(re.findall(r"\b[\w'-]+\b", text))
def _norm(text):
    """Whitespace-normalized text."""
    return " ".join((text or "").split())
def _bad_quote_spans(interjection, claim):
    """Quoted spans of at least eight words that are not verbatim in grounding text."""
    source = _norm(_grounding_text(claim))
    bad = []
    for span in QUOTE_RE.findall(interjection.get("text", "")):
        if _word_count(span) >= 8 and _norm(span) not in source:
            bad.append(span)
    return bad
def _regenerate_without_fake_quote(interjection, claim, tone, model, chat):
    """Ask once for a quote-safe replacement."""
    prompt = (
        "The draft virtual Deutsch interjection used a quoted span that is not verbatim in the provided sources. "
        "Rewrite it once. Use no double-quoted span unless it appears exactly in SOURCES. Keep citations from ALLOWED_IDS only.\n\n"
        "TONE: %s\nCLAIM JSON:\n%s\nDRAFT JSON:\n%s\nALLOWED_IDS: %s\nSOURCES:\n%s\n\n"
        "Return ONLY JSON: {\"interjection\": {\"claim_id\": \"%s\", \"text\": \"...\", \"citations\": [\"...\"]}}"
    ) % (ctools_config.TONES[tone]["instruction"], json.dumps(claim, ensure_ascii=True), json.dumps(interjection, ensure_ascii=True),
         json.dumps(sorted(_allowed_ids(claim))), _grounding_text(claim), claim["id"])
    try:
        data = llm_util.json_from(chat([{"role": "user", "content": prompt}], model=model))
    except Exception:
        return None
    row = data.get("interjection") if isinstance(data, dict) else None
    if row is None and isinstance(data, dict):
        rows = data.get("interjections", [])
        row = rows[0] if rows else None
    return _sanitize_interjection(row, claim)
def _verify_or_regenerate(interjection, claim, tone, fidelity, model, chat, notes):
    """Verify quote-mode interjections, regenerating once or dropping."""
    if fidelity != "quote":
        return interjection
    bad = _bad_quote_spans(interjection, claim)
    if not bad:
        return interjection
    replacement = _regenerate_without_fake_quote(interjection, claim, tone, model, chat)
    if replacement and not _bad_quote_spans(replacement, claim):
        notes.append({"claim_id": claim["id"], "note": "Regenerated once after non-verbatim quote verification failed."})
        return replacement
    notes.append({"claim_id": claim["id"], "note": "Dropped interjection because quote verification failed.", "bad_quotes": bad})
    return None
def generate_interjections(selected_claims, tone, fidelity, model=None, chat=None, citation_index=None):
    """Generate interjections in batches of about six claims."""
    chat = chat or llm_util.chat
    interjections = []
    notes = []
    claim_by_id = {claim["id"]: claim for claim in selected_claims}
    for chunk in _chunks(selected_claims, 6):
        data = llm_util.json_from(chat([{"role": "user", "content": _generation_prompt(chunk, tone, fidelity)}], model=model))
        rows = data.get("interjections", []) if isinstance(data, dict) else []
        for row in rows:
            claim = claim_by_id.get(row.get("claim_id") if isinstance(row, dict) else None)
            if not claim:
                continue
            item = _sanitize_interjection(row, claim)
            if not item:
                continue
            item = _verify_or_regenerate(item, claim, tone, fidelity, model, chat, notes)
            if item:
                item["citation_details"] = _citation_details(item["citations"], citation_index or {})
                interjections.append(item)
    return interjections, notes

### Pipeline
def _selected_claims(detected, include_agreements):
    """Claims that should receive virtual Deutsch interjections."""
    selected = []
    for claim in detected:
        if claim.get("verdict") == "diverge" or (include_agreements and claim.get("verdict") == "agree"):
            selected.append(claim)
    return selected
def _skipped_claims(detected, interjections, notes):
    """Claims not interjected, including no-position honesty rows and dropped rows."""
    kept = {item["claim_id"] for item in interjections}
    skipped = []
    for claim in detected:
        if claim.get("verdict") == "no-position":
            skipped.append({"claim_id": claim["id"], "verdict": "no-position", "reason": "Deutsch has no recorded position in the routed grounding.", "claim": claim.get("text", "")})
        elif claim.get("id") not in kept:
            skipped.append({"claim_id": claim["id"], "verdict": claim.get("verdict"), "reason": "No interjection selected or kept.", "claim": claim.get("text", "")})
    for note in notes:
        if note.get("note", "").startswith("Dropped"):
            skipped.append({"claim_id": note.get("claim_id"), "reason": note.get("note"), "bad_quotes": note.get("bad_quotes", [])})
    return skipped
def _summary(claims, interjections):
    """Run summary counts."""
    counts = {"claims": len(claims), "diverge": 0, "agree": 0, "no-position": 0, "interjections": len(interjections)}
    for claim in claims:
        verdict = claim.get("verdict")
        if verdict in counts:
            counts[verdict] += 1
    return counts
def run(text, source_name, tone=None, fidelity=None, include_agreements=False, model=None, chat=None, graph=None, citation_index=None, repo_root=None, generated_at=""):
    """Full interject pipeline from raw text to annotated transcript and sidecar."""
    graph = graph or grounding.load_graph()
    citation_index = citation_index or grounding.citation_index(graph)
    repo_root = repo_root or config.REPO_ROOT
    tone = _clamp_tone(tone)
    fidelity = _clean_fidelity(fidelity)
    turns = claim_service.parse_content(text or "")
    raw_claims = claim_service.segment_claims(turns, model=model, chat=chat)
    detected = divergence.detect(graph, raw_claims, repo_root=repo_root, model=model, chat=chat)
    selected = _selected_claims(detected, include_agreements)
    interjections, notes = generate_interjections(selected, tone, fidelity, model=model, chat=chat, citation_index=citation_index)
    skipped = _skipped_claims(detected, interjections, notes)
    provenance = {"source_name": source_name or "pasted text", "tool": "deutsch-interject", "model": model or "", "generated_at": generated_at}
    knobs = {"tone": tone, "tone_label": ctools_config.TONES[tone]["label"], "fidelity": fidelity, "include_agreements": bool(include_agreements)}
    markdown, sidecar = render.assemble(turns, detected, interjections, skipped, provenance, knobs, notes)
    return {"source_name": provenance["source_name"], "generated_at": generated_at, "turns": turns,
            "claims": detected, "interjections": interjections, "skipped": skipped, "markdown": markdown,
            "sidecar": sidecar, "knobs": knobs, "summary": _summary(detected, interjections)}
def _load_sample(name):
    """Load a shared harness sample by basename."""
    safe = os.path.basename(name or "")
    if not safe:
        raise ValueError("missing sample name")
    if not safe.endswith(".md"):
        safe += ".md"
    path = os.path.join(ctools_config.SAMPLES_DIR, safe)
    if not os.path.exists(path):
        raise ValueError("unknown sample: " + safe)
    with open(path, encoding="utf-8") as f:
        return safe, f.read()
def run_from_request(payload, state):
    """Server entry point: payload text or sample -> full result dict."""
    if payload.get("sample"):
        source_name, text = _load_sample(payload.get("sample"))
    else:
        text = payload.get("text") or ""
        source_name = payload.get("source_name") or "pasted text"
    if not text.strip():
        raise ValueError("empty text")
    return run(text, source_name, tone=payload.get("tone"), fidelity=payload.get("fidelity"),
               include_agreements=bool(payload.get("include_agreements")), model=payload.get("model"),
               graph=state.get("graph"), citation_index=state.get("citation_index"),
               repo_root=state.get("repo_root"), generated_at=state.get("generated_at", ""))
