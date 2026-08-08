"""
fetch_corpus_audio.py — download source audio (mp3) for internal corpus episodes
from their transcript-metadata YouTube links, and verify each file's duration
against the Deepgram raw JSON `metadata.duration` so we know it is the same
audio the raw transcripts were made from.

Verification statuses (written to <audio_dir>/audio-inventory.jsonl, one row per
episode, newest attempt wins):
  verified          — duration within tolerance of the Deepgram duration
  duration_mismatch — downloaded, but duration differs beyond tolerance
  no_link           — transcript metadata has no link
  no_dg_duration    — no raw Deepgram JSON to verify against (file kept, unverified)
  download_failed   — yt-dlp error (dead/expired link, geo block, etc.)

Audio lands at <audio_dir>/<stem>.mp3 (audio_dir from config/diar-datasets.json).
S3 archival of the audio dir is a separate, explicitly-confirmed s3_archive step —
this script never touches S3.

Usage:
  .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/fetch_corpus_audio.py --dataset deutsch --limit 10
  .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/fetch_corpus_audio.py --dataset pv --stems 2023-01-05_PV-EPC
"""

import argparse
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from build_diar_dataset import load_registry

DURATION_TOL_SECS = 5.0
DURATION_TOL_FRAC = 0.01

### Episode source discovery
def episode_sources(registry, dataset, spec):
    """Yield {stem, session_id, md_path, json_path} for each built session of an internal corpus."""
    sessions_path = os.path.join(REPO_ROOT, registry["build_root"], dataset, "sessions.jsonl")
    if not os.path.exists(sessions_path):
        raise SystemExit(f"dataset '{dataset}' not built — run build_diar_dataset.py first")
    with open(sessions_path) as f:
        for line in f:
            sess = json.loads(line)
            src = None
            for arm, path in sorted(sess.get("hyps", {}).items()):
                if path.endswith(".json"):
                    src = {"json_path": path, "md_path": path[:-5] + ".md"}
                    break
                src = src or {"json_path": None, "md_path": path}
            if src is None:
                continue
            yield {"stem": sess["stem"], "session_id": sess["session_id"], **src}
def read_md_link(md_path):
    """Extract the source url from a transcript md metadata block."""
    try:
        with open(os.path.join(REPO_ROOT, md_path)) as f:
            for line in f:
                if line.startswith("link"):
                    parts = line.split(":", 1)
                    if len(parts) == 2 and parts[1].strip().lower().startswith("http"):
                        return parts[1].strip()
                if line.startswith("## content"):
                    break
    except OSError:
        return None
    return None
def read_dg_duration(json_path):
    """Read metadata.duration (seconds) from a Deepgram raw response JSON."""
    if not json_path:
        return None
    try:
        with open(os.path.join(REPO_ROOT, json_path)) as f:
            return json.load(f).get("metadata", {}).get("duration")
    except (OSError, json.JSONDecodeError):
        return None

### Download and verify
def download_audio(url, dest_path):
    """Download best audio as mp3 via yt-dlp; returns (ok, message)."""
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    cmd = [
        os.path.join(REPO_ROOT, ".venv", "bin", "yt-dlp"),
        "-f", "bestaudio", "-x", "--audio-format", "mp3",
        # YouTube's n-challenge needs a JS runtime + the yt-dlp-ejs solver;
        # without them downloads fail with HTTP 403.
        "--js-runtimes", "node",
        "--no-playlist", "--no-progress", "-o", dest_path.rsplit(".", 1)[0] + ".%(ext)s",
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()
        return False, tail[-1] if tail else f"yt-dlp exit {proc.returncode}"
    return os.path.exists(dest_path), "ok" if os.path.exists(dest_path) else "yt-dlp succeeded but mp3 missing"
def audio_duration_secs(path):
    """Measure an audio file's duration with mutagen."""
    from mutagen import File as MutagenFile

    info = MutagenFile(path)
    return float(info.info.length) if info is not None else None
def verify_duration(file_secs, dg_secs):
    """True when file duration matches the Deepgram duration within tolerance."""
    if file_secs is None or dg_secs is None:
        return None
    tol = max(DURATION_TOL_SECS, DURATION_TOL_FRAC * dg_secs)
    return abs(file_secs - dg_secs) <= tol

### Inventory
def load_inventory(inv_path):
    rows = {}
    if os.path.exists(inv_path):
        with open(inv_path) as f:
            for line in f:
                row = json.loads(line)
                rows[row["stem"]] = row
    return rows
def save_inventory(inv_path, rows):
    os.makedirs(os.path.dirname(inv_path), exist_ok=True)
    with open(inv_path, "w") as f:
        for stem in sorted(rows):
            f.write(json.dumps(rows[stem]) + "\n")
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--stems", help="comma-separated stem filter (substring match)")
    parser.add_argument("--redo", action="store_true", help="re-attempt episodes already in the inventory")
    args = parser.parse_args()
    registry = load_registry()
    spec = registry["datasets"].get(args.dataset)
    if spec is None or spec.get("kind") != "internal":
        raise SystemExit(f"'{args.dataset}' is not a registered internal corpus")
    audio_dir = spec.get("audio_dir")
    if not audio_dir:
        raise SystemExit(f"no audio_dir configured for '{args.dataset}' in diar-datasets.json")
    audio_root = os.path.join(REPO_ROOT, audio_dir)
    inv_path = os.path.join(audio_root, "audio-inventory.jsonl")
    inventory = load_inventory(inv_path)
    episodes = list(episode_sources(registry, args.dataset, spec))
    if args.stems:
        wants = [s.strip() for s in args.stems.split(",")]
        episodes = [e for e in episodes if any(w in e["stem"] for w in wants)]
    todo = []
    for ep in episodes:
        prior = inventory.get(ep["stem"])
        if prior and not args.redo and prior["status"] in ("verified", "duration_mismatch", "no_dg_duration"):
            continue
        todo.append(ep)
        if args.limit and len(todo) >= args.limit:
            break
    print(f"[{args.dataset}] attempting {len(todo)} episodes -> {audio_dir}")
    counts = {}
    for ep in todo:
        stem = ep["stem"]
        dest = os.path.join(audio_root, f"{stem}.mp3")
        link = read_md_link(ep["md_path"])
        dg_secs = read_dg_duration(ep["json_path"])
        row = {"stem": stem, "session_id": ep["session_id"], "link": link,
               "dg_duration_secs": dg_secs, "audio_path": os.path.relpath(dest, REPO_ROOT)}
        if not link:
            row.update(status="no_link", audio_path=None)
        else:
            if os.path.exists(dest):
                ok, msg = True, "already downloaded"
            else:
                ok, msg = download_audio(link, dest)
            if not ok:
                row.update(status="download_failed", error=msg, audio_path=None)
            else:
                file_secs = audio_duration_secs(dest)
                row["file_duration_secs"] = file_secs
                match = verify_duration(file_secs, dg_secs)
                if match is None:
                    row["status"] = "no_dg_duration"
                elif match:
                    row["status"] = "verified"
                else:
                    row.update(status="duration_mismatch",
                               delta_secs=round(abs(file_secs - dg_secs), 1))
        inventory[stem] = row
        counts[row["status"]] = counts.get(row["status"], 0) + 1
        extra = f" delta={row.get('delta_secs')}s" if row["status"] == "duration_mismatch" else ""
        extra = f" ({row.get('error')})" if row["status"] == "download_failed" else extra
        print(f"  {row['status']:<17} {stem}{extra}")
        save_inventory(inv_path, inventory)
    print(f"\nsummary: {counts} | inventory: {os.path.relpath(inv_path, REPO_ROOT)}")

if __name__ == "__main__":
    main()
