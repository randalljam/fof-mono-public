# ===== START OF FILE apps/content_studio/cli.py =====
# Command-line entry point for the content studio.
#
# Examples:
#   # Animation: still image -> short verified GIF loop (fal by default).
#   python -m apps.content_studio.cli animate --image dragon.png \
#       --prompt "the dragon gently flaps its wings and blinks" --out out/dragon.gif
#
#   # Video: text-to-video (Seedance 2.0 on fal) with verification.
#   python -m apps.content_studio.cli video \
#       --prompt "a pink dragon soars over a castle at sunset" --out out/dragon.mp4
#
#   # Video: image-to-video from a starting frame, via Replicate instead.
#   python -m apps.content_studio.cli video --image dragon.png \
#       --prompt "the dragon takes off and flies away" --provider replicate
#
#   # Audio: speech (verified by transcribe-and-compare), music, or sfx.
#   python -m apps.content_studio.cli audio --kind speech \
#       --text "Welcome back, adventurer!" --out out/welcome.mp3
#   python -m apps.content_studio.cli audio --kind sfx \
#       --prompt "a magical sparkle chime" --duration 3
#
#   # Verify an existing file (visual clips or speech audio).
#   python -m apps.content_studio.cli verify --file out/dragon.gif \
#       --image dragon.png --prompt "the dragon flaps its wings"
#   python -m apps.content_studio.cli verify --file out/welcome.mp3 \
#       --text "Welcome back, adventurer!"
#
# Offline demo without API keys: add --provider mock to any generate command.

import os
import sys
import json
import shutil
import argparse

from apps.content_studio import config
from apps.content_studio.models import (
    AnimationRequest, VideoRequest, AudioRequest, MediaResult,
)
from apps.content_studio.providers import get_provider
from apps.content_studio.pipeline import generate_and_verify, default_verifier_for


### Shared plumbing
def _parse_extra(pairs):
    """Parse repeated --extra key=value flags into a dict (int/float/bool aware)."""
    extra = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise SystemExit(f"--extra expects key=value, got {pair!r}")
        key, value = pair.split("=", 1)
        if value.lower() in ("true", "false"):
            value = value.lower() == "true"
        else:
            for cast in (int, float):
                try:
                    value = cast(value)
                    break
                except ValueError:
                    continue
        extra[key.strip()] = value
    return extra
def _make_provider(args, out_path):
    """Construct the provider for a generate subcommand."""
    kwargs = {}
    if args.provider == "mock":
        if getattr(args, "defect", None):
            kwargs["defect"] = args.defect
    else:
        kwargs["output_dir"] = os.path.dirname(os.path.abspath(out_path))
    return get_provider(args.provider, **kwargs)
def _run_pipeline(args, provider, request):
    """Run generate_and_verify (or a single unverified generation) and report."""
    if args.no_verify:
        result = provider.generate(request)
        final_path = _materialize(result, args.out_path, args)
        print(f"Wrote {final_path} (verification skipped).")
        return 0
    pr = generate_and_verify(provider, request,
                             verifier=default_verifier_for(request),
                             max_attempts=args.attempts,
                             candidates_per_attempt=args.candidates)
    final_path = _materialize(pr.result, args.out_path, args)
    print(pr.to_json())
    print(f"\n{'PASSED' if pr.passed else 'BEST EFFORT (did not fully pass)'}: {final_path}")
    return 0 if pr.passed else 2
def _materialize(result, out_path, args):
    """Land the chosen result at (or near) out_path; return the final path.

    Visual results with in-memory frames are encoded to the requested .gif/.webp.
    Downloaded files are copied; when the source format differs from the request
    (e.g. an .mp4 from a video model vs an --out ending in .gif), visual files
    are transcoded where possible, otherwise the source extension is kept.
    """
    if result is None:
        raise SystemExit("No media was produced.")
    out_ext = os.path.splitext(out_path)[1].lower()
    fps = getattr(args, "fps", config.DEFAULT_FPS)

    if result.frames:
        from apps.content_studio import imaging
        if out_ext not in (".gif", ".webp"):
            out_path = os.path.splitext(out_path)[0] + ".gif"
            print(f"(in-memory frames encode to GIF/WebP; writing {out_path})")
        return imaging.save_animation(result.frames, out_path, fps=fps)

    src = result.output_path
    if not (src and os.path.exists(src)):
        raise SystemExit("Result had neither a file nor in-memory frames.")
    src_ext = os.path.splitext(src)[1].lower()
    if src_ext == out_ext:
        if os.path.abspath(src) != os.path.abspath(out_path):
            os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
            shutil.copyfile(src, out_path)
            return out_path
        return src
    if out_ext in (".gif", ".webp") and result.media_kind in ("animation", "video"):
        from apps.content_studio import imaging
        frames = imaging.read_any_frames(src)
        return imaging.save_animation(frames, out_path, fps=fps)
    final = os.path.splitext(out_path)[0] + src_ext
    os.makedirs(os.path.dirname(os.path.abspath(final)), exist_ok=True)
    shutil.copyfile(src, final)
    if final != out_path:
        print(f"(source format is {src_ext}; wrote {final})")
    return final
def _default_out(args, stem_source, ext):
    slug = os.path.splitext(os.path.basename(stem_source))[0] if stem_source else "output"
    return os.path.join(config.DEFAULT_OUTPUT_DIR, f"{slug}{ext}")

### animate
def cmd_animate(args):
    """Image -> short verified GIF/WebP loop."""
    args.out_path = args.out or _default_out(args, args.image, "_animation.gif")
    provider = _make_provider(args, args.out_path)
    request = AnimationRequest(
        image_path=args.image, prompt=args.prompt, negative_prompt=args.negative,
        duration_s=args.duration, fps=args.fps, seed=args.seed, model=args.model,
        extra=_parse_extra(args.extra),
    )
    return _run_pipeline(args, provider, request)

### video
def cmd_video(args):
    """Text- or image-to-video -> verified clip (mp4 by default)."""
    stem = args.image or args.prompt[:24].replace(" ", "-")
    args.out_path = args.out or _default_out(args, stem, "_video.mp4")
    provider = _make_provider(args, args.out_path)
    request = VideoRequest(
        prompt=args.prompt, image_path=args.image, negative_prompt=args.negative,
        duration_s=args.duration, resolution=args.resolution,
        aspect_ratio=args.aspect, seed=args.seed, model=args.model,
        extra=_parse_extra(args.extra),
    )
    return _run_pipeline(args, provider, request)

### audio
def cmd_audio(args):
    """Speech / music / sfx -> verified audio (speech: transcribe-and-compare)."""
    if args.kind == "speech" and not args.text:
        raise SystemExit("audio --kind speech requires --text")
    if args.kind in ("music", "sfx") and not args.prompt:
        raise SystemExit(f"audio --kind {args.kind} requires --prompt")
    stem = (args.text or args.prompt)[:24].replace(" ", "-")
    args.out_path = args.out or _default_out(args, stem, "_audio.mp3")
    provider = _make_provider(args, args.out_path)
    request = AudioRequest(
        text=args.text, prompt=args.prompt, audio_kind=args.kind,
        voice=args.voice, duration_s=args.duration, seed=args.seed,
        model=args.model, extra=_parse_extra(args.extra),
    )
    return _run_pipeline(args, provider, request)

### verify
def cmd_verify(args):
    """Verify an existing media file (visual clip or speech audio)."""
    from apps.content_studio.verify_audio import AUDIO_EXTS

    ext = os.path.splitext(args.file)[1].lower()
    result = MediaResult(output_path=args.file)
    if ext in AUDIO_EXTS or args.text:
        if not args.text:
            raise SystemExit("Verifying audio requires --text (the intended words).")
        from apps.content_studio.verify_audio import AudioVerifier
        request = AudioRequest(text=args.text, audio_kind="speech")
        verdict = AudioVerifier().assess(result, request)
    else:
        from apps.content_studio.verify import VisualVerifier
        request = AnimationRequest(image_path=args.image, prompt=args.prompt)
        verifier = VisualVerifier(sample_frames=args.sample_frames)
        verdict = verifier.assess(result, request)
    print(json.dumps(verdict.to_dict(), indent=2))
    return 0 if verdict.passed else 2

### parser
def _add_common_generate_args(p, default_provider):
    p.add_argument("--provider", default=default_provider,
                   help="generation provider (mock|fal|replicate|runway)")
    p.add_argument("--out", default=None, help="output file path")
    p.add_argument("--seed", type=int, default=None, help="generation seed")
    p.add_argument("--model", default=None, help="provider model id override")
    p.add_argument("--attempts", type=int, default=config.DEFAULT_MAX_ATTEMPTS,
                   help="regenerate rounds before giving up")
    p.add_argument("--candidates", type=int,
                   default=config.DEFAULT_CANDIDATES_PER_ATTEMPT,
                   help="best-of-N candidates per round")
    p.add_argument("--extra", action="append", default=[], metavar="KEY=VALUE",
                   help="model-specific input field (repeatable)")
    p.add_argument("--no-verify", action="store_true", dest="no_verify",
                   help="skip verification/regeneration; just generate once")
def build_parser():
    """Build the argparse CLI."""
    p = argparse.ArgumentParser(
        prog="apps.content_studio.cli",
        description="Generate and verify animations, video, and audio.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("animate", help="image -> short verified GIF/WebP loop")
    a.add_argument("--image", required=True, help="input image or simple animation")
    a.add_argument("--prompt", required=True, help="verbal description of the motion")
    a.add_argument("--negative", default="", help="extra negative-prompt terms")
    a.add_argument("--duration", type=float, default=config.DEFAULT_DURATION_S,
                   help="clip length in seconds")
    a.add_argument("--fps", type=int, default=config.DEFAULT_FPS, help="frames per second")
    a.add_argument("--defect", default=None,
                   help="(mock only) inject a defect, e.g. 'extra_limb', to test the verifier")
    _add_common_generate_args(a, config.DEFAULT_PROVIDERS["animation"])
    a.add_argument("--sample-frames", type=int, default=config.DEFAULT_SAMPLE_FRAMES,
                   dest="sample_frames", help="frames to inspect per candidate")
    a.set_defaults(func=cmd_animate)

    v = sub.add_parser("video", help="text/image -> verified video clip")
    v.add_argument("--prompt", required=True, help="verbal description of the video")
    v.add_argument("--image", default=None, help="optional starting image (image-to-video)")
    v.add_argument("--negative", default="", help="extra negative-prompt terms")
    v.add_argument("--duration", type=float, default=config.DEFAULT_VIDEO_DURATION_S,
                   help="clip length in seconds")
    v.add_argument("--resolution", default=config.DEFAULT_VIDEO_RESOLUTION,
                   help="output resolution (e.g. 480p, 720p, 1080p)")
    v.add_argument("--aspect", default=config.DEFAULT_VIDEO_ASPECT,
                   help="aspect ratio for text-to-video (e.g. 16:9, 9:16)")
    v.add_argument("--fps", type=int, default=config.DEFAULT_FPS,
                   help="fps used when transcoding to GIF/WebP")
    v.add_argument("--defect", default=None, help=argparse.SUPPRESS)
    _add_common_generate_args(v, config.DEFAULT_PROVIDERS["video"])
    v.set_defaults(func=cmd_video)

    au = sub.add_parser("audio", help="text -> verified speech / music / sfx")
    au.add_argument("--kind", default="speech", choices=("speech", "music", "sfx"),
                    help="what kind of audio to generate")
    au.add_argument("--text", default="", help="the words to speak (speech)")
    au.add_argument("--prompt", default="", help="description of the sound (music/sfx)")
    au.add_argument("--voice", default=None, help="provider voice id (speech)")
    au.add_argument("--duration", type=float, default=None,
                    help="target duration in seconds (music/sfx)")
    _add_common_generate_args(au, config.DEFAULT_PROVIDERS["audio"])
    au.set_defaults(func=cmd_audio)

    ver = sub.add_parser("verify", help="verify an existing media file")
    ver.add_argument("--file", required=True, help="media file to inspect")
    ver.add_argument("--image", default=None, help="reference/source image (visual)")
    ver.add_argument("--prompt", default="", help="the intended clip description (visual)")
    ver.add_argument("--text", default="", help="the intended spoken words (audio)")
    ver.add_argument("--sample-frames", type=int, default=config.DEFAULT_SAMPLE_FRAMES,
                     dest="sample_frames", help="frames to inspect (visual)")
    ver.set_defaults(func=cmd_verify)
    return p
def main(argv=None):
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
if __name__ == "__main__":
    sys.exit(main())

# ===== END OF FILE apps/content_studio/cli.py =====
