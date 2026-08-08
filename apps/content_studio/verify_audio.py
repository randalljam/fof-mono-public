# ===== START OF FILE apps/content_studio/verify_audio.py =====
# The audio verifier: decide whether a generated audio file is good.
#
# Speech gets the strongest check: transcribe the output (fal-hosted Whisper by
# default, same FAL_KEY as generation) and compare the transcript against the
# requested text — a garbled, truncated, or wrong-words render fails. Music and
# sound effects get structural checks (file exists, non-trivial, duration within
# tolerance when one was requested); content-level judgement of music is a
# roadmap item (needs an audio-understanding model).
#
# Mirrors verify.py's split: IO at the edges, a pure audio_policy() in the middle
# so the decision rules are unit-testable without audio files or a network.

import os
import re
import unicodedata
from difflib import SequenceMatcher

from apps.content_studio import config
from apps.content_studio.models import FrameIssue, VerifyResult

AUDIO_EXTS = (".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac", ".opus", ".webm")


### Pure helpers
def normalize_text(text):
    """Normalize text for transcript comparison.

    Case-folds, removes accent marks and punctuation, preserves letters and
    digits from every script, and collapses whitespace. This keeps the
    comparison robust to punctuation/casing/diacritics without turning
    non-Latin text into an empty string.

    :param text: input string.
    :return: normalized string.
    """
    text = unicodedata.normalize("NFKD", (text or "").casefold())
    text = "".join(
        "" if unicodedata.combining(char)
        else char if char.isalnum() or char.isspace()
        else " "
        for char in text
    )
    return re.sub(r"\s+", " ", text).strip()
def text_similarity(expected, actual):
    """Similarity ratio between expected text and a transcript, 0.0-1.0.

    :param expected: the text that was supposed to be spoken.
    :param actual: the transcript of what was actually rendered.
    :return: float in [0, 1].
    """
    a, b = normalize_text(expected), normalize_text(actual)
    if not a and not b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()
def wav_duration_s(path):
    """Duration in seconds for a .wav file; None for other/unreadable formats.

    Uses only the stdlib wave module — mp3/m4a duration is skipped rather than
    pulling in an audio dependency (the policy treats unknown duration as
    'cannot check', not as a failure).

    :param path: path to an audio file.
    :return: float seconds, or None.
    """
    if os.path.splitext(path)[1].lower() != ".wav":
        return None
    try:
        import wave
        with wave.open(path, "rb") as w:
            rate = w.getframerate()
            return w.getnframes() / float(rate) if rate else None
    except Exception:
        return None

### Policy
def audio_policy(audio_kind, similarity=None, transcript="", min_similarity=None,
                 duration_s=None, expected_duration_s=None,
                 duration_tolerance_s=None, transcription_available=True,
                 require_transcription=False, file_ok=True):
    """Turn audio measurements into a pass/fail VerifyResult. Pure Python.

    Rules:
      - a missing/empty output file is a critical fail;
      - speech with a measured similarity below min_similarity is a critical fail
        (wrong/garbled words is the audio equivalent of the janky extra arm);
      - speech that cannot be transcribed fails only if require_transcription,
        otherwise it passes structurally with a 'content unverified' minor issue;
      - a measurable duration more than duration_tolerance_s away from an
        explicitly requested duration is a major fail.

    :param audio_kind: 'speech', 'music', or 'sfx'.
    :param similarity: float 0-1 transcript similarity, or None if not measured.
    :param transcript: the transcript text (for reporting).
    :param min_similarity: pass floor for similarity (default from config).
    :param duration_s: measured duration in seconds, or None if unknown.
    :param expected_duration_s: requested duration, or None if unconstrained.
    :param duration_tolerance_s: allowed |actual-requested| gap (default config).
    :param transcription_available: whether a transcriber was available.
    :param require_transcription: fail speech outright when unverifiable.
    :param file_ok: whether the output file exists and is non-empty.
    :return: a VerifyResult.
    """
    min_similarity = config.MIN_SPEECH_SIMILARITY if min_similarity is None else min_similarity
    duration_tolerance_s = (config.AUDIO_DURATION_TOLERANCE_S
                            if duration_tolerance_s is None else duration_tolerance_s)
    issues = []
    scores = {}
    passed = True

    if not file_ok:
        issues.append(FrameIssue("output", "critical", "audio file missing or empty"))
        passed = False

    if similarity is not None:
        scores["similarity"] = round(similarity, 3)
        if similarity < min_similarity:
            issues.append(FrameIssue(
                "content", "critical",
                f"transcript does not match the requested text "
                f"(similarity {similarity:.2f} < {min_similarity:.2f}); "
                f"heard: {transcript[:200]!r}"))
            passed = False
    elif audio_kind == "speech":
        if require_transcription:
            issues.append(FrameIssue(
                "content", "critical",
                "speech could not be transcription-verified and "
                "require_transcription is set"))
            passed = False
        elif not transcription_available:
            issues.append(FrameIssue(
                "content", "minor",
                "no transcriber available — spoken content is unverified"))

    if (duration_s is not None and expected_duration_s
            and abs(duration_s - expected_duration_s) > duration_tolerance_s):
        issues.append(FrameIssue(
            "duration", "major",
            f"duration {duration_s:.1f}s is outside ±{duration_tolerance_s}s of "
            f"the requested {expected_duration_s:.1f}s"))
        passed = False

    if similarity is not None:
        score = int(round(similarity * 100)) if passed else min(
            int(round(similarity * 100)), 40)
    else:
        score = 75 if passed else 0
    summary_bits = [f"{audio_kind} audio"]
    if similarity is not None:
        summary_bits.append(f"transcript similarity {similarity:.2f}")
    if duration_s is not None:
        summary_bits.append(f"duration {duration_s:.1f}s")
    summary = ("PASS: " if passed else "FAIL: ") + ", ".join(summary_bits)

    return VerifyResult(passed=passed, score=score, scores=scores, issues=issues,
                        summary=summary,
                        raw=dict(similarity=similarity, transcript=transcript,
                                 duration_s=duration_s))

### Audio verifier
class AudioVerifier:
    """Verifies audio MediaResults: transcription check for speech, structural
    checks for everything.

    :param transcriber: callable(path) -> transcript string; "auto" resolves a
                        fal-Whisper transcriber when FAL_KEY is set (else None);
                        pass None to skip transcription entirely.
    :param min_similarity: transcript similarity pass floor (default config).
    :param require_transcription: fail speech that cannot be transcribed.
    :param duration_tolerance_s: allowed duration gap (default from config).
    """
    def __init__(self, transcriber="auto", min_similarity=None,
                 require_transcription=False, duration_tolerance_s=None):
        self._transcriber = transcriber
        self.min_similarity = min_similarity
        self.require_transcription = require_transcription
        self.duration_tolerance_s = duration_tolerance_s
    def _resolve_transcriber(self):
        if self._transcriber == "auto":
            self._transcriber = default_transcriber()
        return self._transcriber
    def assess(self, result, request):
        """Grade one generated audio candidate.

        :param result: a MediaResult with an output_path.
        :param request: the AudioRequest that produced it.
        :return: a VerifyResult.
        """
        path = getattr(result, "output_path", None)
        file_ok = bool(path) and os.path.exists(path) and os.path.getsize(path) > 0
        duration = wav_duration_s(path) if file_ok else None

        similarity = None
        transcript = ""
        transcriber = self._resolve_transcriber()
        if file_ok and request.audio_kind == "speech" and transcriber is not None:
            transcript = str(transcriber(path) or "")
            similarity = text_similarity(request.text, transcript)

        return audio_policy(
            audio_kind=request.audio_kind, similarity=similarity,
            transcript=transcript, min_similarity=self.min_similarity,
            duration_s=duration, expected_duration_s=request.duration_s,
            duration_tolerance_s=self.duration_tolerance_s,
            transcription_available=transcriber is not None,
            require_transcription=self.require_transcription, file_ok=file_ok,
        )

### Default transcriber (fal-hosted Whisper)
def default_transcriber(api_key=None, model=None):
    """Return a callable(path) -> transcript using fal's Whisper, or None.

    Uses the same FAL_KEY as generation so speech verification needs no extra
    account. Returns None when no key is configured (the policy then reports
    speech as structurally-passed-but-unverified unless require_transcription).

    :param api_key: optional FAL key (else FAL_KEY env var).
    :param model: optional transcription model id (default config.TRANSCRIBER_MODEL).
    :return: a transcriber callable, or None.
    """
    key = api_key or os.environ.get("FAL_KEY")
    if not key:
        return None
    model = model or config.TRANSCRIBER_MODEL
    def transcribe(path):
        from apps.content_studio.providers.base import file_data_uri
        from apps.content_studio.providers.fal import run_fal_job
        body = run_fal_job(model, {"audio_url": file_data_uri(path)}, api_key=key)
        return str((body or {}).get("text", ""))
    return transcribe

# ===== END OF FILE apps/content_studio/verify_audio.py =====
