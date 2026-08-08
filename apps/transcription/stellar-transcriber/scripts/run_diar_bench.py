"""
run_diar_bench.py — run diarization/ASR backends against a built dataset and
score with the field-standard metrics (DER/JER via pyannote.metrics, cpWER/tcpWER
via meeteval). See docs/2026-07-25_diarization-bench-plan.md.

Modes:
  Score existing hypotheses (internal corpora — no audio needed):
    run_diar_bench.py --dataset deutsch --score-existing --limit 5
  Run backends on audio (external benchmarks / future internal audio):
    run_diar_bench.py --dataset ami-mini --backends deepgram-nova2,pyannote-community1 --split test
  List backend availability:
    run_diar_bench.py --list-backends

Outputs under data/diarbench/runs/<run-id>/: per-session hypothesis RTTM/SegLST +
raw responses, metrics.jsonl (one row per session x backend), summary.json.
Every metrics row carries protocol fields (collar, overlap, boundary precision).
"""

import argparse
import json
import os
import sys
from datetime import datetime

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from build_diar_dataset import load_registry

### Dataset access
def dataset_root(registry, name):
    return os.path.join(REPO_ROOT, registry["build_root"], name)
def load_sessions(registry, name):
    path = os.path.join(dataset_root(registry, name), "sessions.jsonl")
    if not os.path.exists(path):
        raise SystemExit(f"dataset '{name}' not built — run build_diar_dataset.py --dataset {name} first")
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]
def load_ref_turns(registry, name, session_id):
    from core.diar_formats import read_rttm

    path = os.path.join(dataset_root(registry, name), "rttm", "ref", f"{session_id}.rttm")
    return read_rttm(path) if os.path.exists(path) else None
def load_uem(registry, name, session_id):
    from core.diar_formats import read_uem

    path = os.path.join(dataset_root(registry, name), "uem", f"{session_id}.uem")
    return read_uem(path) if os.path.exists(path) else None
def load_ref_seglst(registry, name, session_id):
    from core.diar_formats import read_seglst

    path = os.path.join(dataset_root(registry, name), "seglst", "ref", f"{session_id}.json")
    return read_seglst(path) if os.path.exists(path) else None
def filter_sessions(sessions, session_filter, include_stem=False):
    """Filter sessions by comma-separated session-id or optional stem fragments."""
    if not session_filter:
        return sessions
    wants = [value.strip() for value in session_filter.split(",") if value.strip()]
    if not wants:
        raise SystemExit(f"no non-empty session filters in --sessions {session_filter!r}")
    filtered = [
        session for session in sessions
        if any(
            value in session["session_id"]
            or (include_stem and value in (session.get("stem") or ""))
            for value in wants
        )
    ]
    if not filtered:
        raise SystemExit(f"no sessions matched --sessions {session_filter!r}")
    return filtered

### Scoring
def score_pair(ref_turns, hyp_turns, ref_seglst, hyp_seglst, session_id, uem_regions=None, boundary_precision="exact"):
    """Score one (ref, hyp) pair with every applicable metric; returns a flat row."""
    from core.diar_metrics import compute_cpwer, compute_diarization_metrics, compute_tcpwer

    row = {"session_id": session_id, "boundary_precision": boundary_precision}
    timing_ok = True
    if boundary_precision == "segment" and ref_turns and hyp_turns:
        # Segment-approximate references need sane timestamp coverage before
        # time-based metrics mean anything: a ref whose timed speech collapses
        # to a sliver (e.g. one timestamped segment) yields absurd DER/tcpWER.
        ref_speech = sum(t["duration"] for t in ref_turns)
        hyp_speech = sum(t["duration"] for t in hyp_turns) or 1.0
        timing_ok = len(ref_turns) >= 2 and ref_speech >= 0.5 * hyp_speech
        if not timing_ok:
            row["timing_skipped"] = f"degenerate ref timestamps ({len(ref_turns)} turns, {ref_speech:.0f}s vs hyp {hyp_speech:.0f}s)"
    if ref_turns and hyp_turns and timing_ok:
        row.update(compute_diarization_metrics(ref_turns, hyp_turns, session_id, uem_regions))
    if ref_seglst and hyp_seglst and any(r.get("words") for r in ref_seglst):
        cp = compute_cpwer(ref_seglst, hyp_seglst)
        if cp.get("skipped"):
            row["cpwer_skipped"] = cp["skipped"]
        else:
            row["cpwer"] = cp["combined"]["error_rate"]
            row["cpwer_errors"] = cp["combined"]["errors"]
            row["cpwer_length"] = cp["combined"]["length"]
            sess = list(cp["per_session"].values())[0] if cp["per_session"] else {}
            row["cpwer_missed_speaker"] = sess.get("missed_speaker")
            row["cpwer_falarm_speaker"] = sess.get("falarm_speaker")
            # tcpWER needs fine-grained turn times on BOTH sides; segment-approximate
            # references (multi-minute merged turns) make its 5s collar meaningless.
            timed = (
                boundary_precision == "exact"
                and timing_ok
                and all(("start_time" in r and "end_time" in r) for r in ref_seglst + hyp_seglst)
            )
            if timed:
                tc = compute_tcpwer(ref_seglst, hyp_seglst, collar=5)
                if not tc.get("skipped"):
                    row["tcpwer"] = tc["combined"]["error_rate"]
                    row["tcpwer_collar"] = tc["collar"]
    return row

### Mode: score existing hypotheses (internal corpora)
def score_existing(registry, name, limit=None, arms=None, session_filter=None):
    from core.diar_formats import read_rttm, read_seglst

    root = dataset_root(registry, name)
    sessions = load_sessions(registry, name)
    sessions = filter_sessions(sessions, session_filter, include_stem=True)
    if limit:
        sessions = sessions[:limit]
    rows = []
    for sess in sessions:
        sid = sess["session_id"]
        ref_turns = load_ref_turns(registry, name, sid)
        ref_seglst = load_ref_seglst(registry, name, sid)
        for arm in sorted(sess.get("hyps", {})):
            if arms and arm not in arms:
                continue
            hyp_rttm = os.path.join(root, "rttm", "hyp", arm, f"{sid}.rttm")
            hyp_seglst_path = os.path.join(root, "seglst", "hyp", arm, f"{sid}.json")
            hyp_turns = read_rttm(hyp_rttm) if os.path.exists(hyp_rttm) else None
            hyp_seglst = read_seglst(hyp_seglst_path) if os.path.exists(hyp_seglst_path) else None
            row = score_pair(ref_turns, hyp_turns, ref_seglst, hyp_seglst, sid, boundary_precision="segment")
            row["dataset"] = name
            row["backend"] = f"existing:{arm}"
            rows.append(row)
            print(f"  {sid} [{arm}] " + _fmt_row(row))
    return rows

### Mode: run backends on audio
def run_backends(registry, name, backend_names, split=None, limit=None, run_dir=None, session_filter=None):
    from core.diar_backends import backend_available, run_backend
    from core.diar_formats import write_rttm, write_seglst

    spec = registry["datasets"][name]
    sessions = load_sessions(registry, name)
    if split:
        list_path = os.path.join(dataset_root(registry, name), "lists", f"{split}.txt")
        with open(list_path) as f:
            keep = {line.strip() for line in f if line.strip()}
        sessions = [s for s in sessions if s["session_id"] in keep]
    sessions = [s for s in sessions if s.get("audio_present")]
    sessions = filter_sessions(sessions, session_filter)
    if limit:
        sessions = sessions[:limit]
    if not sessions:
        raise SystemExit("no sessions with audio present — fetch audio first (see registry audio_mirror)")
    rows = []
    for backend in backend_names:
        ok, reason = backend_available(backend)
        if not ok:
            print(f"SKIP backend {backend}: {reason}")
            continue
        for sess in sessions:
            sid = sess["session_id"]
            audio = os.path.join(REPO_ROOT, sess["audio_path"])
            print(f"RUN {backend} on {sid} ({os.path.getsize(audio)/1e6:.0f}MB)")
            overrides = {}
            if backend == "pyannote-community1" and sess.get("num_speakers"):
                overrides["num_speakers"] = sess["num_speakers"]
            try:
                result = run_backend(backend, audio, sid, out_dir=os.path.join(run_dir, "raw"), **overrides)
            except Exception as exc:
                print(f"  ERROR {backend}/{sid}: {exc}")
                rows.append({"dataset": name, "backend": backend, "session_id": sid, "error": str(exc)})
                continue
            turns = [dict(t, uri=sid) for t in result["turns"]]
            write_rttm(turns, os.path.join(run_dir, "hyp", backend, f"{sid}.rttm"))
            hyp_seglst = None
            if result["has_words"]:
                from core.diar_formats import wer_normalize

                hyp_seglst = [
                    {"session_id": sid, "speaker": t["speaker"], "words": wer_normalize(t.get("words", "")),
                     "start_time": t["start"], "end_time": t["start"] + t["duration"]}
                    for t in result["turns"]
                ]
                write_seglst(hyp_seglst, os.path.join(run_dir, "hyp", backend, f"{sid}.seglst.json"))
            ref_turns = load_ref_turns(registry, name, sid)
            ref_seglst = load_ref_seglst(registry, name, sid)
            uem = load_uem(registry, name, sid)
            row = score_pair(ref_turns, result["turns"], ref_seglst, hyp_seglst, sid,
                             uem_regions=uem, boundary_precision=spec.get("boundary_precision", "exact"))
            row["dataset"] = name
            row["backend"] = backend
            row["model"] = result["model"]
            row["params"] = result["params"]
            rows.append(row)
            print(f"  {sid} [{backend}] " + _fmt_row(row))
    return rows

### Output
def _fmt_row(row):
    parts = []
    for key in ("der_strict", "der_lenient", "jer", "cpwer", "tcpwer"):
        if row.get(key) is not None:
            parts.append(f"{key}={row[key]:.3f}")
    if row.get("speaker_count_error") is not None:
        parts.append(f"spk_err={row['speaker_count_error']:+d}")
    return " ".join(parts) if parts else "no metrics (missing ref or hyp side)"
def write_outputs(rows, run_dir, args):
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, "metrics.jsonl"), "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    by_backend = {}
    for row in rows:
        if "error" in row:
            continue
        by_backend.setdefault(row["backend"], []).append(row)
    summary = {"created": datetime.now().isoformat(timespec="seconds"), "args": vars(args), "backends": {}}
    for backend, brows in by_backend.items():
        entry = {"sessions": len(brows)}
        for key in ("der_strict", "der_lenient", "jer", "cpwer", "tcpwer"):
            vals = [r[key] for r in brows if r.get(key) is not None]
            if vals:
                entry[f"mean_{key}"] = sum(vals) / len(vals)
        summary["backends"][backend] = entry
    with open(os.path.join(run_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print(f"\nWrote {len(rows)} rows -> {run_dir}/metrics.jsonl")
    print(json.dumps(summary["backends"], indent=1))
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset")
    parser.add_argument("--backends", help="comma-separated backend ids (see --list-backends)")
    parser.add_argument("--score-existing", action="store_true", help="score prebuilt hypothesis arms instead of running backends")
    parser.add_argument("--arms", help="comma-separated arm names for --score-existing (default: all)")
    parser.add_argument("--split", help="list name filter for external datasets (e.g. test)")
    parser.add_argument("--sessions", help="comma-separated session_id/stem substring filter (score-existing or backend runs)")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--run-id", help="run folder name (default: timestamped)")
    parser.add_argument("--list-backends", action="store_true")
    args = parser.parse_args()
    if args.list_backends:
        from core.diar_backends import list_backends

        print(json.dumps(list_backends(), indent=1))
        return
    if not args.dataset:
        parser.error("--dataset required unless --list-backends")
    registry = load_registry()
    run_id = args.run_id or f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_{args.dataset}"
    run_dir = os.path.join(REPO_ROOT, registry["runs_root"], run_id)
    if args.score_existing:
        rows = score_existing(
            registry,
            args.dataset,
            limit=args.limit,
            arms=set(args.arms.split(",")) if args.arms else None,
            session_filter=args.sessions,
        )
    else:
        if not args.backends:
            parser.error("--backends required (or use --score-existing)")
        rows = run_backends(registry, args.dataset, args.backends.split(","), split=args.split, limit=args.limit, run_dir=run_dir, session_filter=args.sessions)
    write_outputs(rows, run_dir, args)

if __name__ == "__main__":
    main()
