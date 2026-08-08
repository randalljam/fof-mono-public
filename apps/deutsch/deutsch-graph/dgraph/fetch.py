"""Download the corpus inputs the graph build needs from S3 ([S3-FILES-BUCKET]), driven by
manifests/deutsch.manifest.jsonl. Never uploads, never deletes. Uses the scoped
FOF_FILES_DATA_S3_* credentials when present, else the default AWS chain."""
import concurrent.futures
import os
from . import inventory

### Prefixes (under data/deutsch/) required for a full build
FETCH_PREFIXES = (
    "f8_done_qafixed_and_vrb/",
    "f8_qafixed_talks/",
    "f8_vrb_talks_only/",
    "dd_top-stars_qa-multi/",
    "books/",
    "essays/",
    "interviews_print_web/",
)
FETCH_ROOT_FILES = (
    "data/deutsch/topics_matrix_2025-01-31.csv",
    "data/deutsch/INVENTORY_dd_post_qafixed.md",
    "data/deutsch/deutsch_large_context_v1.md",
)
### Prefixes fetched by direct S3 listing (uploaded ahead of their manifest rows)
UNMANIFESTED_PREFIXES = (
    "data/deutsch/deutsch-well_2023/",
    "data/deutsch/terms/",
)

def s3_client():
    """boto3 client with scoped creds when available."""
    import boto3
    key = os.environ.get("FOF_FILES_DATA_S3_ACCESS_KEY_ID")
    secret = os.environ.get("FOF_FILES_DATA_S3_SECRET_ACCESS_KEY")
    if key and secret:
        return boto3.client("s3", region_name="us-west-2", aws_access_key_id=key, aws_secret_access_key=secret)
    return boto3.client("s3", region_name="us-west-2")
def wanted_rows(rows):
    """Manifest rows the build reads: md files under fetch prefixes + root files."""
    out = []
    for r in rows:
        p = r["repo_path"]
        if p in FETCH_ROOT_FILES:
            out.append(r)
            continue
        if not p.startswith("data/deutsch/") or not p.endswith(".md"):
            continue
        rel = p[len("data/deutsch/"):]
        if any(rel.startswith(prefix) for prefix in FETCH_PREFIXES):
            out.append(r)
    return out
def list_unmanifested(client, bucket="[S3-FILES-BUCKET]"):
    """S3 rows for UNMANIFESTED_PREFIXES (folders uploaded before their manifest rows land)."""
    rows = []
    paginator = client.get_paginator("list_objects_v2")
    for prefix in UNMANIFESTED_PREFIXES:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                rows.append({"repo_path": obj["Key"], "size_bytes": obj["Size"],
                             "s3_bucket": bucket, "s3_key": obj["Key"]})
    return rows
def fetch_corpus(repo_root, workers=8, verbose=True):
    """Download all missing/size-mismatched inputs; returns (downloaded, skipped)."""
    rows = inventory.load_manifest(repo_root)
    want = wanted_rows(rows)
    client = s3_client()
    manifested = {r["repo_path"] for r in want}
    want.extend(r for r in list_unmanifested(client) if r["repo_path"] not in manifested)
    def one(r):
        dest = os.path.join(repo_root, r["repo_path"])
        if os.path.exists(dest) and os.path.getsize(dest) == r["size_bytes"]:
            return "skip"
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        client.download_file(r["s3_bucket"], r["s3_key"], dest)
        return "ok"
    with concurrent.futures.ThreadPoolExecutor(workers) as ex:
        results = list(ex.map(one, want))
    downloaded, skipped = results.count("ok"), results.count("skip")
    if verbose:
        print("fetched %d files (%d already present) of %d needed" % (downloaded, skipped, len(want)))
    return downloaded, skipped
