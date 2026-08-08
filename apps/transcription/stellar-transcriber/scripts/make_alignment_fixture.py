"""
Build segment-alignment eval fixtures by injecting known boundary defects into a clean
reference transcript.

Purpose: ground-truth development of the alignment error metric and the LLM segmentation
repair without needing the S3 eval corpus. The injected-defect log gives the exact expected
segment-error counts, so the metric and the repair can both be validated locally.

Defect taxonomy (matches references/denovo-pipeline-design.md):
- boundary_shift  — words moved across a speaker transition (errant boundary text)
- merge           — two ref segments merged into one (missing speaker change; ref segment eliminated)
- split           — one ref segment split into two same-speaker segments (spurious split)
- wrong_speaker   — segment attributed to the wrong speaker (speaker dimension, not alignment)

Run from the repo root:
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/make_alignment_fixture.py --out data/stellar-eval/fixtures
"""
import argparse
import copy
import os
import random
import re
import sys
from unittest.mock import MagicMock

os.environ.setdefault("ELEVENLABS_API_KEY", "unused-for-fixture-build")
sys.modules.setdefault("elevenlabs", MagicMock())
sys.modules.setdefault("elevenlabs.client", MagicMock())

SOURCE_MD_REL = os.path.join(
    "tests", "test_data_files", "transcription", "alignment_source.md",
)
WORDS_PER_SECOND = 2.5

### Repo root
def find_repo_root(start_dir):
    current = os.path.abspath(start_dir)
    while True:
        if os.path.isfile(os.path.join(current, SOURCE_MD_REL)):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            raise FileNotFoundError(f"Could not locate repo root containing {SOURCE_MD_REL}")
        current = parent

### Reference construction
def format_timestamp(total_seconds):
    """Format seconds as H:MM:SS or M:SS matching transcript conventions."""
    total_seconds = int(total_seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"
def build_reference_segments(source_md_path, max_segments=30, min_words=8, max_words=120):
    """
    Build a clean reference segment list from a colon-format transcript, assigning
    synthetic timestamps from cumulative word counts.

    :return: list of segment dicts (speaker_full, timestamp, dialogue)
    """
    from core.transcript_eval import extract_transcript_data

    raw = extract_transcript_data(source_md_path)
    if not raw:
        raise ValueError(f"No transcript content in {source_md_path}")
    segments = []
    elapsed = 0.0
    for seg in raw:
        dialogue = (seg.get("dialogue") or "").strip()
        words = dialogue.split()
        if len(words) < min_words:
            elapsed += max(len(words), 1) / WORDS_PER_SECOND
            continue
        if len(words) > max_words:
            dialogue = " ".join(words[:max_words])
            if not re.search(r'[.!?]$', dialogue):
                dialogue += "."
            words = words[:max_words]
        segments.append({
            "speaker_full": seg.get("speaker_name") or "Speaker 0",
            "speaker_name": seg.get("speaker_name") or "Speaker 0",
            "speaker_role": None,
            "timestamp": format_timestamp(elapsed),
            "timestamp_link": None,
            "dialogue": dialogue,
        })
        elapsed += len(words) / WORDS_PER_SECOND + 2.0
        if len(segments) >= max_segments:
            break
    return segments

### Defect injection
def _shift_words_forward(segments, i, k):
    """Move the last k words of segment i to the start of segment i+1 (errant boundary text)."""
    words = segments[i]["dialogue"].split()
    if len(words) <= k:
        return False
    moved = words[-k:]
    segments[i]["dialogue"] = " ".join(words[:-k])
    segments[i + 1]["dialogue"] = " ".join(moved) + " " + segments[i + 1]["dialogue"]
    return True
def _shift_words_backward(segments, i, k):
    """Move the first k words of segment i+1 to the end of segment i (errant boundary text)."""
    words = segments[i + 1]["dialogue"].split()
    if len(words) <= k:
        return False
    moved = words[:k]
    segments[i + 1]["dialogue"] = " ".join(words[k:])
    segments[i]["dialogue"] = segments[i]["dialogue"] + " " + " ".join(moved)
    return True
def _merge_segments(segments, i):
    """Merge segment i+1 into i (missing speaker change; eliminates a ref segment)."""
    segments[i]["dialogue"] = segments[i]["dialogue"] + " " + segments[i + 1]["dialogue"]
    segments.pop(i + 1)
    return True
def _split_segment(segments, i):
    """Split segment i into two same-speaker segments (spurious split)."""
    words = segments[i]["dialogue"].split()
    if len(words) < 12:
        return False
    mid = len(words) // 2
    first = copy.deepcopy(segments[i])
    second = copy.deepcopy(segments[i])
    first["dialogue"] = " ".join(words[:mid])
    second["dialogue"] = " ".join(words[mid:])
    ts_seconds = _timestamp_to_seconds(segments[i]["timestamp"]) + max(1, int(mid / WORDS_PER_SECOND))
    second["timestamp"] = format_timestamp(ts_seconds)
    segments[i] = first
    segments.insert(i + 1, second)
    return True
def _wrong_speaker(segments, i, speakers):
    """Assign segment i to a different speaker."""
    others = [s for s in speakers if s != segments[i]["speaker_full"]]
    if not others:
        return False
    segments[i]["speaker_full"] = others[0]
    segments[i]["speaker_name"] = others[0]
    return True
def _timestamp_to_seconds(ts):
    parts = [int(p) for p in ts.split(":")]
    seconds = 0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds
def inject_defects(ref_segments, n_boundary=4, n_merge=2, n_split=2, n_wrong_speaker=1, seed=7):
    """
    Inject a known defect set into a copy of ref_segments.

    Defects target distinct, non-adjacent segment indices so injected errors do not
    interact and expected error counts stay exact.

    :return: (eval_segments, injection_log list of dicts)
    """
    rng = random.Random(seed)
    segs = copy.deepcopy(ref_segments)
    speakers = sorted({s["speaker_full"] for s in segs})
    n = len(segs)
    # Pick target indices spaced >= 3 apart so defects never touch the same transition
    candidates = list(range(1, n - 2))
    rng.shuffle(candidates)
    chosen = []
    for idx in candidates:
        if all(abs(idx - c) >= 3 for c in chosen):
            chosen.append(idx)
    plan = []
    needed = [("boundary_shift", n_boundary), ("merge", n_merge), ("split", n_split), ("wrong_speaker", n_wrong_speaker)]
    pos = 0
    for defect_type, count in needed:
        for _ in range(count):
            if pos >= len(chosen):
                break
            plan.append((defect_type, chosen[pos]))
            pos += 1
    # Apply in descending index order so earlier indices stay valid as segments shift
    plan.sort(key=lambda x: -x[1])
    log = []
    for defect_type, idx in plan:
        ok = False
        if defect_type == "boundary_shift":
            k = rng.randint(3, 6)
            if rng.random() < 0.5:
                ok = _shift_words_forward(segs, idx, k)
                direction = "forward"
            else:
                ok = _shift_words_backward(segs, idx, k)
                direction = "backward"
            if ok:
                log.append({"type": defect_type, "index": idx, "words": k, "direction": direction})
        elif defect_type == "merge":
            ok = _merge_segments(segs, idx)
            if ok:
                log.append({"type": defect_type, "index": idx})
        elif defect_type == "split":
            ok = _split_segment(segs, idx)
            if ok:
                log.append({"type": defect_type, "index": idx})
        elif defect_type == "wrong_speaker":
            ok = _wrong_speaker(segs, idx, speakers)
            if ok:
                log.append({"type": defect_type, "index": idx})
    return segs, log
def expected_error_counts(injection_log):
    """
    Expected segment-error counts from an injection log.

    boundary_shift -> 2 boundary-error segments (both sides of the transition mismatch)
    merge          -> 1 missing ref segment + 1 boundary-error segment (merged segment end mismatch)
    split          -> 1 spurious eval segment + 1 boundary-error segment (first half end mismatch)
    wrong_speaker  -> 0 alignment errors (speaker dimension, not alignment)
    """
    counts = {"seg_missing_count": 0, "seg_spurious_count": 0, "seg_boundary_error_count": 0}
    for entry in injection_log:
        if entry["type"] == "boundary_shift":
            counts["seg_boundary_error_count"] += 2
        elif entry["type"] == "merge":
            counts["seg_missing_count"] += 1
            counts["seg_boundary_error_count"] += 1
        elif entry["type"] == "split":
            counts["seg_spurious_count"] += 1
            counts["seg_boundary_error_count"] += 1
    counts["seg_error_count"] = sum(counts.values())
    return counts

### Output
def segments_to_md_file(segments, out_path, title, source_note):
    """Write segments as a transcript markdown file (metadata + ### transcript)."""
    lines = [
        "## metadata",
        f"title: {title}",
        f"transcript source: {source_note}",
        "",
        "## content",
        "",
        "### transcript",
        "",
    ]
    for seg in segments:
        lines.append(f"{seg['speaker_full']}  {seg['timestamp']}")
        lines.append(seg["dialogue"])
        lines.append("")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    return out_path
def build_fixture_set(out_dir, max_segments=30, seed_a=7, seed_b=13, stem="fixture-townhall30"):
    """
    Build ref + two defect-injected raws (A/B) with injection logs.

    :return: dict with paths, injection logs, and expected error counts per raw
    """
    repo_root = find_repo_root(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    source_md = os.path.join(repo_root, SOURCE_MD_REL)
    ref_segments = build_reference_segments(source_md, max_segments=max_segments)
    eval_a, log_a = inject_defects(ref_segments, seed=seed_a)
    eval_b, log_b = inject_defects(ref_segments, seed=seed_b)
    ref_path = segments_to_md_file(ref_segments, os.path.join(out_dir, f"{stem}_vrb.md"), stem, "fixture reference")
    a_path = segments_to_md_file(eval_a, os.path.join(out_dir, f"{stem}_nova2gen.md"), stem, "fixture raw A (injected defects)")
    b_path = segments_to_md_file(eval_b, os.path.join(out_dir, f"{stem}_dgwhspm.md"), stem, "fixture raw B (injected defects)")
    return {
        "ref": ref_path,
        "raw_a": a_path,
        "raw_b": b_path,
        "log_a": log_a,
        "log_b": log_b,
        "expected_a": expected_error_counts(log_a),
        "expected_b": expected_error_counts(log_b),
        "ref_segment_count": len(ref_segments),
    }

def main():
    parser = argparse.ArgumentParser(description="Build alignment eval fixtures with injected defects")
    parser.add_argument("--out", default="data/stellar-eval/fixtures")
    parser.add_argument("--max-segments", type=int, default=30)
    args = parser.parse_args()
    repo_root = find_repo_root(os.path.dirname(os.path.abspath(__file__)))
    out_dir = args.out if os.path.isabs(args.out) else os.path.join(repo_root, args.out)
    result = build_fixture_set(out_dir, max_segments=args.max_segments)
    print(f"ref:   {result['ref']}  ({result['ref_segment_count']} segments)")
    for side in ("a", "b"):
        print(f"raw {side.upper()}: {result['raw_' + side]}")
        for entry in result["log_" + side]:
            print(f"   injected {entry}")
        print(f"   expected errors: {result['expected_' + side]}")
    return 0
if __name__ == "__main__":
    sys.exit(main())
