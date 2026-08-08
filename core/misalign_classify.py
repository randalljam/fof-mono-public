import json

MISALIGN_LABELS = [
    "boundary_bleed_start",
    "boundary_bleed_end",
    "blip_merge",
    "cutoff_ellipsis",
    "missing_turn",
    "spurious_turn",
    "split_needed",
    "structural_divergence",
    "matcher_artifact",
    "asr_edge_word",
    "other",
]
REPAIR_FAMILIES = [
    "boundary_move",
    "merge",
    "split",
    "insert_missing",
    "delete_spurious",
    "none_structural",
    "none_artifact",
]
CLASSIFIER_SYSTEM_PROMPT = """
You classify one diarized ASR transcript misalignment window.

The candidate is a diarized ASR transcript region flanked by two already-correct anchor turns. The reference is the human-correct segmentation of the same span. Classify the single dominant defect in this window using the label taxonomy.

Set repairable to true ONLY when a segmentation-only edit could fix the defect WITHOUT adding, removing, or altering any words — by re-drawing boundaries over text that is ALREADY PRESENT in the candidate: moving a boundary, merging a blip into its neighbor, deleting a spurious/duplicate turn, or splitting one candidate turn into the correct multiple turns.

Critical rule for missing_turn: a reference turn marked <<missing>> is repairable=true ONLY if that turn's words are actually present in the shown candidate (merged into an adjacent candidate segment) and can be recovered by splitting. If the missing turn's words are ABSENT from the candidate entirely (the ASR dropped them), set repairable=false with repair_family=insert_missing — no single-transcript segmentation edit can recover words that are not there. In that case say in suggested_fix that recovery needs the other ASR transcript (dual merge) or the source audio.

Use structural_divergence when the reference and candidate are segmented at incompatibly different granularity, such as large merge/split-scale disagreement, and the window is usually not cleanly repairable. Use matcher_artifact when the shown misalignment looks like an eval alignment artifact rather than a real transcript defect. Use asr_edge_word when the only difference is a mis-transcribed edge word and no segmentation fix applies.

Do not invent words. Base your judgment only on the shown text.
""".strip()
TOOLS_CLASSIFY_MISALIGNMENT = [
    {
        "type": "function",
        "function": {
            "name": "classify_misalignment_window",
            "description": "Classify the dominant defect in one misalignment window.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "enum": MISALIGN_LABELS,
                        "description": "Dominant misalignment label.",
                    },
                    "repairable": {
                        "type": "boolean",
                        "description": "Whether a segmentation-only edit can fix the window without changing words.",
                    },
                    "repair_family": {
                        "type": "string",
                        "enum": REPAIR_FAMILIES,
                        "description": "Broad repair family.",
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Confidence in the classification.",
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Brief basis for the classification.",
                    },
                    "suggested_fix": {
                        "type": "string",
                        "description": "Concise segmentation-only fix, or why none applies.",
                    },
                },
                "required": [
                    "label",
                    "repairable",
                    "repair_family",
                    "confidence",
                    "rationale",
                    "suggested_fix",
                ],
                "additionalProperties": False,
            },
        },
    }
]

### Rendering
def _format_segment(seg):
    timestamp = seg.get("timestamp") or ""
    speaker = seg.get("speaker") or ""
    dialogue = seg.get("dialogue") or ""
    return f"[{timestamp}] {speaker}: {dialogue}"
def _format_anchor_section(anchors):
    if anchors is None:
        return ["(open boundary)"]
    if not anchors:
        return ["(none)"]
    return [_format_segment(anchor) for anchor in anchors]
def _candidate_markers(seg):
    markers = []
    if seg.get("is_delete"):
        markers.append("<<spurious>>")
    if seg.get("is_boundary_misplaced"):
        markers.append("<<misplaced>>")
    if seg.get("is_boundary_error"):
        markers.append("<<boundary_error>>")
    return "  " + " ".join(markers) if markers else ""
def _reference_markers(seg):
    if seg.get("is_missing"):
        return "  <<missing>>"
    return ""
def render_window_prompt_content(window):
    """
    Render one misalignment window as deterministic compact classifier input.

    :param window: dict window returned by core.transcript_misalign.
    :return content: str prompt content for the classifier LLM.
    """
    lines = [
        f"window_id: {window.get('window_id')}",
        f"window_kind_hint: {window.get('window_kind_hint')}",
        "error_signature: " + json.dumps(window.get("error_signature") or {}, sort_keys=True),
        "",
        "## anchor before",
    ]
    lines.extend(_format_anchor_section(window.get("anchor_before")))
    lines.extend(["", "## candidate"])
    candidate_segments = window.get("candidate_segments") or []
    if candidate_segments:
        for seg in candidate_segments:
            lines.append(_format_segment(seg) + _candidate_markers(seg))
    else:
        lines.append("(none)")
    lines.extend(["", "## reference"])
    reference_segments = window.get("reference_segments") or []
    if reference_segments:
        for seg in reference_segments:
            lines.append(_format_segment(seg) + _reference_markers(seg))
    else:
        lines.append("(none)")
    lines.extend(["", "## anchor after"])
    lines.extend(_format_anchor_section(window.get("anchor_after")))
    return "\n".join(lines)

### Classification
def _valid_classification(parsed):
    if not isinstance(parsed, dict):
        return False
    if parsed.get("label") not in MISALIGN_LABELS:
        return False
    if parsed.get("repair_family") not in REPAIR_FAMILIES:
        return False
    return True
def classify_misalignment_window(window, model="gpt-5-mini", provider="openai", max_retries=3, usage_accumulator=None, verbose=False):
    """
    Classify one misalignment window via an OpenAI strict function call.

    :param window: dict window returned by core.transcript_misalign.
    :param model: str model name, explicitly defaulting to gpt-5-mini.
    :param provider: str provider parser name; only openai calls are issued.
    :param max_retries: int number of attempts before returning None.
    :param usage_accumulator: optional TokenUsageAccumulator-compatible object.
    :param verbose: bool print retry diagnostics.
    :return classification: parsed classification dict, or None.
    """
    from core.llm import openai_function_call_with_usage, parse_function_call_response

    if provider != "openai":
        if verbose:
            print(f"classify_misalignment_window only supports openai calls, got {provider}")
        return None
    content = render_window_prompt_content(window)
    attempts = max(1, int(max_retries or 1))
    last_error = None
    for attempt in range(attempts):
        response, usage, _ = openai_function_call_with_usage(
            CLASSIFIER_SYSTEM_PROMPT, content, TOOLS_CLASSIFY_MISALIGNMENT,
            model=model, verbose=verbose)
        if usage_accumulator:
            usage_accumulator.add_usage(
                usage["input_tokens"], usage["output_tokens"], usage.get("cached_input_tokens", 0),
                is_retry=attempt > 0,
            )
        parsed = parse_function_call_response(response, provider="openai")
        if _valid_classification(parsed):
            return parsed
        last_error = f"invalid classification response: {parsed!r}"
        if verbose:
            print(f"classify_misalignment_window attempt {attempt + 1} failed: {last_error}")
    if verbose:
        print(f"classify_misalignment_window failed after {attempts} attempts: {last_error}")
    return None
def _summary_label(label):
    if label in MISALIGN_LABELS:
        return label
    return "other"
def _count_summary(summary, classification):
    label = _summary_label(classification.get("label"))
    summary["label_counts"][label] = summary["label_counts"].get(label, 0) + 1
    if classification.get("repairable") is True:
        summary["repairable_count"] += 1
    else:
        summary["not_repairable_count"] += 1
    family = classification.get("repair_family")
    if family in REPAIR_FAMILIES:
        summary["repair_family_counts"][family] = summary["repair_family_counts"].get(family, 0) + 1
def classify_misalignment_windows(result, model="gpt-5-mini", limit=None, usage_accumulator=None, classify_fn=None, verbose=False):
    """
    Classify windows in-place and return aggregate classification counts.

    :param result: dict returned by core.transcript_misalign.
    :param model: str model passed to classify_misalignment_window.
    :param limit: optional int maximum number of windows to classify.
    :param usage_accumulator: optional TokenUsageAccumulator-compatible object.
    :param classify_fn: optional injected callable for tests/dry-runs.
    :param verbose: bool passed to classify_misalignment_window.
    :return summary: dict aggregate counts and optional usage summary.
    """
    windows = result.get("windows") or []
    selected = windows if limit is None else windows[:limit]
    summary = {
        "classified": 0,
        "unclassified": 0,
        "label_counts": {},
        "repairable_count": 0,
        "not_repairable_count": 0,
        "repair_family_counts": {},
        "usage": None,
    }
    for window in selected:
        if classify_fn:
            classification = classify_fn(window)
        else:
            classification = classify_misalignment_window(
                window, model=model, usage_accumulator=usage_accumulator, verbose=verbose)
        window["classification"] = classification
        if classification is None:
            summary["unclassified"] += 1
            continue
        summary["classified"] += 1
        _count_summary(summary, classification)
    summary["unclassified"] += max(0, len(windows) - len(selected))
    if usage_accumulator:
        summary["usage"] = usage_accumulator.summary()
    return summary
