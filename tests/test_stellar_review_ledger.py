"""Tests for Stellar Transcriber bulk review ledgers."""
import importlib
import importlib.util
import json
import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("ELEVENLABS_API_KEY", "unused-for-review-ledger-tests")
sys.modules.setdefault("elevenlabs", MagicMock())
sys.modules.setdefault("elevenlabs.client", MagicMock())

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
FIXTURE_SCRIPT = os.path.join(
    REPO_ROOT, "apps", "transcription", "stellar-transcriber", "scripts",
    "make_alignment_fixture.py",
)
def _ledger_module():
    assert importlib.util.find_spec("core.review_ledger") is not None
    return importlib.import_module("core.review_ledger")
def _fixture_module():
    spec = importlib.util.spec_from_file_location("make_alignment_fixture_review", FIXTURE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
def _write_transcript(path, segments):
    from core.denovo import segments_to_md_content
    path.write_text("## metadata\nlast updated: test\n\n\n" + segments_to_md_content(segments))
def test_single_review_ledger_marks_raw_errors_fixed_by_clean_draft(tmp_path):
    ledger = _ledger_module()
    fixture = _fixture_module().build_fixture_set(str(tmp_path / "fixture"), max_segments=30)
    payload = ledger.build_single_review_ledger(
        fixture["raw_a"], fixture["ref"], fixture["ref"], profile=None)
    assert payload["mode"] == "single"
    assert payload["summary"]["case_count"] > 0
    assert all(case["change_status"] == "fixed" for case in payload["cases"])
    assert all(case["text_raw"] and case["text_ref"] for case in payload["cases"])
def test_single_review_ledger_marks_new_draft_errors_made_worse(tmp_path):
    ledger = _ledger_module()
    fixture = _fixture_module().build_fixture_set(str(tmp_path / "fixture"), max_segments=30)
    payload = ledger.build_single_review_ledger(
        fixture["ref"], fixture["raw_a"], fixture["ref"], profile=None)
    assert any(case["change_status"] == "made_worse" for case in payload["cases"])
def test_review_fields_survive_regeneration(tmp_path):
    ledger = _ledger_module()
    fixture = _fixture_module().build_fixture_set(str(tmp_path / "fixture"), max_segments=30)
    payload = ledger.build_single_review_ledger(
        fixture["raw_a"], fixture["ref"], fixture["ref"], profile=None)
    payload["cases"][0]["review_status"] = "confirmed"
    payload["cases"][0]["review_category"] = "misplaced_phrase"
    payload["cases"][0]["review_notes"] = "Checked manually."
    out_path = tmp_path / "ledger.json"
    out_path.write_text(json.dumps(payload))
    regenerated = ledger.build_single_review_ledger(
        fixture["raw_a"], fixture["ref"], fixture["ref"],
        profile=None, existing_path=str(out_path))
    case = next(c for c in regenerated["cases"] if c["case_id"] == payload["cases"][0]["case_id"])
    assert case["review_status"] == "confirmed"
    assert case["review_category"] == "misplaced_phrase"
    assert case["review_notes"] == "Checked manually."
def test_match_dual_output_choices_detects_mixed_a_b_selection():
    ledger = _ledger_module()
    chunks = [
        {
            "chunk_id": 0,
            "a": {"segments": [{"speaker": "A", "timestamp": "0:01", "dialogue": "A first."}]},
            "b": {"segments": [{"speaker": "B", "timestamp": "0:02", "dialogue": "B first."}]},
        },
        {
            "chunk_id": 1,
            "a": {"segments": [{"speaker": "A", "timestamp": "0:11", "dialogue": "A second."}]},
            "b": {"segments": [{"speaker": "B", "timestamp": "0:12", "dialogue": "B second."}]},
        },
    ]
    output = [
        {"speaker": "A", "timestamp": "0:01", "dialogue": "A first."},
        {"speaker": "B", "timestamp": "0:12", "dialogue": "B second."},
    ]
    assert ledger.match_dual_output_choices(chunks, output) == {0: "a", 1: "b"}
def test_match_dual_output_choices_ignores_speaker_role_suffix():
    ledger = _ledger_module()
    chunks = [
        {
            "chunk_id": 0,
            "a": {"segments": [{"speaker": "Chris Raanes", "timestamp": "1:00", "dialogue": "Hello."}]},
            "b": {"segments": [{"speaker": "Chris Raanes", "timestamp": "1:00", "dialogue": "Hi there."}]},
        },
    ]
    output = [
        {"speaker": "Chris Raanes (EPC Chair)", "timestamp": "1:00", "dialogue": "Hi there."},
    ]
    assert ledger.match_dual_output_choices(chunks, output) == {0: "b"}
def test_dual_review_ledger_detects_exact_selected_source(tmp_path):
    ledger = _ledger_module()
    common_open = "Welcome everyone to the emergency preparedness committee meeting this morning here in town."
    middle = "We should review all current policies before making another recommendation to the full council."
    common_tail = "Let us move to the next agenda item and hear the staff report now."
    source_a = [
        {"speaker_full": "Chair", "speaker_name": "Chair", "timestamp": "0:01", "dialogue": common_open},
        {"speaker_full": "Member A", "speaker_name": "Member A", "timestamp": "0:20", "dialogue": middle},
        {"speaker_full": "Chair", "speaker_name": "Chair", "timestamp": "0:40", "dialogue": common_tail},
    ]
    source_b = [
        {"speaker_full": "Chair", "speaker_name": "Chair", "timestamp": "0:02", "dialogue": common_open},
        {"speaker_full": "Member B", "speaker_name": "Member B", "timestamp": "0:20", "dialogue": "We should review all current policies."},
        {"speaker_full": "Member C", "speaker_name": "Member C", "timestamp": "0:26", "dialogue": "Before making another recommendation to the full council."},
        {"speaker_full": "Chair", "speaker_name": "Chair", "timestamp": "0:41", "dialogue": common_tail},
    ]
    path_a = tmp_path / "ep_nova2gen.md"
    path_b = tmp_path / "ep_dgwhspm.md"
    path_dual = tmp_path / "ep_nova2gen_draftld.md"
    path_ref = tmp_path / "ep_ref.md"
    _write_transcript(path_a, source_a)
    _write_transcript(path_b, source_b)
    _write_transcript(path_dual, source_b)
    _write_transcript(path_ref, source_b)
    payload = ledger.build_dual_review_ledger(
        str(path_a), str(path_b), str(path_dual), str(path_ref), profile=None)
    assert payload["choices_matched_exactly"] is True
    assert payload["cases"]
    assert all(case["selected_source"] == "b" for case in payload["cases"])
    assert all(case["text_dual"] for case in payload["cases"])
def test_render_review_markdown_contains_cases_and_counts(tmp_path):
    ledger = _ledger_module()
    fixture = _fixture_module().build_fixture_set(str(tmp_path / "fixture"), max_segments=30)
    payload = ledger.build_single_review_ledger(
        fixture["raw_a"], fixture["ref"], fixture["ref"], profile=None)
    markdown = ledger.render_review_markdown(payload)
    assert "# Transcript Review Ledger" in markdown
    assert "## Category counts" in markdown
    assert payload["cases"][0]["case_id"] in markdown
def test_write_review_ledger_creates_json_and_markdown(tmp_path):
    ledger = _ledger_module()
    payload = {
        "mode": "single",
        "episode_stem": "episode",
        "summary": {"case_count": 0, "category_counts": {}, "status_counts": {}, "review_counts": {}},
        "cases": [],
    }
    json_path, markdown_path = ledger.write_review_ledger(payload, str(tmp_path / "ledger.json"))
    assert os.path.isfile(json_path)
    assert os.path.isfile(markdown_path)
