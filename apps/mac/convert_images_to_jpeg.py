#!/usr/bin/env python3
"""
Convert non-JPEG images (PNG, WebP, HEIC from iPhone, etc.) to JPEG for AirDrop
to iPhone and import into the Photos camera roll.
"""
import argparse
import subprocess
from pathlib import Path
from PIL import Image

DEFAULT_INPUT_DIR = Path.home() / "Pictures" / "Minecraft for Kid1 2nd funsch"
HEIC_EXTENSIONS = {".heic", ".heif"}
SOURCE_EXTENSIONS = {".png", ".webp", ".bmp", ".tif", ".tiff", ".gif"} | HEIC_EXTENSIONS
SKIP_EXTENSIONS = {".jpg", ".jpeg"}
JPEG_QUALITY = 92
JPEG_SUFFIX = ".jpg"

### Helpers: image conversion
def _flatten_alpha(image):
    """Composite RGBA (or P with transparency) onto a white background."""
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    return image.convert("RGB")
def _validate_quality(quality):
    """Raise ValueError when quality is outside Pillow/sips JPEG range."""
    if not 1 <= quality <= 95:
        raise ValueError(f"JPEG quality must be 1-95, got {quality}")
def _convert_heic_via_sips(source_path, output_path, quality):
    """Convert HEIC/HEIF to JPEG using macOS sips (quality 1-95)."""
    _validate_quality(quality)
    result = subprocess.run(
        [
            "sips",
            "-s", "format", "jpeg",
            "-s", "formatOptions", str(quality),
            str(source_path),
            "--out", str(output_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "sips failed").strip()
        raise RuntimeError(f"sips HEIC conversion failed: {detail}")
def convert_image_to_jpeg(source_path, output_path, quality=JPEG_QUALITY, overwrite=False):
    """
    Convert a single image file to JPEG.

    :param source_path: path to the source image
    :param output_path: path for the output .jpg file
    :param quality: JPEG quality 1-95
    :param overwrite: replace an existing output file
    :return: output path if converted, None if skipped
    """
    source_path = Path(source_path)
    output_path = Path(output_path)
    _validate_quality(quality)
    if output_path.exists() and not overwrite:
        print(f"Skip (exists): {output_path}")
        return None
    if source_path.suffix.lower() in HEIC_EXTENSIONS:
        _convert_heic_via_sips(source_path, output_path, quality)
    else:
        with Image.open(source_path) as image:
            rgb = _flatten_alpha(image)
            rgb.save(
                output_path,
                format="JPEG",
                quality=quality,
                optimize=True,
                subsampling=0,
            )
    print(f"Converted: {source_path} -> {output_path}")
    return str(output_path)

### Helpers: folder scan
def _is_source_image(path):
    """Return True if path is an image we should convert to JPEG."""
    ext = path.suffix.lower()
    if ext in SKIP_EXTENSIONS:
        return False
    return ext in SOURCE_EXTENSIONS
def _iter_source_images(input_dir):
    """Yield source image files under input_dir, including subfolders."""
    for entry in sorted(input_dir.rglob("*")):
        if entry.is_file() and _is_source_image(entry):
            yield entry
def convert_folder_to_jpeg(input_dir, quality=JPEG_QUALITY, overwrite=False):
    """
    Convert every non-JPEG image under input_dir (recursively) to a sibling .jpg file.

    :param input_dir: root folder containing source images
    :param quality: JPEG quality 1-95
    :param overwrite: replace existing .jpg files
    :return: list of output paths created or updated
    """
    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input folder not found: {input_dir}")
    outputs = []
    for source_path in _iter_source_images(input_dir):
        output_path = source_path.with_suffix(JPEG_SUFFIX)
        result = convert_image_to_jpeg(source_path, output_path, quality=quality, overwrite=overwrite)
        if result:
            outputs.append(result)
    return outputs

### CLI
def _parse_args():
    parser = argparse.ArgumentParser(
        description="Convert non-JPEG images (including HEIC) to JPEG for iPhone AirDrop / Photos import."
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        default=str(DEFAULT_INPUT_DIR),
        help=f"Folder with source images (default: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=JPEG_QUALITY,
        metavar="N",
        help=f"JPEG quality 1-95 (default: {JPEG_QUALITY})",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing .jpg files (default: skip when .jpg already exists)",
    )
    args = parser.parse_args()
    _validate_quality(args.quality)
    return args
def main():
    args = _parse_args()
    outputs = convert_folder_to_jpeg(args.input_dir, quality=args.quality, overwrite=args.overwrite)
    print(f"\nDone. {len(outputs)} file(s) converted in {args.input_dir}")
if __name__ == "__main__":
    main()
