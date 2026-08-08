# ===== START OF FILE apps/content_studio/providers/mock.py =====
# Offline media provider.
#
# MockProvider synthesizes media locally so the whole pipeline (generate ->
# verify -> retry) can be exercised end-to-end offline, in tests, and in demos
# without API keys:
#   - animation: a gentle breathing/sway/bob loop from the input image (PIL);
#   - video: the same idle loop when an image is given, or a procedural
#     moving-shape scene for text-to-video;
#   - audio: stdlib-only WAV synthesis (beeps per word for speech, a little
#     arpeggio for music, a decaying burst for sfx).
#
# It can also intentionally inject a "janky extra limb" defect into visual
# output, which is how we demonstrate and test that the verifier actually
# catches the failure the real tools produce.

import os
import math
import tempfile

from apps.content_studio import config
from apps.content_studio.models import MediaResult
from apps.content_studio.providers.base import MediaProvider, ProviderError


### Mock provider
class MockProvider(MediaProvider):
    """Synthesize media locally with simple, deterministic transforms.

    :param output_dir: where to write files; None keeps visual output in memory
                       only (audio always writes, to a temp dir if unset).
    :param defect: None for clean output, or 'extra_limb' to inject a janky,
                   duplicated-appendage artifact into visual frames (used to
                   exercise the verifier).
    :param breath_amp: scale oscillation amplitude (breathing).
    :param sway_amp: horizontal sway as a fraction of width.
    :param bob_amp: vertical bob as a fraction of height.
    """
    name = "mock"
    def __init__(self, output_dir=None, defect=None, breath_amp=0.045,
                 sway_amp=0.02, bob_amp=0.02):
        self.output_dir = output_dir
        self.defect = defect
        self.breath_amp = breath_amp
        self.sway_amp = sway_amp
        self.bob_amp = bob_amp

    ### Animation
    def generate_animation(self, request):
        """Synthesize an idle-motion loop from the request's input image.

        :param request: an AnimationRequest.
        :return: a MediaResult carrying in-memory frames (and a file path if
                 output_dir is set).
        """
        frames = self._image_motion_frames(
            request.image_path, request.duration_s, request.fps)
        output_path = None
        if self.output_dir:
            output_path = self._write_frames(frames, request, request.fps)
        return MediaResult(
            output_path=output_path, frames=frames, provider=self.name,
            model="mock-idle-v1", request=request,
            meta=dict(frame_count=len(frames), defect=self.defect, seed=request.seed),
        )

    ### Video
    def generate_video(self, request):
        """Synthesize a short clip: idle motion from the image (i2v) or a
        procedural moving-shape scene (t2v).

        :param request: a VideoRequest.
        :return: a MediaResult carrying in-memory frames (and a .gif path if
                 output_dir is set — the mock cannot encode mp4).
        """
        fps = int(request.extra.get("fps", config.DEFAULT_FPS))
        if request.image_path:
            frames = self._image_motion_frames(request.image_path,
                                               request.duration_s, fps)
        else:
            frames = self._procedural_scene_frames(request.duration_s, fps,
                                                   request.seed)
        output_path = None
        if self.output_dir:
            output_path = self._write_frames(frames, request, fps)
        return MediaResult(
            output_path=output_path, frames=frames, provider=self.name,
            model="mock-video-v1", request=request,
            meta=dict(frame_count=len(frames), defect=self.defect, seed=request.seed),
        )

    ### Audio
    def generate_audio(self, request):
        """Synthesize a WAV entirely with the stdlib (no audio deps).

        speech -> two-tone beeps, one per word (duration ~0.35s/word unless
        request.duration_s is set); music -> a looping four-note arpeggio;
        sfx -> a decaying harmonic burst.

        :param request: an AudioRequest.
        :return: a MediaResult with an output_path to the written .wav.
        """
        import wave, struct

        kind = request.audio_kind
        if request.duration_s:
            duration = float(request.duration_s)
        elif kind == "speech":
            words = max(1, len((request.text or "").split()))
            duration = max(0.6, 0.35 * words)
        else:
            duration = 2.0

        rate = 16000
        n = int(duration * rate)
        samples = self._audio_samples(kind, n, rate, request)

        out_dir = self.output_dir or tempfile.mkdtemp(prefix="content_studio_mock_")
        os.makedirs(out_dir, exist_ok=True)
        from apps.content_studio.providers.base import output_stem
        path = os.path.join(out_dir, f"{output_stem(request, self.name)}.wav")
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(b"".join(
                struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767))
                for s in samples))
        return MediaResult(
            output_path=path, provider=self.name, model="mock-audio-v1",
            request=request, meta=dict(duration_s=duration, sample_rate=rate),
        )
    def _audio_samples(self, kind, n, rate, request):
        """Yieldable list of float samples in [-1, 1] for the given kind."""
        samples = []
        if kind == "speech":
            words = max(1, len((request.text or "").split()))
            seg = max(1, n // words)
            for i in range(n):
                word_i = min(i // seg, words - 1)
                freq = 220.0 if word_i % 2 == 0 else 330.0
                # brief silence between "words"
                gate = 0.0 if (i % seg) > seg * 0.8 else 1.0
                samples.append(0.4 * gate * math.sin(2 * math.pi * freq * i / rate))
        elif kind == "music":
            notes = [261.63, 329.63, 392.00, 523.25]  # C-E-G-C arpeggio
            seg = max(1, n // 8)
            for i in range(n):
                freq = notes[(i // seg) % len(notes)]
                samples.append(0.35 * math.sin(2 * math.pi * freq * i / rate))
        else:  # sfx: decaying harmonic burst
            for i in range(n):
                t = i / rate
                decay = math.exp(-3.0 * t)
                s = (math.sin(2 * math.pi * 180 * t)
                     + 0.5 * math.sin(2 * math.pi * 540 * t)
                     + 0.25 * math.sin(2 * math.pi * 1100 * t))
                samples.append(0.4 * decay * s / 1.75)
        return samples

    ### Visual synthesis internals
    def _image_motion_frames(self, image_path, duration_s, fps):
        """Breathing/sway/bob loop composed from a source image."""
        Image, imaging = _require_pil()
        base = imaging.load_input_image(image_path)
        base = imaging.downscale(base, config.DEFAULT_MAX_EDGE)
        w, h = base.size
        bg = _background_color(base)
        n = max(2, int(round(duration_s * fps)))
        frames = []
        for i in range(n):
            phase = 2.0 * math.pi * (i / float(n))  # one full loop
            scale = 1.0 + self.breath_amp * math.sin(phase)
            dx = int(self.sway_amp * w * math.sin(phase))
            dy = int(self.bob_amp * h * math.sin(2.0 * phase))
            frames.append(self._compose_frame(Image, base, w, h, bg, scale, dx, dy))
        return frames
    def _procedural_scene_frames(self, duration_s, fps, seed, size=(320, 180)):
        """Text-to-video stand-in: a shaded sky with a drifting circle."""
        Image, _ = _require_pil()
        from PIL import ImageDraw
        w, h = size
        n = max(2, int(round(duration_s * fps)))
        phase0 = (seed or 0) % 7
        frames = []
        for i in range(n):
            t = i / float(n)
            img = Image.new("RGB", (w, h), (18, 24, 48))
            d = ImageDraw.Draw(img)
            for y in range(0, h, 4):  # vertical gradient bands
                shade = int(30 + 60 * (y / h))
                d.rectangle([0, y, w, y + 4], fill=(shade // 2, shade // 2, shade))
            cx = int(w * (0.15 + 0.7 * t))
            cy = int(h * (0.35 + 0.15 * math.sin(2 * math.pi * (t + phase0 / 7.0))))
            r = h // 7
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(250, 210, 120))
            frames.append(img)
        return frames
    def _compose_frame(self, Image, base, w, h, bg, scale, dx, dy):
        """Build one frame: scaled/offset subject on a filled background."""
        canvas = Image.new("RGB", (w, h), bg)
        sw, sh = max(1, int(w * scale)), max(1, int(h * scale))
        subject = base.resize((sw, sh), Image.LANCZOS)
        ox = (w - sw) // 2 + dx
        oy = (h - sh) // 2 + dy
        canvas.paste(subject, (ox, oy))
        if self.defect == "extra_limb":
            self._inject_extra_limb(Image, canvas, subject, ox, oy, sw, sh)
        return canvas
    def _inject_extra_limb(self, Image, canvas, subject, ox, oy, sw, sh):
        """Paste a duplicated, rotated strip to mimic a grotesque extra limb."""
        # Take a vertical strip where an arm might be and clone it outward.
        x0 = int(sw * 0.55)
        strip = subject.crop((x0, int(sh * 0.35), int(sw * 0.8), int(sh * 0.85)))
        strip = strip.transpose(Image.FLIP_LEFT_RIGHT).rotate(20, expand=True)
        canvas.paste(strip, (ox + sw - int(sw * 0.1), oy + int(sh * 0.3)))
    def _write_frames(self, frames, request, fps):
        """Write visual frames to a .gif under output_dir and return the path."""
        from apps.content_studio import imaging
        from apps.content_studio.providers.base import output_stem
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(
            self.output_dir, f"{output_stem(request, self.name)}.gif")
        return imaging.write_gif(frames, path, fps=fps)

### Helpers
def _require_pil():
    """Import PIL + the imaging module, with a clear error when missing."""
    try:
        from PIL import Image
        from apps.content_studio import imaging
        return Image, imaging
    except Exception as e:
        raise ProviderError(f"MockProvider visual synthesis requires Pillow: {e}")
def _background_color(img):
    """Estimate a background fill color from the image corners."""
    w, h = img.size
    corners = [img.getpixel((0, 0)), img.getpixel((w - 1, 0)),
               img.getpixel((0, h - 1)), img.getpixel((w - 1, h - 1))]
    r = sum(c[0] for c in corners) // 4
    g = sum(c[1] for c in corners) // 4
    b = sum(c[2] for c in corners) // 4
    return (r, g, b)

# ===== END OF FILE apps/content_studio/providers/mock.py =====
