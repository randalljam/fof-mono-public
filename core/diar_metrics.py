"""
diar_metrics.py — protocol-pinned wrappers over the field-standard scoring tools.

- DER/JER via pyannote.metrics, reported under two named protocols:
  `strict`  = collar 0.0, overlap scored (pyannote model-card protocol)
  `lenient` = collar 0.25, overlap scored
- cpWER/tcpWER via meeteval on SegLST records.

Every result dict carries the protocol fields so numbers are never reported
without their conditions (the top comparability trap flagged in
apps/transcription/2026-07-25_diarization-research.md).
"""

DER_PROTOCOLS = {
    "strict": {"collar": 0.0, "skip_overlap": False},
    "lenient": {"collar": 0.25, "skip_overlap": False},
}

### Annotation building
def turns_to_annotation(turns, uri):
    """Convert turns [{speaker, start, duration}] to a pyannote Annotation."""
    from pyannote.core import Annotation, Segment

    ann = Annotation(uri=uri)
    for t in turns:
        ann[Segment(t["start"], t["start"] + t["duration"]), f"{t['start']:.3f}-{t['speaker']}"] = t["speaker"]
    return ann.support()
def uem_regions_to_timeline(regions, uri):
    """Convert UEM regions [{uri, start, end}] for one uri to a pyannote Timeline (None if empty)."""
    from pyannote.core import Segment, Timeline

    segs = [Segment(r["start"], r["end"]) for r in regions if r["uri"] == uri]
    if not segs:
        return None
    return Timeline(segs, uri=uri)

### Diarization metrics (DER/JER)
def compute_der(ref_turns, hyp_turns, uri, protocol="strict", uem_regions=None):
    """Compute DER for one recording under a named protocol; returns a flat dict with components."""
    from pyannote.metrics.diarization import DiarizationErrorRate

    params = DER_PROTOCOLS[protocol]
    metric = DiarizationErrorRate(collar=params["collar"], skip_overlap=params["skip_overlap"])
    ref = turns_to_annotation(ref_turns, uri)
    hyp = turns_to_annotation(hyp_turns, uri)
    uem = uem_regions_to_timeline(uem_regions, uri) if uem_regions else None
    detail = metric(ref, hyp, uem=uem, detailed=True)
    return {
        "uri": uri,
        "protocol": protocol,
        "collar": params["collar"],
        "skip_overlap": params["skip_overlap"],
        "der": detail["diarization error rate"],
        "missed": detail["missed detection"],
        "false_alarm": detail["false alarm"],
        "confusion": detail["confusion"],
        "total_speech": detail["total"],
    }
def compute_jer(ref_turns, hyp_turns, uri, uem_regions=None):
    """Compute JER (collar 0) for one recording."""
    from pyannote.metrics.diarization import JaccardErrorRate

    metric = JaccardErrorRate(collar=0.0)
    ref = turns_to_annotation(ref_turns, uri)
    hyp = turns_to_annotation(hyp_turns, uri)
    uem = uem_regions_to_timeline(uem_regions, uri) if uem_regions else None
    return {"uri": uri, "jer": metric(ref, hyp, uem=uem)}
def compute_diarization_metrics(ref_turns, hyp_turns, uri, uem_regions=None):
    """DER strict + lenient + JER + speaker-count error for one recording, as one flat dict."""
    strict = compute_der(ref_turns, hyp_turns, uri, "strict", uem_regions)
    lenient = compute_der(ref_turns, hyp_turns, uri, "lenient", uem_regions)
    jer = compute_jer(ref_turns, hyp_turns, uri, uem_regions)
    ref_spk = len({t["speaker"] for t in ref_turns})
    hyp_spk = len({t["speaker"] for t in hyp_turns})
    return {
        "uri": uri,
        "der_strict": strict["der"],
        "der_strict_missed": strict["missed"],
        "der_strict_false_alarm": strict["false_alarm"],
        "der_strict_confusion": strict["confusion"],
        "der_lenient": lenient["der"],
        "jer": jer["jer"],
        "ref_speaker_count": ref_spk,
        "hyp_speaker_count": hyp_spk,
        "speaker_count_error": hyp_spk - ref_spk,
        "total_speech": strict["total_speech"],
    }

### Speaker-attributed WER (cpWER/tcpWER)
def _seglst(records):
    """Wrap plain record dicts in a meeteval SegLST."""
    from meeteval.io.seglst import SegLST

    return SegLST(records)
def _flatten_cp(result):
    """Flatten a meeteval per-session result dict into per-session + combined rows."""
    from meeteval.wer import combine_error_rates

    per_session = {}
    for sid, er in result.items():
        per_session[sid] = {
            "error_rate": er.error_rate,
            "errors": er.errors,
            "length": er.length,
            "insertions": er.insertions,
            "deletions": er.deletions,
            "substitutions": er.substitutions,
            "missed_speaker": er.missed_speaker,
            "falarm_speaker": er.falarm_speaker,
        }
    combined = combine_error_rates(*result.values()) if result else None
    summary = {
        "error_rate": combined.error_rate if combined else None,
        "errors": combined.errors if combined else 0,
        "length": combined.length if combined else 0,
    }
    return {"combined": summary, "per_session": per_session}
def compute_cpwer(ref_records, hyp_records):
    """cpWER over SegLST records. Sessions over meeteval's 20-speaker cap come back skipped, not raised."""
    import meeteval

    try:
        result = meeteval.wer.cpwer(reference=_seglst(ref_records), hypothesis=_seglst(hyp_records))
    except RuntimeError as exc:
        return {"metric": "cpwer", "combined": {"error_rate": None, "errors": 0, "length": 0},
                "per_session": {}, "skipped": f"meeteval speaker cap: {str(exc).splitlines()[1] if len(str(exc).splitlines()) > 1 else exc}"}
    out = _flatten_cp(result)
    out["metric"] = "cpwer"
    return out
def compute_tcpwer(ref_records, hyp_records, collar=5):
    """tcpWER over SegLST records; collar in seconds (meeteval default convention)."""
    import meeteval

    try:
        result = meeteval.wer.tcpwer(reference=_seglst(ref_records), hypothesis=_seglst(hyp_records), collar=collar)
    except RuntimeError as exc:
        return {"metric": "tcpwer", "collar": collar, "combined": {"error_rate": None, "errors": 0, "length": 0},
                "per_session": {}, "skipped": f"meeteval speaker cap: {str(exc).splitlines()[1] if len(str(exc).splitlines()) > 1 else exc}"}
    out = _flatten_cp(result)
    out["metric"] = "tcpwer"
    out["collar"] = collar
    return out
