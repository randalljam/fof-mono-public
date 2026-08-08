"""
Build the Stellar Transcriber corpus inventory catalog from the committed S3 manifests.

Reads the corpus manifest JSONL files in manifests/
(read-only; never runs s3_archive build/refresh), pairs raw machine-diarized
transcripts with human-edited reference transcripts by filename stem, and writes
a catalog CSV plus a per-corpus summary to stdout.

Run from the repo root:
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/build_corpus_inventory.py

Output: apps/transcription/stellar-transcriber/references/corpus-inventory-catalog.csv
Conventions: apps/transcription/stellar-transcriber/references/transcript-file-conventions.md
"""
import csv
import json
import os
import sys

### Constants
CORPORA = ["deutsch", "pv", "sovereign-child"]
MANIFEST_DIR = "manifests"
CATALOG_PATH = os.path.join("apps", "transcription", "stellar-transcriber", "references", "corpus-inventory-catalog.csv")
# Longest-first so _nova2meet/_nova2gen match before _nova2.
RAW_SUFFIXES = ["_nova2meet", "_nova2gen", "_dgwhspm", "_enhmeet", "_nova2", "_otter"]
REF_SUFFIXES = ["_qafixed", "_cemanual", "_vrb"]
# Pipeline stages, supporting files, and candidate references pending confirmation
# (see references/corpus-inventory.md). Not used for pairing.
STAGE_SUFFIXES = ["_partialcemanual", "_propernames", "_convertnums", "_copyedit", "_propers",
                  "_postce", "_spasgn", "_llmce", "_spfix", "_pub", "_yt"]
KNOWN_SUFFIXES = RAW_SUFFIXES + REF_SUFFIXES + STAGE_SUFFIXES

### Parsing
def find_repo_root(start_dir):
    """Walk up from start_dir until a directory containing the manifest dir is found."""
    current = os.path.abspath(start_dir)
    while True:
        if os.path.isdir(os.path.join(current, MANIFEST_DIR)):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            raise FileNotFoundError(f"Could not locate repo root containing {MANIFEST_DIR}")
        current = parent
def split_stem_suffix(filename):
    """Split a transcript filename into (stem, suffix, ext); suffix is '' when none matches."""
    base, ext = os.path.splitext(filename)
    for suffix in KNOWN_SUFFIXES:
        if base.endswith(suffix):
            return base[: -len(suffix)], suffix, ext
    return base, "", ext
def load_manifest_rows(manifest_path):
    """Load JSONL manifest rows as a list of dicts."""
    with open(manifest_path) as f:
        return [json.loads(line) for line in f if line.strip()]

### Cataloging
def build_corpus_catalog(rows, corpus):
    """Group manifest rows by filename stem; return dict stem -> episode record."""
    episodes = {}
    for row in rows:
        repo_path = row["repo_path"]
        filename = os.path.basename(repo_path)
        stem, suffix, ext = split_stem_suffix(filename)
        if ext not in (".md", ".json") or not suffix:
            continue
        episode = episodes.setdefault(stem, {
            "corpus": corpus, "stem": stem,
            "raw_suffixes": set(), "ref_suffixes": set(), "stage_suffixes": set(),
            "json_suffixes": set(), "s3_keys": [],
        })
        if ext == ".json":
            episode["json_suffixes"].add(suffix)
            continue
        if suffix in RAW_SUFFIXES:
            episode["raw_suffixes"].add(suffix)
        elif suffix in REF_SUFFIXES:
            episode["ref_suffixes"].add(suffix)
        else:
            episode["stage_suffixes"].add(suffix)
        episode["s3_keys"].append(row["s3_key"])
    # Keep only episodes relevant to eval pairing: at least one raw or reference transcript.
    return {stem: ep for stem, ep in episodes.items() if ep["raw_suffixes"] or ep["ref_suffixes"]}
def catalog_to_csv_rows(episodes):
    """Flatten episode records into sorted CSV row dicts."""
    csv_rows = []
    for stem in sorted(episodes):
        ep = episodes[stem]
        csv_rows.append({
            "corpus": ep["corpus"],
            "stem": stem,
            "raw_suffixes": ";".join(sorted(ep["raw_suffixes"])),
            "ref_suffixes": ";".join(sorted(ep["ref_suffixes"])),
            "stage_suffixes": ";".join(sorted(ep["stage_suffixes"])),
            "json_suffixes": ";".join(sorted(ep["json_suffixes"])),
            "has_pair": "yes" if ep["raw_suffixes"] and ep["ref_suffixes"] else "no",
            "s3_keys": ";".join(sorted(ep["s3_keys"])),
        })
    return csv_rows

### Summary
def summarize_corpus(episodes):
    """Return summary counts for one corpus' episode dict."""
    total = len(episodes)
    pairs = sum(1 for ep in episodes.values() if ep["raw_suffixes"] and ep["ref_suffixes"])
    raw_only = sum(1 for ep in episodes.values() if ep["raw_suffixes"] and not ep["ref_suffixes"])
    ref_only = sum(1 for ep in episodes.values() if ep["ref_suffixes"] and not ep["raw_suffixes"])
    return {"episodes": total, "pairs": pairs, "raw_only": raw_only, "ref_only": ref_only}
def print_summary(corpus, summary):
    """Print one corpus summary line."""
    print(f"{corpus:16s} episodes={summary['episodes']:5d}  raw+ref pairs={summary['pairs']:5d}  "
          f"raw-only={summary['raw_only']:5d}  ref-only={summary['ref_only']:5d}")

### Main
def main():
    repo_root = find_repo_root(os.path.dirname(os.path.abspath(__file__)))
    all_csv_rows = []
    print("Corpus inventory summary (episodes = stems with >=1 raw or reference transcript):")
    for corpus in CORPORA:
        manifest_path = os.path.join(repo_root, MANIFEST_DIR, f"{corpus}.manifest.jsonl")
        rows = load_manifest_rows(manifest_path)
        episodes = build_corpus_catalog(rows, corpus)
        print_summary(corpus, summarize_corpus(episodes))
        all_csv_rows.extend(catalog_to_csv_rows(episodes))
    catalog_path = os.path.join(repo_root, CATALOG_PATH)
    os.makedirs(os.path.dirname(catalog_path), exist_ok=True)
    fieldnames = ["corpus", "stem", "raw_suffixes", "ref_suffixes", "stage_suffixes",
                  "json_suffixes", "has_pair", "s3_keys"]
    with open(catalog_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_csv_rows)
    print(f"\nWrote {len(all_csv_rows)} catalog rows to {os.path.relpath(catalog_path, repo_root)}")
if __name__ == "__main__":
    sys.exit(main())
