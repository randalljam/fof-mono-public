"""
diar_formats.py — standard diarization/ASR interchange formats and converters.

Adopts the field-standard formats so stellar-transcriber corpora and hypotheses
can be scored with community tooling (see
apps/transcription/stellar-transcriber/docs/2026-07-25_diarization-bench-plan.md):
- RTTM (NIST/pyannote): one `SPEAKER` line per turn — diarization ground truth/hypothesis.
- UEM: scored-region masks.
- SegLST (meeteval/CHiME): JSON list of {session_id, speaker, words, start_time, end_time}
  — the input for cpWER/tcpWER.

Converters cover our two native shapes:
- transcript markdown (via core.transcript_eval.extract_transcript_data): segment-level
  speaker + start timestamp only, so RTTM durations are approximated from the next
  segment start (`boundary_precision='segment'`).
- Deepgram raw JSON: word-level speaker + start/end, so turns and times are exact.
"""

import json
import os
import re
import string

### Timestamp helpers
def parse_timestamp_to_seconds(ts):
    """Convert 'M:SS' / 'H:MM:SS' timestamp string to float seconds; None if unparseable."""
    if ts is None:
        return None
    parts = str(ts).strip().split(":")
    try:
        parts = [float(p) for p in parts]
    except ValueError:
        return None
    if not parts or len(parts) > 3:
        return None
    secs = 0.0
    for p in parts:
        secs = secs * 60 + p
    return secs
def wer_normalize(text):
    """Standard WER-side text normalization: lowercase, strip punctuation except apostrophes, collapse whitespace."""
    if not text:
        return ""
    text = text.lower()
    keep = set(string.ascii_lowercase + string.digits + "' ")
    text = "".join(ch if ch in keep else " " for ch in text)
    return " ".join(text.split())

### RTTM I/O
def rttm_speaker_id(speaker):
    """Sanitize a speaker label for RTTM (space-separated fields; no spaces in the speaker token)."""
    if speaker is None or speaker == "":
        return "unknown"
    # Collapse whitespace / punctuation that would break whitespace-split RTTM parsing.
    sid = re.sub(r"\s+", "_", str(speaker).strip())
    sid = re.sub(r"[^A-Za-z0-9._+-]", "_", sid)
    sid = re.sub(r"_+", "_", sid).strip("_")
    return sid or "unknown"
def write_rttm(turns, out_path):
    """Write turns [{uri, speaker, start, duration}] as an RTTM file."""
    lines = []
    for t in sorted(turns, key=lambda x: (x["uri"], x["start"])):
        spk = rttm_speaker_id(t["speaker"])
        lines.append(
            f"SPEAKER {t['uri']} 1 {t['start']:.3f} {t['duration']:.3f} <NA> <NA> {spk} <NA> <NA>"
        )
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    return out_path
def read_rttm(path):
    """Read an RTTM file into turns [{uri, speaker, start, duration}].

    Speaker is field 8 in NIST RTTM and must not contain spaces when written by
    `write_rttm`. Older files that embedded multi-word labels (e.g. ``Speaker 0``)
    are recovered by joining tokens between the orthography ``<NA>`` and the
    trailing ``<NA> <NA>``.
    """
    turns = []
    with open(path) as f:
        for line in f:
            fields = line.split()
            if len(fields) < 9 or fields[0] != "SPEAKER":
                continue
            # Prefer: ... <NA> <NA> SPEAKER <NA> <NA>
            if len(fields) >= 10 and fields[5] == "<NA>" and fields[6] == "<NA>" and fields[-2:] == ["<NA>", "<NA>"]:
                speaker = " ".join(fields[7:-2]) if len(fields) > 10 else fields[7]
            else:
                speaker = fields[7]
            turns.append({
                "uri": fields[1],
                "start": float(fields[3]),
                "duration": float(fields[4]),
                "speaker": speaker,
            })
    return turns

### UEM I/O
def read_uem(path):
    """Read a UEM file into regions [{uri, start, end}]."""
    regions = []
    with open(path) as f:
        for line in f:
            fields = line.split()
            if len(fields) < 4:
                continue
            regions.append({"uri": fields[0], "start": float(fields[2]), "end": float(fields[3])})
    return regions

### SegLST I/O
def write_seglst(records, out_path):
    """Write SegLST records (list of dicts) as a JSON file (meeteval-compatible)."""
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(records, f, indent=1)
    return out_path
def read_seglst(path):
    """Read a SegLST JSON file into a list of dicts."""
    with open(path) as f:
        return json.load(f)

### Converters: transcript markdown
def md_to_segments(md_path):
    """Parse a transcript markdown file into segments with start seconds added (key 'start_secs')."""
    from core.transcript_eval import extract_transcript_data

    segments = extract_transcript_data(md_path)
    if segments is None:
        raise ValueError(f"No transcript content in {md_path}")
    for seg in segments:
        seg["start_secs"] = parse_timestamp_to_seconds(seg.get("timestamp"))
    return segments
def segments_to_seglst(segments, session_id, normalize=True):
    """Convert markdown segments to SegLST records; end_time approximated by next start."""
    records = []
    for i, seg in enumerate(segments):
        words = seg.get("dialogue") or ""
        if normalize:
            words = wer_normalize(words)
        start = seg.get("start_secs")
        end = None
        if start is not None:
            for nxt in segments[i + 1:]:
                if nxt.get("start_secs") is not None:
                    end = nxt["start_secs"]
                    break
        rec = {
            "session_id": session_id,
            "speaker": seg.get("speaker_full") or seg.get("speaker_name") or "unknown",
            "words": words,
        }
        if start is not None:
            rec["start_time"] = start
            rec["end_time"] = end if end is not None and end > start else start
        records.append(rec)
    return records
def segments_to_rttm_turns(segments, session_id, tail_duration=5.0):
    """
    Convert markdown segments to approximate RTTM turns (duration = next start - start).
    Boundary precision is segment-level only — suitable for approximate DER, not
    published-comparable DER. The final segment gets `tail_duration` seconds.
    """
    turns = []
    timed = [s for s in segments if s.get("start_secs") is not None]
    for i, seg in enumerate(timed):
        start = seg["start_secs"]
        end = timed[i + 1]["start_secs"] if i + 1 < len(timed) else start + tail_duration
        if end <= start:
            continue
        turns.append({
            "uri": session_id,
            "speaker": seg.get("speaker_full") or seg.get("speaker_name") or "unknown",
            "start": start,
            "duration": end - start,
        })
    return turns

### Converters: Deepgram raw JSON
def deepgram_json_to_words(json_path):
    """Extract the word list (word, start, end, speaker, punctuated_word) from a Deepgram response JSON."""
    with open(json_path) as f:
        data = json.load(f)
    alt = data["results"]["channels"][0]["alternatives"][0]
    return alt.get("words", [])
def deepgram_words_to_turns(words, session_id):
    """Group consecutive same-speaker words into exact turns [{uri, speaker, start, duration, words}]."""
    turns = []
    current = None
    for w in words:
        spk = f"spk{w.get('speaker', 0)}"
        if current is None or current["speaker"] != spk:
            if current is not None:
                turns.append(current)
            current = {
                "uri": session_id,
                "speaker": spk,
                "start": w["start"],
                "end": w["end"],
                "word_list": [w.get("punctuated_word") or w.get("word", "")],
            }
        else:
            current["end"] = w["end"]
            current["word_list"].append(w.get("punctuated_word") or w.get("word", ""))
    if current is not None:
        turns.append(current)
    for t in turns:
        t["duration"] = t.pop("end") - t["start"]
        t["words"] = " ".join(t.pop("word_list"))
    return turns
def deepgram_json_to_rttm_turns(json_path, session_id):
    """Deepgram JSON → exact RTTM turns."""
    return deepgram_words_to_turns(deepgram_json_to_words(json_path), session_id)
def deepgram_json_to_seglst(json_path, session_id, normalize=True):
    """Deepgram JSON → SegLST records with exact word-derived turn times."""
    records = []
    for t in deepgram_json_to_rttm_turns(json_path, session_id):
        words = wer_normalize(t["words"]) if normalize else t["words"]
        records.append({
            "session_id": session_id,
            "speaker": t["speaker"],
            "words": words,
            "start_time": t["start"],
            "end_time": t["start"] + t["duration"],
        })
    return records

### Session naming
def stem_to_session_id(stem):
    """Sanitize an episode stem into an RTTM/SegLST-safe session id (no spaces)."""
    sid = re.sub(r"\s+", "-", stem.strip())
    return re.sub(r"[^A-Za-z0-9._-]", "", sid)
