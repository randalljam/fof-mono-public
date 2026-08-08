"""Build reusable transcript review ledgers from existing alignment data."""
import copy
import hashlib
import json
import os
import re
import tempfile
from collections import Counter

REVIEW_FIELDS = ("review_status", "review_category", "review_notes")
REVIEW_DEFAULTS = {
    "review_status": "pending",
    "review_category": None,
    "review_notes": None,
}

### Shared helpers
def _speaker(seg):
    return seg.get("speaker_name") or seg.get("speaker_full") or seg.get("speaker") or "Speaker 0"
def _normalize_dual_speaker(speaker):
    speaker = speaker or "Speaker 0"
    if " (" in speaker:
        speaker = speaker.split(" (", 1)[0].strip()
    return speaker
def _segment_key(seg):
    return (_speaker(seg), seg.get("timestamp"), seg.get("dialogue") or "")
def _dual_match_segment_key(seg):
    return (_normalize_dual_speaker(_speaker(seg)), seg.get("timestamp"), seg.get("dialogue") or "")
def _segments_text(segments):
    blocks = []
    for seg in segments or []:
        blocks.append(f"{_speaker(seg)}  {seg.get('timestamp') or ''}\n{seg.get('dialogue') or ''}".strip())
    return "\n\n".join(blocks)
def _timestamp_seconds(timestamp):
    if not timestamp:
        return 0
    parts = [int(part) for part in str(timestamp).split(":")]
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + part
    return seconds
def _nearest_ref_index(seg, ref_segments):
    if not ref_segments:
        return None
    seconds = _timestamp_seconds(seg.get("timestamp"))
    return min(
        range(len(ref_segments)),
        key=lambda index: abs(_timestamp_seconds(ref_segments[index].get("timestamp")) - seconds),
    )
def _nearest_candidate_segments(ref_seg, candidate_segments):
    if not candidate_segments:
        return []
    seconds = _timestamp_seconds(ref_seg.get("timestamp"))
    nearest = min(
        candidate_segments,
        key=lambda seg: abs(_timestamp_seconds(seg.get("timestamp")) - seconds),
    )
    return [nearest]
def _load_policy(profile):
    from core.denovo import resolve_profile_policy
    return resolve_profile_policy(profile)
def _align_path(path, ref_segments, policy):
    from core.transcript_eval import evaluate_step_segments_align, extract_transcript_data
    candidate = extract_transcript_data(path) or []
    tagged, metrics, _ = evaluate_step_segments_align(
        copy.deepcopy(candidate), copy.deepcopy(ref_segments),
        verbose=False, normalization_policy=policy)
    by_ref = {}
    for index, seg in enumerate(tagged):
        seg["_ledger_index"] = index
        ref_index = seg.get("aligned_ref_index")
        if ref_index is not None:
            by_ref.setdefault(ref_index, []).append(seg)
    missing = sorted(set(range(len(ref_segments))) - set(by_ref))
    spurious = [seg for seg in tagged if seg.get("is_delete")]
    return {
        "segments": tagged,
        "by_ref": by_ref,
        "missing": missing,
        "spurious": spurious,
        "metrics": metrics,
    }
def _error_kinds(aligned_segments, ref_seg, include_wording=False):
    if not aligned_segments:
        return ["missing_segment"]
    kinds = []
    if any(seg.get("is_boundary_misplaced") for seg in aligned_segments):
        kinds.append("misplaced_phrase")
    elif any(seg.get("is_boundary_error") for seg in aligned_segments):
        kinds.append("boundary_word_error")
    if any(_speaker(seg) != _speaker(ref_seg) for seg in aligned_segments):
        kinds.append("wrong_speaker")
    if include_wording and not kinds and any(not seg.get("is_norm_identical") for seg in aligned_segments):
        kinds.append("wording_only")
    return kinds
def _suggest_category(raw_kinds, draft_kinds, change_status):
    kinds = raw_kinds if change_status == "fixed" else draft_kinds
    priority = (
        "missing_segment",
        "spurious_split",
        "misplaced_phrase",
        "wrong_speaker",
        "boundary_word_error",
        "wording_only",
    )
    for category in priority:
        if category in kinds:
            return category
    return "unclear"
def _base_case(case_id, episode_stem):
    return {
        "case_id": case_id,
        "episode_stem": episode_stem,
        "region_id": None,
        "category_suggested": "unclear",
        "category_signals": [],
        **REVIEW_DEFAULTS,
    }
def _preserve_review_fields(cases, existing_path):
    if not existing_path or not os.path.isfile(existing_path):
        return cases
    with open(existing_path) as handle:
        previous = json.load(handle)
    by_id = {case.get("case_id"): case for case in previous.get("cases", [])}
    for case in cases:
        old = by_id.get(case["case_id"])
        if not old:
            continue
        for field in REVIEW_FIELDS:
            if field in old:
                case[field] = old[field]
    return cases
def _assign_regions(cases, episode_stem):
    region = 0
    previous_ref = None
    for case in sorted(cases, key=lambda item: (item.get("ref_index", -1), item["case_id"])):
        ref_index = case.get("ref_index")
        if previous_ref is None or ref_index is None or ref_index > previous_ref + 1:
            region += 1
        case["region_id"] = f"{episode_stem}::region-{region:04d}"
        if ref_index is not None:
            previous_ref = ref_index
    return cases
def _summary(cases):
    return {
        "case_count": len(cases),
        "status_counts": dict(Counter(case.get("change_status", "unknown") for case in cases)),
        "category_counts": dict(Counter(case.get("category_suggested", "unclear") for case in cases)),
        "review_counts": dict(Counter(case.get("review_status", "pending") for case in cases)),
    }
def _stable_spurious_id(episode_stem, seg):
    signature = "|".join(str(value) for value in _segment_key(seg))
    digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:10]
    timestamp = str(seg.get("timestamp") or "no-time").replace(":", "-")
    return f"{episode_stem}::spurious-{timestamp}-{digest}"

### Single review
def build_single_review_ledger(raw_path, draft_path, ref_path, profile=None, include_wording=False, include_fixed=True, existing_path=None):
    from core.transcript_eval import extract_transcript_data
    ref_segments = extract_transcript_data(ref_path) or []
    policy = _load_policy(profile)
    raw = _align_path(raw_path, ref_segments, policy)
    draft = _align_path(draft_path, ref_segments, policy)
    episode_stem = os.path.basename(ref_path).rsplit("_", 1)[0]
    cases = []
    for ref_index, ref_seg in enumerate(ref_segments):
        raw_segments = raw["by_ref"].get(ref_index, [])
        draft_segments = draft["by_ref"].get(ref_index, [])
        raw_kinds = _error_kinds(raw_segments, ref_seg, include_wording=include_wording)
        draft_kinds = _error_kinds(draft_segments, ref_seg, include_wording=include_wording)
        if not raw_kinds and not draft_kinds:
            continue
        if raw_kinds and not draft_kinds:
            change_status = "fixed"
        elif not raw_kinds and draft_kinds:
            change_status = "made_worse"
        else:
            change_status = "remaining"
        if change_status == "fixed" and not include_fixed:
            continue
        raw_display = raw_segments or _nearest_candidate_segments(ref_seg, raw["segments"])
        draft_display = draft_segments or _nearest_candidate_segments(ref_seg, draft["segments"])
        case = _base_case(f"{episode_stem}::ref-{ref_index:04d}", episode_stem)
        case.update({
            "mode": "single",
            "ref_index": ref_index,
            "timestamp_start": ref_seg.get("timestamp"),
            "change_status": change_status,
            "error_kinds_raw": raw_kinds,
            "error_kinds_draft": draft_kinds,
            "category_suggested": _suggest_category(raw_kinds, draft_kinds, change_status),
            "category_signals": sorted(set(raw_kinds + draft_kinds)),
            "text_raw": _segments_text(raw_display),
            "text_draft": _segments_text(draft_display),
            "text_ref": _segments_text([ref_seg]),
            "source_files": {
                "raw": os.path.basename(raw_path),
                "draft": os.path.basename(draft_path),
                "reference": os.path.basename(ref_path),
            },
        })
        cases.append(case)
    raw_spurious = {_segment_key(seg): seg for seg in raw["spurious"]}
    draft_spurious = {_segment_key(seg): seg for seg in draft["spurious"]}
    for key in sorted(set(raw_spurious) | set(draft_spurious), key=str):
        raw_seg = raw_spurious.get(key)
        draft_seg = draft_spurious.get(key)
        if raw_seg and draft_seg:
            change_status = "remaining"
        elif raw_seg:
            change_status = "fixed"
        else:
            change_status = "made_worse"
        if change_status == "fixed" and not include_fixed:
            continue
        seg = draft_seg or raw_seg
        ref_index = _nearest_ref_index(seg, ref_segments)
        ref_seg = ref_segments[ref_index] if ref_index is not None else {}
        case_id = _stable_spurious_id(episode_stem, seg)
        case = _base_case(case_id, episode_stem)
        case.update({
            "mode": "single",
            "ref_index": ref_index,
            "timestamp_start": seg.get("timestamp"),
            "change_status": change_status,
            "error_kinds_raw": ["spurious_split"] if raw_seg else [],
            "error_kinds_draft": ["spurious_split"] if draft_seg else [],
            "category_suggested": "spurious_split",
            "category_signals": ["is_delete"],
            "text_raw": _segments_text([raw_seg] if raw_seg else _nearest_candidate_segments(ref_seg, raw["segments"])),
            "text_draft": _segments_text([draft_seg] if draft_seg else _nearest_candidate_segments(ref_seg, draft["segments"])),
            "text_ref": _segments_text([ref_seg]) if ref_seg else "",
            "source_files": {
                "raw": os.path.basename(raw_path),
                "draft": os.path.basename(draft_path),
                "reference": os.path.basename(ref_path),
            },
        })
        cases.append(case)
    cases = _assign_regions(cases, episode_stem)
    cases = _preserve_review_fields(cases, existing_path)
    payload = {
        "mode": "single",
        "episode_stem": episode_stem,
        "profile": profile,
        "source_files": {
            "raw": raw_path,
            "draft": draft_path,
            "reference": ref_path,
        },
        "alignment_metrics": {
            "raw": raw["metrics"],
            "draft": draft["metrics"],
        },
        "cases": cases,
    }
    payload["summary"] = _summary(cases)
    return payload

### Dual review
def load_markdown_segments_strict(path):
    """Load rendered transcript segments without treating inline timestamp links as headers."""
    header = re.compile(r"^(.*?)  (?:\[(\d+(?::\d+){1,2})\]\([^)]*\)|(\d+(?::\d+){1,2}))$")
    segments = []
    current = None
    with open(path) as handle:
        for line in handle.read().splitlines():
            match = header.match(line)
            if match:
                if current:
                    current["dialogue"] = "\n".join(current.pop("_lines")).strip()
                    segments.append(current)
                current = {
                    "speaker": match.group(1),
                    "timestamp": match.group(2) or match.group(3),
                    "_lines": [],
                }
            elif current is not None:
                current["_lines"].append(line)
    if current:
        current["dialogue"] = "\n".join(current.pop("_lines")).strip()
        segments.append(current)
    return segments
def match_dual_output_choices(chunks, output_segments):
    """Return exact A/B selection per chunk, or an empty dict when no exact path exists."""
    output_keys = [_dual_match_segment_key(seg) for seg in output_segments]
    states = {0: []}
    for chunk in chunks:
        next_states = {}
        for position, path in states.items():
            for side in ("b", "a"):
                candidate = [_dual_match_segment_key(seg) for seg in chunk[side]["segments"]]
                end = position + len(candidate)
                if output_keys[position:end] == candidate and end not in next_states:
                    next_states[end] = path + [(chunk["chunk_id"], side)]
        states = next_states
        if not states:
            return {}
    complete = states.get(len(output_keys))
    return dict(complete) if complete else {}
def _similarity_to_ref(segments, ref_segments, policy):
    from core.transcript_eval import calc_lev_dist_ratio, normalize_dialogue
    source = " ".join(normalize_dialogue(seg.get("dialogue"), policy) for seg in segments).strip()
    reference = " ".join(normalize_dialogue(seg.get("dialogue"), policy) for seg in ref_segments).strip()
    if not source and not reference:
        return 1.0
    return calc_lev_dist_ratio(source, reference)
def _boundary_score(segments, ref_segments, policy):
    from core.transcript_eval import normalize_dialogue
    def keys(items):
        result = set()
        for seg in items[1:]:
            words = normalize_dialogue(seg.get("dialogue"), policy).split()
            if words:
                result.add(" ".join(words[:3]))
        return result
    source = keys(segments)
    reference = keys(ref_segments)
    if not source and not reference:
        return 1.0
    if not source or not reference:
        return 0.0
    hits = len(source & reference)
    precision = hits / len(source)
    recall = hits / len(reference)
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0
def build_dual_review_ledger(raw_a_path, raw_b_path, dual_output_path, ref_path, profile=None, existing_path=None):
    from core.denovo import extract_dual_chunk_triples
    policy = _load_policy(profile)
    with tempfile.TemporaryDirectory() as tmpdir:
        chunk_path = os.path.join(tmpdir, "chunks.json")
        extract_dual_chunk_triples(
            raw_a_path, raw_b_path, ref_path=ref_path, profile=profile, out_path=chunk_path)
        with open(chunk_path) as handle:
            chunk_payload = json.load(handle)
    chunks = chunk_payload["chunks"]
    output_segments = load_markdown_segments_strict(dual_output_path)
    choices = match_dual_output_choices(chunks, output_segments)
    episode_stem = os.path.basename(ref_path).rsplit("_", 1)[0]
    cases = []
    for chunk in chunks:
        if chunk.get("kind") != "diff":
            continue
        chunk_id = chunk["chunk_id"]
        selected = choices.get(chunk_id)
        a_segments = chunk["a"]["segments"]
        b_segments = chunk["b"]["segments"]
        ref_segments = (chunk.get("ref") or {}).get("segments", [])
        a_score = _similarity_to_ref(a_segments, ref_segments, policy)
        b_score = _similarity_to_ref(b_segments, ref_segments, policy)
        a_boundary = _boundary_score(a_segments, ref_segments, policy)
        b_boundary = _boundary_score(b_segments, ref_segments, policy)
        if selected is None:
            assessment = "unknown"
            selected_segments = []
        else:
            selected_score = a_boundary if selected == "a" else b_boundary
            best_score = max(a_boundary, b_boundary)
            assessment = "best_or_tied" if selected_score >= best_score else "selected_worse_source"
            selected_segments = a_segments if selected == "a" else b_segments
        case = _base_case(
            f"{episode_stem}::dual-{chunk.get('parent_chunk_id', chunk_id):04d}-{chunk.get('decision_sub_id', 0):02d}",
            episode_stem,
        )
        case.update({
            "mode": "dual",
            "ref_index": chunk_id,
            "timestamp_start": (selected_segments or a_segments or b_segments or [{}])[0].get("timestamp"),
            "change_status": assessment,
            "selected_source": selected,
            "category_suggested": "dual_source_choice",
            "category_signals": [chunk.get("kind"), assessment],
            "source_similarity_a": round(a_score, 4),
            "source_similarity_b": round(b_score, 4),
            "boundary_score_a": round(a_boundary, 4),
            "boundary_score_b": round(b_boundary, 4),
            "text_raw_a": _segments_text(a_segments),
            "text_raw_b": _segments_text(b_segments),
            "text_dual": _segments_text(selected_segments),
            "text_ref": _segments_text(ref_segments),
            "source_files": {
                "raw_a": os.path.basename(raw_a_path),
                "raw_b": os.path.basename(raw_b_path),
                "dual_output": os.path.basename(dual_output_path),
                "reference": os.path.basename(ref_path),
            },
        })
        cases.append(case)
    cases = _assign_regions(cases, episode_stem)
    cases = _preserve_review_fields(cases, existing_path)
    payload = {
        "mode": "dual",
        "episode_stem": episode_stem,
        "profile": profile,
        "source_files": {
            "raw_a": raw_a_path,
            "raw_b": raw_b_path,
            "dual_output": dual_output_path,
            "reference": ref_path,
        },
        "choices_matched_exactly": bool(choices),
        "cases": cases,
    }
    payload["summary"] = _summary(cases)
    return payload

### Output
def render_review_markdown(payload):
    lines = [
        "# Transcript Review Ledger",
        "",
        f"Mode: `{payload['mode']}`",
        f"Episode: `{payload['episode_stem']}`",
        f"Cases: **{payload['summary']['case_count']}**",
        "Edit review fields in the JSON ledger; they are preserved when regenerated.",
        "",
        "",
        "## Category counts",
    ]
    for category, count in sorted(payload["summary"]["category_counts"].items()):
        lines.append(f"- `{category}`: {count}")
    current_region = None
    for case in payload["cases"]:
        if case.get("region_id") != current_region:
            current_region = case.get("region_id")
            lines.extend(["", "", f"## {current_region}"])
        lines.extend([
            "",
            f"### {case['case_id']}",
            f"- Suggested category: `{case['category_suggested']}`",
            f"- Change/choice status: `{case['change_status']}`",
            f"- Review status: `{case['review_status']}`",
            f"- Review category: `{case['review_category']}`",
            f"- Review notes: {case['review_notes'] or ''}",
        ])
        field_labels = (
            ("text_raw", "Raw"),
            ("text_draft", "Draftds"),
            ("text_raw_a", "Source A"),
            ("text_raw_b", "Source B"),
            ("text_dual", "Dual output"),
            ("text_ref", "Human reference"),
        )
        for field, label in field_labels:
            if field not in case:
                continue
            lines.extend(["", f"#### {label}", "```text", case.get(field) or "(empty)", "```"])
    return "\n".join(lines).rstrip() + "\n"
def write_review_ledger(payload, json_path):
    os.makedirs(os.path.dirname(os.path.abspath(json_path)), exist_ok=True)
    with open(json_path, "w") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    markdown_path = os.path.splitext(json_path)[0] + ".md"
    with open(markdown_path, "w") as handle:
        handle.write(render_review_markdown(payload))
    return json_path, markdown_path
