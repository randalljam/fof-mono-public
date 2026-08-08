# ===== START OF FILE apps/content_studio/imaging.py =====
# PIL-backed image/animation I/O and the file codec used by the pipeline.
#
# This is the only module that touches pixels. Everything PIL-specific is here
# so the pipeline, verifier, and prompt logic stay image-library-agnostic and
# unit-testable. Importing this module requires Pillow.

import io
import os
import base64

from PIL import Image, ImageSequence

from apps.content_studio import config


### Loading
def load_input_image(path):
    """Load an input image (or the first frame of an animation) as RGB.

    :param path: path to a png/jpg/webp/gif file.
    :return: a PIL.Image in RGB mode.
    """
    with Image.open(path) as img:
        img.seek(0)
        return img.convert("RGB")
def load_animation_frames(path):
    """Load all frames of an animation (or the single frame of a still) as RGB.

    Supports animated GIF and WebP (and any multi-frame format PIL can iterate).
    A still image returns a one-element list.

    :param path: path to the animation/image file.
    :return: list of PIL.Image frames in RGB mode.
    """
    with Image.open(path) as img:
        frames = [frame.convert("RGB") for frame in ImageSequence.Iterator(img)]
        return frames or [img.convert("RGB")]
VIDEO_EXTS = (".mp4", ".webm", ".mov", ".mkv", ".m4v", ".avi")
def read_video_frames(path):
    """Decode a video file to a list of RGB PIL frames.

    Real providers return mp4/webm; this lets the codec sample them just like a
    GIF. Uses imageio if available, falling back to OpenCV. Both are optional.

    :param path: path to the video file.
    :return: list of PIL.Image frames in RGB mode.
    :raises RuntimeError: if neither imageio nor OpenCV is installed.
    """
    try:
        import imageio.v3 as iio
        return [Image.fromarray(f).convert("RGB") for f in iio.imiter(path)]
    except ImportError:
        pass
    try:
        import cv2
    except ImportError:
        raise RuntimeError(
            "Reading video frames needs imageio or opencv-python. "
            "Install one, or have the provider return a GIF/WebP."
        )
    cap = cv2.VideoCapture(path)
    frames = []
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(Image.fromarray(rgb).convert("RGB"))
    finally:
        cap.release()
    return frames
def read_any_frames(path):
    """Read frames from any supported animation/video/still, dispatching by ext.

    :param path: path to a gif/webp/png/jpg or mp4/webm/... file.
    :return: list of PIL.Image frames in RGB mode.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext in VIDEO_EXTS:
        return read_video_frames(path)
    return load_animation_frames(path)

### Resizing / encoding
def downscale(img, max_edge):
    """Return a copy of img scaled so its long edge is at most max_edge.

    Never upscales. Preserves aspect ratio.

    :param img: a PIL.Image.
    :param max_edge: int max length of the longer side.
    :return: a (possibly new) PIL.Image.
    """
    w, h = img.size
    longest = max(w, h)
    if longest <= max_edge:
        return img
    scale = max_edge / float(longest)
    return img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
def pil_to_png_b64(img, max_edge=None):
    """Encode a PIL image as a raw base64 PNG string (no data-URI prefix).

    :param img: a PIL.Image.
    :param max_edge: optional long-edge cap applied before encoding.
    :return: base64-encoded PNG bytes as an ascii string.
    """
    if max_edge:
        img = downscale(img, max_edge)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")

### Writing
def _durations_ms(fps, count):
    """Per-frame duration list in milliseconds for a given fps."""
    per = max(1, int(round(1000.0 / max(1, fps))))
    return [per] * count
def write_gif(frames, path, fps=12):
    """Write a list of PIL frames as an animated GIF.

    :param frames: list of PIL.Image frames.
    :param path: output file path (.gif).
    :param fps: frames per second.
    :return: the output path.
    """
    _ensure_parent(path)
    rgb = [f.convert("RGB") for f in frames]
    durations = _durations_ms(fps, len(rgb))
    rgb[0].save(path, format="GIF", save_all=True, append_images=rgb[1:],
                duration=durations, loop=0, disposal=2, optimize=False)
    return path
def write_webp(frames, path, fps=12):
    """Write a list of PIL frames as an animated WebP.

    :param frames: list of PIL.Image frames.
    :param path: output file path (.webp).
    :param fps: frames per second.
    :return: the output path.
    """
    _ensure_parent(path)
    rgb = [f.convert("RGB") for f in frames]
    durations = _durations_ms(fps, len(rgb))
    rgb[0].save(path, format="WEBP", save_all=True, append_images=rgb[1:],
                duration=durations, loop=0)
    return path
def save_animation(frames, path, fps=12):
    """Write frames to disk, picking the format from the file extension.

    :param frames: list of PIL.Image frames.
    :param path: output file path (.gif or .webp).
    :param fps: frames per second.
    :return: the output path.
    :raises ValueError: for an unsupported extension.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".gif":
        return write_gif(frames, path, fps=fps)
    if ext == ".webp":
        return write_webp(frames, path, fps=fps)
    raise ValueError(f"Unsupported animation extension {ext!r}; use .gif or .webp")
def _ensure_parent(path):
    """Create the parent directory of path if needed."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

### Codec for the pipeline
class FileCodec:
    """Reads frames and encodes base64 from real MediaResults / files.

    The pipeline talks to a codec rather than PIL directly so the same
    orchestration runs against in-memory stubs in tests.

    :param frame_max_edge: long-edge cap for frames sent to the verifier.
    """
    def __init__(self, frame_max_edge=None):
        self.frame_max_edge = frame_max_edge or config.VERIFIER_FRAME_MAX_EDGE
    def read_frames(self, result):
        """Return the list of frames for a MediaResult.

        Prefers in-memory frames (mock path); otherwise reads the output file.
        """
        if getattr(result, "frames", None):
            return list(result.frames)
        if getattr(result, "output_path", None):
            return read_any_frames(result.output_path)
        raise ValueError("MediaResult has neither frames nor output_path.")
    def frame_png_b64(self, frame):
        """Encode one frame (a PIL.Image) as a raw base64 PNG string."""
        return pil_to_png_b64(frame, max_edge=self.frame_max_edge)
    def image_png_b64(self, path):
        """Encode the reference image at `path` as a raw base64 PNG string."""
        return pil_to_png_b64(load_input_image(path), max_edge=self.frame_max_edge)

# ===== END OF FILE apps/content_studio/imaging.py =====
