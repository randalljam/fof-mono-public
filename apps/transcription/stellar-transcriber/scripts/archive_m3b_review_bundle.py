"""
Build M3B five-file review bundle: inputs, per-model drafts, eval artifacts, S3 manifest.

Run from repo root after model comparison runs:
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/archive_m3b_review_bundle.py --regenerate-missing
    .venv/bin/python3 apps/transcription/stellar-transcriber/scripts/archive_m3b_review_bundle.py --regenerate-missing --upload
"""
import argparse
import json
import os
import shutil
import sys

BUNDLE_REL = os.path.join("data", "stellar-eval", "m3b-five-model-review")
MANIFEST_AREA = "stellar-eval_m3b-five-review"
MODELS = [
    {
        "slug": "gpt-5-mini",
        "model_tier": "cheap",
        "provider": "openai",
        "eval_run_dir": "m3b-five-2026-07-03_131152",
        "regenerate": True,
    },
    {
        "slug": "gpt-5.4",
        "model_tier": "standard",
        "provider": "openai",
        "eval_run_dir": "m3b-gpt54-2026-07-03_140715",
        "regenerate": True,
    },
    {
        "slug": "claude-sonnet-4-6",
        "model_tier": "standard",
        "provider": "anthropic",
        "eval_run_dir": "m3b-claude-sonnet-4-6-2026-07-03_142343",
        "regenerate": False,
    },
]
REPORT_FILES = [
    "m3b-model-comparison.md",
    "m3b-results-five.md",
    "m3b-results-five-gpt54.md",
    "m3b-results-five-claude-sonnet-4-6.md",
    "m3b-results-single.md",
    "m3b-episode-selection.md",
]

def find_repo_root(start_dir):
    catalog = os.path.join("apps", "transcription", "stellar-transcriber", "references", "corpus-inventory-catalog.csv")
    current = os.path.abspath(start_dir)
    while True:
        if os.path.isfile(os.path.join(current, catalog)):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            raise FileNotFoundError(f"Could not locate repo root containing {catalog}")
        current = parent

_REPO_ROOT = find_repo_root(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
os.environ.setdefault("ELEVENLABS_API_KEY", "unused-for-m3b-archive")
from unittest.mock import MagicMock
sys.modules.setdefault("elevenlabs", MagicMock())
sys.modules.setdefault("elevenlabs.client", MagicMock())

from core.denovo import merge_dual_llm
from core.fileops import add_suffix_in_str, get_current_datetime_filefriendly

def import_m3b():
    import importlib.util
    script = os.path.join(_REPO_ROOT, "apps", "transcription", "stellar-transcriber", "scripts", "run_m3b_dual_llm_eval.py")
    spec = importlib.util.spec_from_file_location("m3b_eval", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path

def copy_if_exists(src, dst):
    if os.path.isfile(src):
        ensure_dir(os.path.dirname(dst))
        shutil.copy2(src, dst)
        return True
    return False

def archive_inputs(m3b, bundle_root):
    inputs_dir = ensure_dir(os.path.join(bundle_root, "inputs"))
    copied = []
    for stem in m3b.M3B_NEXT_FIVE:
        paths = m3b.resolve_episode_paths(_REPO_ROOT, stem, "deutsch")
        if not paths:
            print(f"SKIP inputs — no paths for {stem}", flush=True)
            continue
        for key, label in [("raw_a", "nova2gen"), ("raw_b", "dgwhspm"), ("ref", "vrb")]:
            src = paths[key]
            dst = os.path.join(inputs_dir, f"{stem}_{label}.md")
            if copy_if_exists(src, dst):
                copied.append(os.path.relpath(dst, _REPO_ROOT))
    return copied

def archive_reports(bundle_root):
    refs = os.path.join(_REPO_ROOT, "apps", "transcription", "stellar-transcriber", "references")
    reports_dir = ensure_dir(os.path.join(bundle_root, "reports"))
    copied = []
    for name in REPORT_FILES:
        src = os.path.join(refs, name)
        if copy_if_exists(src, os.path.join(reports_dir, name)):
            copied.append(f"reports/{name}")
    return copied

def archive_eval_artifacts(bundle_root, eval_base, eval_run_dir):
    src_dir = os.path.join(eval_base, eval_run_dir)
    if not os.path.isdir(src_dir):
        return []
    dst_dir = ensure_dir(os.path.join(bundle_root, "eval", eval_run_dir))
    copied = []
    for name in ("eval_metrics.csv", "eval_log.md"):
        if copy_if_exists(os.path.join(src_dir, name), os.path.join(dst_dir, name)):
            copied.append(f"eval/{eval_run_dir}/{name}")
    seg_src = os.path.join(src_dir, "eval-seg_csv_files")
    if os.path.isdir(seg_src):
        seg_dst = ensure_dir(os.path.join(dst_dir, "eval-seg_csv_files"))
        for fn in os.listdir(seg_src):
            if fn.endswith(".csv"):
                shutil.copy2(os.path.join(seg_src, fn), os.path.join(seg_dst, fn))
                copied.append(f"eval/{eval_run_dir}/eval-seg_csv_files/{fn}")
    return copied

def archive_draft_for_model(m3b, bundle_root, model_cfg, regenerate):
    slug = model_cfg["slug"]
    draft_dir = ensure_dir(os.path.join(bundle_root, "drafts", slug))
    archived = []
    total_cost = 0.0
    for stem in m3b.M3B_NEXT_FIVE:
        paths = m3b.resolve_episode_paths(_REPO_ROOT, stem, "deutsch")
        if not paths:
            continue
        dst = os.path.join(draft_dir, f"{stem}_draftld.md")
        if regenerate:
            print(f"Regenerating draft: {slug} / {stem}", flush=True)
            _, summary = merge_dual_llm(
                paths["raw_a"], paths["raw_b"],
                profile="deutsch",
                model_tier=model_cfg["model_tier"],
                provider=model_cfg["provider"],
                verbose=True,
                return_summary=True,
            )
            src = add_suffix_in_str(paths["raw_a"], "_draftld")
            shutil.copy2(src, dst)
            total_cost += summary.get("total_cost_usd", 0)
        else:
            src = add_suffix_in_str(paths["raw_a"], "_draftld")
            if not os.path.isfile(src):
                print(f"WARN missing draft for {stem}, expected {src}", flush=True)
                continue
            shutil.copy2(src, dst)
        archived.append(f"drafts/{slug}/{os.path.basename(dst)}")
    return archived, total_cost

def write_bundle_index(bundle_root, index):
    path = os.path.join(bundle_root, "bundle-index.json")
    with open(path, "w") as f:
        json.dump(index, f, indent=2)
    return os.path.relpath(path, _REPO_ROOT)

def build_and_upload(upload):
    from core.s3_archive import build_area_manifest, upload_corpus
    records = build_area_manifest(
        MANIFEST_AREA,
        BUNDLE_REL,
        repo_root=_REPO_ROOT,
        compute_hash=True,
        respect_gitignore=False,
    )
    print(f"Manifest: {len(records)} files in {MANIFEST_AREA}", flush=True)
    if upload:
        summary = upload_corpus(MANIFEST_AREA, repo_root=_REPO_ROOT, execute=True)
        print(f"Upload summary: {summary}", flush=True)
        return summary
    upload_corpus(MANIFEST_AREA, repo_root=_REPO_ROOT, execute=False)
    return {"planned": len(records)}

def main():
    parser = argparse.ArgumentParser(description="Archive M3B review bundle for cloud reviewer")
    parser.add_argument("--regenerate-missing", action="store_true", help="Re-run LLM merge for models not preserved locally")
    parser.add_argument("--upload", action="store_true", help="Upload bundle to S3 after build (requires AWS creds)")
    args = parser.parse_args()
    m3b = import_m3b()
    bundle_root = os.path.join(_REPO_ROOT, BUNDLE_REL)
    ensure_dir(bundle_root)
    ts = get_current_datetime_filefriendly()
    index = {
        "bundle": BUNDLE_REL,
        "created": ts,
        "episodes": m3b.M3B_NEXT_FIVE,
        "models": [m["slug"] for m in MODELS],
        "review_index_repo_path": "apps/transcription/stellar-transcriber/references/m3b-model-comparison.md",
        "files": {},
        "regeneration_cost_usd": {},
    }
    index["files"]["inputs"] = archive_inputs(m3b, bundle_root)
    index["files"]["reports"] = archive_reports(bundle_root)
    eval_base = os.path.join(_REPO_ROOT, "data", "stellar-eval", "deutsch")
    index["files"]["eval"] = []
    for model_cfg in MODELS:
        index["files"]["eval"].extend(
            archive_eval_artifacts(bundle_root, eval_base, model_cfg["eval_run_dir"]))
    for model_cfg in MODELS:
        do_regen = args.regenerate_missing and model_cfg.get("regenerate")
        drafts, cost = archive_draft_for_model(m3b, bundle_root, model_cfg, regenerate=do_regen)
        index["files"][f"drafts_{model_cfg['slug']}"] = drafts
        if cost:
            index["regeneration_cost_usd"][model_cfg["slug"]] = round(cost, 4)
    index_path = write_bundle_index(bundle_root, index)
    print(f"Wrote {index_path}", flush=True)
    upload_summary = build_and_upload(args.upload)
    index["s3_manifest_area"] = MANIFEST_AREA
    index["upload"] = upload_summary
    write_bundle_index(bundle_root, index)
    return 0

if __name__ == "__main__":
    sys.exit(main())
