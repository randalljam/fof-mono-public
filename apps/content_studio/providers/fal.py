# ===== START OF FILE apps/content_studio/providers/fal.py =====
# fal.ai provider: video, animation, and audio generation.
#
# fal is one of the two primary aggregators this studio targets (the other is
# Replicate). One queue API covers every hosted model: submit to
# queue.fal.run/{model}, poll the returned status_url, fetch the result. That
# uniformity is why a single provider class can serve Seedance video, GIF-scale
# animation loops, MiniMax speech, Lyria music, and ElevenLabs sound effects.
#
# Auth: set FAL_KEY in the environment (or pass api_key=).
# Docs: https://fal.ai/models  (each model page lists its exact input schema —
# use request.extra for fields beyond the common ones sent here).

import os
import time

from apps.content_studio import config
from apps.content_studio.models import MediaResult
from apps.content_studio.providers.base import (
    MediaProvider, ProviderError, file_data_uri, extract_output_url,
    download_to_file, output_stem,
)

QUEUE_BASE = "https://queue.fal.run"


### Queue-job runner (module-level so the audio verifier's transcriber reuses it)
def run_fal_job(model, payload, api_key=None, poll_timeout=600, poll_interval=3):
    """Submit a fal queue job, poll to completion, and return the result body.

    :param model: fal model id (e.g. 'bytedance/seedance-2.0/text-to-video').
    :param payload: dict, the model input.
    :param api_key: FAL key; resolved from FAL_KEY env var if omitted.
    :param poll_timeout: max seconds to wait for the job.
    :param poll_interval: seconds between status polls.
    :return: the parsed JSON result body.
    :raises ProviderError: on missing key, failed job, or timeout.
    """
    import requests

    key = api_key or os.environ.get("FAL_KEY")
    if not key:
        raise ProviderError("fal needs an API key (set FAL_KEY).")
    headers = {"Authorization": f"Key {key}", "Content-Type": "application/json"}

    submit = requests.post(f"{QUEUE_BASE}/{model}", headers=headers, json=payload,
                           timeout=60)
    submit.raise_for_status()
    job = submit.json()
    status_url = job.get("status_url")
    response_url = job.get("response_url")
    if not status_url or not response_url:
        raise ProviderError(f"Unexpected fal submit response: {job}")

    deadline = time.time() + poll_timeout
    while time.time() < deadline:
        r = requests.get(status_url, headers=headers, timeout=30)
        r.raise_for_status()
        status = r.json().get("status")
        if status == "COMPLETED":
            got = requests.get(response_url, headers=headers, timeout=60)
            got.raise_for_status()
            return got.json()
        if status in ("FAILED", "ERROR", "CANCELLED"):
            raise ProviderError(f"fal job ended with status {status}: {r.json()}")
        time.sleep(poll_interval)
    raise ProviderError(f"fal job for {model} timed out after {poll_timeout}s.")

### fal provider
class FalProvider(MediaProvider):
    """Generate video, animation, and audio via fal.ai models.

    :param output_dir: directory to write downloaded media into.
    :param api_key: FAL key; resolved from FAL_KEY env var if omitted.
    :param poll_timeout / poll_interval: queue polling controls in seconds.
    :param animation_model / video_model_t2v / video_model_i2v /
           speech_model / music_model / sfx_model: per-kind model id overrides
           (defaults from config; request.model overrides these per call).
    """
    name = "fal"
    def __init__(self, output_dir=None, api_key=None, poll_timeout=600,
                 poll_interval=3, animation_model=None, video_model_t2v=None,
                 video_model_i2v=None, speech_model=None, music_model=None,
                 sfx_model=None):
        self.output_dir = output_dir or config.DEFAULT_OUTPUT_DIR
        self.api_key = api_key or os.environ.get("FAL_KEY")
        self.poll_timeout = poll_timeout
        self.poll_interval = poll_interval
        self.animation_model = animation_model or config.FAL_ANIMATION_MODEL
        self.video_model_t2v = video_model_t2v or config.FAL_VIDEO_MODEL_T2V
        self.video_model_i2v = video_model_i2v or config.FAL_VIDEO_MODEL_I2V
        self.speech_model = speech_model or config.FAL_SPEECH_MODEL
        self.music_model = music_model or config.FAL_MUSIC_MODEL
        self.sfx_model = sfx_model or config.FAL_SFX_MODEL
    def _run(self, model, payload):
        return run_fal_job(model, payload, api_key=self.api_key,
                           poll_timeout=self.poll_timeout,
                           poll_interval=self.poll_interval)
    def _finish(self, request, model, body, default_ext):
        """Extract the output URL, download it, and wrap it in a MediaResult."""
        url = extract_output_url(body)
        if not url:
            raise ProviderError(f"No output URL in fal result for {model}: {body}")
        ext = os.path.splitext(url.split("?")[0])[1] or default_ext
        path = os.path.join(self.output_dir, f"{output_stem(request, self.name)}{ext}")
        download_to_file(url, path)
        return MediaResult(output_path=path, provider=self.name, model=model,
                           request=request, meta={"output_url": url})
    def generate_animation(self, request):
        """Short image-to-video loop; the CLI converts the clip to GIF/WebP."""
        model = request.model or self.animation_model
        payload = {
            "image_url": file_data_uri(request.image_path),
            "prompt": request.prompt,
        }
        _put_common(payload, request)
        payload.update(request.extra)
        return self._finish(request, model, self._run(model, payload), ".mp4")
    def generate_video(self, request):
        """Text-to-video or (with image_path) image-to-video."""
        i2v = bool(request.image_path)
        model = request.model or (self.video_model_i2v if i2v else self.video_model_t2v)
        payload = {"prompt": request.prompt}
        if i2v:
            payload["image_url"] = file_data_uri(request.image_path)
        if request.duration_s:
            payload["duration"] = int(round(request.duration_s))
        if request.resolution:
            payload["resolution"] = request.resolution
        if request.aspect_ratio and not i2v:
            payload["aspect_ratio"] = request.aspect_ratio
        _put_common(payload, request)
        payload.update(request.extra)
        return self._finish(request, model, self._run(model, payload), ".mp4")
    def generate_audio(self, request):
        """Speech (TTS), music, or sound effects, by request.audio_kind."""
        kind = request.audio_kind
        if kind == "speech":
            model = request.model or self.speech_model
            payload = {"text": request.text}
            if request.voice:
                payload["voice_setting"] = {"voice_id": request.voice}
        elif kind == "sfx":
            model = request.model or self.sfx_model
            payload = {"text": request.prompt}
            if request.duration_s:
                payload["duration_seconds"] = request.duration_s
        else:  # music
            model = request.model or self.music_model
            payload = {"prompt": request.prompt}
        if request.seed is not None:
            payload["seed"] = request.seed
        payload.update(request.extra)
        return self._finish(request, model, self._run(model, payload), ".mp3")

### Helpers
def _put_common(payload, request):
    """Fold the common visual fields (negative prompt, seed) into a payload."""
    if request.negative_prompt:
        payload["negative_prompt"] = request.negative_prompt
    if request.seed is not None:
        payload["seed"] = request.seed

# ===== END OF FILE apps/content_studio/providers/fal.py =====
