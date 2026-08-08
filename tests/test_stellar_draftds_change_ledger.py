"""Tests for pipeline change ledgers."""
import importlib
import json
import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("ELEVENLABS_API_KEY", "unused-for-draftds-change-ledger-tests")
sys.modules.setdefault("elevenlabs", MagicMock())
sys.modules.setdefault("elevenlabs.client", MagicMock())

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
def _module():
    return importlib.import_module("core.draftds_change_ledger")
def test_build_draftds_change_ledger_records_blip_merge():
    ledger = _module()
    segments = [
        {
            "speaker_name": "Chris Raanes",
            "speaker_full": "Chris Raanes",
            "timestamp": "46:21",
            "dialogue": "You can",
        },
        {
            "speaker_name": "Speaker 1",
            "speaker_full": "Speaker 1",
            "timestamp": "46:21",
            "dialogue": "hear me",
        },
        {
            "speaker_name": "Chris Raanes",
            "speaker_full": "Chris Raanes",
            "timestamp": "46:21",
            "dialogue": "okay here?",
        },
    ]
    raw_path = os.path.join(REPO_ROOT, "tests", "tmp_draftds_change_raw.md")
    try:
        from core.denovo import segments_to_md_content
        with open(raw_path, "w") as handle:
            handle.write("## metadata\nlast updated: test\n\n\n" + segments_to_md_content(segments))
        payload = ledger.build_draftds_change_ledger(raw_path, profile=None)
        assert payload["mode"] == "draftds_change"
        assert payload["summary"]["change_count"] > 0
        assert any(case["change_type"] == "short_speaker_blip" for case in payload["cases"])
        blip = next(case for case in payload["cases"] if case["change_type"] == "short_speaker_blip")
        assert "hear" in blip["change_summary"]
    finally:
        if os.path.isfile(raw_path):
            os.remove(raw_path)
def test_render_pipeline_change_markdown_is_summary_only():
    ledger = _module()
    payload = {
        "mode": "pipeline_change",
        "episode_stem": "sample",
        "summary": {"stage_count": 2, "change_count": 3, "stage_ids": ["raw_to_draftds", "draftds_to_draftls"]},
        "stages": [
            {
                "stage_id": "raw_to_draftds",
                "label": "raw → draftds",
                "input_segment_count": 4,
                "output_segment_count": 3,
                "net_segment_delta": -1,
                "change_count": 2,
                "change_type_labels": ledger.FIX_LABELS,
            },
            {
                "stage_id": "draftds_to_draftls",
                "label": "draftds → draftls",
                "input_segment_count": 3,
                "output_segment_count": 3,
                "net_segment_delta": 0,
                "change_count": 1,
                "change_type_labels": ledger.LLM_CHANGE_LABELS,
            },
        ],
        "cases": [
            {
                "case_id": "sample::raw_to_draftds::fix-0000-short_speaker_blip",
                "stage_id": "raw_to_draftds",
                "change_type": "short_speaker_blip",
                "timestamp_start": "1:00",
            },
            {
                "case_id": "sample::raw_to_draftds::fix-0001-interrupted_turn_ellipsis",
                "stage_id": "raw_to_draftds",
                "change_type": "interrupted_turn_ellipsis",
                "timestamp_start": "2:00",
            },
            {
                "case_id": "sample::draftds_to_draftls::change-0000-speaker_change",
                "stage_id": "draftds_to_draftls",
                "change_type": "speaker_change",
                "timestamp_start": "3:00",
            },
        ],
    }
    markdown = ledger.render_pipeline_change_markdown(payload)
    assert "## All stages" in markdown
    assert "| Decisions |" in markdown
    assert "Stages in this report" in ledger.render_pipeline_change_markdown({
        **payload,
        "run_timestamp": "2026-07-17_120000",
    })
    assert "| `short_speaker_blip` |" in markdown
    assert "| `speaker_change` |" in markdown
    assert "#### Before (raw)" not in markdown
    assert "```text" not in markdown
def test_pipeline_change_ledger_runs_single_stage_from_raw(tmp_path):
    ledger = _module()
    segments = [
        {"speaker_name": "A", "speaker_full": "A", "timestamp": "0:01", "dialogue": "Hello."},
        {"speaker_name": "B", "speaker_full": "B", "timestamp": "0:02", "dialogue": "World."},
    ]
    from core.denovo import segments_to_md_content
    raw_path = tmp_path / "raw.md"
    raw_path.write_text("## metadata\nlast updated: test\n\n\n" + segments_to_md_content(segments))
    payload = ledger.build_pipeline_change_ledger(raw_path=str(raw_path), profile=None)
    assert payload["mode"] == "pipeline_change"
    assert payload["summary"]["stage_ids"] == ["raw_to_draftds"]
def test_pipeline_change_ledger_labels_ab_arms(tmp_path):
    ledger = _module()
    from core.denovo import segments_to_md_content
    header = "## metadata\nlast updated: test\n\n\n"
    segments = [
        {"speaker_name": "A", "speaker_full": "A", "timestamp": "0:01", "dialogue": "Hello."},
    ]
    raw_a = tmp_path / "2025-03-06_PV-EPC_spasgn_nova2gen.md"
    raw_b = tmp_path / "2025-03-06_PV-EPC_spasgn_dgwhspm.md"
    raw_a.write_text(header + segments_to_md_content(segments))
    raw_b.write_text(header + segments_to_md_content(segments))
    payload = ledger.build_pipeline_change_ledger(
        raw_a_path=str(raw_a), raw_b_path=str(raw_b), profile=None)
    labels = [stage["label"] for stage in payload["stages"]]
    assert labels[0] == "raw_A_nova2gen → draftds_A"
    assert labels[1] == "raw_B_dgwhspm → draftds_B"
    assert payload["episode_stem"] == "2025-03-06_PV-EPC"
    assert payload["summary"]["stage_ids"] == ["raw_to_draftds_a", "raw_to_draftds_b"]
def test_review_fields_survive_regeneration(tmp_path):
    ledger = _module()
    segments = [
        {"speaker_name": "A", "speaker_full": "A", "timestamp": "0:01", "dialogue": "Hello there"},
        {"speaker_name": "B", "speaker_full": "B", "timestamp": "0:02", "dialogue": "World."},
    ]
    raw_path = tmp_path / "raw.md"
    from core.denovo import segments_to_md_content
    raw_path.write_text("## metadata\nlast updated: test\n\n\n" + segments_to_md_content(segments))
    payload = ledger.build_pipeline_change_ledger(raw_path=str(raw_path), profile=None)
    payload["cases"][0]["review_status"] = "confirmed"
    payload["cases"][0]["review_notes"] = "Looks correct."
    out_path = tmp_path / "ledger.json"
    out_path.write_text(json.dumps(payload))
    regenerated = ledger.build_pipeline_change_ledger(
        raw_path=str(raw_path), profile=None, existing_path=str(out_path))
    assert regenerated["cases"][0]["review_status"] == "confirmed"
    assert regenerated["cases"][0]["review_notes"] == "Looks correct."
