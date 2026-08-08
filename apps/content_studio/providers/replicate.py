# ===== START OF FILE apps/content_studio/providers/replicate.py =====
# Replicate provider: video, animation, and audio generation.
#
# Replicate is one of the two primary aggregators this studio targets (the other
# is fal). One predictions API covers every hosted model: create a prediction
# against owner/name, poll its get URL, download the output. Defaults: Seedance
# 2.0 for video/animation, MiniMax Speech-02 HD for TTS, MusicGen for music.
#
# Auth: set REPLICATE_API_TOKEN in the environment (or pass api_key=).
# Docs: https://replicate.com/docs/reference/http  (each model page lists its
# input schema — use request.extra for fields beyond the common ones sent here).

import os
import time

from apps.content_studio import config
from apps.content_studio.models import MediaResult
from apps.content_studio.providers.base import (
    MediaProvider, ProviderError, file_data_uri, extract_output_url,
    download_to_file, output_stem,
)

API_BASE = "https://api.replicate.com/v1"


### Prediction runner
def run_replicate_job(model, input_data, api_key=None, poll_timeout=600,
                      poll_interval=3):
    """Create a Replicate prediction, poll to completion, and return its output.

    :param model: 'owner/name' model slug (e.g. 'bytedance/seedance-2.0').
    :param input_data: dict, the model input.
    :param api_key: Replicate token; resolved from REPLICATE_API_TOKEN if omitted.
    :param poll_timeout: max seconds to wait.
    :param poll_interval: seconds between polls.
    :return: the prediction's `output` field (string, list, or dict).
    :raises ProviderError: on missing key, failed prediction, or timeout.
    """
    import requests

    key = api_key or os.environ.get("REPLICATE_API_TOKEN")
    if not key:
        raise ProviderError("Replicate needs an API key (set REPLICATE_API_TOKEN).")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    create = requests.post(f"{API_BASE}/models/{model}/predictions",
                           headers=headers, json={"input": input_data}, timeout=60)
    create.raise_for_status()
    pred = create.json()
    get_url = (pred.get("urls") or {}).get("get")
    if not get_url:
        raise ProviderError(f"Unexpected Replicate create response: {pred}")

    deadline = time.time() + poll_timeout
    while time.time() < deadline:
        status = pred.get("status")
        if status == "succeeded":
            return pred.get("output")
        if status in ("failed", "canceled"):
            raise ProviderError(f"Replicate prediction {status}: {pred.get('error')}")
        time.sleep(poll_interval)
        r = requests.get(get_url, headers=headers, timeout=30)
        r.raise_for_status()
        pred = r.json()
    raise ProviderError(f"Replicate prediction for {model} timed out after {poll_timeout}s.")

### Replicate provider
class ReplicateProvider(MediaProvider):
    """Generate video, animation, and audio via Replicate models.

    :param output_dir: directory to write downloaded media into.
    :param api_key: Replicate token; resolved from REPLICATE_API_TOKEN if omitted.
    :param poll_timeout / poll_interval: polling controls in seconds.
    :param video_model / animation_model / speech_model / music_model /
           sfx_model: per-kind model slug overrides (defaults from config;
           request.model overrides these per call).
    """
    name = "replicate"
    def __init__(self, output_dir=None, api_key=None, poll_timeout=600,
                 poll_interval=3, video_model=None, animation_model=None,
                 speech_model=None, music_model=None, sfx_model=None):
        self.output_dir = output_dir or config.DEFAULT_OUTPUT_DIR
        self.api_key = api_key or os.environ.get("REPLICATE_API_TOKEN")
        self.poll_timeout = poll_timeout
        self.poll_interval = poll_interval
        self.video_model = video_model or config.REPLICATE_VIDEO_MODEL
        self.animation_model = animation_model or config.REPLICATE_ANIMATION_MODEL
        self.speech_model = speech_model or config.REPLICATE_SPEECH_MODEL
        self.music_model = music_model or config.REPLICATE_MUSIC_MODEL
        self.sfx_model = sfx_model or config.REPLICATE_SFX_MODEL
    def _run(self, model, input_data):
        return run_replicate_job(model, input_data, api_key=self.api_key,
                                 poll_timeout=self.poll_timeout,
                                 poll_interval=self.poll_interval)
    def _finish(self, request, model, output, default_ext):
        """Extract the output URL, download it, and wrap it in a MediaResult."""
        url = extract_output_url(output)
        if not url:
            raise ProviderError(f"No output URL in Replicate result for {model}: {output}")
        ext = os.path.splitext(url.split("?")[0])[1] or default_ext
        path = os.path.join(self.output_dir, f"{output_stem(request, self.name)}{ext}")
        download_to_file(url, path)
        return MediaResult(output_path=path, provider=self.name, model=model,
                           request=request, meta={"output_url": url})
    def generate_animation(self, request):
        """Short image-to-video loop; the CLI converts the clip to GIF/WebP."""
        model = request.model or self.animation_model
        input_data = {
            "prompt": request.prompt,
            "image": file_data_uri(request.image_path),
        }
        _put_common(input_data, request)
        input_data.update(request.extra)
        return self._finish(request, model, self._run(model, input_data), ".mp4")
    def generate_video(self, request):
        """Text-to-video or (with image_path) image-to-video."""
        model = request.model or self.video_model
        input_data = {"prompt": request.prompt}
        if request.image_path:
            input_data["image"] = file_data_uri(request.image_path)
        if request.duration_s:
            input_data["duration"] = int(round(request.duration_s))
        if request.resolution:
            input_data["resolution"] = request.resolution
        if request.aspect_ratio and not request.image_path:
            input_data["aspect_ratio"] = request.aspect_ratio
        _put_common(input_data, request)
        input_data.update(request.extra)
        return self._finish(request, model, self._run(model, input_data), ".mp4")
    def generate_audio(self, request):
        """Speech (TTS), music, or sound effects, by request.audio_kind."""
        kind = request.audio_kind
        if kind == "speech":
            model = request.model or self.speech_model
            input_data = {"text": request.text}
            if request.voice:
                input_data["voice_id"] = request.voice
        else:  # music / sfx (sfx default model is prompted music-gen)
            model = request.model or (self.music_model if kind == "music"
                                      else self.sfx_model)
            input_data = {"prompt": request.prompt}
            if request.duration_s:
                input_data["duration"] = int(round(request.duration_s))
        if request.seed is not None:
            input_data["seed"] = request.seed
        input_data.update(request.extra)
        return self._finish(request, model, self._run(model, input_data), ".mp3")

### Helpers
def _put_common(input_data, request):
    """Fold the common visual fields (negative prompt, seed) into an input."""
    if request.negative_prompt:
        input_data["negative_prompt"] = request.negative_prompt
    if request.seed is not None:
        input_data["seed"] = request.seed

# ===== END OF FILE apps/content_studio/providers/replicate.py =====
