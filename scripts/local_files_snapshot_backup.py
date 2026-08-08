#!/usr/bin/env python3
"""Create and optionally upload a ZIP snapshot of the fof-mono local files root."""

import argparse
import os
import subprocess
import zipfile
from datetime import datetime
from zoneinfo import ZoneInfo

DEFAULT_LOCAL_ROOT = "/Users/randytrue/Documents/Code/_LOCAL_FILES/fof-mono"
DEFAULT_S3_URI = "s3://[S3-FILES-BUCKET]/_LOCAL_FILES_fof-mono_backup/"
PACIFIC_TZ = "America/Los_Angeles"

### Helpers: paths and timestamps
def timestamp_pacific():
    """Return YYYY-MM-DD_HHMM in Pacific time."""
    return datetime.now(ZoneInfo(PACIFIC_TZ)).strftime("%Y-%m-%d_%H%M")
def default_zip_path(local_root, stamp):
    """Return the default local ZIP path under an excluded underscore folder."""
    output_dir = os.path.join(local_root, "_backup-zips")
    return os.path.join(output_dir, f"_LOCAL_FILES_fof-mono_backup_{stamp}.zip")
def should_skip_top_level(path, local_root):
    """Return true for top-level underscore directories excluded from snapshots."""
    rel = os.path.relpath(path, local_root)
    if rel == ".":
        return False
    first = rel.split(os.sep, 1)[0]
    first_path = os.path.join(local_root, first)
    return os.path.isdir(first_path) and first.startswith("_")
def iter_snapshot_files(local_root):
    """Yield files under local_root, excluding top-level underscore directories."""
    for dirpath, dirnames, filenames in os.walk(local_root):
        dirnames[:] = [
            name for name in dirnames
            if not (dirpath == local_root and name.startswith("_"))
        ]
        if should_skip_top_level(dirpath, local_root):
            continue
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if should_skip_top_level(file_path, local_root):
                continue
            yield file_path

### Snapshot and upload
def create_zip(local_root, zip_path):
    """Create the snapshot ZIP and return file count plus byte count."""
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)
    file_count = 0
    byte_count = 0
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for file_path in iter_snapshot_files(local_root):
            arcname = os.path.relpath(file_path, local_root).replace(os.sep, "/")
            zf.write(file_path, arcname)
            file_count += 1
            byte_count += os.path.getsize(file_path)
    return file_count, byte_count
def upload_zip(zip_path, s3_uri, dry_run):
    """Upload the ZIP to S3 using the AWS CLI."""
    target = s3_uri.rstrip("/") + "/" + os.path.basename(zip_path)
    cmd = ["aws", "s3", "cp", zip_path, target]
    if dry_run:
        print("DRY RUN: " + " ".join(cmd))
        return target
    subprocess.run(cmd, check=True)
    return target
def human_mb(byte_count):
    """Format bytes as MB."""
    return f"{byte_count / (1024 * 1024):.2f} MB"

### CLI
def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Create and upload a fof-mono _LOCAL_FILES ZIP snapshot.")
    parser.add_argument("--local-root", default=os.environ.get("FOF_MONO_LOCAL_FILES_ROOT", DEFAULT_LOCAL_ROOT))
    parser.add_argument("--s3-uri", default=DEFAULT_S3_URI)
    parser.add_argument("--output", help="Local ZIP path. Defaults to <local-root>/_backup-zips/<timestamp>.zip.")
    parser.add_argument("--skip-upload", action="store_true", help="Create the ZIP but do not upload it.")
    parser.add_argument("--dry-run-upload", action="store_true", help="Create the ZIP and print the AWS upload command without running it.")
    parser.add_argument("--delete-local-after-upload", action="store_true", help="Delete the local ZIP after a successful upload.")
    args = parser.parse_args()
    local_root = os.path.abspath(args.local_root)
    if not os.path.isdir(local_root):
        raise SystemExit(f"local root does not exist: {local_root}")
    stamp = timestamp_pacific()
    zip_path = os.path.abspath(args.output or default_zip_path(local_root, stamp))
    print("=== local files snapshot backup ===")
    print(f"local root: {local_root}")
    print("excluded:   top-level directories beginning with '_'")
    print(f"zip path:   {zip_path}")
    file_count, byte_count = create_zip(local_root, zip_path)
    print(f"created:    {file_count} files, {human_mb(byte_count)} source bytes")
    print(f"zip size:   {human_mb(os.path.getsize(zip_path))}")
    if args.skip_upload:
        print("upload:     skipped")
        return
    target = upload_zip(zip_path, args.s3_uri, args.dry_run_upload)
    print(f"uploaded:   {target}" if not args.dry_run_upload else f"upload:     dry-run -> {target}")
    if args.delete_local_after_upload and not args.dry_run_upload:
        os.remove(zip_path)
        print("local zip:  deleted after upload")
if __name__ == "__main__":
    main()
