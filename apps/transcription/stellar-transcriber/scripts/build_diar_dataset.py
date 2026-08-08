"""
build_diar_dataset.py — build standard-format (RTTM/SegLST) references and
hypotheses for a registered dataset into the diarbench layout.

Internal corpora (deutsch, pv, sovereign-child): reads the corpus inventory
catalog, converts reference markdown (speaker-turn suffixes only) to SegLST +
approximate RTTM, and existing raw arms (Deepgram JSON preferred, md fallback)
to SegLST + RTTM hypotheses.

External benchmarks (ami-mini): links the clone's ground-truth RTTM/UEM files
and session lists into the same layout; audio is expected under the registry's
audio_root (see fetch instructions in the registry / plan doc).

Usage:
  .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/build_diar_dataset.py --dataset deutsch
  .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/build_diar_dataset.py --dataset ami-mini
Output layout: data/diarbench/datasets/<dataset>/{seglst/ref,seglst/hyp/<arm>,rttm/ref,rttm/hyp/<arm>,uem,lists,sessions.jsonl}
"""

import argparse
import csv
import json
import os
import shutil
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

CONFIG_PATH = os.path.join(REPO_ROOT, "apps/transcription/stellar-transcriber/config/diar-datasets.json")

### Registry
def load_registry():
    """Load the dataset registry config."""
    with open(CONFIG_PATH) as f:
        return json.load(f)

### Internal corpora
def build_internal(name, spec, registry):
    """Build SegLST + approximate RTTM refs and hyps for an internal corpus."""
    from core.diar_formats import (
        deepgram_json_to_rttm_turns,
        deepgram_json_to_seglst,
        md_to_segments,
        segments_to_rttm_turns,
        segments_to_seglst,
        stem_to_session_id,
        write_rttm,
        write_seglst,
    )

    out_root = os.path.join(REPO_ROOT, registry["build_root"], name)
    catalog = os.path.join(REPO_ROOT, spec["catalog_csv"])
    sessions = []
    skipped = []
    with open(catalog) as f:
        rows = [r for r in csv.DictReader(f) if r["corpus"] == name and r["has_pair"] == "yes"]
    for row in rows:
        stem = row["stem"]
        paths = row["s3_keys"].split(";")
        ref_path = None
        for suffix in spec["ref_suffix_priority"]:
            ref_path = next((p for p in paths if p.endswith(f"{suffix}.md")), None)
            if ref_path:
                break
        if not ref_path:
            skipped.append((stem, "no speaker-turn reference"))
            continue
        sid = stem_to_session_id(stem)
        try:
            ref_segments = md_to_segments(os.path.join(REPO_ROOT, ref_path))
        except Exception as exc:
            skipped.append((stem, f"ref parse failed: {exc}"))
            continue
        if not ref_segments:
            skipped.append((stem, "empty reference"))
            continue
        write_seglst(segments_to_seglst(ref_segments, sid), os.path.join(out_root, "seglst", "ref", f"{sid}.json"))
        ref_turns = segments_to_rttm_turns(ref_segments, sid)
        if ref_turns:
            write_rttm(ref_turns, os.path.join(out_root, "rttm", "ref", f"{sid}.rttm"))
        session = {"session_id": sid, "stem": stem, "ref_path": ref_path, "hyps": {}}
        audio_dir = spec.get("audio_dir")
        if audio_dir:
            audio_abs = os.path.join(REPO_ROOT, audio_dir, f"{stem}.mp3")
            session["audio_path"] = os.path.join(audio_dir, f"{stem}.mp3")
            # audio_present gates end-to-end backend runs: the file must exist AND be
            # duration-verified against the Deepgram raw (same audio as the transcripts).
            status = _audio_inventory(audio_dir).get(stem, {}).get("status")
            session["audio_present"] = os.path.exists(audio_abs) and status == "verified"
            if status and status != "verified":
                session["audio_status"] = status
        for arm in spec["hyp_suffixes"]:
            md_path = next((p for p in paths if p.endswith(f"{arm}.md")), None)
            if md_path is None:
                continue
            json_path = md_path[:-3] + ".json"
            json_abs = os.path.join(REPO_ROOT, json_path)
            try:
                if os.path.exists(json_abs):
                    seglst = deepgram_json_to_seglst(json_abs, sid)
                    turns = deepgram_json_to_rttm_turns(json_abs, sid)
                    source = json_path
                else:
                    segs = md_to_segments(os.path.join(REPO_ROOT, md_path))
                    seglst = segments_to_seglst(segs, sid)
                    turns = segments_to_rttm_turns(segs, sid)
                    source = md_path
            except Exception as exc:
                skipped.append((stem, f"hyp {arm} failed: {exc}"))
                continue
            write_seglst(seglst, os.path.join(out_root, "seglst", "hyp", arm.lstrip("_"), f"{sid}.json"))
            if turns:
                write_rttm(turns, os.path.join(out_root, "rttm", "hyp", arm.lstrip("_"), f"{sid}.rttm"))
            session["hyps"][arm.lstrip("_")] = source
        sessions.append(session)
    _write_sessions(out_root, sessions)
    print(f"[{name}] built {len(sessions)} sessions -> {out_root}")
    for stem, why in skipped:
        print(f"  skipped {stem}: {why}")
    return sessions

### External benchmarks
def build_external(name, spec, registry):
    """Link ground-truth RTTM/UEM + lists from the external clone into the layout."""
    clone_root = os.path.join(registry["external_clones_dir"], spec["clone_subdir"])
    out_root = os.path.join(REPO_ROOT, registry["build_root"], name)
    uris = {}
    for split, rel in spec["lists"].items():
        with open(os.path.join(clone_root, rel)) as f:
            uris[split] = [line.strip() for line in f if line.strip()]
        os.makedirs(os.path.join(out_root, "lists"), exist_ok=True)
        with open(os.path.join(out_root, "lists", f"{split}.txt"), "w") as f:
            f.write("\n".join(uris[split]) + "\n")
    all_uris = sorted({u for us in uris.values() for u in us})
    copied = 0
    for uri in all_uris:
        for rttm_dir in spec["rttm_dirs"]:
            src = os.path.join(clone_root, rttm_dir, f"{uri}.rttm")
            if os.path.exists(src):
                dst = os.path.join(out_root, "rttm", "ref", f"{uri}.rttm")
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                copied += 1
                break
        for uem_dir in spec.get("uem_dirs", []):
            src = os.path.join(clone_root, uem_dir, f"{uri}.uem")
            if os.path.exists(src):
                dst = os.path.join(out_root, "uem", f"{uri}.uem")
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                break
    audio_root = os.path.join(REPO_ROOT, spec["audio_root"])
    sessions = []
    for uri in all_uris:
        audio = os.path.join(audio_root, spec["audio_pattern"].format(uri=uri))
        sessions.append({
            "session_id": uri,
            "audio_path": os.path.relpath(audio, REPO_ROOT),
            "audio_present": os.path.exists(audio),
            "num_speakers": spec.get("num_speakers"),
        })
    _write_sessions(out_root, sessions)
    present = sum(1 for s in sessions if s["audio_present"])
    print(f"[{name}] {len(all_uris)} sessions, {copied} ref RTTMs copied, audio present for {present} -> {out_root}")
    return sessions

### Shared
_INVENTORY_CACHE = {}
def _audio_inventory(audio_dir):
    """Load (and cache) an audio_dir's audio-inventory.jsonl as {stem: row}."""
    if audio_dir not in _INVENTORY_CACHE:
        rows = {}
        inv_path = os.path.join(REPO_ROOT, audio_dir, "audio-inventory.jsonl")
        if os.path.exists(inv_path):
            with open(inv_path) as f:
                for line in f:
                    row = json.loads(line)
                    rows[row["stem"]] = row
        _INVENTORY_CACHE[audio_dir] = rows
    return _INVENTORY_CACHE[audio_dir]
def _write_sessions(out_root, sessions):
    """Write the sessions.jsonl index for a built dataset."""
    os.makedirs(out_root, exist_ok=True)
    with open(os.path.join(out_root, "sessions.jsonl"), "w") as f:
        for s in sessions:
            f.write(json.dumps(s) + "\n")
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, help="registry key, e.g. deutsch | pv | ami-mini")
    args = parser.parse_args()
    registry = load_registry()
    spec = registry["datasets"].get(args.dataset)
    if spec is None:
        raise SystemExit(f"unknown dataset '{args.dataset}'; known: {', '.join(registry['datasets'])}")
    if spec.get("status") == "planned":
        raise SystemExit(f"dataset '{args.dataset}' is registered as planned only: {spec.get('note')}")
    if spec["kind"] == "internal":
        build_internal(args.dataset, spec, registry)
    else:
        build_external(args.dataset, spec, registry)

if __name__ == "__main__":
    main()
