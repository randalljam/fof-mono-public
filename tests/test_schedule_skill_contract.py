#!/usr/bin/env python3
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "skills/family/schedule-coordinator/scripts/schedule_files.py"
ROLLOVER_SCRIPT = (
    REPO_ROOT
    / "skills/family/schedule-coordinator/scripts/weekly_rollover.py"
)
CANONICAL_SKILL = REPO_ROOT / "skills/family/schedule-coordinator/README.md"
HERMES_WRAPPER = REPO_ROOT / "agents/hermes/skills/family/schedule-coordinator/SKILL.md"
SCHEDULE_SCHEMA = (
    REPO_ROOT
    / "skills/family/schedule-coordinator/references/schedule-schema.md"
)
def _load_contract():
    spec = importlib.util.spec_from_file_location("schedule_files_contract", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
def _load_rollover_contract():
    spec = importlib.util.spec_from_file_location(
        "weekly_rollover_contract", ROLLOVER_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
def test_canonical_and_hermes_skills_pin_same_routing_contract():
    contract_id = _load_contract().ROUTING_CONTRACT_ID
    canonical = CANONICAL_SKILL.read_text(encoding="utf-8")
    wrapper = HERMES_WRAPPER.read_text(encoding="utf-8")
    assert contract_id == "family-schedule-routing-v1"
    assert contract_id in canonical
    assert contract_id in wrapper
def test_hermes_wrapper_derives_routing_and_format_from_canonical_skill():
    canonical = CANONICAL_SKILL.read_text(encoding="utf-8")
    wrapper = HERMES_WRAPPER.read_text(encoding="utf-8")
    assert "skills/family/schedule-coordinator/README.md" in wrapper
    assert "/opt/data/repo/skills/family/schedule-coordinator/scripts/schedule_files.py route" in wrapper
    assert "/opt/data/repo/skills/family/schedule-coordinator/references/schedule-schema.md" in wrapper
    assert "- **{blocked_time}** {who} — {title}" in canonical
    assert "- **{blocked_time}** {who} — {title}" not in wrapper
def test_both_skills_forbid_authoring_dashboard_aliases():
    canonical = CANONICAL_SKILL.read_text(encoding="utf-8")
    wrapper = HERMES_WRAPPER.read_text(encoding="utf-8")
    for text in (canonical, wrapper):
        assert "current-week.md" in text
        assert "next-week.md" in text
        assert "never" in text.casefold()
def test_canonical_and_hermes_skills_pin_automatic_rollover_contract():
    contract_id = _load_rollover_contract().ROLLOVER_CONTRACT_ID
    canonical = CANONICAL_SKILL.read_text(encoding="utf-8")
    wrapper = HERMES_WRAPPER.read_text(encoding="utf-8")
    assert contract_id == "family-schedule-weekly-rollover-v1"
    assert contract_id in canonical
    assert contract_id in wrapper
    for text in (canonical, wrapper):
        assert "bootstrap" in text.casefold()
        assert "proposal-sha256" in text
        assert "America/Los_Angeles" in text
def test_canonical_schema_and_hermes_pin_multiday_materialization_contract():
    canonical = CANONICAL_SKILL.read_text(encoding="utf-8")
    schema = SCHEDULE_SCHEMA.read_text(encoding="utf-8")
    wrapper = HERMES_WRAPPER.read_text(encoding="utf-8")
    for text in (canonical, schema, wrapper):
        assert "YYYY-MM-DD through YYYY-MM-DD" in text
        assert "individual" in text.casefold() or "one ordinary entry" in text
        assert "residual" in text.casefold() or "unconsumed" in text.casefold()
    for text in (canonical, wrapper):
        assert "repair-range" in text
        assert "--source-sha256" in text
        assert "--proposal-sha256" in text
