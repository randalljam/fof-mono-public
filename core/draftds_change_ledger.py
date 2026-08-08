"""Build pipeline change ledgers from stage-to-stage transcript diffs and repair logs."""
import copy
import json
import os
import tempfile
from collections import Counter

from core.review_ledger import REVIEW_DEFAULTS, REVIEW_FIELDS, _speaker

STAGE_LABELS = {
    "raw_to_draftds": "raw → draftds",
    "draftds_to_draftls": "draftds → draftls",
    "raw_to_draftld_raws": "raw A+B → draftld_raws",
    "draftls_to_draftld_singles": "draftls A+B → draftld_singles",
}
EPISODE_SUFFIXES = (
    "_draftls_draftld", "_draftls", "_draftld", "_draftds",
    "_spasgn_nova2gen", "_spasgn_dgwhspm", "_nova2gen", "_dgwhspm", "_spasgn",
)

FIX_LABELS = {
    "short_speaker_blip": "blip merge (A-B-A collapse)",
    "short_speaker_blip_tail": "blip tail move",
    "merge_phrase_only_transition": "phrase-only merge",
    "question_tail_to_next": "question tail move",
    "broken_sentence_transition": "misplaced words (generic boundary repair)",
    "trailing_acknowledgement_to_next": "trailing acknowledgement move",
    "stranded_turn_opener_to_next": "stranded discourse opener",
    "cutoff_transition": "cutoff word move + ellipsis",
    "trailing_cutoff_before_next_start": "meeting cutoff overlap",
    "interrupted_turn_ellipsis": "cutoff ellipsis only (no word move)",
    "terminal_cutoff_dash": "ASR dash replaced with ellipsis",
    "merge_same_speaker": "same-speaker merge",
    "drop_empty_segment": "drop empty segment",
}
FIX_DESCRIPTIONS = {
    "short_speaker_blip": "Collapsed a short wrong-speaker blip into the surrounding same-speaker turn.",
    "short_speaker_blip_tail": "Moved a dangling tail from a blip onto the next speaker turn.",
    "merge_phrase_only_transition": "Merged a phrase-only segment into the longer neighboring turn.",
    "question_tail_to_next": "Moved a dangling question fragment onto the next speaker.",
    "broken_sentence_transition": (
        "Generic boundary repair: previous turn lacks ending punctuation and the next turn "
        "starts lowercase. Moves a short word chunk across the boundary to rejoin a broken "
        "sentence. Used when no more specific pattern matched. "
        "Example: prev ends `...representing goal` / next starts `number two...`."
    ),
    "trailing_acknowledgement_to_next": "Moved a trailing acknowledgement (e.g. Yeah,) to the next speaker.",
    "stranded_turn_opener_to_next": (
        "Previous turn ends with a discourse opener (So, And then) that the next speaker "
        "repeats at the start of their turn. Moves that opener to the next speaker and "
        "marks the previous turn with `...`. "
        "Example: prev ends `discussion that So` / next starts `so right now...`."
    ),
    "cutoff_transition": (
        "Moved completion words across a cutoff boundary and added `...` to the interrupted turn."
    ),
    "trailing_cutoff_before_next_start": (
        "Meeting interrupt pattern: previous turn ends mid-phrase and the next speaker "
        "continues the same words. Moves the overlapping start onto the next speaker and "
        "marks the cutoff with `...`. "
        "Example: prev ends `trying to Yeah.` / next starts `to Yeah. They overlapped...`."
    ),
    "interrupted_turn_ellipsis": (
        "Previous turn has no ending punctuation and the next speaker starts a new turn "
        "with a capital letter. No words to move — only marks the interruption with `...`. "
        "Example: prev ends `I can always flip` / next starts `Yeah. No. I think...`."
    ),
    "terminal_cutoff_dash": "Replaced a trailing ASR cutoff dash (e.g. `So-`) with `...`.",
    "merge_same_speaker": "Merged consecutive segments from the same speaker.",
    "drop_empty_segment": "Removed an empty segment left after a boundary repair.",
}
LLM_CHANGE_LABELS = {
    "speaker_change": "speaker relabel",
    "dialogue_change": "dialogue edit at same turn",
    "segment_added": "new segment in output",
    "segment_removed": "segment removed from input",
}
DUAL_CHANGE_LABELS = {
    "dual_selected_a": "chose source A at disagreement",
    "dual_selected_b": "chose source B at disagreement",
    "dual_choice_unknown": "A/B side not recovered from output file",
}
DUAL_STAGE_IDS = frozenset({"raw_to_draftld_raws", "draftls_to_draftld_singles"})

### Helpers
def _timestamp_seconds(timestamp):
    if not timestamp:
        return 0
    parts = [int(part) for part in str(timestamp).split(":")]
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + part
    return seconds
def _episode_stem(path):
    base = os.path.splitext(os.path.basename(path or ""))[0]
    changed = True
    while changed:
        changed = False
        for suffix in EPISODE_SUFFIXES:
            if base.endswith(suffix):
                base = base[: -len(suffix)]
                changed = True
                break
    return base or "episode"
def _transcript_arm(path):
    base = os.path.basename(path or "").lower()
    if "nova2gen" in base:
        return "A", "nova2gen"
    if "dgwhspm" in base:
        return "B", "dgwhspm"
    return None, None
def _raw_variant_label(path):
    arm, source = _transcript_arm(path)
    if arm and source:
        return f"raw_{arm}_{source}"
    return _episode_stem(path)
def _draft_variant_label(path, stage_kind):
    arm, _ = _transcript_arm(path)
    if arm:
        return f"{stage_kind}_{arm}"
    return stage_kind
def _single_arm_stage_label(input_path, output_kind):
    return f"{_raw_variant_label(input_path)} → {_draft_variant_label(input_path, output_kind)}"
def _draftds_to_draftls_label(before_path):
    arm, _ = _transcript_arm(before_path)
    if arm:
        return f"draftds_{arm} → draftls_{arm}"
    return STAGE_LABELS["draftds_to_draftls"]
def _normalize_episode_stem(*paths):
    stems = [_episode_stem(path) for path in paths if path]
    return stems[0] if stems else "episode"
def _infer_draft_path(raw_path, suffix):
    from core.fileops import add_suffix_in_str
    return add_suffix_in_str(raw_path, suffix)
def _speaker_keys(log):
    keys = []
    for field in (
        "speaker", "kept_speaker", "removed_speaker", "phrase_speaker",
        "from_speaker", "to_speaker", "tail_to_speaker", "next_speaker",
    ):
        value = log.get(field)
        if value and value not in keys:
            keys.append(value)
    return keys
def _anchor_timestamp(log, raw_segments):
    timestamp = log.get("timestamp")
    if timestamp:
        return timestamp
    moved = " ".join(log.get("moved_words") or [])
    speakers = _speaker_keys(log)
    best = None
    best_score = None
    for seg in raw_segments:
        dialogue = seg.get("dialogue") or ""
        score = 0
        if _speaker(seg) in speakers:
            score += 2
        if moved and moved in dialogue:
            score += 3
        elif moved:
            first = (log.get("moved_words") or [""])[0]
            if first and first in dialogue.split():
                score += 1
        if score <= 0:
            continue
        seconds = _timestamp_seconds(seg.get("timestamp"))
        if best_score is None or score > best_score or (score == best_score and seconds < _timestamp_seconds(best)):
            best = seg.get("timestamp")
            best_score = score
    if best:
        return best
    for seg in raw_segments:
        if _speaker(seg) in speakers:
            return seg.get("timestamp")
    return raw_segments[0].get("timestamp") if raw_segments else None
def _nearest_index(segments, timestamp):
    if not segments:
        return None
    target = _timestamp_seconds(timestamp)
    return min(
        range(len(segments)),
        key=lambda index: abs(_timestamp_seconds(segments[index].get("timestamp")) - target),
    )
def _match_segment(before_seg, after_segments, used_indexes, max_gap_seconds=15):
    target = _timestamp_seconds(before_seg.get("timestamp"))
    best = None
    best_score = None
    for index, after_seg in enumerate(after_segments):
        if index in used_indexes:
            continue
        gap = abs(_timestamp_seconds(after_seg.get("timestamp")) - target)
        if gap > max_gap_seconds:
            continue
        score = gap
        if _speaker(before_seg) == _speaker(after_seg):
            score -= 5
        if best_score is None or score < best_score:
            best = index
            best_score = score
    return best
def _summarize_fix(log):
    fix_type = log.get("type") or "unknown"
    parts = [FIX_LABELS.get(fix_type, fix_type)]
    moved = log.get("moved_words") or []
    if moved:
        parts.append(f"moved: {' '.join(moved)}")
    direction = log.get("direction")
    if direction == "prev_to_next":
        parts.append(f"{log.get('from_speaker')} -> {log.get('to_speaker')}")
    elif direction == "next_to_prev":
        parts.append(f"{log.get('from_speaker')} -> {log.get('to_speaker')}")
    elif fix_type == "short_speaker_blip":
        parts.append(f"removed {log.get('removed_speaker')}, kept {log.get('kept_speaker')}")
    elif fix_type == "merge_phrase_only_transition":
        parts.append(f"kept {log.get('kept_speaker')}, merged {log.get('phrase_speaker')}")
    elif fix_type == "interrupted_turn_ellipsis":
        parts.append(f"{log.get('speaker')} before {log.get('next_speaker')}")
    elif fix_type == "merge_same_speaker":
        parts.append(str(log.get("speaker")))
    return " · ".join(part for part in parts if part)
def _base_case(case_id, episode_stem, stage_id):
    return {
        "case_id": case_id,
        "episode_stem": episode_stem,
        "stage_id": stage_id,
        "change_type": "unknown",
        "change_label": "unknown",
        "change_summary": "",
        **REVIEW_DEFAULTS,
    }
def _preserve_review_fields(cases, existing_path):
    if not existing_path or not os.path.isfile(existing_path):
        return cases
    with open(existing_path) as handle:
        previous = json.load(handle)
    by_id = {}
    for case in previous.get("cases", []):
        by_id[case.get("case_id")] = case
    for stage in previous.get("stages", []):
        for case in stage.get("cases", []):
            by_id[case.get("case_id")] = case
    for case in cases:
        old = by_id.get(case["case_id"])
        if not old:
            continue
        for field in REVIEW_FIELDS:
            if field in old:
                case[field] = old[field]
    return cases
def _stage_summary(stage_id, before_count, after_count, cases, labels, label=None):
    return {
        "stage_id": stage_id,
        "label": label or STAGE_LABELS.get(stage_id, stage_id),
        "input_segment_count": before_count,
        "output_segment_count": after_count,
        "net_segment_delta": after_count - before_count,
        "change_count": len(cases),
        "change_type_counts": dict(Counter(case.get("change_type", "unknown") for case in cases)),
        "change_type_labels": labels,
        "cases": cases,
    }
def _render_change_type_table(cases, labels, heading="## Change type counts"):
    lines = [
        heading,
        "",
        "| Change type | Label | Count |",
        "|-------------|-------|------:|",
    ]
    counts = Counter(case.get("change_type", "unknown") for case in cases)
    total = 0
    for change_type, count in sorted(counts.items()):
        label = labels.get(change_type, change_type)
        lines.append(f"| `{change_type}` | {label} | {count} |")
        total += count
    lines.append(f"| **Total** | | **{total}** |")
    return lines
def _render_stage_overview_table(stages):
    lines = [
        "## All stages",
        "",
        "Use diff view for individual spots; this report is classification counts only.",
        "",
        "Segment columns are full transcript size. **Decisions** counts review items for that stage "
        "(deterministic fixes, LLM edits, or dual A/B picks — see each stage section).",
        "",
        "| Stage | Input segments | Output segments | Net change | Decisions |",
        "|-------|---------------:|----------------:|-----------:|----------:|",
    ]
    for stage in stages:
        lines.append(
            f"| {stage['label']} | {stage['input_segment_count']} | "
            f"{stage['output_segment_count']} | {stage['net_segment_delta']:+d} | "
            f"{stage['change_count']} |"
        )
    return lines
def _render_dual_stage_intro(stage_meta):
    count = stage_meta.get("change_count", 0)
    diff_count = stage_meta.get("diff_chunk_count", count)
    return [
        f"**{count} disagreement regions** where source A and B differed "
        f"({diff_count} required an explicit A/B choice during merge).",
        "",
        "Dual merge does not rewrite text: at each region it copies one source's segments verbatim. "
        "Agreeing regions pass through from the configured base side without an LLM call.",
        "",
        "Each decision row is one disagreement region (not one word change and not one output segment).",
        "",
    ]

### Build: draftds stage
def build_draftds_stage(raw_path, profile=None, draft_path=None, episode_stem=None, stage_id=None, label=None):
    from core.denovo import apply_deterministic_cleanup, load_segments_from_md, resolve_profile_policy

    raw_segments = load_segments_from_md(raw_path) or []
    policy = resolve_profile_policy(profile)
    cleaned_segments, repair_logs = apply_deterministic_cleanup(
        copy.deepcopy(raw_segments), policy=policy, verbose=False,
    )
    draft_matches = True
    if draft_path and os.path.isfile(draft_path):
        draft_segments = load_segments_from_md(draft_path) or []
        draft_keys = [
            _speaker(seg) + "|" + str(seg.get("timestamp")) + "|" + (seg.get("dialogue") or "")
            for seg in draft_segments
        ]
        cleaned_keys = [
            _speaker(seg) + "|" + str(seg.get("timestamp")) + "|" + (seg.get("dialogue") or "")
            for seg in cleaned_segments
        ]
        draft_matches = draft_keys == cleaned_keys
    episode_stem = episode_stem or _episode_stem(raw_path)
    stage_id = stage_id or "raw_to_draftds"
    cases = []
    for index, log in enumerate(repair_logs):
        change_type = log.get("type") or "unknown"
        timestamp = _anchor_timestamp(log, raw_segments)
        case = _base_case(
            f"{episode_stem}::{stage_id}::fix-{index:04d}-{change_type}",
            episode_stem,
            stage_id,
        )
        case.update({
            "change_index": index,
            "change_type": change_type,
            "change_label": FIX_LABELS.get(change_type, change_type),
            "change_description": FIX_DESCRIPTIONS.get(change_type, ""),
            "change_summary": _summarize_fix(log),
            "timestamp_start": timestamp,
            "repair_log": log,
        })
        cases.append(case)
    stage = _stage_summary(
        stage_id, len(raw_segments), len(cleaned_segments), cases, FIX_LABELS, label=label)
    stage.update({
        "input_path": raw_path,
        "output_path": draft_path,
        "draft_matches_recomputed": draft_matches,
    })
    return stage
def build_draftds_change_ledger(raw_path, profile=None, draft_path=None, existing_path=None):
    stage = build_draftds_stage(raw_path, profile=profile, draft_path=draft_path)
    cases = _preserve_review_fields(stage["cases"], existing_path)
    payload = {
        "mode": "draftds_change",
        "episode_stem": _episode_stem(raw_path),
        "profile": profile,
        "source_files": {"raw": raw_path, "draftds": draft_path},
        "draft_matches_recomputed": stage.get("draft_matches_recomputed", True),
        "stages": [{key: stage[key] for key in stage if key != "cases"}],
        "cases": cases,
        "summary": {
            "stage_count": 1,
            "change_count": len(cases),
            "case_count": len(cases),
            "input_segment_count": stage["input_segment_count"],
            "output_segment_count": stage["output_segment_count"],
            "net_segment_delta": stage["net_segment_delta"],
            "change_type_counts": stage["change_type_counts"],
        },
    }
    return payload

### Build: file diff stage
def build_segment_diff_stage(before_path, after_path, stage_id, episode_stem, profile=None, label=None):
    from core.denovo import load_segments_from_md
    from core.transcript_eval import normalize_dialogue

    before_segments = load_segments_from_md(before_path) or []
    after_segments = load_segments_from_md(after_path) or []
    used_after = set()
    cases = []
    change_index = 0
    for before_seg in before_segments:
        match_index = _match_segment(before_seg, after_segments, used_after)
        if match_index is None:
            change_type = "segment_removed"
            summary = f"{_speaker(before_seg)} {before_seg.get('timestamp') or ''}".strip()
        else:
            used_after.add(match_index)
            after_seg = after_segments[match_index]
            before_text = normalize_dialogue(before_seg.get("dialogue"), None)
            after_text = normalize_dialogue(after_seg.get("dialogue"), None)
            if before_text == after_text and _speaker(before_seg) == _speaker(after_seg):
                continue
            if _speaker(before_seg) != _speaker(after_seg):
                change_type = "speaker_change"
                summary = f"{_speaker(before_seg)} -> {_speaker(after_seg)} at {before_seg.get('timestamp')}"
            else:
                change_type = "dialogue_change"
                summary = f"{_speaker(before_seg)} {before_seg.get('timestamp') or ''}".strip()
        case = _base_case(
            f"{episode_stem}::{stage_id}::change-{change_index:04d}-{change_type}",
            episode_stem,
            stage_id,
        )
        case.update({
            "change_index": change_index,
            "change_type": change_type,
            "change_label": LLM_CHANGE_LABELS.get(change_type, change_type),
            "change_summary": summary,
            "timestamp_start": before_seg.get("timestamp"),
        })
        cases.append(case)
        change_index += 1
    for index, after_seg in enumerate(after_segments):
        if index in used_after:
            continue
        change_type = "segment_added"
        case = _base_case(
            f"{episode_stem}::{stage_id}::change-{change_index:04d}-{change_type}",
            episode_stem,
            stage_id,
        )
        case.update({
            "change_index": change_index,
            "change_type": change_type,
            "change_label": LLM_CHANGE_LABELS.get(change_type, change_type),
            "change_summary": f"{_speaker(after_seg)} {after_seg.get('timestamp') or ''}".strip(),
            "timestamp_start": after_seg.get("timestamp"),
        })
        cases.append(case)
        change_index += 1
    stage = _stage_summary(
        stage_id, len(before_segments), len(after_segments), cases, LLM_CHANGE_LABELS, label=label)
    stage.update({"input_path": before_path, "output_path": after_path})
    return stage

### Build: dual stage
def build_dual_change_stage(
    input_a_path, input_b_path, dual_output_path, stage_id, episode_stem, profile=None, label=None):
    from core.denovo import extract_dual_chunk_triples
    from core.review_ledger import load_markdown_segments_strict, match_dual_output_choices

    with tempfile.TemporaryDirectory() as tmpdir:
        chunk_path = os.path.join(tmpdir, "chunks.json")
        extract_dual_chunk_triples(
            input_a_path, input_b_path, ref_path=None, profile=profile, out_path=chunk_path)
        with open(chunk_path) as handle:
            chunks = json.load(handle)["chunks"]
    output_segments = load_markdown_segments_strict(dual_output_path)
    choices = match_dual_output_choices(chunks, output_segments)
    cases = []
    change_index = 0
    for chunk in chunks:
        if chunk.get("kind") != "diff":
            continue
        chunk_id = chunk["chunk_id"]
        selected = choices.get(chunk_id)
        if selected == "a":
            change_type = "dual_selected_a"
        elif selected == "b":
            change_type = "dual_selected_b"
        else:
            change_type = "dual_choice_unknown"
        timestamp = (chunk.get("a") or {}).get("segments", [{}])[0].get("timestamp")
        case = _base_case(
            f"{episode_stem}::{stage_id}::chunk-{chunk_id:04d}-{change_type}",
            episode_stem,
            stage_id,
        )
        case.update({
            "change_index": change_index,
            "change_type": change_type,
            "change_label": DUAL_CHANGE_LABELS.get(change_type, change_type),
            "change_summary": (
                f"disagreement region {chunk_id}: "
                f"{'source ' + selected.upper() if selected else 'side not recovered'}"
            ),
            "timestamp_start": timestamp,
            "chunk_id": chunk_id,
            "selected_source": selected,
        })
        cases.append(case)
        change_index += 1
    input_a_count = len(load_markdown_segments_strict(input_a_path))
    input_b_count = len(load_markdown_segments_strict(input_b_path))
    output_count = len(output_segments)
    stage = _stage_summary(stage_id, input_a_count, output_count, cases, DUAL_CHANGE_LABELS, label=label)
    stage.update({
        "input_a_path": input_a_path,
        "input_b_path": input_b_path,
        "input_b_segment_count": input_b_count,
        "output_path": dual_output_path,
        "choices_matched_exactly": bool(choices),
        "diff_chunk_count": sum(1 for chunk in chunks if chunk.get("kind") == "diff"),
    })
    return stage

### Build: pipeline
def build_pipeline_change_ledger(
    raw_path=None,
    draftds_path=None,
    draftls_path=None,
    raw_a_path=None,
    raw_b_path=None,
    draftds_a_path=None,
    draftds_b_path=None,
    draftld_path=None,
    draftls_a_path=None,
    draftls_b_path=None,
    draftls_draftld_path=None,
    profile=None,
    existing_path=None,
):
    all_paths = [
        raw_path, draftds_path, draftls_path, raw_a_path, raw_b_path,
        draftds_a_path, draftds_b_path, draftld_path, draftls_a_path,
        draftls_b_path, draftls_draftld_path,
    ]
    episode_stem = _normalize_episode_stem(*all_paths)
    stages = []
    use_ab_arms = bool(raw_a_path or raw_b_path or draftls_a_path or draftls_b_path)
    if raw_path and not use_ab_arms:
        stages.append(build_draftds_stage(
            raw_path, profile=profile, draft_path=draftds_path, episode_stem=episode_stem))
    if raw_a_path:
        draftds_a = draftds_a_path or _infer_draft_path(raw_a_path, "_draftds")
        stages.append(build_draftds_stage(
            raw_a_path,
            profile=profile,
            draft_path=draftds_a,
            episode_stem=episode_stem,
            stage_id="raw_to_draftds_a",
            label=_single_arm_stage_label(raw_a_path, "draftds"),
        ))
    if raw_b_path:
        draftds_b = draftds_b_path or _infer_draft_path(raw_b_path, "_draftds")
        stages.append(build_draftds_stage(
            raw_b_path,
            profile=profile,
            draft_path=draftds_b,
            episode_stem=episode_stem,
            stage_id="raw_to_draftds_b",
            label=_single_arm_stage_label(raw_b_path, "draftds"),
        ))
    if not use_ab_arms and draftds_path and draftls_path:
        stages.append(build_segment_diff_stage(
            draftds_path, draftls_path, "draftds_to_draftls", episode_stem, profile=profile))
    arm_llm_pairs = (
        ("a", raw_a_path, draftds_a_path, draftls_a_path),
        ("b", raw_b_path, draftds_b_path, draftls_b_path),
    )
    for arm_key, raw_arm_path, draftds_arm_path, draftls_arm_path in arm_llm_pairs:
        if not draftls_arm_path:
            continue
        draftds_arm = draftds_arm_path or (
            _infer_draft_path(raw_arm_path, "_draftds") if raw_arm_path else None)
        if not draftds_arm:
            continue
        stages.append(build_segment_diff_stage(
            draftds_arm,
            draftls_arm_path,
            f"draftds_to_draftls_{arm_key}",
            episode_stem,
            profile=profile,
            label=_draftds_to_draftls_label(raw_arm_path or draftds_arm),
        ))
    if raw_a_path and raw_b_path and draftld_path:
        if os.path.isfile(draftld_path):
            stages.append(build_dual_change_stage(
                raw_a_path,
                raw_b_path,
                draftld_path,
                "raw_to_draftld_raws",
                episode_stem,
                profile=profile,
                label=STAGE_LABELS["raw_to_draftld_raws"],
            ))
    if draftls_a_path and draftls_b_path and draftls_draftld_path:
        if os.path.isfile(draftls_draftld_path):
            stages.append(build_dual_change_stage(
                draftls_a_path,
                draftls_b_path,
                draftls_draftld_path,
                "draftls_to_draftld_singles",
                episode_stem,
                profile=profile,
                label=STAGE_LABELS["draftls_to_draftld_singles"],
            ))
    if not stages:
        raise ValueError(
            "Provide at least one stage input. Examples: --raw-a + --raw-b for draftds only; "
            "add --draftls-a/--draftls-b for draftds→draftls; --draftld for raw dual; "
            "--draftls-draftld for dual after singles."
        )
    cases = []
    for stage in stages:
        cases.extend(stage["cases"])
    cases = _preserve_review_fields(cases, existing_path)
    case_by_id = {case["case_id"]: case for case in cases}
    for stage in stages:
        stage["cases"] = [case_by_id[case["case_id"]] for case in stage["cases"]]
    payload = {
        "mode": "pipeline_change",
        "episode_stem": episode_stem,
        "profile": profile,
        "stages": [{key: value for key, value in stage.items() if key != "cases"} for stage in stages],
        "cases": cases,
        "summary": {
            "stage_count": len(stages),
            "stage_ids": [stage["stage_id"] for stage in stages],
            "change_count": len(cases),
            "review_counts": dict(Counter(case.get("review_status", "pending") for case in cases)),
        },
    }
    return payload

### Output
def render_pipeline_change_markdown(payload):
    lines = [
        "# Pipeline Change Ledger",
        "",
    ]
    if payload.get("run_timestamp"):
        lines.append(f"Run `{payload['run_timestamp']}` · episode `{payload['episode_stem']}`")
    else:
        lines.append(f"Episode: `{payload['episode_stem']}`")
    stage_ids = payload["summary"].get("stage_ids") or []
    if stage_ids:
        lines.append(f"Stages in this report: `{', '.join(stage_ids)}`")
    lines.extend([
        f"Classified decisions: **{payload['summary']['change_count']}**",
        "",
        "Only stages requested on the CLI are included. Passing `--raw-a` / `--raw-b` alone "
        "reports raw→draftds only; add `--draftls-a` / `--draftls-b`, `--draftld`, or "
        "`--draftls-draftld` to include later pipeline steps.",
        "",
        "Stage-to-stage review only (no human reference). Use this table to spot-check categories, "
        "then open diff view for the timestamps that matter.",
        "Edit review fields in the JSON ledger; they are preserved when regenerated to the same `--out` path.",
        "",
    ])
    stage_rows = []
    for stage_meta in payload["stages"]:
        stage_rows.append({
            "label": stage_meta["label"],
            "input_segment_count": stage_meta["input_segment_count"],
            "output_segment_count": stage_meta["output_segment_count"],
            "net_segment_delta": stage_meta["net_segment_delta"],
            "change_count": stage_meta["change_count"],
        })
    lines.extend(_render_stage_overview_table(stage_rows))
    cases_by_stage = {}
    for case in payload["cases"]:
        cases_by_stage.setdefault(case["stage_id"], []).append(case)
    for stage_meta in payload["stages"]:
        stage_id = stage_meta["stage_id"]
        stage_cases = cases_by_stage.get(stage_id, [])
        labels = stage_meta.get("change_type_labels") or FIX_LABELS
        lines.extend([
            "",
            "",
            f"## {stage_meta['label']}",
            "",
        ])
        if stage_meta.get("draft_matches_recomputed") is False:
            lines.append("**Warning:** supplied draftds file does not match a fresh deterministic run.")
            lines.append("")
        if stage_id in DUAL_STAGE_IDS:
            lines.extend(_render_dual_stage_intro(stage_meta))
        lines.extend(_render_change_type_table(
            stage_cases, labels, heading="## Decision breakdown"))
    return "\n".join(lines).rstrip() + "\n"
def render_draftds_change_markdown(payload, max_cases_per_type=8):
    pipeline_payload = {
        "mode": "pipeline_change",
        "episode_stem": payload["episode_stem"],
        "summary": {
            "stage_count": 1,
            "change_count": payload["summary"]["change_count"],
        },
        "stages": payload.get("stages") or [{
            "stage_id": "raw_to_draftds",
            "label": STAGE_LABELS["raw_to_draftds"],
            "input_segment_count": payload["summary"]["input_segment_count"],
            "output_segment_count": payload["summary"]["output_segment_count"],
            "net_segment_delta": payload["summary"]["net_segment_delta"],
            "change_count": payload["summary"]["change_count"],
            "draft_matches_recomputed": payload.get("draft_matches_recomputed", True),
            "change_type_labels": FIX_LABELS,
        }],
        "cases": [
            dict(case, stage_id=case.get("stage_id") or "raw_to_draftds", change_type=case.get("change_type") or case.get("fix_type"))
            for case in payload["cases"]
        ],
    }
    return render_pipeline_change_markdown(pipeline_payload)
def write_pipeline_change_ledger(payload, json_path):
    os.makedirs(os.path.dirname(os.path.abspath(json_path)), exist_ok=True)
    with open(json_path, "w") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    markdown_path = os.path.splitext(json_path)[0] + ".md"
    with open(markdown_path, "w") as handle:
        handle.write(render_pipeline_change_markdown(payload))
    return json_path, markdown_path
def write_draftds_change_ledger(payload, json_path, max_cases_per_type=8):
    return write_pipeline_change_ledger(payload, json_path)
