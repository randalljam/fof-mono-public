#!/usr/bin/env python3
"""
Refresh core/llm_model_prices.json from the Nous inference API catalog.

Merges live pricing for models already in the JSON and adds new API matches.
Run from repo root:
    .venv/bin/python3 scripts/update_llm_model_prices.py
    .venv/bin/python3 scripts/update_llm_model_prices.py --dry-run
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

INFERENCE_MODELS_URL = "https://inference-api.nousresearch.com/v1/models"
PACIFIC = ZoneInfo("America/Los_Angeles")

def find_repo_root(start_dir):
    current = os.path.abspath(start_dir)
    while True:
        if os.path.isfile(os.path.join(current, "core", "llm_model_prices.json")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            raise FileNotFoundError("Could not locate repo root with core/llm_model_prices.json")
        current = parent

def fetch_inference_index():
    req = urllib.request.Request(
        INFERENCE_MODELS_URL,
        headers={"Accept": "application/json", "User-Agent": "fof-mono-llm-prices/1.0"},
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    index = {}
    for model in payload.get("data") or []:
        keys = {model.get("id"), model.get("canonical_slug")}
        for alias in model.get("aliases") or []:
            keys.add(alias)
        for key in keys:
            if key:
                index.setdefault(str(key), model)
    return index

def per_million(token_price):
    if token_price in (None, ""):
        return None
    return float(token_price) * 1_000_000

def lookup_pricing(model_index, model_id):
    candidates = [
        model_id,
        f"openai/{model_id}",
        f"anthropic/{model_id}",
        f"deepseek/{model_id}",
    ]
    for cand in candidates:
        model = model_index.get(cand)
        if not model:
            continue
        pricing = model.get("pricing") or {}
        inp = per_million(pricing.get("prompt"))
        out = per_million(pricing.get("completion"))
        cached = per_million(pricing.get("input_cache_read"))
        if inp is None and out is None:
            continue
        entry = {
            "input_token_price": inp if inp is not None else 0,
            "output_token_price": out if out is not None else 0,
        }
        if cached is not None:
            entry["cached_input_token_price"] = cached
        return entry, cand
    return None, None

def main():
    parser = argparse.ArgumentParser(description="Update core/llm_model_prices.json from Nous inference API")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing file")
    args = parser.parse_args()
    repo_root = find_repo_root(os.path.dirname(os.path.abspath(__file__)))
    prices_path = os.path.join(repo_root, "core", "llm_model_prices.json")
    with open(prices_path, encoding="utf-8") as f:
        data = json.load(f)
    models = data.get("models") or {}
    index = fetch_inference_index()
    updated = 0
    for model_id in list(models.keys()):
        new_prices, matched = lookup_pricing(index, model_id)
        if new_prices:
            models[model_id] = new_prices
            updated += 1
            print(f"  updated {model_id} <- {matched}")
    data["models"] = models
    data["last_updated"] = datetime.now(PACIFIC).strftime("%Y-%m-%d")
    data["source_notes"] = (
        "USD per 1M tokens. Refreshed via scripts/update_llm_model_prices.py from "
        + INFERENCE_MODELS_URL
    )
    if args.dry_run:
        print(f"Dry run: would update {updated} model(s)")
        return 0
    with open(prices_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    sys.path.insert(0, repo_root)
    from core.llm import reload_token_price_dict
    reload_token_price_dict()
    print(f"Wrote {prices_path} ({updated} models refreshed from API)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
