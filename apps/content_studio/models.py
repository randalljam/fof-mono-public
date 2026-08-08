# ===== START OF FILE apps/content_studio/models.py =====
# Plain data holders shared across the content studio.
#
# These are deliberately simple classes (no type hints, per repo Python style).
# They carry data between the providers, the verifiers, and the pipeline.
#
# Media kinds: "animation" (short GIF/WebP-style loop from a still image),
# "video" (text- or image-to-video clip), and "audio" (speech / music / sfx).

import json

VISUAL_KINDS = ("animation", "video")
AUDIO_KINDS = ("speech", "music", "sfx")


### Requests
class MediaRequest:
    """Base class for all generation requests.

    Common fields shared by every media kind:
    :param prompt: verbal description of what to generate.
    :param negative_prompt: text describing what to avoid (visual kinds).
    :param seed: optional int seed for reproducible generation.
    :param model: optional provider-specific model id override.
    :param extra: dict of provider/model-specific extra parameters.
    """
    media_kind = "media"
    def __init__(self, prompt="", negative_prompt="", seed=None, model=None, extra=None):
        self.prompt = prompt
        self.negative_prompt = negative_prompt
        self.seed = seed
        self.model = model
        self.extra = extra or {}
    def to_kwargs(self):
        """Return the constructor kwargs for this request (subclasses extend)."""
        return dict(prompt=self.prompt, negative_prompt=self.negative_prompt,
                    seed=self.seed, model=self.model, extra=dict(self.extra))
    def copy_with(self, **changes):
        """Return a shallow copy of this request with the given fields replaced."""
        data = self.to_kwargs()
        data.update(changes)
        return self.__class__(**data)
    @property
    def description(self):
        """The human description of the intent (what verifiers grade against)."""
        return self.prompt
    def __repr__(self):
        return f"{self.__class__.__name__}(prompt={self.prompt!r})"
class AnimationRequest(MediaRequest):
    """Turn a still image (or simple animation) into a short GIF-like loop.

    :param image_path: path to the input image/animation (png/jpg/webp/gif).
    :param prompt: verbal description of the motion to produce.
    :param duration_s: target clip length in seconds.
    :param fps: target frames per second.
    :param size: optional (width, height) tuple; None keeps the source aspect.
    """
    media_kind = "animation"
    def __init__(self, image_path, prompt, negative_prompt="", duration_s=2.0,
                 fps=12, size=None, seed=None, model=None, extra=None):
        MediaRequest.__init__(self, prompt=prompt, negative_prompt=negative_prompt,
                              seed=seed, model=model, extra=extra)
        self.image_path = image_path
        self.duration_s = duration_s
        self.fps = fps
        self.size = size
    def to_kwargs(self):
        data = MediaRequest.to_kwargs(self)
        data.update(image_path=self.image_path, duration_s=self.duration_s,
                    fps=self.fps, size=self.size)
        return data
class VideoRequest(MediaRequest):
    """Generate a video clip from text (t2v) or from a starting image (i2v).

    :param prompt: verbal description of the video.
    :param image_path: optional starting/reference image; None means text-to-video.
    :param duration_s: target clip length in seconds.
    :param resolution: provider resolution string (e.g. '480p', '720p', '1080p').
    :param aspect_ratio: aspect string for text-to-video (e.g. '16:9', '9:16').
    """
    media_kind = "video"
    def __init__(self, prompt, image_path=None, negative_prompt="", duration_s=5.0,
                 resolution="720p", aspect_ratio="16:9", seed=None, model=None,
                 extra=None):
        MediaRequest.__init__(self, prompt=prompt, negative_prompt=negative_prompt,
                              seed=seed, model=model, extra=extra)
        self.image_path = image_path
        self.duration_s = duration_s
        self.resolution = resolution
        self.aspect_ratio = aspect_ratio
    def to_kwargs(self):
        data = MediaRequest.to_kwargs(self)
        data.update(image_path=self.image_path, duration_s=self.duration_s,
                    resolution=self.resolution, aspect_ratio=self.aspect_ratio)
        return data
class AudioRequest(MediaRequest):
    """Generate audio: spoken text, music, or a sound effect.

    :param text: the words to speak (speech only).
    :param prompt: description of the sound (music / sfx; optional for speech).
    :param audio_kind: one of 'speech', 'music', 'sfx'.
    :param voice: optional provider voice id (speech).
    :param duration_s: optional target duration in seconds (music / sfx).
    """
    media_kind = "audio"
    def __init__(self, text="", prompt="", audio_kind="speech", voice=None,
                 duration_s=None, negative_prompt="", seed=None, model=None,
                 extra=None):
        if audio_kind not in AUDIO_KINDS:
            raise ValueError(f"audio_kind must be one of {AUDIO_KINDS}, got {audio_kind!r}")
        if audio_kind == "speech" and not text:
            raise ValueError("AudioRequest(audio_kind='speech') requires text.")
        if audio_kind in ("music", "sfx") and not prompt:
            raise ValueError(f"AudioRequest(audio_kind={audio_kind!r}) requires a prompt.")
        MediaRequest.__init__(self, prompt=prompt, negative_prompt=negative_prompt,
                              seed=seed, model=model, extra=extra)
        self.text = text
        self.audio_kind = audio_kind
        self.voice = voice
        self.duration_s = duration_s
    def to_kwargs(self):
        data = MediaRequest.to_kwargs(self)
        data.update(text=self.text, audio_kind=self.audio_kind, voice=self.voice,
                    duration_s=self.duration_s)
        return data
    @property
    def description(self):
        return self.text if self.audio_kind == "speech" else self.prompt
    def __repr__(self):
        return f"AudioRequest(audio_kind={self.audio_kind!r}, description={self.description!r})"

### Result
class MediaResult:
    """The output of a provider generate call (any media kind).

    A result carries EITHER an on-disk output_path (real providers) OR an
    in-memory frames list (the mock/stub visual path used offline) — audio
    results always use output_path. The codec knows how to read frames from
    whichever is present.

    :param output_path: path to the written media file, or None.
    :param frames: optional in-memory list of frame handles (visual), or None.
    :param provider: name of the provider that produced this.
    :param model: provider model id used.
    :param meta: dict of provider metadata (seed, raw response ids, etc.).
    :param request: the MediaRequest that produced this result.
    """
    def __init__(self, output_path=None, frames=None, provider="", model="",
                 meta=None, request=None):
        self.output_path = output_path
        self.frames = frames
        self.provider = provider
        self.model = model
        self.meta = meta or {}
        self.request = request
    @property
    def media_kind(self):
        """The media kind of the request that produced this (or 'media')."""
        return getattr(self.request, "media_kind", "media")
    def __repr__(self):
        n = None if self.frames is None else len(self.frames)
        return (f"MediaResult(kind={self.media_kind!r}, provider={self.provider!r}, "
                f"output_path={self.output_path!r}, frames={n})")

### Verification
class FrameIssue:
    """A single problem a verifier found in the generated media.

    :param category: short tag, e.g. 'anatomy', 'identity', 'artifact', 'motion',
                     'content', 'duration'.
    :param severity: one of 'critical', 'major', 'minor'.
    :param description: human-readable description of the problem.
    :param frame_index: index of the offending sampled frame, or None if global
                        (always None for audio).
    """
    def __init__(self, category, severity, description, frame_index=None):
        self.category = category
        self.severity = severity
        self.description = description
        self.frame_index = frame_index
    def to_dict(self):
        """Return a plain dict (for JSON serialization / reporting)."""
        return dict(category=self.category, severity=self.severity,
                    description=self.description, frame_index=self.frame_index)
    def __repr__(self):
        loc = "global" if self.frame_index is None else f"frame {self.frame_index}"
        return f"[{self.severity}/{self.category}@{loc}] {self.description}"
class VerifyResult:
    """A verifier's verdict on one candidate.

    :param passed: bool, whether the candidate clears the quality policy.
    :param score: int 0-100 overall quality score.
    :param scores: dict of per-dimension scores (anatomy/identity/... for visual,
                   similarity for speech).
    :param extra_limbs: bool, the headline 'janky extra arm' flag (visual only).
    :param issues: list of FrameIssue.
    :param summary: short text summary from the verifier.
    :param recommended_negative_prompt: text to add to the next attempt (visual).
    :param raw: the raw assessment dict / data behind the verdict.
    """
    def __init__(self, passed, score, scores=None, extra_limbs=False, issues=None,
                 summary="", recommended_negative_prompt="", raw=None):
        self.passed = passed
        self.score = score
        self.scores = scores or {}
        self.extra_limbs = extra_limbs
        self.issues = issues or []
        self.summary = summary
        self.recommended_negative_prompt = recommended_negative_prompt
        self.raw = raw or {}
    def critical_issues(self):
        """Return the list of issues marked 'critical'."""
        return [i for i in self.issues if i.severity == "critical"]
    def to_dict(self):
        """Return a plain JSON-serializable dict of the verdict."""
        return dict(
            passed=self.passed, score=self.score, scores=self.scores,
            extra_limbs=self.extra_limbs,
            issues=[i.to_dict() for i in self.issues],
            summary=self.summary,
            recommended_negative_prompt=self.recommended_negative_prompt,
        )
    def __repr__(self):
        return (f"VerifyResult(passed={self.passed}, score={self.score}, "
                f"extra_limbs={self.extra_limbs}, issues={len(self.issues)})")
class PipelineResult:
    """The final output of the generate->verify->retry pipeline.

    :param result: the best MediaResult produced.
    :param verdict: the VerifyResult for that best result.
    :param passed: bool, whether the best result cleared the policy.
    :param attempts: list of (MediaResult, VerifyResult) for every try.
    """
    def __init__(self, result, verdict, passed, attempts=None):
        self.result = result
        self.verdict = verdict
        self.passed = passed
        self.attempts = attempts or []
    @property
    def output_path(self):
        """Convenience accessor for the chosen media's file path."""
        return None if self.result is None else self.result.output_path
    def to_dict(self):
        """Return a plain JSON-serializable summary of the run."""
        return dict(
            passed=self.passed,
            output_path=self.output_path,
            attempt_count=len(self.attempts),
            verdict=None if self.verdict is None else self.verdict.to_dict(),
        )
    def to_json(self, indent=2):
        """Return the run summary as a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    def __repr__(self):
        return (f"PipelineResult(passed={self.passed}, "
                f"attempts={len(self.attempts)}, output_path={self.output_path!r})")

# ===== END OF FILE apps/content_studio/models.py =====
