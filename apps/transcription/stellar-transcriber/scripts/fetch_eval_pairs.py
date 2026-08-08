"""
Fetch eval-pair transcript markdown files from S3 for Stellar Transcriber baseline runs.

Read-only: performs S3 GETs only (never s3_archive build/refresh). Downloads .md files
listed in the corpus inventory catalog for episodes with raw+ref pairs.

Run from the repo root:
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/fetch_eval_pairs.py
"""
import csv
import hashlib
import json
import os
import sys

DEFAULT_BUCKET = "[S3-FILES-BUCKET]"
CATALOG_REL = os.path.join("apps", "transcription", "stellar-transcriber", "references", "corpus-inventory-catalog.csv")
MANIFEST_DIR = "manifests"
EXTRA_SUPPORT_FILES = ["data/capitalized_words_not_proper_names.txt"]

### Repo root
def find_repo_root(start_dir):
    current = os.path.abspath(start_dir)
    while True:
        if os.path.isfile(os.path.join(current, CATALOG_REL)):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            raise FileNotFoundError(f"Could not locate repo root containing {CATALOG_REL}")
        current = parent

### Manifest index
def load_manifest_sha_index(repo_root, corpora):
    """Build s3_key -> sha256 lookup from committed manifests."""
    index = {}
    for corpus in corpora:
        manifest_path = os.path.join(repo_root, MANIFEST_DIR, f"{corpus}.manifest.jsonl")
        if not os.path.isfile(manifest_path):
            continue
        with open(manifest_path) as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                key = row.get("s3_key")
                if key:
                    index[key] = row.get("sha256")
    return index

### Catalog
def load_pair_keys(catalog_path):
    """Return sorted unique S3 keys for .md files in paired episodes."""
    keys = set()
    with open(catalog_path, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("has_pair") != "yes":
                continue
            for key in row.get("s3_keys", "").split(";"):
                key = key.strip()
                if key.endswith(".md"):
                    keys.add(key)
    return sorted(keys)

### Download
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()
def download_key(client, bucket, s3_key, local_path, expected_sha=None):
    """Download one S3 object; verify sha256 when expected_sha is provided."""
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    if os.path.isfile(local_path):
        if expected_sha and sha256_file(local_path) == expected_sha:
            return "skipped"
        if expected_sha is None:
            return "skipped"
    client.download_file(bucket, s3_key, local_path)
    if expected_sha and sha256_file(local_path) != expected_sha:
        raise RuntimeError(f"sha256 mismatch after download: {s3_key}")
    return "downloaded"

### Main
def main():
    repo_root = find_repo_root(os.path.dirname(os.path.abspath(__file__)))
    catalog_path = os.path.join(repo_root, CATALOG_REL)
    keys = load_pair_keys(catalog_path)
    keys = sorted(set(keys + EXTRA_SUPPORT_FILES))
    sha_index = load_manifest_sha_index(repo_root, ["deutsch", "pv", "sovereign-child"])
    try:
        import boto3
        # Cataclysm cloud environments carry a scoped no-delete grant for s3://[S3-FILES-BUCKET]/data/*
        # in FOF_FILES_DATA_S3_*; prefer it over the default chain when present.
        fof_key = os.environ.get("FOF_FILES_DATA_S3_ACCESS_KEY_ID")
        fof_secret = os.environ.get("FOF_FILES_DATA_S3_SECRET_ACCESS_KEY")
        if fof_key and fof_secret:
            client = boto3.client("s3", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"),
                                  aws_access_key_id=fof_key, aws_secret_access_key=fof_secret)
        else:
            client = boto3.client("s3", region_name="us-west-2")
    except Exception as exc:
        print(f"ERROR: Could not initialize boto3/S3 client: {exc}")
        print("AWS credentials are required for Phase E baseline fetch. Stop and configure credentials.")
        return 1
    downloaded = skipped = failed = 0
    print(f"Fetching {len(keys)} markdown files from s3://{DEFAULT_BUCKET}/ ...")
    for s3_key in keys:
        local_path = os.path.join(repo_root, s3_key)
        expected_sha = sha_index.get(s3_key)
        try:
            result = download_key(client, DEFAULT_BUCKET, s3_key, local_path, expected_sha)
            if result == "skipped":
                skipped += 1
            else:
                downloaded += 1
        except Exception as exc:
            failed += 1
            print(f"FAILED {s3_key}: {exc}")
    print(f"Done: downloaded={downloaded} skipped={skipped} failed={failed}")
    return 1 if failed else 0
if __name__ == "__main__":
    sys.exit(main())
