import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("ELEVENLABS_API_KEY", "unused")
sys.modules.setdefault("elevenlabs", MagicMock())
sys.modules.setdefault("elevenlabs.client", MagicMock())

import json

from core.transcript_eval import evaluate_step_segments_align, extract_transcript_data

METRIC_KEYS = (
    "seg_error_count",
    "seg_error_count_strict",
    "seg_missing_count",
    "seg_spurious_count",
    "seg_boundary_error_count",
    "seg_boundary_misplaced_count",
)

### Segment Predicates
def _validate_mode(mode):
    if mode not in ("strict", "loose"):
        raise ValueError('mode must be "strict" or "loose"')
def _is_misaligned(seg, mode):
    if seg.get("is_delete") is True:
        return True
    if mode == "strict":
        return seg.get("is_boundary_misplaced") is True
    return seg.get("is_boundary_error") is True
def _is_clean_anchor(seg, mode):
    if seg.get("is_aligned") is not True:
        return False
    if seg.get("is_delete") is True:
        return False
    if mode == "strict":
        return seg.get("is_boundary_misplaced") is not True
    return seg.get("is_boundary_error") is not True
def _speaker(seg):
    return seg.get("speaker_name") or seg.get("speaker_full") or ""

### Projection Helpers
def _project_anchor(seg, eval_index):
    return {
        "role": "anchor",
        "eval_index": eval_index,
        "timestamp": seg.get("timestamp") or "",
        "speaker": _speaker(seg),
        "dialogue": seg.get("dialogue") or "",
        "aligned_ref_index": seg.get("aligned_ref_index"),
    }
def _project_candidate(seg, eval_index):
    return {
        "eval_index": eval_index,
        "timestamp": seg.get("timestamp") or "",
        "speaker": _speaker(seg),
        "dialogue": seg.get("dialogue") or "",
        "aligned_ref_index": seg.get("aligned_ref_index"),
        "is_delete": bool(seg.get("is_delete")),
        "is_boundary_error": bool(seg.get("is_boundary_error")),
        "is_boundary_misplaced": bool(seg.get("is_boundary_misplaced")),
    }
def _project_reference(seg, ref_index, aligned_ref_indices):
    return {
        "ref_index": ref_index,
        "timestamp": seg.get("timestamp") or "",
        "speaker": _speaker(seg),
        "dialogue": seg.get("dialogue") or "",
        "is_missing": ref_index not in aligned_ref_indices,
    }
def _project_anchor_context(eval_transcript_data, anchor_indices):
    if anchor_indices is None:
        return None
    return [_project_anchor(eval_transcript_data[idx], idx) for idx in anchor_indices]
def _reference_segments(ref_transcript_data, r_before, r_after, aligned_ref_indices):
    return [
        _project_reference(ref_transcript_data[ref_index], ref_index, aligned_ref_indices)
        for ref_index in range(r_before + 1, r_after)
    ]

### Window Helpers
def _anchor_context(clean_anchor_indices, start_idx, end_idx, context_segments):
    before_candidates = [idx for idx in clean_anchor_indices if idx < start_idx]
    after_candidates = [idx for idx in clean_anchor_indices if idx > end_idx]
    nearest_before = before_candidates[-1] if before_candidates else None
    nearest_after = after_candidates[0] if after_candidates else None
    if nearest_before is None:
        anchor_before_indices = None
    elif context_segments == 0:
        anchor_before_indices = []
    else:
        anchor_before_indices = before_candidates[-context_segments:]
    if nearest_after is None:
        anchor_after_indices = None
    elif context_segments == 0:
        anchor_after_indices = []
    else:
        anchor_after_indices = after_candidates[:context_segments]
    return anchor_before_indices, anchor_after_indices, nearest_before, nearest_after
def _anchor_ref_index(eval_transcript_data, anchor_idx, fallback):
    if anchor_idx is None:
        return fallback
    return eval_transcript_data[anchor_idx].get("aligned_ref_index")
def _error_signature(candidate_segments, reference_segments):
    return {
        "missing": sum(1 for seg in reference_segments if seg["is_missing"]),
        "spurious": sum(1 for seg in candidate_segments if seg["is_delete"]),
        "boundary_misplaced": sum(1 for seg in candidate_segments if seg["is_boundary_misplaced"]),
        "boundary_error": sum(1 for seg in candidate_segments if seg["is_boundary_error"]),
    }
def _window_kind_hint(error_signature):
    missing = error_signature["missing"]
    spurious = error_signature["spurious"]
    boundary_misplaced = error_signature["boundary_misplaced"]
    if boundary_misplaced > 0 and missing == 0 and spurious == 0:
        return "boundary_only"
    if spurious > 0 and missing == 0 and boundary_misplaced == 0:
        return "spurious_block"
    if missing > 0 and spurious == 0 and boundary_misplaced == 0:
        return "missing_block"
    return "mixed_structural"
def _make_window(eval_transcript_data, ref_transcript_data, aligned_ref_indices, candidate_indices, anchor_before_indices, anchor_after_indices, r_before, r_after, sort_key):
    candidate_segments = [_project_candidate(eval_transcript_data[idx], idx) for idx in candidate_indices]
    reference_segments = _reference_segments(ref_transcript_data, r_before, r_after, aligned_ref_indices)
    signature = _error_signature(candidate_segments, reference_segments)
    return {
        "_sort_key": sort_key,
        "window_id": None,
        "anchor_before": _project_anchor_context(eval_transcript_data, anchor_before_indices),
        "anchor_after": _project_anchor_context(eval_transcript_data, anchor_after_indices),
        "candidate_segments": candidate_segments,
        "reference_segments": reference_segments,
        "error_signature": signature,
        "window_kind_hint": _window_kind_hint(signature),
        "classification": None,
    }
def _misaligned_runs(eval_transcript_data, mode):
    runs = []
    current = []
    for idx, seg in enumerate(eval_transcript_data):
        if _is_misaligned(seg, mode):
            current.append(idx)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return runs
def _add_candidate_windows(windows, eval_transcript_data, ref_transcript_data, aligned_ref_indices, clean_anchor_indices, mode, context_segments):
    covered_ref_indices = set()
    for run in _misaligned_runs(eval_transcript_data, mode):
        anchor_before_indices, anchor_after_indices, nearest_before, nearest_after = _anchor_context(clean_anchor_indices, run[0], run[-1], context_segments)
        r_before = _anchor_ref_index(eval_transcript_data, nearest_before, -1)
        r_after = _anchor_ref_index(eval_transcript_data, nearest_after, len(ref_transcript_data))
        window = _make_window(eval_transcript_data, ref_transcript_data, aligned_ref_indices, run, anchor_before_indices, anchor_after_indices, r_before, r_after, run[0])
        windows.append(window)
        covered_ref_indices.update(seg["ref_index"] for seg in window["reference_segments"])
    return covered_ref_indices
def _add_pure_missing_windows(windows, eval_transcript_data, ref_transcript_data, aligned_ref_indices, clean_anchor_indices, mode, context_segments, covered_ref_indices):
    # Walk every region bounded by consecutive clean anchors, including the open-ended head
    # region (before the first anchor) and tail region (after the last anchor). A region with
    # no misaligned eval segment but a non-contiguous ref span holds dropped ref turns with no
    # candidate counterpart, so it must still surface as a pure-missing window. Sentinels: -1
    # marks "before all eval segments" (ref span opens at 0), len(eval) marks "after all".
    total_eval = len(eval_transcript_data)
    total_ref = len(ref_transcript_data)
    boundaries = [-1] + clean_anchor_indices + [total_eval]
    for pair_idx in range(len(boundaries) - 1):
        before_idx = boundaries[pair_idx]
        after_idx = boundaries[pair_idx + 1]
        has_misaligned_eval = any(_is_misaligned(eval_transcript_data[idx], mode) for idx in range(before_idx + 1, after_idx))
        if has_misaligned_eval:
            continue
        r_before = -1 if before_idx == -1 else eval_transcript_data[before_idx].get("aligned_ref_index")
        r_after = total_ref if after_idx == total_eval else eval_transcript_data[after_idx].get("aligned_ref_index")
        if r_after - r_before <= 1:
            continue
        ref_indices = set(range(r_before + 1, r_after))
        if ref_indices & covered_ref_indices:
            continue
        anchor_before_indices, anchor_after_indices, nearest_before, nearest_after = _anchor_context(clean_anchor_indices, before_idx + 1, after_idx - 1, context_segments)
        r_before = _anchor_ref_index(eval_transcript_data, nearest_before, -1)
        r_after = _anchor_ref_index(eval_transcript_data, nearest_after, total_ref)
        windows.append(_make_window(eval_transcript_data, ref_transcript_data, aligned_ref_indices, [], anchor_before_indices, anchor_after_indices, r_before, r_after, before_idx))

### Public API
def extract_misalignment_windows(eval_transcript_data, ref_transcript_data, mode="strict", context_segments=1, normalization_policy=None):
    """
    Evaluate transcript alignment and return deterministic contiguous misalignment windows.

    :param eval_transcript_data: list of parsed candidate/eval segment dictionaries.
    :param ref_transcript_data: list of parsed reference segment dictionaries.
    :param mode: "strict" counts delete or boundary-misplaced segments; "loose" counts delete or boundary-error segments.
    :param context_segments: int count of clean anchor segments to include on each side.
    :param normalization_policy: optional normalization policy passed through to the evaluator.
    :return result: dict with metrics and window dictionaries ready for review or classification.
    """
    _validate_mode(mode)
    if context_segments < 0:
        raise ValueError("context_segments must be >= 0")
    eval_transcript_data, metrics_data, _ = evaluate_step_segments_align(
        eval_transcript_data,
        ref_transcript_data,
        verbose=False,
        normalization_policy=normalization_policy,
    )
    aligned_ref_indices = {
        seg["aligned_ref_index"]
        for seg in eval_transcript_data
        if seg.get("aligned_ref_index") is not None
    }
    clean_anchor_indices = [
        idx
        for idx, seg in enumerate(eval_transcript_data)
        if _is_clean_anchor(seg, mode)
    ]
    windows = []
    covered_ref_indices = _add_candidate_windows(
        windows,
        eval_transcript_data,
        ref_transcript_data,
        aligned_ref_indices,
        clean_anchor_indices,
        mode,
        context_segments,
    )
    _add_pure_missing_windows(
        windows,
        eval_transcript_data,
        ref_transcript_data,
        aligned_ref_indices,
        clean_anchor_indices,
        mode,
        context_segments,
        covered_ref_indices,
    )
    windows.sort(key=lambda item: item["_sort_key"])
    for window_id, window in enumerate(windows):
        window["window_id"] = window_id
        del window["_sort_key"]
    return {
        "mode": mode,
        "total_ref_segments": len(ref_transcript_data),
        "total_eval_segments": len(eval_transcript_data),
        "metrics": {key: metrics_data[key] for key in METRIC_KEYS},
        "windows": windows,
    }
def write_misalignment_windows_json(result, out_path):
    """
    Write misalignment-window results to pretty JSON, creating parent directories.

    :param result: dict returned by extract_misalignment_windows.
    :param out_path: str path to the JSON file to write.
    :return out_path: str, the written path.
    """
    parent = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return out_path
def misalignment_windows_from_paths(eval_path, ref_path, mode="strict", context_segments=1, normalization_policy=None):
    """
    Parse transcript markdown files and return deterministic misalignment windows.

    :param eval_path: str path to the candidate/eval transcript markdown file.
    :param ref_path: str path to the reference transcript markdown file.
    :param mode: "strict" or "loose".
    :param context_segments: int count of clean anchor segments to include on each side.
    :param normalization_policy: optional normalization policy passed through to the evaluator.
    :return result: dict with metrics and extracted windows.
    """
    eval_transcript_data = extract_transcript_data(eval_path)
    ref_transcript_data = extract_transcript_data(ref_path)
    return extract_misalignment_windows(
        eval_transcript_data,
        ref_transcript_data,
        mode=mode,
        context_segments=context_segments,
        normalization_policy=normalization_policy,
    )
