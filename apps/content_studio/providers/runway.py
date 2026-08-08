# ===== START OF FILE apps/content_studio/providers/runway.py =====
# Runway provider: image-to-video (animation and video kinds).
#
# Optional third backend alongside the two primary aggregators (fal, Replicate).
# Runway's Gen-4 models are strong at coherent character motion. Image-driven
# only: both media kinds here require a source image (no t2v on this endpoint,
# and no audio).
#
# Auth: set RUNWAYML_API_SECRET in the environment (or pass api_key=).
# Docs: https://docs.dev.runwayml.com

import os
import time

from apps.content_studio import config
from apps.content_studio.models import MediaResult
from apps.content_studio.providers.base import (
    MediaProvider, ProviderError, file_data_uri, download_to_file, output_stem,
)

API_BASE = "https://api.dev.runwayml.com/v1"
API_VERSION = "2024-11-06"
DEFAULT_RUNWAY_MODEL = "gen4_turbo"


### Runway provider
class RunwayProvider(MediaProvider):
    """Generate clips via Runway's image_to_video endpoint.

    :param output_dir: directory to write the downloaded clip into.
    :param model: Runway model id ('gen4_turbo', 'gen3a_turbo', ...).
    :param api_key: Runway secret; resolved from RUNWAYML_API_SECRET if omitted.
    :param ratio: output aspect ratio string Runway expects (e.g. '1280:720').
    :param poll_timeout / poll_interval: polling controls in seconds.
    """
    name = "runway"
    def __init__(self, output_dir=None, model=None, api_key=None,
                 ratio="1280:720", poll_timeout=600, poll_interval=4):
        self.output_dir = output_dir or config.DEFAULT_OUTPUT_DIR
        self.model = model or DEFAULT_RUNWAY_MODEL
        self.api_key = api_key or os.environ.get("RUNWAYML_API_SECRET")
        self.ratio = ratio
        self.poll_timeout = poll_timeout
        self.poll_interval = poll_interval
    def _headers(self):
        if not self.api_key:
            raise ProviderError("RunwayProvider needs an API key (set RUNWAYML_API_SECRET).")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-Runway-Version": API_VERSION,
            "Content-Type": "application/json",
        }
    def _payload(self, request):
        duration_s = getattr(request, "duration_s", 5) or 5
        duration = 10 if duration_s > 7 else 5  # Runway accepts 5 or 10
        payload = {
            "model": request.model or self.model,
            "promptImage": file_data_uri(request.image_path),
            "promptText": request.prompt,
            "duration": duration,
            "ratio": request.extra.get("ratio", self.ratio),
        }
        if request.seed is not None:
            payload["seed"] = request.seed
        for k, v in request.extra.items():
            if k != "ratio":
                payload[k] = v
        return payload
    def generate_animation(self, request):
        """Short image-to-video loop; the CLI converts the clip to GIF/WebP."""
        return self._generate_i2v(request)
    def generate_video(self, request):
        """Image-to-video clip. Runway's endpoint requires a source image."""
        return self._generate_i2v(request)
    def _generate_i2v(self, request):
        """Create the task, poll until SUCCEEDED, and download the output."""
        import requests

        if not getattr(request, "image_path", None):
            raise ProviderError(
                "RunwayProvider is image-to-video only — provide an image_path "
                "(use fal or replicate for text-to-video).")
        create = requests.post(
            f"{API_BASE}/image_to_video", headers=self._headers(),
            json=self._payload(request), timeout=60,
        )
        create.raise_for_status()
        task_id = create.json().get("id")
        if not task_id:
            raise ProviderError(f"Unexpected Runway create response: {create.json()}")

        url = self._poll(requests, task_id)
        ext = os.path.splitext(url.split("?")[0])[1] or ".mp4"
        path = os.path.join(self.output_dir, f"{output_stem(request, self.name)}{ext}")
        download_to_file(url, path)
        return MediaResult(
            output_path=path, provider=self.name,
            model=request.model or self.model, request=request,
            meta={"runway_task_id": task_id, "output_url": url},
        )
    def _poll(self, requests, task_id):
        """Poll the task until SUCCEEDED and return the first output URL."""
        deadline = time.time() + self.poll_timeout
        while time.time() < deadline:
            r = requests.get(f"{API_BASE}/tasks/{task_id}", headers=self._headers(),
                             timeout=30)
            r.raise_for_status()
            body = r.json()
            status = body.get("status")
            if status == "SUCCEEDED":
                outputs = body.get("output") or []
                if not outputs:
                    raise ProviderError(f"Runway task succeeded but had no output: {body}")
                return outputs[0]
            if status in ("FAILED", "CANCELLED"):
                raise ProviderError(f"Runway task {status}: {body.get('failure')}")
            time.sleep(self.poll_interval)
        raise ProviderError("Runway task timed out.")

# ===== END OF FILE apps/content_studio/providers/runway.py =====
