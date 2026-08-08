import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("ELEVENLABS_API_KEY", "unused")
sys.modules.setdefault("elevenlabs", MagicMock())
sys.modules.setdefault("elevenlabs.client", MagicMock())

import copy

from core.transcript_eval import (
    calc_lev_dist_ratio,
    convert_timestamp_to_seconds,
    extract_transcript_data,
    normalize_dialogue,
)
from core.transcript_misalign import extract_misalignment_windows

### Helpers
def _empty_match_result():
    return {
        "found": False,
        "sim": 0.0,
        "contained": False,
        "matched_index": None,
        "matched_timestamp": None,
        "matched_dialogue": None,
    }
def _segment_seconds(segment):
    timestamp = segment.get("timestamp")
    try:
        return convert_timestamp_to_seconds(timestamp)
    except (TypeError, ValueError):
        return None
def _contains_word_run(target_words, candidate_words):
    if not target_words or len(candidate_words) <= len(target_words):
        return False
    max_start = len(candidate_words) - len(target_words)
    for start in range(max_start + 1):
        if candidate_words[start:start + len(target_words)] == target_words:
            return True
    return False
def _matched_fields(match):
    idx, segment = match
    return {
        "matched_index": idx,
        "matched_timestamp": segment.get("timestamp"),
        "matched_dialogue": segment.get("dialogue"),
    }
def _project_missing_ref(segment):
    return {
        "ref_index": segment.get("ref_index"),
        "timestamp": segment.get("timestamp") or "",
        "speaker": segment.get("speaker") or segment.get("speaker_name") or segment.get("speaker_full") or "",
        "dialogue": segment.get("dialogue") or "",
    }

### Public API
def locate_turn_in_transcript(target_dialogue, target_seconds, transcript_data, window_secs=30, sim_threshold=0.6, normalization_policy=None, min_contained_words=3):
    """
    Locate a reference turn in a sibling transcript using deterministic time-windowed text matching.

    :param target_dialogue: str reference dialogue to search for.
    :param target_seconds: numeric reference timestamp in seconds.
    :param transcript_data: list of transcript segment dictionaries.
    :param window_secs: numeric search radius on either side of target_seconds.
    :param sim_threshold: Levenshtein similarity threshold for a direct match.
    :param normalization_policy: optional normalization policy passed to normalize_dialogue.
    :param min_contained_words: minimum target word count for a contiguous sub-run (contained) match; shorter turns must match a whole short sibling segment by similarity to avoid counting a common word buried in a long segment as a recovery.
    :return result: dict describing whether the target was found and the best sibling match.
    """
    try:
        target_seconds = float(target_seconds)
    except (TypeError, ValueError):
        return _empty_match_result()
    normalized_target = normalize_dialogue(target_dialogue, normalization_policy)
    target_words = normalized_target.split()
    best_sim = 0.0
    best_match = None
    contained_match = None
    contained_sim = -1.0
    in_window_count = 0
    for idx, segment in enumerate(transcript_data or []):
        segment_seconds = _segment_seconds(segment)
        if segment_seconds is None or abs(segment_seconds - target_seconds) > window_secs:
            continue
        in_window_count += 1
        normalized_dialogue = normalize_dialogue(segment.get("dialogue"), normalization_policy)
        sim = calc_lev_dist_ratio(normalized_target, normalized_dialogue)
        if best_match is None or sim > best_sim:
            best_sim = sim
            best_match = (idx, segment)
        candidate_words = normalized_dialogue.split()
        if len(target_words) >= min_contained_words and _contains_word_run(target_words, candidate_words) and sim > contained_sim:
            contained_match = (idx, segment)
            contained_sim = sim
    if in_window_count == 0:
        return _empty_match_result()
    found_by_similarity = best_sim >= sim_threshold
    contained = contained_match is not None
    found = found_by_similarity or contained
    matched = None
    if found_by_similarity:
        matched = best_match
    elif contained:
        matched = contained_match
    result = _empty_match_result()
    result["found"] = found
    result["sim"] = best_sim
    result["contained"] = contained
    if matched is not None:
        result.update(_matched_fields(matched))
    return result
def collect_missing_ref_segments(windows_result):
    """
    Collect missing reference segments across misalignment windows, de-duplicated by ref_index.

    :param windows_result: dict returned by extract_misalignment_windows.
    :return missing_segments: list of projected missing reference segment dictionaries.
    """
    by_ref_index = {}
    for window in (windows_result or {}).get("windows", []):
        for segment in window.get("reference_segments", []):
            ref_index = segment.get("ref_index")
            if segment.get("is_missing") and ref_index not in by_ref_index:
                by_ref_index[ref_index] = _project_missing_ref(segment)
    return [by_ref_index[ref_index] for ref_index in sorted(by_ref_index)]
def analyze_missing_recovery(ref_data, arm_data, sibling_data, mode="strict", window_secs=30, sim_threshold=0.6, normalization_policy=None, min_contained_words=3):
    """
    Measure how many missing reference turns in one ASR arm are present in its sibling arm.

    :param ref_data: list of reference transcript segment dictionaries.
    :param arm_data: list of transcript segment dictionaries for the arm being scored for missing turns.
    :param sibling_data: list of transcript segment dictionaries for the other arm to search.
    :param mode: "strict" or "loose" mode passed to extract_misalignment_windows.
    :param window_secs: numeric search radius on either side of each missing reference timestamp.
    :param sim_threshold: Levenshtein similarity threshold for direct sibling recovery.
    :param normalization_policy: optional normalization policy passed through to alignment and matching.
    :return summary: dict with missing counts, recovery counts, rate, and per-turn details.
    """
    arm_copy = copy.deepcopy(arm_data)
    ref_copy = copy.deepcopy(ref_data)
    windows_result = extract_misalignment_windows(
        arm_copy,
        ref_copy,
        mode=mode,
        normalization_policy=normalization_policy,
    )
    missing = collect_missing_ref_segments(windows_result)
    details = []
    recoverable_count = 0
    for segment in missing:
        match = locate_turn_in_transcript(
            segment.get("dialogue"),
            convert_timestamp_to_seconds(segment.get("timestamp")),
            sibling_data,
            window_secs=window_secs,
            sim_threshold=sim_threshold,
            normalization_policy=normalization_policy,
            min_contained_words=min_contained_words,
        )
        recovered = match["found"]
        if recovered:
            recoverable_count += 1
        details.append({
            "ref_index": segment.get("ref_index"),
            "timestamp": segment.get("timestamp"),
            "dialogue": segment.get("dialogue"),
            "recovered": recovered,
            "sibling_sim": match["sim"],
            "contained": match["contained"],
            "sibling_timestamp": match["matched_timestamp"],
            "sibling_dialogue": match["matched_dialogue"],
        })
    missing_count = len(missing)
    return {
        "arm_missing_count": missing_count,
        "recoverable_from_sibling": recoverable_count,
        "not_in_sibling": missing_count - recoverable_count,
        "recovery_rate": round(recoverable_count / missing_count, 3) if missing_count else None,
        "missing_details": details,
    }
def recovery_from_paths(ref_path, arm_path, sibling_path, mode="strict", window_secs=30, sim_threshold=0.6, normalization_policy=None):
    """
    Parse transcript markdown paths and measure missing-turn recovery from a sibling arm.

    :param ref_path: str path to the reference markdown transcript.
    :param arm_path: str path to the ASR arm markdown transcript being scored.
    :param sibling_path: str path to the sibling ASR arm markdown transcript being searched.
    :param mode: "strict" or "loose" mode passed to extract_misalignment_windows.
    :param window_secs: numeric search radius on either side of each missing reference timestamp.
    :param sim_threshold: Levenshtein similarity threshold for direct sibling recovery.
    :param normalization_policy: optional normalization policy passed through to alignment and matching.
    :return summary: dict returned by analyze_missing_recovery.
    """
    ref_data = extract_transcript_data(ref_path)
    arm_data = extract_transcript_data(arm_path)
    sibling_data = extract_transcript_data(sibling_path)
    return analyze_missing_recovery(
        ref_data,
        arm_data,
        sibling_data,
        mode=mode,
        window_secs=window_secs,
        sim_threshold=sim_threshold,
        normalization_policy=normalization_policy,
    )
