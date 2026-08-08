#!/usr/bin/env python3
import importlib.util
import json
import os
import subprocess
import sys
from argparse import Namespace
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = (
    REPO_ROOT
    / "skills/family/schedule-coordinator/scripts/weekly_rollover.py"
)
HERMES_WRAPPER = REPO_ROOT / "agents/hermes/family_schedule_weekly_rollover.py"
RUNTIME_JOBS = REPO_ROOT / "agents/hermes/runtime_cron_jobs.json"
HERMES_CONFIG_SYNC = REPO_ROOT / "agents/hermes/sync_hermes_config.py"
def _load():
    spec = importlib.util.spec_from_file_location(
        "family_schedule_weekly_rollover", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
def _horizon(*upcoming_lines):
    return "\n".join([
        "file: schedule/horizon_family-schedule.md",
        "",
        "## Recurring",
        "- **Gymnastics** · Mon 4:00p",
        "",
        "## Upcoming",
        "",
        "### Next 2 weeks",
        *upcoming_lines,
        "",
        "### Later",
        "- 2026-09-15 · Back to school",
        "",
        "## Notes",
        "- preserve this note",
        "",
    ])
def _write_state(module, schedule_dir, boundary):
    path = schedule_dir / module.STATE_FILENAME
    path.write_text(module._state_content(boundary), encoding="utf-8")
def test_pacific_boundary_guard_is_dst_safe_for_pst_and_pdt():
    module = _load()
    assert module.active_boundary_monday(
        datetime(2026, 1, 5, 7, 59, tzinfo=timezone.utc)
    ) == date(2025, 12, 29)
    assert module.active_boundary_monday(
        datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc)
    ) == date(2026, 1, 5)
    assert module.active_boundary_monday(
        datetime(2026, 3, 9, 6, 59, tzinfo=timezone.utc)
    ) == date(2026, 3, 2)
    assert module.active_boundary_monday(
        datetime(2026, 3, 9, 7, 0, tzinfo=timezone.utc)
    ) == date(2026, 3, 9)
def test_scheduled_mode_without_bootstrap_is_non_mutating(tmp_path):
    module = _load()
    horizon_path = tmp_path / module.HORIZON_FILENAME
    horizon_path.write_text(_horizon("- 2026-08-03 · Soccer camp"), encoding="utf-8")
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    with pytest.raises(module.BootstrapRequiredError, match="bootstrap required"):
        module.run_scheduled(tmp_path, now="2026-07-27T00:00:00-07:00")
    after = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    assert after == before
    assert not (tmp_path / module.LOCK_FILENAME).exists()
def test_bootstrap_dry_run_inventories_diff_and_writes_nothing(tmp_path):
    module = _load()
    horizon_path = tmp_path / module.HORIZON_FILENAME
    horizon_path.write_text(
        _horizon(
            "- 2026-08-03 (Mon) · Soccer camp · 9:00a–3:00p",
            "  Pack lunch and sunscreen",
            "- 2026-08-15 · Keep this in Horizon",
        ),
        encoding="utf-8",
    )
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    proposal = module.bootstrap(
        tmp_path, now="2026-07-29T12:00:00-07:00")
    rendered = module.render_proposal(proposal)
    after = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    assert after == before
    assert proposal["target_monday"] == "2026-08-03"
    assert len(proposal["inventory"]) == 1
    assert "Soccer camp" in rendered
    assert "proposal-sha256:" in rendered
    assert "--- " in rendered
    assert "+++ " in rendered
    assert not (tmp_path / module.LOCK_FILENAME).exists()
    assert not (tmp_path / module.STATE_FILENAME).exists()
    assert not (tmp_path / "2026-08-03_week_family-schedule.md").exists()
def test_bootstrap_apply_requires_matching_reviewed_digest(tmp_path):
    module = _load()
    horizon_path = tmp_path / module.HORIZON_FILENAME
    horizon_path.write_text(
        _horizon("- 2026-08-03 · Soccer camp"), encoding="utf-8")
    proposal = module.bootstrap(
        tmp_path, now="2026-07-29T12:00:00-07:00")
    with pytest.raises(module.ProposalChangedError, match="required"):
        module.bootstrap(
            tmp_path,
            now="2026-07-29T12:00:00-07:00",
            apply=True,
        )
    assert not (tmp_path / module.STATE_FILENAME).exists()
    with pytest.raises(module.ProposalChangedError, match="proposal changed"):
        module.bootstrap(
            tmp_path,
            now="2026-07-29T12:00:00-07:00",
            apply=True,
            proposal_sha256="0" * 64,
        )
    assert not (tmp_path / module.STATE_FILENAME).exists()
    applied = module.bootstrap(
        tmp_path,
        now="2026-07-29T12:00:00-07:00",
        apply=True,
        proposal_sha256=proposal["sha256"],
    )
    state = json.loads(
        (tmp_path / module.STATE_FILENAME).read_text(encoding="utf-8"))
    destination = (
        tmp_path / "2026-08-03_week_family-schedule.md"
    ).read_text(encoding="utf-8")
    horizon = horizon_path.read_text(encoding="utf-8")
    assert applied["sha256"] == proposal["sha256"]
    assert state["last_completed_boundary"] == "2026-07-27"
    assert "Soccer camp" in destination
    assert "family-schedule-source: horizon:" in destination
    assert "Soccer camp" not in horizon
    assert "Back to school" in horizon
def test_bootstrap_rejects_a_stale_digest_without_schedule_mutation(tmp_path):
    module = _load()
    horizon_path = tmp_path / module.HORIZON_FILENAME
    horizon_path.write_text(
        _horizon("- 2026-08-03 · Soccer camp"), encoding="utf-8")
    proposal = module.bootstrap(
        tmp_path, now="2026-07-29T12:00:00-07:00")
    changed_horizon = horizon_path.read_text(encoding="utf-8").replace(
        "preserve this note", "a user changed this note")
    horizon_path.write_text(changed_horizon, encoding="utf-8")
    with pytest.raises(module.ProposalChangedError, match="proposal changed"):
        module.bootstrap(
            tmp_path,
            now="2026-07-29T12:00:00-07:00",
            apply=True,
            proposal_sha256=proposal["sha256"],
        )
    assert horizon_path.read_text(encoding="utf-8") == changed_horizon
    assert not (tmp_path / module.STATE_FILENAME).exists()
    assert not (tmp_path / "2026-08-03_week_family-schedule.md").exists()
def test_promotion_includes_both_week_edges_and_preserves_later_items(tmp_path):
    module = _load()
    horizon_path = tmp_path / module.HORIZON_FILENAME
    horizon_path.write_text(
        _horizon(
            "- 2026-08-03 (Mon) · Monday edge",
            "- 2026-08-09 (Sun) · Sunday edge",
            "  Keep this continuation with Sunday",
            "- 2026-08-10 (Mon) · Following week",
        ),
        encoding="utf-8",
    )
    proposal = module.bootstrap(
        tmp_path, now="2026-07-29T12:00:00-07:00")
    module.bootstrap(
        tmp_path,
        now="2026-07-29T12:00:00-07:00",
        apply=True,
        proposal_sha256=proposal["sha256"],
    )
    destination = (
        tmp_path / "2026-08-03_week_family-schedule.md"
    ).read_text(encoding="utf-8")
    horizon = horizon_path.read_text(encoding="utf-8")
    assert "## Monday Aug 3" in destination
    assert "Monday edge" in destination
    assert "## Sunday Aug 9" in destination
    assert "Sunday edge" in destination
    assert "Keep this continuation with Sunday" in destination
    assert "Following week" not in destination
    assert "Monday edge" not in horizon
    assert "Sunday edge" not in horizon
    assert "Keep this continuation with Sunday" not in horizon
    assert "Following week" in horizon
def test_multiday_horizon_range_expands_to_one_concise_occurrence_per_day(
        tmp_path):
    module = _load()
    horizon_path = tmp_path / module.HORIZON_FILENAME
    source_line = (
        "- 2026-08-03 through 2026-08-07 · "
        "**9:00a–12:00p** daily (Mon–Fri) · "
        "Kids soccer camp · pickup at noon"
    )
    horizon_path.write_text(_horizon(source_line), encoding="utf-8")
    proposal = module.bootstrap(
        tmp_path, now="2026-07-29T12:00:00-07:00")
    assert len(proposal["inventory"]) == 5
    assert [item["date"] for item in proposal["inventory"]] == [
        "2026-08-03",
        "2026-08-04",
        "2026-08-05",
        "2026-08-06",
        "2026-08-07",
    ]
    module.bootstrap(
        tmp_path,
        now="2026-07-29T12:00:00-07:00",
        apply=True,
        proposal_sha256=proposal["sha256"],
    )
    destination = (
        tmp_path / "2026-08-03_week_family-schedule.md"
    ).read_text(encoding="utf-8")
    horizon = horizon_path.read_text(encoding="utf-8")
    assert destination.count("Kids soccer camp") == 5
    assert destination.count("pickup at noon") == 5
    assert destination.count("family-schedule-source: horizon:") == 5
    assert "through 2026-08-07" not in destination
    assert "daily (Mon–Fri)" not in destination
    assert (
        "- **9:00a–12:00p** Kids soccer camp · pickup at noon"
        in destination
    )
    for heading in (
        "## Monday Aug 3",
        "## Tuesday Aug 4",
        "## Wednesday Aug 5",
        "## Thursday Aug 6",
        "## Friday Aug 7",
    ):
        section = destination.split(heading, 1)[1].split("\n## ", 1)[0]
        assert section.count("Kids soccer camp") == 1
    assert "Kids soccer camp" not in horizon
def test_range_cleanup_preserves_daily_when_it_is_part_of_event_title():
    module = _load()
    assert module._clean_range_body(
        "**8:00a–9:00a** daily (Mon–Fri) · Daily Grind meetup · bring notes"
    ) == "**8:00a–9:00a** Daily Grind meetup · bring notes"
def test_multiday_range_moves_only_intersection_and_splits_horizon_residuals(
        tmp_path):
    module = _load()
    horizon_path = tmp_path / module.HORIZON_FILENAME
    horizon_path.write_text(
        _horizon(
            "- 2026-08-01 through 2026-08-10 · "
            "**10:00a–11:00a** daily (Sat–Wed) · Robotics workshop",
            "  Bring the project notebook",
            "- 2026-08-15 · Keep this separate",
        ),
        encoding="utf-8",
    )
    proposal = module.bootstrap(
        tmp_path, now="2026-07-29T12:00:00-07:00")
    module.bootstrap(
        tmp_path,
        now="2026-07-29T12:00:00-07:00",
        apply=True,
        proposal_sha256=proposal["sha256"],
    )
    destination = (
        tmp_path / "2026-08-03_week_family-schedule.md"
    ).read_text(encoding="utf-8")
    horizon = horizon_path.read_text(encoding="utf-8")
    assert destination.count("Robotics workshop") == 7
    assert destination.count("Bring the project notebook") == 7
    assert "daily (Sat–Wed)" not in destination
    assert (
        "- 2026-08-01 through 2026-08-02 · "
        "**10:00a–11:00a** daily (Sat–Wed) · Robotics workshop"
        in horizon
    )
    assert (
        "- 2026-08-10 · **10:00a–11:00a** Robotics workshop"
        in horizon
    )
    assert horizon.count("daily (Sat–Wed)") == 1
    assert horizon.count("Bring the project notebook") == 2
    assert "Keep this separate" in horizon
def test_scheduled_pre_boundary_tick_is_a_noop(tmp_path):
    module = _load()
    (tmp_path / module.HORIZON_FILENAME).write_text(
        _horizon("- 2026-01-12 · Future item"), encoding="utf-8")
    _write_state(module, tmp_path, date(2025, 12, 29))
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    completed = module.run_scheduled(
        tmp_path, now="2026-01-05T07:59:00+00:00")
    after = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    assert completed == []
    assert after == before
    assert not (tmp_path / module.LOCK_FILENAME).exists()
def test_destination_first_partial_failure_retries_without_duplicates(
        tmp_path, monkeypatch):
    module = _load()
    horizon_path = tmp_path / module.HORIZON_FILENAME
    horizon_path.write_text(
        _horizon(
            "- 2026-08-03 (Mon) · Soccer camp · 9:00a–3:00p",
            "  Pack lunch",
            "- 2026-08-15 · Keep this in Horizon",
        ),
        encoding="utf-8",
    )
    destination_path = tmp_path / "2026-08-03_week_family-schedule.md"
    destination_path.write_text(
        module.week_file_content(date(2026, 8, 3)), encoding="utf-8")
    _write_state(module, tmp_path, date(2026, 7, 20))
    real_atomic_write = module._atomic_write
    writes = []
    def fail_on_horizon(path, content):
        writes.append(Path(path).name)
        if Path(path).name == module.HORIZON_FILENAME:
            raise OSError("simulated interruption after destination write")
        real_atomic_write(path, content)
    monkeypatch.setattr(module, "_atomic_write", fail_on_horizon)
    with pytest.raises(OSError, match="simulated interruption"):
        module.run_scheduled(
            tmp_path, now="2026-07-27T00:01:00-07:00")
    assert writes[:2] == [
        "2026-08-03_week_family-schedule.md",
        module.HORIZON_FILENAME,
    ]
    partially_written = destination_path.read_text(encoding="utf-8")
    assert partially_written.count("Soccer camp") == 1
    assert "Soccer camp" in horizon_path.read_text(encoding="utf-8")
    assert json.loads(
        (tmp_path / module.STATE_FILENAME).read_text(encoding="utf-8")
    )["last_completed_boundary"] == "2026-07-20"
    monkeypatch.setattr(module, "_atomic_write", real_atomic_write)
    completed = module.run_scheduled(
        tmp_path, now="2026-07-27T00:02:00-07:00")
    final_destination = destination_path.read_text(encoding="utf-8")
    final_horizon = horizon_path.read_text(encoding="utf-8")
    assert len(completed) == 1
    assert final_destination.count("Soccer camp") == 1
    assert final_destination.count("family-schedule-source: horizon:") == 1
    assert final_destination.count(
        "family-schedule-rollover: boundary=2026-07-27") == 1
    assert "Soccer camp" not in final_horizon
    assert "Keep this in Horizon" in final_horizon
    assert "Back to school" in final_horizon
    assert "**Gymnastics**" in final_horizon
    assert "preserve this note" in final_horizon
    assert json.loads(
        (tmp_path / module.STATE_FILENAME).read_text(encoding="utf-8")
    )["last_completed_boundary"] == "2026-07-27"
    assert module.run_scheduled(
        tmp_path, now="2026-07-27T12:00:00-07:00") == []
    assert destination_path.read_text(encoding="utf-8") == final_destination
def test_multiday_destination_first_retry_does_not_duplicate_occurrences(
        tmp_path, monkeypatch):
    module = _load()
    horizon_path = tmp_path / module.HORIZON_FILENAME
    horizon_path.write_text(
        _horizon(
            "- 2026-08-03 through 2026-08-07 · "
            "**9:00a–12:00p** daily (Mon–Fri) · Kids soccer camp",
        ),
        encoding="utf-8",
    )
    destination_path = tmp_path / "2026-08-03_week_family-schedule.md"
    destination_path.write_text(
        module.week_file_content(date(2026, 8, 3)), encoding="utf-8")
    _write_state(module, tmp_path, date(2026, 7, 20))
    real_atomic_write = module._atomic_write
    def fail_on_horizon(path, content):
        if Path(path).name == module.HORIZON_FILENAME:
            raise OSError("simulated range interruption")
        real_atomic_write(path, content)
    monkeypatch.setattr(module, "_atomic_write", fail_on_horizon)
    with pytest.raises(OSError, match="range interruption"):
        module.run_scheduled(
            tmp_path, now="2026-07-27T00:01:00-07:00")
    assert destination_path.read_text(
        encoding="utf-8").count("Kids soccer camp") == 5
    assert "Kids soccer camp" in horizon_path.read_text(encoding="utf-8")
    monkeypatch.setattr(module, "_atomic_write", real_atomic_write)
    module.run_scheduled(
        tmp_path, now="2026-07-27T00:02:00-07:00")
    final_destination = destination_path.read_text(encoding="utf-8")
    assert final_destination.count("Kids soccer camp") == 5
    assert final_destination.count(
        "family-schedule-source: horizon:") == 5
    assert "Kids soccer camp" not in horizon_path.read_text(encoding="utf-8")
def test_new_rollover_replaces_legacy_range_marker_during_partial_retry(
        tmp_path):
    module = _load()
    source_line = (
        "- 2026-08-03 through 2026-08-07 · "
        "**9:00a–12:00p** daily (Mon–Fri) · Kids soccer camp"
    )
    raw_sha256 = module._source_sha256(source_line)
    horizon_path = tmp_path / module.HORIZON_FILENAME
    horizon_path.write_text(_horizon(source_line), encoding="utf-8")
    destination_path = tmp_path / "2026-08-03_week_family-schedule.md"
    malformed = module.week_file_content(date(2026, 8, 3)).replace(
        "(nothing scheduled)",
        "\n".join([
            f"<!-- family-schedule-source: horizon:{raw_sha256} -->",
            "- through 2026-08-07 · **9:00a–12:00p** daily (Mon–Fri) "
            "· Kids soccer camp",
        ]),
        1,
    )
    destination_path.write_text(malformed, encoding="utf-8")
    _write_state(module, tmp_path, date(2026, 7, 20))
    module.run_scheduled(
        tmp_path, now="2026-07-27T00:02:00-07:00")
    repaired = destination_path.read_text(encoding="utf-8")
    assert repaired.count("Kids soccer camp") == 5
    assert f"horizon:{raw_sha256} -->" not in repaired
    assert repaired.count(f"horizon:{raw_sha256}:date=") == 5
    assert "through 2026-08-07" not in repaired
    assert "Kids soccer camp" not in horizon_path.read_text(encoding="utf-8")
def test_legacy_range_repair_is_dry_run_digest_gated_and_idempotent(tmp_path):
    module = _load()
    source_sha256 = module._source_sha256(
        "- 2026-08-03 through 2026-08-07 · "
        "**9:00a–12:00p** daily (Mon–Fri) · Kids soccer camp · pickup at noon"
    )
    destination_path = tmp_path / "2026-08-03_week_family-schedule.md"
    malformed = module.week_file_content(date(2026, 8, 3)).replace(
        "(nothing scheduled)",
        "\n".join([
            f"<!-- family-schedule-source: horizon:{source_sha256} -->",
            "- through 2026-08-07 · **9:00a–12:00p** daily (Mon–Fri) "
            "· Kids soccer camp · pickup at noon",
        ]),
        1,
    )
    destination_path.write_text(malformed, encoding="utf-8")
    cli_preview = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "repair-range",
            str(tmp_path),
            "2026-08-03",
            "--source-sha256",
            source_sha256,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert cli_preview.returncode == 0
    assert "operation: repair-range" in cli_preview.stdout
    assert "occurrence-count: 5" in cli_preview.stdout
    assert cli_preview.stderr == ""
    assert destination_path.read_text(encoding="utf-8") == malformed
    proposal = module.repair_range(
        tmp_path, date(2026, 8, 3), source_sha256)
    rendered = module.render_range_repair_proposal(proposal)
    assert destination_path.read_text(encoding="utf-8") == malformed
    assert proposal["occurrence_dates"] == [
        "2026-08-03",
        "2026-08-04",
        "2026-08-05",
        "2026-08-06",
        "2026-08-07",
    ]
    assert "occurrence-count: 5" in rendered
    assert "proposal-sha256:" in rendered
    with pytest.raises(module.ProposalChangedError, match="proposal changed"):
        module.repair_range(
            tmp_path,
            date(2026, 8, 3),
            source_sha256,
            apply=True,
            proposal_sha256="0" * 64,
        )
    assert destination_path.read_text(encoding="utf-8") == malformed
    module.repair_range(
        tmp_path,
        date(2026, 8, 3),
        source_sha256,
        apply=True,
        proposal_sha256=proposal["sha256"],
    )
    repaired = destination_path.read_text(encoding="utf-8")
    assert repaired.count("Kids soccer camp") == 5
    assert repaired.count("pickup at noon") == 5
    assert f"horizon:{source_sha256} -->" not in repaired
    assert repaired.count(f"horizon:{source_sha256}:date=") == 5
    assert "through 2026-08-07" not in repaired
    assert "daily (Mon–Fri)" not in repaired
    rerun = module.repair_range(
        tmp_path, date(2026, 8, 3), source_sha256)
    assert rerun["already_applied"] is True
    assert rerun["destination_after"] == repaired
    lines = repaired.splitlines()
    missing_entry_index = next(
        index
        for index, line in enumerate(lines)
        if f"horizon:{source_sha256}:date=2026-08-05" in line
    ) + 1
    del lines[missing_entry_index]
    destination_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(
            ValueError, match="not followed by a weekly entry"):
        module.repair_range(
            tmp_path, date(2026, 8, 3), source_sha256)
def test_restart_catches_up_missed_boundaries_in_order(tmp_path):
    module = _load()
    horizon_path = tmp_path / module.HORIZON_FILENAME
    horizon_path.write_text(
        _horizon(
            "- 2026-07-27 · Week one item",
            "- 2026-08-03 · Week two item",
            "- 2026-08-10 · Leave for later boundary",
        ),
        encoding="utf-8",
    )
    _write_state(module, tmp_path, date(2026, 7, 13))
    completed = module.run_scheduled(
        tmp_path, now="2026-07-27T09:00:00-07:00")
    assert [proposal["boundary"] for proposal in completed] == [
        "2026-07-20",
        "2026-07-27",
    ]
    assert "Week one item" in (
        tmp_path / "2026-07-27_week_family-schedule.md"
    ).read_text(encoding="utf-8")
    assert "Week two item" in (
        tmp_path / "2026-08-03_week_family-schedule.md"
    ).read_text(encoding="utf-8")
    remaining = horizon_path.read_text(encoding="utf-8")
    assert "Week one item" not in remaining
    assert "Week two item" not in remaining
    assert "Leave for later boundary" in remaining
    assert json.loads(
        (tmp_path / module.STATE_FILENAME).read_text(encoding="utf-8")
    )["last_completed_boundary"] == "2026-07-27"
def test_runtime_job_polls_utc_while_canonical_code_owns_pacific_guard():
    jobs = json.loads(RUNTIME_JOBS.read_text(encoding="utf-8"))
    job = jobs["jobs"]["family_schedule_weekly_rollover"]
    assert job["schedule"] == "*/5 * * * *"
    assert job["no_agent"] is True
    assert job["script"] == "family_schedule_weekly_rollover.py"
    assert "expand explicit date ranges" in job["description"]
    assert "residual Horizon dates" in job["description"]
    assert "America/Los_Angeles" in jobs["_comment"]
    mac_jobs = json.loads(
        (REPO_ROOT / "agents/hermes/cron_jobs.json").read_text(encoding="utf-8"))
    assert "family_schedule_weekly_rollover" not in mac_jobs["jobs"]
    spec = importlib.util.spec_from_file_location(
        "hermes_config_sync_contract", HERMES_CONFIG_SYNC)
    sync_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sync_module)
    static = sync_module._gather_static()
    assert static["runtime_cron"][0]["key"] == (
        "family_schedule_weekly_rollover")
    rendered = sync_module._render_static_body(static)
    assert "Hermes gateway runtime jobs" in rendered
    assert "Source contract only" in rendered


def test_live_config_snapshot_normalizes_terminal_output_and_masked_keys():
    spec = importlib.util.spec_from_file_location(
        "hermes_config_sync_redaction", HERMES_CONFIG_SYNC)
    sync_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sync_module)
    rendered = sync_module._redact(
        "\x1b[1mApp\x1b[0m   \n"
        " OpenAI        ✓ sk-p...HwkA\n"
        " safe value   \n"
    )
    assert rendered == "\n".join([
        "App",
        "    [redacted line — looked like a credential]",
        " safe value",
    ])
    assert "\x1b" not in rendered
    assert "sk-p" not in rendered
    assert all(line == line.rstrip() for line in rendered.splitlines())


def test_live_config_sync_preserves_snapshot_when_fly_status_fails(
        tmp_path, monkeypatch, capsys):
    spec = importlib.util.spec_from_file_location(
        "hermes_config_sync_failure", HERMES_CONFIG_SYNC)
    sync_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sync_module)
    config_path = tmp_path / "hermes_live_config.md"
    state_path = tmp_path / ".hermes_sync_state.json"
    existing = (
        REPO_ROOT / "agents/hermes/hermes_live_config.md"
    ).read_text(encoding="utf-8")
    config_path.write_text(existing, encoding="utf-8")
    state_path.write_text(json.dumps({
        "live_checked_at": "2026-07-30T18:00:00-07:00",
    }), encoding="utf-8")
    old_live_body = sync_module._between(
        existing, sync_module.LIVE_BEGIN, sync_module.LIVE_END)
    old_live_prov = sync_module._parse_prov(existing, "LIVE")
    monkeypatch.setattr(sync_module, "_config_path", lambda: str(config_path))
    monkeypatch.setattr(sync_module, "_state_path", lambda: str(state_path))
    monkeypatch.setattr(sync_module, "_find_fly", lambda: "/fake/fly")
    monkeypatch.setattr(
        sync_module,
        "_gather_live",
        lambda _fly: {
            "status": "",
            "secrets": "",
            "volumes": "",
            "hermes_status": "",
            "channels": "",
        },
    )
    monkeypatch.setattr(
        sync_module,
        "_now",
        lambda: datetime.fromisoformat("2026-07-30T19:30:00-07:00"),
    )

    sync_module.cmd_sync(Namespace(
        agent="Codex",
        no_live=False,
        if_stale=None,
        force=False,
    ))

    updated = config_path.read_text(encoding="utf-8")
    assert sync_module._between(
        updated, sync_module.LIVE_BEGIN, sync_module.LIVE_END
    ) == old_live_body
    assert sync_module._parse_prov(updated, "LIVE") == old_live_prov
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert "live_checked_at" not in state
    assert state["last_run"]["attempted_live"] is True
    assert state["last_run"]["did_live"] is False
    assert "preserving the previous live snapshot" in capsys.readouterr().out


def test_fly_image_installs_runtime_wrapper_without_mutating_job_registry():
    dockerfile = (
        REPO_ROOT / "agents/hermes/Dockerfile"
    ).read_text(encoding="utf-8")
    run_main = (
        REPO_ROOT / "agents/hermes/run-fly-main.sh"
    ).read_text(encoding="utf-8")
    assert "COPY family_schedule_weekly_rollover.py" in dockerfile
    assert (
        "/opt/data/scripts/family_schedule_weekly_rollover.py" in run_main)
    assert "hermes cron create" not in run_main
    assert "/opt/data/cron/jobs.json" not in run_main
def test_hermes_wrapper_is_silent_on_noop_and_notifies_after_work(tmp_path):
    repo_dir = tmp_path / "repo"
    scripts_dir = repo_dir / "skills/family/schedule-coordinator/scripts"
    scripts_dir.mkdir(parents=True)
    rollover_script = scripts_dir / "weekly_rollover.py"
    notify_script = scripts_dir / "notify_dashboard.py"
    notify_marker = tmp_path / "notified"
    rollover_script.write_text(
        "import sys\nsys.exit(0)\n", encoding="utf-8")
    notify_script.write_text(
        f"from pathlib import Path\nPath({str(notify_marker)!r}).write_text('yes')\n",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment.update({
        "HERMES_HOME": str(tmp_path / "hermes"),
        "HERMES_REPO_DIR": str(repo_dir),
        "HERMES_SCHEDULE_DIR": str(tmp_path / "schedule"),
    })
    no_op = subprocess.run(
        [sys.executable, str(HERMES_WRAPPER)],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert no_op.returncode == 0
    assert no_op.stdout == ""
    assert no_op.stderr == ""
    assert not notify_marker.exists()
    rollover_script.write_text(
        "print('weekly-rollover-complete: moved=1')\n", encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(HERMES_WRAPPER)],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert completed.returncode == 0
    assert completed.stdout == "weekly-rollover-complete: moved=1\n"
    assert completed.stderr == ""
    assert notify_marker.read_text(encoding="utf-8") == "yes"
