"""
Run M3B six (pilot + next five) through pyannote community-1, score DER strict
plus transcript_eval alignment strict/loose against raws and deterministic single
drafts (_draftds), and print a combined table + per-episode timing.

Note: pyannote-community1 is diarization-only (no ASR words). Alignment metrics
for that arm are N/A; DER still applies. Transcript arms get both metric families.

Usage (repo root):
  PATH="/opt/homebrew/bin:$PATH" .venv/bin/python3 \
    apps/transcription/stellar-transcriber/scripts/run_m3b_pyannote_compare.py
"""

import json
import os
import sys
import time
from datetime import datetime

# Unbuffered progress when piped through tee
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(REPO_ROOT, ".env"), override=True)

M3B_SIX = [
    "2024-03-06_Peter Boghossian - Ideological Contagion",  # pilot
    "2024-08-26_Reason Is Fun - Ep6 Are Feelings Ideas",
    "2024-03-31_Sagenhaft und Sonderbar der Podcast",
    "2024-03-04_Alex OConnor - The Multiverse is Real",
    "2024-01-04_Reason Is Fun - Ep5 The Art of Decision Making",
    "2024-01-01_Arjun Khemani - Free-Will TCS and Anarcho-Capitalism",
]
RAW_DIR = os.path.join(REPO_ROOT, "data/deutsch/f9_raw")
REF_DIR = os.path.join(REPO_ROOT, "data/deutsch/f8_done_qafixed_and_vrb")
AUDIO_DIR = os.path.join(REPO_ROOT, "data/deutsch/f0_source_audio")
RUN_ID = f"2026-07-25_m3b6_pyannote"
RUN_DIR = os.path.join(REPO_ROOT, "data/diarbench/runs", RUN_ID)
DRAFT_DIR = os.path.join(RUN_DIR, "draftds")
ALIGN_DIR = os.path.join(RUN_DIR, "alignment")

### Paths
def stem_paths(stem):
    return {
        "stem": stem,
        "audio": os.path.join(AUDIO_DIR, f"{stem}.mp3"),
        "ref": os.path.join(REF_DIR, f"{stem}_vrb.md"),
        "nova2gen": os.path.join(RAW_DIR, f"{stem}_nova2gen.md"),
        "dgwhspm": os.path.join(RAW_DIR, f"{stem}_dgwhspm.md"),
        "nova2gen_json": os.path.join(RAW_DIR, f"{stem}_nova2gen.json"),
        "dgwhspm_json": os.path.join(RAW_DIR, f"{stem}_dgwhspm.json"),
        "draftds_nova": os.path.join(DRAFT_DIR, f"{stem}_nova2gen_draftds.md"),
        "draftds_dg": os.path.join(DRAFT_DIR, f"{stem}_dgwhspm_draftds.md"),
    }
def audio_duration_secs(path):
    from mutagen import File as MutagenFile

    info = MutagenFile(path)
    return float(info.info.length) if info is not None else None
def ensure_dirs():
    for d in (RUN_DIR, DRAFT_DIR, ALIGN_DIR, os.path.join(RUN_DIR, "hyp", "pyannote-community1"), os.path.join(RUN_DIR, "raw")):
        os.makedirs(d, exist_ok=True)

### Drafts
def build_draftds(paths):
    from core.denovo import create_draft_deterministic

    for raw_key, out_key in (("nova2gen", "draftds_nova"), ("dgwhspm", "draftds_dg")):
        out = paths[out_key]
        if os.path.exists(out):
            print(f"  draftds exists: {os.path.basename(out)}")
            continue
        print(f"  building draftds from {os.path.basename(paths[raw_key])}")
        create_draft_deterministic(paths[raw_key], profile="deutsch", output_path=out, verbose=False)

### Alignment (speaker-segment) metrics
def score_alignment(eval_path, ref_path):
    """Return seg_error_count (loose) + seg_error_count_strict + subscores."""
    from core.transcript_eval import (
        compute_subscore_alignment_loose,
        compute_subscore_alignment_strict,
        evaluate_step_segments_align,
        extract_transcript_data,
        normalize_dialogue,
    )

    eval_data = extract_transcript_data(eval_path, fields_to_omit=["speaker_name", "speaker_role", "timestamp_link"])
    ref_data = extract_transcript_data(ref_path, fields_to_omit=["speaker_name", "speaker_role", "timestamp_link"])
    if not eval_data or not ref_data:
        return {"error": "missing transcript content"}
    for seg in ref_data:
        seg["normalized_dialogue"] = normalize_dialogue(seg.get("dialogue", ""), None)
    _eval_out, metrics, _log = evaluate_step_segments_align(eval_data, ref_data, debug=False, verbose=False)
    metrics["subscore_alignment_loose"] = compute_subscore_alignment_loose(metrics)
    metrics["subscore_alignment_strict"] = compute_subscore_alignment_strict(metrics)
    return {
        "seg_error_count": metrics.get("seg_error_count"),
        "seg_error_count_strict": metrics.get("seg_error_count_strict"),
        "total_ref_segments": metrics.get("total_ref_segments"),
        "align_loose": metrics.get("subscore_alignment_loose"),
        "align_strict": metrics.get("subscore_alignment_strict"),
    }

### DER
def turns_from_md(md_path, session_id):
    from core.diar_formats import md_to_segments, segments_to_rttm_turns

    return segments_to_rttm_turns(md_to_segments(md_path), session_id)
def turns_from_dg_json(json_path, session_id):
    from core.diar_formats import deepgram_json_to_rttm_turns

    return deepgram_json_to_rttm_turns(json_path, session_id)
def score_der(ref_turns, hyp_turns, session_id):
    from core.diar_metrics import compute_diarization_metrics

    if not ref_turns or not hyp_turns:
        return {"error": "missing turns for DER"}
    return compute_diarization_metrics(ref_turns, hyp_turns, session_id)

### Pyannote run
def run_pyannote(paths, session_id):
    from core.diar_backends import run_backend
    from core.diar_formats import write_rttm

    hyp_rttm = os.path.join(RUN_DIR, "hyp", "pyannote-community1", f"{session_id}.rttm")
    timing_path = os.path.join(RUN_DIR, "timing.jsonl")
    if os.path.exists(hyp_rttm):
        print(f"  pyannote hyp exists, skipping run: {session_id}")
        turns = None
        from core.diar_formats import read_rttm
        turns = read_rttm(hyp_rttm)
        wall = None
        for line in open(timing_path) if os.path.exists(timing_path) else []:
            row = json.loads(line)
            if row.get("session_id") == session_id:
                wall = row.get("wall_secs")
                break
        return turns, wall
    audio_secs = audio_duration_secs(paths["audio"])
    print(f"  RUN pyannote-community1 on {session_id} ({audio_secs/60:.1f} min audio)")
    t0 = time.perf_counter()
    result = run_backend("pyannote-community1", paths["audio"], session_id, out_dir=os.path.join(RUN_DIR, "raw"))
    wall = time.perf_counter() - t0
    turns = [dict(t, uri=session_id) for t in result["turns"]]
    write_rttm(turns, hyp_rttm)
    row = {
        "session_id": session_id,
        "stem": paths["stem"],
        "audio_secs": audio_secs,
        "wall_secs": wall,
        "realtime_factor": (wall / audio_secs) if audio_secs else None,
        "n_turns": len(turns),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }
    with open(timing_path, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"  done in {wall/60:.1f} min wall ({row['realtime_factor']:.2f}x realtime)")
    return turns, wall

### Episode scoring
def score_transcript_arms(paths):
    from core.diar_formats import stem_to_session_id

    sid = stem_to_session_id(paths["stem"])
    ref_turns = turns_from_md(paths["ref"], sid)
    rows = []
    arms = [
        ("nova2gen", paths["nova2gen"], paths["nova2gen_json"]),
        ("dgwhspm", paths["dgwhspm"], paths["dgwhspm_json"]),
        ("nova2gen_draftds", paths["draftds_nova"], None),
        ("dgwhspm_draftds", paths["draftds_dg"], None),
    ]
    for arm, md_path, json_path in arms:
        if json_path and os.path.exists(json_path):
            hyp_turns = turns_from_dg_json(json_path, sid)
        else:
            hyp_turns = turns_from_md(md_path, sid)
        der = score_der(ref_turns, hyp_turns, sid)
        align = score_alignment(md_path, paths["ref"])
        rows.append({
            "stem": paths["stem"],
            "session_id": sid,
            "arm": arm,
            "der_strict": der.get("der_strict"),
            "der_lenient": der.get("der_lenient"),
            "jer": der.get("jer"),
            "align_strict": align.get("align_strict"),
            "align_loose": align.get("align_loose"),
            "seg_error_count_strict": align.get("seg_error_count_strict"),
            "seg_error_count": align.get("seg_error_count"),
            "error": der.get("error") or align.get("error"),
        })
        print(f"  scored {arm}: DER={rows[-1]['der_strict']} align_strict={rows[-1]['align_strict']} align_loose={rows[-1]['align_loose']}")
    return rows
def score_pyannote_arm(paths):
    from core.diar_formats import stem_to_session_id

    sid = stem_to_session_id(paths["stem"])
    ref_turns = turns_from_md(paths["ref"], sid)
    hyp_turns, wall = run_pyannote(paths, sid)
    der = score_der(ref_turns, hyp_turns, sid)
    audio_secs = audio_duration_secs(paths["audio"])
    row = {
        "stem": paths["stem"],
        "session_id": sid,
        "arm": "pyannote-community1",
        "der_strict": der.get("der_strict"),
        "der_lenient": der.get("der_lenient"),
        "jer": der.get("jer"),
        "align_strict": None,
        "align_loose": None,
        "seg_error_count_strict": None,
        "seg_error_count": None,
        "audio_secs": audio_secs,
        "wall_secs": wall,
        "realtime_factor": (wall / audio_secs) if (wall and audio_secs) else None,
        "error": der.get("error"),
        "note": "diarization-only; alignment N/A (no ASR words)",
    }
    print(f"  scored pyannote-community1: DER={row['der_strict']}")
    return row

### Reporting
def print_tables(all_rows, timing_rows):
    print("\n" + "=" * 100)
    print("COMBINED RESULTS — M3B six (pilot + next five)")
    print("DER strict = collar 0.0 + overlap scored (segment-approximate refs for internal corpus)")
    print("align_strict / align_loose = transcript_eval speaker-segment subscores (0–100, higher better)")
    print("=" * 100)
    header = f"{'stem':<42} {'arm':<22} {'DER_strict':>10} {'align_strict':>12} {'align_loose':>11} {'seg_strict':>10} {'seg_loose':>9}"
    print(header)
    print("-" * len(header))
    for r in all_rows:
        stem = r["stem"][:42]
        der = f"{r['der_strict']:.3f}" if r.get("der_strict") is not None else "—"
        a_s = f"{r['align_strict']:.1f}" if r.get("align_strict") is not None else "—"
        a_l = f"{r['align_loose']:.1f}" if r.get("align_loose") is not None else "—"
        s_s = str(r["seg_error_count_strict"]) if r.get("seg_error_count_strict") is not None else "—"
        s_l = str(r["seg_error_count"]) if r.get("seg_error_count") is not None else "—"
        print(f"{stem:<42} {r['arm']:<22} {der:>10} {a_s:>12} {a_l:>11} {s_s:>10} {s_l:>9}")
    print("\n" + "=" * 100)
    print("PYANNOTE COMMUNITY-1 TIMING (local diarization only)")
    print("=" * 100)
    print(f"{'stem':<50} {'audio_min':>9} {'wall_min':>9} {'x_realtime':>11}")
    print("-" * 82)
    for t in timing_rows:
        audio_m = t["audio_secs"] / 60.0
        wall_m = t["wall_secs"] / 60.0 if t.get("wall_secs") is not None else None
        rtf = t.get("realtime_factor")
        wall_s = f"{wall_m:.1f}" if wall_m is not None else "—"
        rtf_s = f"{rtf:.2f}x" if rtf is not None else "—"
        print(f"{t['stem'][:50]:<50} {audio_m:>9.1f} {wall_s:>9} {rtf_s:>11}")
    if timing_rows:
        tot_a = sum(t["audio_secs"] for t in timing_rows)
        tot_w = sum(t["wall_secs"] for t in timing_rows if t.get("wall_secs") is not None)
        print("-" * 82)
        print(f"{'TOTAL':<50} {tot_a/60:>9.1f} {tot_w/60:>9.1f} {tot_w/tot_a if tot_a else 0:>10.2f}x")
def main():
    ensure_dirs()
    print(f"Run dir: {RUN_DIR}")
    print(f"Episodes: {len(M3B_SIX)}")
    # Confirm audio
    for stem in M3B_SIX:
        p = stem_paths(stem)
        ok = all(os.path.exists(p[k]) for k in ("audio", "ref", "nova2gen", "dgwhspm"))
        print(f"  [{'OK' if ok else 'MISSING'}] {stem}  audio={os.path.exists(p['audio'])}")
        if not ok:
            raise SystemExit(f"missing inputs for {stem}")
    all_rows = []
    # Phase 1: drafts + transcript-arm scoring (fast)
    for stem in M3B_SIX:
        print(f"\n### transcript arms: {stem}")
        paths = stem_paths(stem)
        build_draftds(paths)
        all_rows.extend(score_transcript_arms(paths))
        with open(os.path.join(RUN_DIR, "combined_metrics.jsonl"), "w") as f:
            for r in all_rows:
                f.write(json.dumps(r) + "\n")
    print("\n--- interim table (transcript arms only; pyannote next) ---")
    print_tables(all_rows, [])
    # Phase 2: pyannote shortest-first
    by_len = sorted(M3B_SIX, key=lambda s: audio_duration_secs(stem_paths(s)["audio"]) or 0)
    for stem in by_len:
        print(f"\n### pyannote: {stem}")
        all_rows.append(score_pyannote_arm(stem_paths(stem)))
        with open(os.path.join(RUN_DIR, "combined_metrics.jsonl"), "w") as f:
            for r in all_rows:
                f.write(json.dumps(r) + "\n")
    timing_path = os.path.join(RUN_DIR, "timing.jsonl")
    timing_rows = [json.loads(l) for l in open(timing_path)] if os.path.exists(timing_path) else []
    print_tables(all_rows, timing_rows)
    print(f"\nWrote: {RUN_DIR}/combined_metrics.jsonl")
    print(f"Wrote: {RUN_DIR}/timing.jsonl")

if __name__ == "__main__":
    main()
