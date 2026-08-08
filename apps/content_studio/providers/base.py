# ===== START OF FILE apps/content_studio/providers/base.py =====
# Provider abstraction for media generation (animation / video / audio).
#
# A provider takes a MediaRequest and returns a MediaResult. Concrete providers
# wrap external generation APIs (fal, Replicate, Runway, ...) or, in the case of
# MockProvider, synthesize media locally for offline use.
#
# Capability dispatch: generate(request) routes to generate_<media_kind>() on the
# provider. A provider supports a media kind by implementing that method; asking
# for an unimplemented kind raises ProviderError with a clear message.

import os
import base64
from abc import ABC


### Base class
class MediaProvider(ABC):
    """Base class for all media generators.

    Subclasses set a unique `name` and implement one method per supported media
    kind: generate_animation(request), generate_video(request), and/or
    generate_audio(request).
    """
    name = "base"
    def generate(self, request):
        """Generate media for the given request, dispatching on its media_kind.

        :param request: a MediaRequest subclass instance.
        :return: a MediaResult.
        :raises ProviderError: if this provider does not support the media kind.
        """
        kind = getattr(request, "media_kind", None)
        method = getattr(self, f"generate_{kind}", None)
        if method is None or kind == "media":
            raise ProviderError(
                f"Provider {self.name!r} does not support media kind {kind!r} "
                f"(supported: {', '.join(self.supported_kinds()) or 'none'}).")
        return method(request)
    @classmethod
    def supported_kinds(cls):
        """Return the media kinds this provider implements, as a tuple."""
        return tuple(k for k in ("animation", "video", "audio")
                     if callable(getattr(cls, f"generate_{k}", None)))
class ProviderError(RuntimeError):
    """Raised when a provider fails to produce the requested media."""
    pass

### Shared helpers (used by the HTTP providers)
_EXT_MIME = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif",
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
    ".ogg": "audio/ogg", ".flac": "audio/flac", ".aac": "audio/aac",
    ".opus": "audio/opus",
    ".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime",
}
def file_data_uri(path):
    """Read a local media file and return a base64 data URI for it.

    Most fal/Replicate models accept a data URI in place of a hosted file URL,
    which lets us submit local files without a separate upload step.

    :param path: path to the media file.
    :return: a 'data:<mime>;base64,<...>' string.
    """
    ext = os.path.splitext(path)[1].lower()
    mime = _EXT_MIME.get(ext, "application/octet-stream")
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{data}"
def extract_output_url(body):
    """Pull the output media URL out of a provider result body (schemas vary).

    Handles the common shapes fal and Replicate return: {'video': {'url':..}},
    {'videos': [..]}, {'audio': {'url':..}}, {'audio_url':..}, {'audio_file':
    {'url':..}}, {'output': 'url'|[..]}, {'url':..}, or a bare string/list.

    :param body: the parsed JSON result (dict, list, or string).
    :return: the URL string, or None if none was found.
    """
    if isinstance(body, str):
        return body or None
    if isinstance(body, list):
        return extract_output_url(body[-1]) if body else None
    if not isinstance(body, dict):
        return None
    for key in ("video", "audio", "audio_file", "image"):
        val = body.get(key)
        if isinstance(val, dict) and val.get("url"):
            return val["url"]
        if isinstance(val, str) and val:
            return val
    videos = body.get("videos")
    if isinstance(videos, list) and videos:
        first = videos[0]
        return first.get("url") if isinstance(first, dict) else first
    for key in ("audio_url", "video_url", "url"):
        if isinstance(body.get(key), str) and body[key]:
            return body[key]
    if "output" in body:
        return extract_output_url(body["output"])
    return None
def download_to_file(url, path, headers=None, timeout=120):
    """Stream a URL to a local file path, creating parent dirs as needed.

    :param url: the file URL to download.
    :param path: local destination path.
    :param headers: optional request headers.
    :param timeout: per-request timeout in seconds.
    :return: the destination path.
    """
    import requests
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    with requests.get(url, headers=headers or {}, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
    return path
def slug_for(request, max_len=32):
    """Build a filesystem-friendly stem for a request's output file.

    Uses the source image basename when there is one, else the first words of
    the description.

    :param request: a MediaRequest.
    :param max_len: max characters of description slug.
    :return: a short slug string.
    """
    image_path = getattr(request, "image_path", None)
    if image_path:
        return os.path.splitext(os.path.basename(image_path))[0]
    text = request.description or "output"
    slug = "".join(c if c.isalnum() else "-" for c in text.lower())
    slug = "-".join(p for p in slug.split("-") if p)
    return slug[:max_len].rstrip("-") or "output"
def output_stem(request, provider_name):
    """Build a provider output stem that stays unique across pipeline retries.

    The pipeline assigns a distinct seed to every candidate after the first.
    Including that seed in downloaded/generated filenames prevents a later
    failed candidate from overwriting the on-disk file selected as best.
    """
    stem = f"{slug_for(request)}_{provider_name}"
    if request.seed is not None:
        stem += f"_seed-{int(request.seed)}"
    return stem

# ===== END OF FILE apps/content_studio/providers/base.py =====
