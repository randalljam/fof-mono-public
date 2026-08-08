# Pacing analysis of Deepgram word-level timestamps for the autolearner assessor.
# Pure functions, no API calls: takes the Deepgram response dict, returns metrics
# and a compact timeline the LLM can read to judge how the student moved through
# the problem (mastery shows up as steady forward progress; long silences and
# stated confusion show up as pauses and hesitation markers).

import json


### Word extraction
def extract_words(dg_response):
    """Pull the flat word list [{word, start, end}] out of a Deepgram response dict."""
    try:
        alt = dg_response["results"]["channels"][0]["alternatives"][0]
    except (KeyError, IndexError, TypeError):
        return []
    words = []
    for w in alt.get("words", []):
        words.append({
            "word": w.get("punctuated_word") or w.get("word", ""),
            "start": float(w.get("start", 0.0)),
            "end": float(w.get("end", 0.0)),
        })
    return words
def extract_transcript(dg_response):
    """Pull the plain transcript text out of a Deepgram response dict."""
    try:
        return dg_response["results"]["channels"][0]["alternatives"][0].get("transcript", "")
    except (KeyError, IndexError, TypeError):
        return ""

### Pacing metrics
def compute_pacing_metrics(words, pause_threshold=3.0):
    """
    Compute pacing metrics from a word list.

    :param words: list of {word, start, end} dicts (from extract_words)
    :param pause_threshold: seconds of silence between words that counts as a notable pause
    :return: dict of metrics (durations, wpm, pauses, hesitation markers)
    """
    if not words:
        return {
            "total_words": 0, "recording_duration_s": 0.0, "speaking_time_s": 0.0,
            "words_per_minute": 0.0, "time_to_first_word_s": 0.0,
            "pause_count": 0, "pauses": [], "longest_pause_s": 0.0,
            "total_pause_time_s": 0.0, "silence_ratio": 0.0, "filler_count": 0,
        }
    first_start = words[0]["start"]
    last_end = words[-1]["end"]
    duration = last_end
    speaking_time = sum(max(0.0, w["end"] - w["start"]) for w in words)
    pauses = []
    for prev, cur in zip(words, words[1:]):
        gap = cur["start"] - prev["end"]
        if gap >= pause_threshold:
            pauses.append({
                "start_s": round(prev["end"], 1),
                "duration_s": round(gap, 1),
                "before_word": cur["word"],
                "after_word": prev["word"],
            })
    total_pause = sum(p["duration_s"] for p in pauses)
    active_span = max(0.001, last_end - first_start)
    wpm = len(words) / (active_span / 60.0)
    fillers = {"um", "uh", "hmm", "hm", "er", "uhh", "umm", "mmm"}
    filler_count = sum(1 for w in words if w["word"].lower().strip(".,?!") in fillers)
    return {
        "total_words": len(words),
        "recording_duration_s": round(duration, 1),
        "speaking_time_s": round(speaking_time, 1),
        "words_per_minute": round(wpm, 1),
        "time_to_first_word_s": round(first_start, 1),
        "pause_count": len(pauses),
        "pauses": pauses,
        "longest_pause_s": max((p["duration_s"] for p in pauses), default=0.0),
        "total_pause_time_s": round(total_pause, 1),
        "silence_ratio": round(min(1.0, total_pause / max(0.001, duration)), 2),
        "filler_count": filler_count,
    }

### Timeline for the LLM
def build_timeline(words, bucket_seconds=15):
    """
    Bucket the spoken words into fixed time windows so the assessor LLM can see
    the pace of progress through the problem. Returns a list of text lines like
    "[0:15-0:30] (12 words) so the slope is rise over run ...".
    """
    if not words:
        return []
    lines = []
    end_time = words[-1]["end"]
    bucket_count = int(end_time // bucket_seconds) + 1
    for i in range(bucket_count):
        lo = i * bucket_seconds
        hi = lo + bucket_seconds
        bucket_words = [w["word"] for w in words if lo <= w["start"] < hi]
        label = f"[{_fmt_ts(lo)}-{_fmt_ts(hi)}]"
        if bucket_words:
            lines.append(f"{label} ({len(bucket_words)} words) {' '.join(bucket_words)}")
        else:
            lines.append(f"{label} (silence)")
    return lines
def _fmt_ts(seconds):
    """Format seconds as M:SS."""
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}:{s:02d}"
def pacing_report_text(metrics, timeline_lines):
    """Render metrics + timeline as a text block for inclusion in the LLM prompt."""
    lines = [
        "PACING METRICS (from word-level timestamps):",
        f"- recording duration: {metrics['recording_duration_s']}s, total words: {metrics['total_words']}, pace: {metrics['words_per_minute']} words/min",
        f"- time before first word: {metrics['time_to_first_word_s']}s",
        f"- notable pauses (>=3s): {metrics['pause_count']}, longest {metrics['longest_pause_s']}s, total pause time {metrics['total_pause_time_s']}s (silence ratio {metrics['silence_ratio']})",
        f"- filler words (um/uh/...): {metrics['filler_count']}",
    ]
    for p in metrics["pauses"][:10]:
        lines.append(f"  - pause of {p['duration_s']}s at {p['start_s']}s (after \"{p['after_word']}\", before \"{p['before_word']}\")")
    lines.append("")
    lines.append("TIMELINE (what was said in each window):")
    lines.extend(timeline_lines)
    return "\n".join(lines)

### Loading
def load_deepgram_json(json_file_path):
    """Load a saved Deepgram response JSON file."""
    with open(json_file_path) as f:
        return json.load(f)
