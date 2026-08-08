import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("ELEVENLABS_API_KEY", "unused")
sys.modules.setdefault("elevenlabs", MagicMock())
sys.modules.setdefault("elevenlabs.client", MagicMock())

import json

from core.transcript_eval import EVAL_CODE_VERSION, compute_subscore_alignment_loose, compute_subscore_alignment_strict

ERROR_COUNT_KEYS = [
    "seg_error_count",
    "seg_error_count_strict",
    "seg_missing_count",
    "seg_spurious_count",
    "seg_boundary_error_count",
    "seg_boundary_misplaced_count",
]

### Records
def _metric_value(metrics, key):
    value = metrics.get(key, 0)
    return 0 if value is None or value == "" else value
def _mean(values):
    if not values:
        return None
    return round(sum(values) / float(len(values)), 1)
def build_episode_record(stem, asr, mode, windows_result, classify_summary=None):
    """
    Build one episode/asr ledger record from extracted misalignment windows.

    :param stem: str episode stem.
    :param asr: str ASR source label.
    :param mode: str extraction mode.
    :param windows_result: dict returned by core.transcript_misalign.
    :param classify_summary: optional dict returned by core.misalign_classify.
    :return record: dict episode ledger record.
    """
    metrics = dict(windows_result.get("metrics") or {})
    scoring_metrics = dict(metrics)
    scoring_metrics["total_ref_segments"] = windows_result.get("total_ref_segments")
    strict = round(compute_subscore_alignment_strict(scoring_metrics), 1)
    loose = round(compute_subscore_alignment_loose(scoring_metrics), 1)
    return {
        "stem": stem,
        "asr": asr,
        "mode": mode,
        "total_ref_segments": windows_result.get("total_ref_segments"),
        "n_windows": len(windows_result.get("windows") or []),
        "strict": strict,
        "loose": loose,
        "seg_error_count": _metric_value(metrics, "seg_error_count"),
        "seg_error_count_strict": _metric_value(metrics, "seg_error_count_strict"),
        "seg_missing_count": _metric_value(metrics, "seg_missing_count"),
        "seg_spurious_count": _metric_value(metrics, "seg_spurious_count"),
        "seg_boundary_error_count": _metric_value(metrics, "seg_boundary_error_count"),
        "seg_boundary_misplaced_count": _metric_value(metrics, "seg_boundary_misplaced_count"),
        "label_counts": classify_summary["label_counts"] if classify_summary else {},
        "repairable_count": classify_summary["repairable_count"] if classify_summary else None,
        "not_repairable_count": classify_summary["not_repairable_count"] if classify_summary else None,
    }
def build_run_record(run_id, datetime, mode, corpus, profile, classifier_model, policy_id, episode_records, output_dir, notes=""):
    """
    Build one append-only run ledger record.

    :param run_id: str run identifier.
    :param datetime: str file-friendly run datetime.
    :param mode: str extraction mode.
    :param corpus: str corpus label.
    :param profile: str eval profile label.
    :param classifier_model: str classifier model or dry-run marker.
    :param policy_id: str normalization policy id.
    :param episode_records: list of episode ledger records.
    :param output_dir: str output directory for window JSON files.
    :param notes: optional str run notes.
    :return record: dict run ledger record.
    """
    from core.denovo import DENOVO_PIPELINE_VERSION

    means = {
        "strict": _mean([record["strict"] for record in episode_records]),
        "loose": _mean([record["loose"] for record in episode_records]),
    }
    for key in ERROR_COUNT_KEYS:
        means[key] = sum(_metric_value(record, key) for record in episode_records)
    return {
        "run_id": run_id,
        "datetime": datetime,
        "mode": mode,
        "corpus": corpus,
        "profile": profile,
        "classifier_model": classifier_model,
        "policy_id": policy_id,
        "denovo_pipeline_version": DENOVO_PIPELINE_VERSION,
        "eval_code_version": EVAL_CODE_VERSION,
        "episodes": episode_records,
        "means": means,
        "output_dir": output_dir,
        "notes": notes,
    }
def append_run_record(record, jsonl_path):
    """
    Append one run record as JSONL, creating parent directories.

    :param record: dict run record.
    :param jsonl_path: str JSONL path.
    :return jsonl_path: str written path.
    """
    parent = os.path.dirname(os.path.abspath(jsonl_path))
    os.makedirs(parent, exist_ok=True)
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return jsonl_path
def load_run_log(jsonl_path):
    """
    Load run records from JSONL.

    :param jsonl_path: str JSONL path.
    :return records: list of run record dicts.
    """
    if not os.path.isfile(jsonl_path):
        return []
    records = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records

### Markdown
def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def _escape_md_cell(value):
    if value is None:
        return "—"
    return str(value).replace("|", "\\|")
def _top_labels(label_counts, limit=3):
    if not label_counts:
        return "—"
    items = sorted(label_counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return ", ".join(f"{label}:{count}" for label, count in items)
def _render_episode_table(episodes):
    lines = [
        "| Episode | ASR | strict | loose | missing | spurious | misplaced | windows | repairable | labels(top-3) |",
        "|---------|-----|--------|-------|---------|----------|-----------|---------|------------|---------------|",
    ]
    for episode in episodes:
        repairable = episode.get("repairable_count")
        repairable_cell = "—" if repairable is None else str(repairable)
        lines.append(
            "| "
            + " | ".join([
                _escape_md_cell(episode.get("stem")),
                _escape_md_cell(episode.get("asr")),
                _escape_md_cell(episode.get("strict")),
                _escape_md_cell(episode.get("loose")),
                _escape_md_cell(episode.get("seg_missing_count")),
                _escape_md_cell(episode.get("seg_spurious_count")),
                _escape_md_cell(episode.get("seg_boundary_misplaced_count")),
                _escape_md_cell(episode.get("n_windows")),
                repairable_cell,
                _escape_md_cell(_top_labels(episode.get("label_counts") or {})),
            ])
            + " |"
        )
    return lines
def _means_line(record):
    means = record.get("means") or {}
    return (
        f"Means: strict {means.get('strict', '—')}, loose {means.get('loose', '—')}; "
        f"errors {means.get('seg_error_count', 0)}, strict errors {means.get('seg_error_count_strict', 0)}, "
        f"missing {means.get('seg_missing_count', 0)}, spurious {means.get('seg_spurious_count', 0)}, "
        f"misplaced {means.get('seg_boundary_misplaced_count', 0)}."
    )
def render_run_log_md(jsonl_path, md_path):
    """
    Render the JSONL run log as a readable markdown summary.

    :param jsonl_path: str JSONL source path.
    :param md_path: str markdown output path.
    :return md_path: str written path.
    """
    records = load_run_log(jsonl_path)
    rel_md = os.path.relpath(os.path.abspath(md_path), _repo_root())
    lines = [
        f"file: {rel_md}",
        "title: Stellar Transcriber — run + results log",
        "last-updated:",
        "ai:",
        "session:",
        "",
        "# Stellar Transcriber — run + results log",
        "",
        "Generated from stellar-run-log.jsonl",
    ]
    for record in reversed(records):
        lines.extend([
            "",
            "",
            f"## {record.get('run_id')} — {record.get('mode')} (denovo {record.get('denovo_pipeline_version')} / eval {record.get('eval_code_version')})",
            "",
            f"Corpus `{record.get('corpus')}` · profile `{record.get('profile')}` · classifier `{record.get('classifier_model')}` · policy `{record.get('policy_id')}` · notes: {record.get('notes') or '—'}",
            "",
        ])
        lines.extend(_render_episode_table(record.get("episodes") or []))
        lines.extend(["", _means_line(record)])
    parent = os.path.dirname(os.path.abspath(md_path))
    os.makedirs(parent, exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")
    return md_path
