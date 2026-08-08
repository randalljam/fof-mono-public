"""Pipeline for divergence-aware optimistic rewrites of existing content."""
import json
import math
import os
import re
from dgraph import claims as claim_service
from dgraph import divergence
from dgraph import grounding
from dgraph import llm_util
from ctools import config as ctools_config
from . import config
from . import render

CHANGE_TYPES = ("correct", "reframe", "add")

### Helpers
def _clamp_tone(value):
    """Normalize tone level."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = ctools_config.DEFAULT_TONE
    return value if value in ctools_config.TONES else ctools_config.DEFAULT_TONE
def _chunks(items, size):
    """Yield fixed-size chunks."""
    for idx in range(0, len(items), size):
        yield items[idx:idx + size]
def _word_count(text):
    """Approximate word count."""
    return len(re.findall(r"\b[\w'-]+\b", text or ""))
def _length_bounds(text):
    """Allowed rewrite word-count bounds for one source turn."""
    count = max(1, _word_count(text))
    low = max(1, int(math.floor(count * (1.0 - config.LENGTH_TOLERANCE))))
    high = max(1, int(math.ceil(count * (1.0 + config.LENGTH_TOLERANCE))))
    return low, high
def _length_ok(original, rewritten):
    """True when rewritten text is within the length guard."""
    if not isinstance(rewritten, str) or not rewritten.strip():
        return False
    low, high = _length_bounds(original)
    count = _word_count(rewritten)
    return low <= count <= high
def _citation_details(ids, citation_index):
    """Resolve citation ids for UI rendering."""
    out = []
    for cid in ids:
        entry = citation_index.get(cid, {"id": cid, "label": cid}) if citation_index else {"id": cid, "label": cid}
        item = dict(entry)
        item.setdefault("id", cid)
        out.append(item)
    return out
def _turns_payload(turns):
    """Compact JSON payload for planning."""
    payload = []
    for turn in turns:
        payload.append({"index": turn["index"], "speaker": turn.get("speaker"),
                        "timestamp": turn.get("timestamp"), "text": turn.get("text", "")})
    return json.dumps(payload, ensure_ascii=True)
def _claim_payload(claims):
    """Compact judged-claim payload for planning."""
    rows = []
    for claim in claims:
        rows.append({"id": claim.get("id"), "turn_index": claim.get("turn_index"), "claim": claim.get("text"),
                     "quote": claim.get("quote"), "verdict": claim.get("verdict"),
                     "deutsch_position": claim.get("deutsch_position"), "citations": claim.get("citations", []),
                     "grounding": claim.get("grounding", [])})
    return json.dumps(rows, ensure_ascii=True)
def _plan_prompt(turns, claims, tone, degree, reading_level):
    """Prompt for the rewrite-plan LLM call."""
    tone_row = ctools_config.TONES[tone]
    degree_row = config.REMIX_DEGREES[degree]
    level_row = config.READING_LEVELS[reading_level]
    return (
        "Plan a divergence-aware optimistic rewrite of this source. Keep the original structure. "
        "Use correct changes only for outright contradictions of Deutsch's recorded positions, reframe changes for "
        "pessimistic/inductivist/authority-based framing, and add changes only for new knowledge-creation material "
        "that should appear after a specific paragraph. Do not correct claims with no recorded Deutsch position. "
        "Tone: %s. %s Degree: %s. %s Reading level: %s. %s\n\nTURNS JSON:\n%s\n\nJUDGED CLAIMS JSON:\n%s\n\n"
        "Return ONLY JSON: {\"changes\": [{\"turn_index\": 0, \"change_type\": \"correct|reframe|add\", "
        "\"instruction\": \"one sentence\", \"claim_ids\": [\"clm:001\"], \"citations\": [\"qa:...\"]}]}"
    ) % (tone_row["label"], tone_row["instruction"], degree_row["label"], degree_row["instruction"],
         level_row["label"], level_row["instruction"], _turns_payload(turns), _claim_payload(claims))
def _rows_from_plan_response(data):
    """Extract model-proposed plan rows from supported envelope keys."""
    if not isinstance(data, dict):
        return []
    rows = data.get("changes")
    if rows is None:
        rows = data.get("plan")
    return rows if isinstance(rows, list) else []
def _known_claim_ids(row, claims_by_id):
    """Known claim ids referenced by one row."""
    ids = row.get("claim_ids", []) if isinstance(row, dict) else []
    if not isinstance(ids, list):
        return []
    return [cid for cid in ids if cid in claims_by_id]
def _claim_ids_for_type(change_type, row, claims_by_id):
    """Claim ids kept for one change type."""
    ids = _known_claim_ids(row, claims_by_id)
    if change_type == "correct":
        return [cid for cid in ids if claims_by_id[cid].get("verdict") == "diverge"]
    return ids
def _allowed_citation_ids(claim_ids, claims_by_id):
    """Grounding ids allowed by the referenced claims."""
    allowed = set()
    for cid in claim_ids:
        claim = claims_by_id.get(cid, {})
        for item in claim.get("grounding", []):
            if item.get("id"):
                allowed.add(item["id"])
    return allowed
def _fallback_citations(claim_ids, claims_by_id, allowed):
    """Claim-level citation fallback when model citations are missing or overbroad."""
    out = []
    for cid in claim_ids:
        for citation in claims_by_id.get(cid, {}).get("citations", []):
            if citation in allowed and citation not in out:
                out.append(citation)
    return out
def _clean_instruction(text):
    """One-sentence instruction fallback."""
    text = text.strip() if isinstance(text, str) else ""
    if not text:
        return "Improve this passage using the cited Deutsch graph grounding."
    parts = re.findall(r"[^.!?]+[.!?]?", text)
    return (parts[0] if parts else text).strip()
def _coerce_turn_index(row, claim_ids, claims_by_id, turn_by_index):
    """Return a valid target turn index, falling back to referenced claim turn."""
    try:
        idx = int(row.get("turn_index"))
    except (TypeError, ValueError):
        idx = None
    if idx in turn_by_index:
        return idx
    for cid in claim_ids:
        idx = claims_by_id[cid].get("turn_index")
        if idx in turn_by_index:
            return idx
    return None
def _drop(raw, reason):
    """Dropped plan row with reason."""
    return {"raw": raw, "reason": reason}
def _sanitize_plan_rows(rows, turns, claims, degree, citation_index):
    """Apply hard policy filters to a proposed rewrite plan."""
    allowed_types = set(config.REMIX_DEGREES[degree]["change_types"])
    claims_by_id = {claim.get("id"): claim for claim in claims if claim.get("id")}
    turn_by_index = {turn["index"]: turn for turn in turns}
    kept, dropped = [], []
    for raw in rows:
        if not isinstance(raw, dict):
            dropped.append(_drop(raw, "malformed plan row"))
            continue
        change_type = raw.get("change_type")
        if change_type not in CHANGE_TYPES:
            dropped.append(_drop(raw, "unsupported change_type"))
            continue
        if change_type not in allowed_types:
            dropped.append(_drop(raw, "change_type not allowed by degree %s" % degree))
            continue
        claim_ids = _claim_ids_for_type(change_type, raw, claims_by_id)
        if change_type == "correct" and not claim_ids:
            dropped.append(_drop(raw, "correct changes require at least one diverge claim"))
            continue
        if not claim_ids:
            dropped.append(_drop(raw, "no known claim_ids with grounding"))
            continue
        turn_index = _coerce_turn_index(raw, claim_ids, claims_by_id, turn_by_index)
        if turn_index is None:
            dropped.append(_drop(raw, "invalid turn_index"))
            continue
        allowed = _allowed_citation_ids(claim_ids, claims_by_id)
        requested = raw.get("citations", [])
        if not isinstance(requested, list):
            requested = []
        citations = [cid for cid in requested if cid in allowed]
        if citation_index:
            citations = [cid for cid in citations if cid in citation_index]
        if not citations:
            citations = _fallback_citations(claim_ids, claims_by_id, allowed)
            if citation_index:
                citations = [cid for cid in citations if cid in citation_index]
        if not citations:
            dropped.append(_drop(raw, "no grounded citations after filtering"))
            continue
        kept.append({"id": "chg:%03d" % (len(kept) + 1), "turn_index": turn_index, "change_type": change_type,
                     "instruction": _clean_instruction(raw.get("instruction", "")), "claim_ids": claim_ids,
                     "citations": citations, "citation_details": _citation_details(citations, citation_index or {})})
    return {"applied": kept, "dropped": dropped, "raw": rows}
def generate_plan(turns, claims, tone, degree, reading_level, model=None, chat=None, citation_index=None):
    """Generate and sanitize the rewrite plan."""
    chat = chat or llm_util.chat
    data = llm_util.json_from(chat([{"role": "user", "content": _plan_prompt(turns, claims, tone, degree, reading_level)}], model=model))
    rows = _rows_from_plan_response(data)
    return _sanitize_plan_rows(rows, turns, claims, degree, citation_index or {})
def _turn_change_groups(plan_rows):
    """Plan rows grouped by target turn."""
    groups = {}
    for item in plan_rows:
        groups.setdefault(item["turn_index"], []).append(item)
    return groups
def _rewrite_targets(plan_rows):
    """Turns whose original text should be rewritten."""
    targets = set()
    for item in plan_rows:
        if item.get("change_type") in ("correct", "reframe"):
            targets.add(item["turn_index"])
    return targets
def _child_concepts(claims):
    """Concept definitions from BOI concept nodes in grounding."""
    rows, seen = [], set()
    for claim in claims:
        for item in claim.get("grounding", []):
            cid = item.get("id")
            if cid in seen or not cid or not cid.startswith("concept:boi/"):
                continue
            definition = item.get("definition") or item.get("brief") or ""
            label = item.get("label") or cid
            if definition:
                rows.append({"id": cid, "label": label, "definition": definition})
                seen.add(cid)
            if len(rows) >= 3:
                return rows
    return rows
def _claim_verdicts(plan_row, claims_by_id):
    """Claim verdict audit rows behind one change."""
    rows = []
    for cid in plan_row.get("claim_ids", []):
        claim = claims_by_id.get(cid, {})
        rows.append({"id": cid, "verdict": claim.get("verdict"), "text": claim.get("text"),
                     "deutsch_position": claim.get("deutsch_position"), "citations": claim.get("citations", [])})
    return rows
def _rewrite_payload(turns, groups):
    """Compact rewrite task payload."""
    payload = []
    for turn in turns:
        changes = groups.get(turn["index"], [])
        payload.append({"turn_index": turn["index"], "speaker": turn.get("speaker"), "timestamp": turn.get("timestamp"),
                        "original_text": turn.get("text", ""), "changes": changes})
    return json.dumps(payload, ensure_ascii=True)
def _rewrite_prompt(turns, groups, tone, reading_level, concepts=None, retry=False):
    """Prompt for a constrained rewrite batch."""
    tone_row = ctools_config.TONES[tone]
    level_row = config.READING_LEVELS[reading_level]
    bounds = []
    for turn in turns:
        low, high = _length_bounds(turn.get("text", ""))
        bounds.append({"turn_index": turn["index"], "min_words": low, "max_words": high})
    extra = ""
    if reading_level == "child":
        extra = "\n\nCHILD CONCEPT DEFINITIONS JSON:\n%s\nUse two or three of these terms only if they fit, and define them in kid-friendly words inline." % json.dumps(concepts or [], ensure_ascii=True)
    retry_line = " This is a retry: the previous answer exceeded the word limit, so obey the min_words/max_words bounds exactly." if retry else ""
    return (
        "Rewrite ONLY the listed Content Redo turns. Do not alter turns not listed here. "
        "For correct/reframe changes, return one rewritten text for the original turn. For add changes, return a new paragraph "
        "in additions after the turn; keep the original turn unchanged when it has only add changes. Keep structure and meaning "
        "except for the cited improvement. Do not invent Deutsch positions or citations. Tone: %s. %s Reading level: %s. %s%s\n\n"
        "WORD BOUNDS JSON:\n%s\n\nTASKS JSON:\n%s%s\n\n"
        "Return ONLY JSON: {\"rewrites\": [{\"turn_index\": 0, \"text\": \"rewritten original turn\", "
        "\"additions\": [{\"plan_id\": \"chg:003\", \"text\": \"new paragraph\"}]}]}"
    ) % (tone_row["label"], tone_row["instruction"], level_row["label"], level_row["instruction"], retry_line,
         json.dumps(bounds, ensure_ascii=True), _rewrite_payload(turns, groups), extra)
def _rewrite_rows_from_response(data):
    """Normalize rewrite rows from model output."""
    if not isinstance(data, dict):
        return {}
    rows = data.get("rewrites", [])
    out = {}
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            idx = int(row.get("turn_index"))
        except (TypeError, ValueError):
            continue
        text = row.get("text")
        if text is None:
            text = row.get("rewritten_text")
        additions = row.get("additions", [])
        out[idx] = {"text": text if isinstance(text, str) else "", "additions": additions if isinstance(additions, list) else []}
    return out
def _call_rewrite(turns, groups, tone, reading_level, concepts, model, chat, retry=False):
    """Run one rewrite batch and return rows by turn index."""
    prompt = _rewrite_prompt(turns, groups, tone, reading_level, concepts=concepts, retry=retry)
    data = llm_util.json_from(chat([{"role": "user", "content": prompt}], model=model))
    return _rewrite_rows_from_response(data)
def _sanitize_additions(row, add_plans):
    """Generated addition paragraphs keyed by plan id."""
    by_id = {}
    for item in row.get("additions", []):
        if not isinstance(item, dict):
            continue
        plan_id = item.get("plan_id") or item.get("id")
        text = item.get("text")
        if plan_id in add_plans and isinstance(text, str) and text.strip():
            by_id[plan_id] = text.strip()
    return by_id
def _build_diff(turns, plan_rows, rewrite_texts, addition_texts):
    """Per-turn original-vs-rewritten data for UI rendering."""
    groups = _turn_change_groups(plan_rows)
    diff = []
    for turn in turns:
        idx = turn["index"]
        original = turn.get("text", "")
        rewritten = rewrite_texts.get(idx, original)
        additions = []
        for plan_row in groups.get(idx, []):
            if plan_row.get("change_type") == "add" and plan_row["id"] in addition_texts:
                additions.append({"id": plan_row["id"], "text": addition_texts[plan_row["id"]],
                                  "citations": plan_row.get("citations", []),
                                  "citation_details": plan_row.get("citation_details", [])})
        change_types = sorted({row.get("change_type") for row in groups.get(idx, []) if row.get("id") in addition_texts or rewritten != original})
        diff.append({"turn_index": idx, "speaker": turn.get("speaker"), "timestamp": turn.get("timestamp"),
                     "original_text": original, "rewritten_text": rewritten, "changed": rewritten != original or bool(additions),
                     "change_ids": [row["id"] for row in groups.get(idx, []) if row.get("id") in addition_texts or rewritten != original],
                     "change_types": change_types, "changes": groups.get(idx, []), "additions": additions})
    return diff
def _assert_verbatim_passthrough(turns, rewrite_texts, rewrite_targets):
    """Assert untouched turns were copied, not round-tripped through the LLM."""
    for turn in turns:
        if turn["index"] not in rewrite_targets:
            assert rewrite_texts.get(turn["index"], turn.get("text", "")) == turn.get("text", "")
def _change_rows(plan_rows, turns, rewrite_texts, addition_texts, claims_by_id):
    """Applied change rows for audit output."""
    turn_by_index = {turn["index"]: turn for turn in turns}
    rows = []
    for plan_row in plan_rows:
        idx = plan_row["turn_index"]
        original = turn_by_index[idx].get("text", "")
        if plan_row["change_type"] == "add":
            if plan_row["id"] not in addition_texts:
                continue
            new_text = addition_texts[plan_row["id"]]
            original_text = ""
        else:
            if rewrite_texts.get(idx, original) == original:
                continue
            new_text = rewrite_texts[idx]
            original_text = original
        item = dict(plan_row)
        item.update({"original_text": original_text, "new_text": new_text, "why": plan_row.get("instruction", ""),
                     "claim_verdicts": _claim_verdicts(plan_row, claims_by_id)})
        rows.append(item)
    return rows
def apply_rewrites(turns, claims, plan_rows, tone, reading_level, model=None, chat=None):
    """Rewrite planned turns in batches and keep untouched turns byte-identical."""
    chat = chat or llm_util.chat
    groups = _turn_change_groups(plan_rows)
    rewrite_targets = _rewrite_targets(plan_rows)
    turn_by_index = {turn["index"]: turn for turn in turns}
    concepts = _child_concepts(claims) if reading_level == "child" else []
    rewrite_texts = {}
    addition_texts = {}
    skipped = []
    target_turns = [turn_by_index[idx] for idx in sorted(groups) if idx in turn_by_index]
    for chunk in _chunks(target_turns, config.REWRITE_BATCH_SIZE):
        chunk_groups = {turn["index"]: groups.get(turn["index"], []) for turn in chunk}
        rows = _call_rewrite(chunk, chunk_groups, tone, reading_level, concepts, model, chat)
        for turn in chunk:
            idx = turn["index"]
            row = rows.get(idx, {"text": "", "additions": []})
            rewrite_plans = [item for item in groups.get(idx, []) if item.get("change_type") in ("correct", "reframe")]
            add_plans = {item["id"]: item for item in groups.get(idx, []) if item.get("change_type") == "add"}
            if rewrite_plans:
                rewritten = row.get("text", "")
                if not _length_ok(turn.get("text", ""), rewritten):
                    retry_rows = _call_rewrite([turn], {idx: groups.get(idx, [])}, tone, reading_level, concepts, model, chat, retry=True)
                    retry_text = retry_rows.get(idx, {}).get("text", "")
                    if _length_ok(turn.get("text", ""), retry_text):
                        rewritten = retry_text
                        skipped.append({"turn_index": idx, "reason": "Regenerated once after length guard failed.", "plan_ids": [p["id"] for p in rewrite_plans]})
                        row = retry_rows.get(idx, row)
                    else:
                        skipped.append({"turn_index": idx, "reason": "Skipped rewrite because the generated text exceeded the length guard after one retry.", "plan_ids": [p["id"] for p in rewrite_plans]})
                        rewritten = turn.get("text", "")
                rewrite_texts[idx] = rewritten
            for plan_id, text in _sanitize_additions(row, add_plans).items():
                addition_texts[plan_id] = text
            for plan_id in add_plans:
                if plan_id not in addition_texts:
                    skipped.append({"turn_index": idx, "reason": "Skipped add change because no addition text was returned.", "plan_ids": [plan_id]})
    _assert_verbatim_passthrough(turns, rewrite_texts, rewrite_targets)
    claims_by_id = {claim.get("id"): claim for claim in claims if claim.get("id")}
    diff = _build_diff(turns, plan_rows, rewrite_texts, addition_texts)
    changes = _change_rows(plan_rows, turns, rewrite_texts, addition_texts, claims_by_id)
    return diff, changes, skipped

### Pipeline
def _summary(claims, plan, changes, skipped_notes):
    """Run summary counts."""
    counts = {"claims": len(claims), "diverge": 0, "agree": 0, "no-position": 0,
              "planned": len(plan.get("applied", [])), "dropped_plan": len(plan.get("dropped", [])),
              "changes": len(changes), "skipped": len(skipped_notes)}
    for claim in claims:
        verdict = claim.get("verdict")
        if verdict in counts:
            counts[verdict] += 1
    return counts
def run(text, source_name, tone=None, degree=None, reading_level=None, model=None, chat=None, graph=None, citation_index=None, repo_root=None, generated_at=""):
    """Full Content Redo pipeline from raw text to rewritten document, change list, and sidecar."""
    graph = graph or grounding.load_graph()
    citation_index = citation_index or grounding.citation_index(graph)
    repo_root = repo_root or config.REPO_ROOT
    tone = _clamp_tone(tone)
    degree = config.clean_degree(degree)
    reading_level = config.clean_reading_level(reading_level)
    turns = claim_service.parse_content(text or "")
    raw_claims = claim_service.segment_claims(turns, model=model, chat=chat)
    detected = divergence.detect(graph, raw_claims, repo_root=repo_root, model=model, chat=chat)
    plan = generate_plan(turns, detected, tone, degree, reading_level, model=model, chat=chat, citation_index=citation_index)
    diff, changes, skipped_notes = apply_rewrites(turns, detected, plan["applied"], tone, reading_level, model=model, chat=chat)
    provenance = {"source_name": source_name or "pasted text", "tool": "content-redo", "model": model or "", "generated_at": generated_at}
    knobs = {"tone": tone, "tone_label": ctools_config.TONES[tone]["label"], "degree": degree,
             "degree_label": config.REMIX_DEGREES[degree]["label"], "reading_level": reading_level,
             "reading_level_label": config.READING_LEVELS[reading_level]["label"]}
    markdown, change_list_markdown, sidecar = render.assemble(turns, detected, plan, diff, changes, skipped_notes, provenance, knobs)
    summary = _summary(detected, plan, changes, skipped_notes)
    return {"source_name": provenance["source_name"], "generated_at": generated_at, "turns": turns,
            "claims": detected, "plan": plan, "changes": changes, "diff": diff, "skipped_notes": skipped_notes,
            "markdown": markdown, "change_list_markdown": change_list_markdown, "sidecar": sidecar,
            "knobs": knobs, "summary": summary}
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
    return run(text, source_name, tone=payload.get("tone"), degree=payload.get("degree"),
               reading_level=payload.get("reading_level"), model=payload.get("model"),
               graph=state.get("graph"), citation_index=state.get("citation_index"),
               repo_root=state.get("repo_root"), generated_at=state.get("generated_at", ""))
