# ===== START OF FILE apps/content_studio/verify.py =====
# The visual verifier: look at a finished animation/video and decide if it is good.
#
# Two layers, deliberately separated so the decision logic is testable without a
# live model:
#   1. an "asker" callable turns (reference image, sampled frames, description)
#      into a raw assessment dict. The default asker uses a Claude vision model;
#      tests inject a fake asker.
#   2. apply_policy() turns that raw assessment into a pass/fail VerifyResult
#      using fixed, inspectable thresholds (this is pure Python).
#
# Audio verification lives in verify_audio.py.

import json

from apps.content_studio import config
from apps.content_studio.frames import evenly_spaced_indices
from apps.content_studio.models import FrameIssue, VerifyResult
from apps.content_studio.prompts import VERIFIER_SYSTEM_PROMPT, VERIFIER_TOOL


### Coercion helpers
def _as_dict(value):
    """Coerce a mapping-like or JSON-object string into a plain dict.

    Vision tool payloads occasionally return nested objects as JSON strings
    (notably `scores`). Calling dict() on a string raises ValueError
    ("dictionary update sequence element #0 has length 1"), so normalize first.
    Non-mapping values become {}.
    """
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except Exception:
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}
    try:
        return dict(value)
    except Exception:
        return {}
def _as_issue_dict(item):
    """Coerce one issues[] entry into a dict; skip unusable shapes."""
    if isinstance(item, dict):
        return item
    if isinstance(item, str):
        text = item.strip()
        if not text:
            return None
        try:
            parsed = json.loads(text)
        except Exception:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None
def _as_issue_items(value):
    """Coerce issues into a list, including JSON-string list/object payloads."""
    if isinstance(value, str):
        if not value.strip():
            return []
        try:
            value = json.loads(value.strip())
        except Exception:
            return [value]
    if isinstance(value, dict):
        return [value]
    if isinstance(value, (list, tuple)):
        return value
    return [] if value is None else [value]
def _as_int(value, default=0):
    """Coerce model-provided integer-like values without raising."""
    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return default
def _as_bool(value, default=False):
    """Coerce booleans and common JSON-like boolean strings."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("true", "1", "yes"):
            return True
        if normalized in ("false", "0", "no", ""):
            return False
        return default
    if value is None:
        return default
    return bool(value)

### Policy
def apply_policy(raw, accept_score=None, min_anatomy=None, min_identity=None,
                 min_temporal=None):
    """Turn a raw assessment dict into a pass/fail VerifyResult.

    The policy is intentionally strict and rule-based rather than trusting the
    model's own overall_pass: a candidate fails if it trips ANY hard gate, even
    if the model called it shippable.

    Hard fail if any of:
      - extra_limbs_detected is true (the headline 'janky arm' case);
      - any issue has severity 'critical';
      - anatomy score < min_anatomy;
      - identity score < min_identity;
      - temporal score < min_temporal.
    Otherwise pass if overall_score >= accept_score.

    :param raw: dict matching the report_animation_quality tool schema.
    :param accept_score: overall_score threshold (default from config).
    :param min_anatomy: anatomy floor (default from config).
    :param min_identity: identity floor (default from config).
    :param min_temporal: temporal floor (default from config).
    :return: a VerifyResult.
    """
    accept_score = config.ACCEPT_SCORE if accept_score is None else accept_score
    min_anatomy = config.MIN_ANATOMY if min_anatomy is None else min_anatomy
    min_identity = config.MIN_IDENTITY if min_identity is None else min_identity
    min_temporal = config.MIN_TEMPORAL if min_temporal is None else min_temporal

    raw = _as_dict(raw)
    scores = _as_dict(raw.get("scores"))
    overall = _as_int(raw.get("overall_score", 0))
    extra_limbs = _as_bool(
        raw.get("extra_limbs_detected", False), default=True)

    issues = []
    for item in _as_issue_items(raw.get("issues")):
        item = _as_issue_dict(item)
        if item is None:
            issues.append(FrameIssue(
                "verifier", "critical",
                "verifier returned an unparseable issue entry"))
            continue
        issues.append(FrameIssue(
            category=str(item.get("category", "unknown")),
            severity=str(item.get("severity", "minor")).strip().lower() or "minor",
            description=str(item.get("description", "")),
            frame_index=item.get("frame_index"),
        ))

    anatomy = _as_int(scores.get("anatomy", 0))
    identity = _as_int(scores.get("identity", 0))
    temporal = _as_int(scores.get("temporal", 0))
    has_critical = any(i.severity == "critical" for i in issues)

    passed = True
    if extra_limbs:
        passed = False
    if has_critical:
        passed = False
    if anatomy < min_anatomy:
        passed = False
    if identity < min_identity:
        passed = False
    if temporal < min_temporal:
        passed = False
    if overall < accept_score:
        passed = False

    return VerifyResult(
        passed=passed,
        score=overall,
        scores=scores,
        extra_limbs=extra_limbs,
        issues=issues,
        summary=str(raw.get("summary", "")),
        recommended_negative_prompt=str(raw.get("recommended_negative_prompt", "")),
        raw=raw,
    )

### Visual verifier
class VisualVerifier:
    """Frame-sampling + asker + policy for animation and video candidates.

    :param asker: callable(reference_b64_or_None, frames_b64, description) -> raw
                  dict. Defaults to the Claude vision asker.
    :param codec: object with read_frames / frame_png_b64 / image_png_b64;
                  defaults to imaging.FileCodec (lazy — needs Pillow).
    :param sample_frames: how many frames to sample per candidate.
    :param accept_score / min_anatomy / min_identity / min_temporal: policy
                  thresholds; None means use config defaults.
    """
    def __init__(self, asker=None, codec=None, sample_frames=None,
                 accept_score=None, min_anatomy=None, min_identity=None,
                 min_temporal=None):
        self.asker = asker or anthropic_vision_asker
        self._codec = codec
        self.sample_frames = sample_frames or config.DEFAULT_SAMPLE_FRAMES
        self.accept_score = accept_score
        self.min_anatomy = min_anatomy
        self.min_identity = min_identity
        self.min_temporal = min_temporal
    @property
    def codec(self):
        """The frame codec, constructed lazily so Pillow stays optional."""
        if self._codec is None:
            from apps.content_studio.imaging import FileCodec
            self._codec = FileCodec()
        return self._codec
    def assess(self, result, request):
        """Sample frames from a generated clip and grade it.

        :param result: a MediaResult from a provider.
        :param request: the request that produced it (image_path may be absent
                        or None for text-to-video).
        :return: a VerifyResult.
        """
        image_path = getattr(request, "image_path", None)
        reference_b64 = self.codec.image_png_b64(image_path) if image_path else None
        frames = self.codec.read_frames(result)
        if not frames:
            return VerifyResult(
                passed=False,
                score=0,
                issues=[FrameIssue(
                    "output", "critical",
                    "visual candidate contained no decodable frames")],
                summary="FAIL: visual candidate contained no decodable frames",
            )
        indices = evenly_spaced_indices(len(frames), self.sample_frames)
        frames_b64 = [self.codec.frame_png_b64(frames[i]) for i in indices]
        return self.verify(reference_b64, frames_b64, request.description)
    def verify(self, reference_b64, frames_b64, description):
        """Grade pre-encoded frames directly (assess() is the usual entry point).

        :param reference_b64: raw base64 PNG of the reference image, or None.
        :param frames_b64: list of raw base64 PNG strings, sampled frames in order.
        :param description: the verbal description of the intended clip.
        :return: a VerifyResult.
        """
        raw = self.asker(reference_b64, frames_b64, description)
        return apply_policy(
            raw, accept_score=self.accept_score, min_anatomy=self.min_anatomy,
            min_identity=self.min_identity, min_temporal=self.min_temporal,
        )

### Default asker (Claude vision)
def _image_block(b64):
    """Build an Anthropic image content block from raw base64 PNG data."""
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/png", "data": b64},
    }
def anthropic_vision_asker(reference_b64, frames_b64, description, model=None,
                           api_key=None, max_tokens=2048):
    """Default asker: ask a Claude vision model to grade the clip.

    Sends the reference image (when present) plus each sampled output frame, and
    forces a call to the report_animation_quality tool so the reply is always
    structured.

    :param reference_b64: raw base64 PNG of the reference image, or None (t2v).
    :param frames_b64: list of raw base64 PNG strings (sampled frames, in order).
    :param description: the verbal description of the intended clip.
    :param model: optional model id override (default config.VERIFIER_MODEL).
    :param api_key: optional Anthropic API key (resolved from env otherwise).
    :param max_tokens: response token cap.
    :return: the raw assessment dict (the tool input).
    :raises RuntimeError: if no API key is configured or no tool call comes back.
    """
    import anthropic

    model = model or config.VERIFIER_MODEL
    key = config.resolve_anthropic_api_key(api_key)
    if not key:
        raise RuntimeError(
            "No Anthropic API key found. Set ANTHROPIC_API_KEY (or "
            "ANTHROPIC_API_KEY_LOCAL), or pass a custom asker to the VisualVerifier."
        )
    client = anthropic.Anthropic(api_key=key)

    content = []
    if reference_b64:
        content.append({"type": "text", "text":
            "REFERENCE IMAGE (the original character/scene; the clip must preserve "
            "this identity and anatomy):"})
        content.append(_image_block(reference_b64))
    else:
        content.append({"type": "text", "text":
            "No reference image was provided (text-to-video). Judge identity as "
            "internal consistency across the frames."})
    content.append({"type": "text", "text":
        f"INTENDED CLIP (verbal description): {description}"})
    content.append({"type": "text", "text":
        f"The {len(frames_b64)} OUTPUT FRAMES below were sampled in order from "
        "the generated clip. Inspect each one and grade the clip."})
    for i, fb in enumerate(frames_b64):
        content.append({"type": "text", "text": f"Output frame index {i}:"})
        content.append(_image_block(fb))

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=VERIFIER_SYSTEM_PROMPT,
        tools=[VERIFIER_TOOL],
        tool_choice={"type": "tool", "name": VERIFIER_TOOL["name"]},
        messages=[{"role": "user", "content": content}],
    )
    for block in response.content:
        if getattr(block, "type", None) == "tool_use":
            return _as_dict(block.input)
    raise RuntimeError("Verifier model did not return a structured tool call.")

# ===== END OF FILE apps/content_studio/verify.py =====
