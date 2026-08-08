"""
diar_backends.py — uniform adapters for diarizing-ASR services and local models.

Every adapter returns the same normalized result dict:
    {
      "backend": <backend id>, "model": <model/pipeline id>, "params": {...},
      "session_id": <uri>,
      "turns": [{"speaker", "start", "duration", "words"(optional)}],
      "has_words": bool,          # False for diarization-only backends
      "raw_path": <path to saved raw response, when applicable>
    }
Turns feed core.diar_formats.write_rttm / core.diar_metrics directly; word-bearing
backends also feed SegLST/cpWER.

Adapters never guess silently: `backend_available(name)` reports (ok, reason) so
runners can skip unavailable backends and say why. Pin exact models/params in
apps/transcription/stellar-transcriber/config/diar-backends.json — scored runs
must not use an ambiguous `latest`.
"""

import importlib.util
import json
import os
import time

from dotenv import load_dotenv

load_dotenv(override=True)

### Normalized result helpers
def normalized_result(backend, model, session_id, turns, params=None, raw_path=None):
    """Assemble the standard adapter result dict."""
    return {
        "backend": backend,
        "model": model,
        "params": params or {},
        "session_id": session_id,
        "turns": turns,
        "has_words": any("words" in t for t in turns),
        "raw_path": raw_path,
    }
def _save_raw(payload, out_dir, session_id, backend):
    """Persist a raw API response next to the run outputs; returns path or None."""
    if out_dir is None:
        return None
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{session_id}_{backend}_raw.json")
    with open(path, "w") as f:
        if isinstance(payload, (dict, list)):
            json.dump(payload, f, indent=1)
        else:
            f.write(str(payload))
    return path

### Backend: Deepgram (batch, diarize v2)
def run_deepgram(audio_path, session_id, model="nova-2-general", diarize_model="v2", out_dir=None):
    """Deepgram prerecorded transcription with the v2 batch diarizer; word-level turns."""
    import httpx
    from deepgram import DeepgramClient

    from core.diar_formats import deepgram_words_to_turns

    client = DeepgramClient(os.environ["DEEPGRAM_API_KEY"])
    with open(audio_path, "rb") as audio:
        payload = {"buffer": audio.read(), "mimetype": f"audio/{audio_path.rsplit('.', 1)[1]}"}
    # Dict options (not PrerecordedOptions) so diarize_model passes through the SDK;
    # diarize_model supersedes the deprecated diarize=true — never set both.
    options = {
        "model": model,
        "smart_format": True,
        "punctuate": True,
        "diarize_model": diarize_model,
    }
    response = client.listen.rest.v("1").transcribe_file(
        payload, options, timeout=httpx.Timeout(1800.0, connect=10.0)
    )
    data = json.loads(response.to_json())
    raw_path = _save_raw(data, out_dir, session_id, f"deepgram-{model}")
    words = data["results"]["channels"][0]["alternatives"][0].get("words", [])
    turns = deepgram_words_to_turns(words, session_id)
    for t in turns:
        t.pop("uri", None)
    return normalized_result(
        "deepgram", model, session_id, turns,
        params={"diarize_model": diarize_model, "smart_format": True, "punctuate": True},
        raw_path=raw_path,
    )

### Backend: pyannote community-1 (local, diarization only)
def _pyannote_diarize(audio_path, num_speakers=None, min_speakers=None, max_speakers=None):
    """Run pyannote community-1 on a locally loaded waveform; returns the raw pipeline output."""
    import torch
    import soundfile as sf
    from pyannote.audio import Pipeline

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-community-1", token=token)
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    pipeline.to(device)
    print(f"  pyannote-community1 device={device}")
    kwargs = {}
    if num_speakers is not None:
        kwargs["num_speakers"] = num_speakers
    if min_speakers is not None:
        kwargs["min_speakers"] = min_speakers
    if max_speakers is not None:
        kwargs["max_speakers"] = max_speakers
    # Load the waveform ourselves (soundfile handles wav+mp3) instead of passing a
    # path: pyannote 4's path loader requires torchcodec, whose dylibs need an
    # ffmpeg install location that doesn't match every machine.
    data, sample_rate = sf.read(audio_path, dtype="float32", always_2d=True)
    waveform = torch.from_numpy(data.T)
    return pipeline({"waveform": waveform, "sample_rate": sample_rate}, **kwargs)
def run_pyannote_community1(audio_path, session_id, num_speakers=None, min_speakers=None, max_speakers=None, out_dir=None):
    """pyannote/speaker-diarization-community-1 local pipeline; diarization-only turns."""
    output = _pyannote_diarize(audio_path, num_speakers=num_speakers, min_speakers=min_speakers, max_speakers=max_speakers)
    annotation = getattr(output, "speaker_diarization", output)
    turns = []
    for segment, _, label in annotation.itertracks(yield_label=True):
        turns.append({"speaker": label, "start": segment.start, "duration": segment.duration})
    rttm_lines = [
        f"SPEAKER {session_id} 1 {t['start']:.3f} {t['duration']:.3f} <NA> <NA> {t['speaker']} <NA> <NA>"
        for t in turns
    ]
    raw_path = _save_raw("\n".join(rttm_lines), out_dir, session_id, "pyannote-community1")
    return normalized_result(
        "pyannote-community1", "pyannote/speaker-diarization-community-1", session_id, turns,
        params={k: v for k, v in [("num_speakers", num_speakers), ("min_speakers", min_speakers), ("max_speakers", max_speakers)] if v is not None},
        raw_path=raw_path,
    )

### Backend: MLX Whisper + pyannote community-1 (local ASR + diarization)
def assign_words_to_speakers(words, turns):
    """Assign each word to the containing speaker turn, then nearest turn edge within 2s."""
    assigned = []
    ordered_turns = sorted(turns, key=lambda t: t["start"])
    for word in words:
        midpoint = (word["start"] + word["end"]) / 2.0
        speaker = None
        for turn in ordered_turns:
            start = turn["start"]
            end = start + turn["duration"]
            if start <= midpoint <= end:
                speaker = turn["speaker"]
                break
        if speaker is None and ordered_turns:
            nearest = None
            for turn in ordered_turns:
                start = turn["start"]
                end = start + turn["duration"]
                distance = min(abs(midpoint - start), abs(midpoint - end))
                if nearest is None or distance < nearest[0]:
                    nearest = (distance, turn["speaker"])
            if nearest[0] <= 2.0:
                speaker = nearest[1]
        assigned_word = dict(word)
        assigned_word["speaker"] = speaker or "unknown"
        assigned.append(assigned_word)
    return assigned
def _words_to_speaker_turns(words):
    """Group consecutive same-speaker word dicts into backend turns."""
    turns = []
    current = None
    for word in words:
        if current is None or current["speaker"] != word["speaker"]:
            if current is not None:
                turns.append(current)
            current = {
                "speaker": word["speaker"],
                "start": word["start"],
                "end": word["end"],
                "word_list": [word["word"]],
            }
        else:
            current["end"] = word["end"]
            current["word_list"].append(word["word"])
    if current is not None:
        turns.append(current)
    for turn in turns:
        turn["duration"] = max(0.0, turn.pop("end") - turn["start"])
        turn["words"] = " ".join(turn.pop("word_list"))
    return turns
def _annotation_to_turns(annotation):
    """Convert a pyannote annotation/timeline object to standard speaker turns."""
    turns = []
    for segment, _, label in annotation.itertracks(yield_label=True):
        turns.append({"speaker": label, "start": segment.start, "duration": segment.duration})
    return turns
def run_mlx_whisper_pyannote(audio_path, session_id, asr_model="mlx-community/whisper-large-v3-turbo", num_speakers=None, min_speakers=None, max_speakers=None, out_dir=None):
    """MLX Whisper ASR with pyannote community-1 diarization; word-level turns."""
    import mlx_whisper

    whisper_result = mlx_whisper.transcribe(audio_path, path_or_hf_repo=asr_model, word_timestamps=True)
    raw_path = _save_raw(whisper_result, out_dir, session_id, "mlx-whisper-pyannote")
    words = []
    for segment in whisper_result.get("segments", []):
        for word in segment.get("words", []):
            words.append({"word": word.get("word", ""), "start": word["start"], "end": word["end"]})
    diar_output = _pyannote_diarize(audio_path, num_speakers=num_speakers, min_speakers=min_speakers, max_speakers=max_speakers)
    annotation = getattr(diar_output, "exclusive_speaker_diarization", None)
    if annotation is None:
        annotation = getattr(diar_output, "speaker_diarization", diar_output)
    diar_turns = _annotation_to_turns(annotation)
    rttm_lines = [
        f"SPEAKER {session_id} 1 {t['start']:.3f} {t['duration']:.3f} <NA> <NA> {t['speaker']} <NA> <NA>"
        for t in diar_turns
    ]
    _save_raw("\n".join(rttm_lines), out_dir, session_id, "mlx-whisper-pyannote-diarization")
    assigned_words = assign_words_to_speakers(words, diar_turns)
    turns = _words_to_speaker_turns(assigned_words)
    params = {"asr_model": asr_model}
    params.update({k: v for k, v in [("num_speakers", num_speakers), ("min_speakers", min_speakers), ("max_speakers", max_speakers)] if v is not None})
    return normalized_result("mlx-whisper-pyannote", asr_model, session_id, turns, params=params, raw_path=raw_path)

### Backend: ElevenLabs Scribe (API, words + speaker ids)
def run_elevenlabs_scribe(audio_path, session_id, model_id="scribe_v1", out_dir=None):
    """ElevenLabs speech-to-text with diarization; word-level speaker ids grouped into turns."""
    import requests

    url = "https://api.elevenlabs.io/v1/speech-to-text"
    headers = {"xi-api-key": os.environ["ELEVENLABS_API_KEY"]}
    with open(audio_path, "rb") as f:
        resp = requests.post(
            url, headers=headers,
            files={"file": (os.path.basename(audio_path), f)},
            data={"model_id": model_id, "diarize": "true", "timestamps_granularity": "word"},
            timeout=1800,
        )
    resp.raise_for_status()
    data = resp.json()
    raw_path = _save_raw(data, out_dir, session_id, f"elevenlabs-{model_id}")
    turns = []
    current = None
    for w in data.get("words", []):
        if w.get("type") == "spacing":
            continue
        spk = w.get("speaker_id") or "speaker_0"
        if current is None or current["speaker"] != spk:
            if current is not None:
                turns.append(current)
            current = {"speaker": spk, "start": w["start"], "end": w["end"], "word_list": [w["text"]]}
        else:
            current["end"] = w["end"]
            current["word_list"].append(w["text"])
    if current is not None:
        turns.append(current)
    for t in turns:
        t["duration"] = t.pop("end") - t["start"]
        t["words"] = " ".join(t.pop("word_list"))
    return normalized_result("elevenlabs-scribe", model_id, session_id, turns, params={"diarize": True}, raw_path=raw_path)

### Backend: OpenAI diarized transcription (API)
def run_openai_diarize(audio_path, session_id, model="gpt-4o-transcribe-diarize", out_dir=None):
    """OpenAI hosted diarized transcription (diarized_json). API upload limit ~25MB."""
    import requests

    size_mb = os.path.getsize(audio_path) / 1e6
    if size_mb > 25:
        raise ValueError(f"{audio_path} is {size_mb:.0f}MB — over the OpenAI audio upload limit; compress/chunk first")
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY_LOCAL")
    with open(audio_path, "rb") as f:
        resp = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {key}"},
            files={"file": (os.path.basename(audio_path), f)},
            # chunking_strategy is mandatory for diarization models on this endpoint
            data={"model": model, "response_format": "diarized_json", "chunking_strategy": "auto"},
            timeout=1800,
        )
    if resp.status_code >= 400:
        raise RuntimeError(f"OpenAI transcription error {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    raw_path = _save_raw(data, out_dir, session_id, "openai-diarize")
    turns = []
    for seg in data.get("segments", []):
        turns.append({
            "speaker": seg.get("speaker", "speaker_0"),
            "start": seg.get("start", 0.0),
            "duration": max(0.0, seg.get("end", 0.0) - seg.get("start", 0.0)),
            "words": seg.get("text", ""),
        })
    return normalized_result("openai-diarize", model, session_id, turns, raw_path=raw_path)

### Backend: AssemblyAI (API, joint transcription+diarization)
def run_assemblyai(audio_path, session_id, speech_model="universal", out_dir=None, poll_secs=5):
    """AssemblyAI async transcription with speaker_labels; utterance-level turns."""
    import requests

    key = os.environ["ASSEMBLYAI_API_KEY"]
    headers = {"authorization": key}
    with open(audio_path, "rb") as f:
        upload = requests.post("https://api.assemblyai.com/v2/upload", headers=headers, data=f, timeout=1800)
    upload.raise_for_status()
    audio_url = upload.json()["upload_url"]
    job = requests.post(
        "https://api.assemblyai.com/v2/transcript", headers=headers,
        json={"audio_url": audio_url, "speaker_labels": True, "speech_model": speech_model},
        timeout=60,
    )
    job.raise_for_status()
    tid = job.json()["id"]
    while True:
        data = requests.get(f"https://api.assemblyai.com/v2/transcript/{tid}", headers=headers, timeout=60).json()
        if data["status"] in ("completed", "error"):
            break
        time.sleep(poll_secs)
    if data["status"] == "error":
        raise RuntimeError(f"AssemblyAI error: {data.get('error')}")
    raw_path = _save_raw(data, out_dir, session_id, "assemblyai")
    turns = []
    for utt in data.get("utterances", []) or []:
        turns.append({
            "speaker": f"spk{utt['speaker']}",
            "start": utt["start"] / 1000.0,
            "duration": (utt["end"] - utt["start"]) / 1000.0,
            "words": utt.get("text", ""),
        })
    return normalized_result("assemblyai", speech_model, session_id, turns, params={"speaker_labels": True}, raw_path=raw_path)

### Backend: pyannoteAI Precision-2 (API, diarization only)
def run_pyannoteai_precision2(audio_path, session_id, out_dir=None, poll_secs=5):
    """pyannoteAI hosted Precision diarization: upload media, create job, poll."""
    import requests

    key = os.environ["PYANNOTEAI_API_KEY"]
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    media_url = f"media://diarbench/{session_id}{os.path.splitext(audio_path)[1]}"
    presign = requests.post("https://api.pyannote.ai/v1/media/input", headers=headers, json={"url": media_url}, timeout=60)
    presign.raise_for_status()
    with open(audio_path, "rb") as f:
        put = requests.put(presign.json()["url"], data=f, timeout=1800)
    put.raise_for_status()
    job = requests.post("https://api.pyannote.ai/v1/diarize", headers=headers, json={"url": media_url}, timeout=60)
    job.raise_for_status()
    jid = job.json()["jobId"]
    while True:
        data = requests.get(f"https://api.pyannote.ai/v1/jobs/{jid}", headers=headers, timeout=60).json()
        if data.get("status") in ("succeeded", "failed", "canceled"):
            break
        time.sleep(poll_secs)
    if data.get("status") != "succeeded":
        raise RuntimeError(f"pyannoteAI job {jid} ended with status {data.get('status')}")
    raw_path = _save_raw(data, out_dir, session_id, "pyannoteai-precision2")
    turns = []
    for seg in data.get("output", {}).get("diarization", []):
        turns.append({"speaker": seg["speaker"], "start": seg["start"], "duration": seg["end"] - seg["start"]})
    return normalized_result("pyannoteai-precision2", "precision-2", session_id, turns, raw_path=raw_path)

### Registry and availability
BACKEND_REGISTRY = {
    "deepgram-nova2": {"runner": run_deepgram, "kwargs": {"model": "nova-2-general", "diarize_model": "v2"}, "needs_env": ["DEEPGRAM_API_KEY"], "needs_import": ["deepgram"]},
    "deepgram-nova3": {"runner": run_deepgram, "kwargs": {"model": "nova-3", "diarize_model": "v2"}, "needs_env": ["DEEPGRAM_API_KEY"], "needs_import": ["deepgram"]},
    "pyannote-community1": {"runner": run_pyannote_community1, "kwargs": {}, "needs_env": ["HF_TOKEN"], "needs_import": ["pyannote.audio"]},
    "mlx-whisper-pyannote": {"runner": run_mlx_whisper_pyannote, "kwargs": {}, "needs_env": ["HF_TOKEN"], "needs_import": ["mlx_whisper", "pyannote.audio"]},
    "elevenlabs-scribe": {"runner": run_elevenlabs_scribe, "kwargs": {}, "needs_env": ["ELEVENLABS_API_KEY"], "needs_import": ["requests"]},
    "openai-diarize": {"runner": run_openai_diarize, "kwargs": {}, "needs_env": ["OPENAI_API_KEY|OPENAI_API_KEY_LOCAL"], "needs_import": ["requests"]},
    "assemblyai": {"runner": run_assemblyai, "kwargs": {}, "needs_env": ["ASSEMBLYAI_API_KEY"], "needs_import": ["requests"]},
    "pyannoteai-precision2": {"runner": run_pyannoteai_precision2, "kwargs": {}, "needs_env": ["PYANNOTEAI_API_KEY"], "needs_import": ["requests"]},
}
def backend_available(name):
    """Return (ok, reason). ok=False when a required env key or package is missing."""
    spec = BACKEND_REGISTRY.get(name)
    if spec is None:
        return False, f"unknown backend '{name}'"
    for env in spec["needs_env"]:
        if not any(os.environ.get(alt) for alt in env.split("|")):
            return False, f"missing env key {env}"
    for mod in spec["needs_import"]:
        try:
            if mod in ("mlx_whisper", "pyannote.audio"):
                if importlib.util.find_spec(mod) is None:
                    return False, f"package '{mod}' not installed"
                continue
            __import__(mod)
        except ImportError:
            return False, f"package '{mod}' not installed"
    return True, "ok"
def list_backends():
    """Availability map for all registered backends."""
    return {name: dict(zip(("available", "reason"), backend_available(name))) for name in BACKEND_REGISTRY}
def run_backend(name, audio_path, session_id, out_dir=None, **overrides):
    """Run a registered backend by id; overrides merge over registry kwargs."""
    ok, reason = backend_available(name)
    if not ok:
        raise RuntimeError(f"backend '{name}' unavailable: {reason}")
    spec = BACKEND_REGISTRY[name]
    kwargs = dict(spec["kwargs"])
    kwargs.update(overrides)
    return spec["runner"](audio_path, session_id, out_dir=out_dir, **kwargs)
