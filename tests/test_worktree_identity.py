#!/usr/bin/env python3
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

from apps.holodeck.collectors.branch_lineage import parse_lineage_message

_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills",
    "repo-ops",
    "create-worktree",
    "scripts",
    "worktree_identity.py",
)
HEX_RE = re.compile(r"^#[0-9a-f]{6}$")
MAIN_GREEN = "#068102"


def _load():
    spec = importlib.util.spec_from_file_location("worktree_identity", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_slug_replaces_slashes():
    mod = _load()
    assert mod.slug("feature/math-quiz-dynamic") == "feature-math-quiz-dynamic"
    assert mod.slug("ops/create-worktree-skill") == "ops-create-worktree-skill"


def test_worktree_path_is_sibling_of_main_repo():
    mod = _load()
    parent = "/Users/randytrue/Documents/Code/fof-mono"
    assert mod.worktree_path(parent, "feature/math-quiz-dynamic") == (
        "/Users/randytrue/Documents/Code/feature-math-quiz-dynamic"
    )


def test_branch_lineage_start_message_is_canonical_and_normalizes_parent():
    mod = _load()
    message = mod.branch_lineage_start_message(
        "feature/deutsch-content-tools",
        "origin/feature/worldview-mirror",
        "build the Deutsch content tools",
        "a" * 40,
        "feat(deutsch): build worldview mirror",
        "Codex Subagent (fable5-w-codex) - GPT 5.6 Sol xhigh",
        "11111111-1111-4111-8111-111111111111",
        "22222222-2222-4222-8222-222222222222",
    )
    assert message == "\n".join([
        "chore(repo): record branch lineage at branch start for feature/deutsch-content-tools",
        "",
        "Record-Type: branch-lineage",
        "Lineage-Type: branch-start",
        "Lineage-ID: 11111111-1111-4111-8111-111111111111",
        "Record-ID: 22222222-2222-4222-8222-222222222222",
        "Relationship: created-from",
        "Update-Reason: initial",
        "Created-By: Codex Subagent (fable5-w-codex) - GPT 5.6 Sol xhigh",
        "Branch: feature/deutsch-content-tools",
        "Parent-Branch: feature/worldview-mirror",
        "Fork-Commit: " + "a" * 40,
        "Fork-Subject: feat(deutsch): build worldview mirror",
        "Branch-Purpose: build the Deutsch content tools",
        "Lineage-Version: 2",
    ])
    assert parse_lineage_message(message)["errors"] == []


def test_branch_lineage_start_message_rejects_ambiguous_or_malformed_identity():
    mod = _load()
    valid = {
        "branch": "feature/child",
        "parent": "main",
        "purpose": "purpose",
        "fork_commit": "a" * 40,
        "fork_subject": "feat(repo): fork",
        "created_by": "Codex App - GPT 5.6 Sol xhigh",
        "lineage_id": "11111111-1111-4111-8111-111111111111",
        "record_id": "22222222-2222-4222-8222-222222222222",
    }
    invalid = (
        ("branch", ""),
        ("parent", ""),
        ("purpose", ""),
        ("parent", "feature/child"),
        ("purpose", "two\nlines"),
        ("branch", "feature/child with spaces"),
        ("parent", "feature/parent with spaces"),
        ("branch", "Feature/Child"),
        ("fork_commit", "abc1234"),
        ("fork_subject", "two\nlines"),
        ("created_by", ""),
        ("lineage_id", "NOT-A-UUID"),
        ("record_id", "11111111-1111-4111-8111-111111111111"),
    )
    for field, value in invalid:
        fields = dict(valid)
        fields[field] = value
        try:
            mod.branch_lineage_start_message(**fields)
        except ValueError:
            continue
        raise AssertionError((field, value))


def test_branch_lineage_start_message_cli_emits_commit_ready_message():
    result = subprocess.run(
        [
            sys.executable,
            _SCRIPT,
            "lineage-message",
            "feature/child",
            "--parent",
            "origin/feature/parent",
            "--purpose",
            "build child capability",
            "--fork-commit",
            "a" * 40,
            "--fork-subject",
            "feat(parent): prepare child",
            "--created-by",
            "Codex App - GPT 5.6 Sol xhigh",
            "--lineage-id",
            "11111111-1111-4111-8111-111111111111",
            "--record-id",
            "22222222-2222-4222-8222-222222222222",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith(
        "chore(repo): record branch lineage at branch start for feature/child\n\n"
        "Record-Type: branch-lineage\nLineage-Type: branch-start\n"
    )
    assert "Parent-Branch: feature/parent\n" in result.stdout
    assert result.stdout.endswith("Lineage-Version: 2\n")


def test_retired_start_message_command_fails_closed():
    result = subprocess.run(
        [sys.executable, _SCRIPT, "start-message", "feature/child"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "unknown command" in result.stderr


def test_title_bar_color_is_deterministic():
    mod = _load()
    branch = "feature/lesson-logger-dashboard"
    first = mod.title_bar_color(branch)
    second = mod.title_bar_color(branch)
    assert first == second
    assert first["titleBar.activeForeground"] == "#ffffff"


def test_title_bar_color_never_main_green():
    mod = _load()
    branches = [
        "feature/math-quiz-dynamic",
        "feature/lesson-logger-dashboard",
        "ops/create-worktree-skill",
        "fix/voice-router",
        "feature/hermes-mom-plan",
    ]
    for branch in branches:
        colors = mod.title_bar_color(branch)
        bg = colors["titleBar.activeBackground"]
        assert HEX_RE.match(bg), bg
        assert bg.lower() != MAIN_GREEN


def test_title_bar_colors_are_distinct_across_branches():
    mod = _load()
    branches = [
        "feature/math-quiz-dynamic",
        "feature/lesson-logger-dashboard",
        "ops/create-worktree-skill",
    ]
    backgrounds = {mod.title_bar_color(b)["titleBar.activeBackground"] for b in branches}
    assert len(backgrounds) == len(branches)


def test_apply_color_rewrites_settings_and_is_idempotent():
    mod = _load()
    branch = "feature/test-worktree-color"
    sample = {
        "workbench.colorCustomizations": {
            "titleBar.activeBackground": "#068102",
            "editor.background": "#151515",
        },
        "editor.fontSize": 14,
    }
    with tempfile.TemporaryDirectory() as tmp:
        settings_path = os.path.join(tmp, "settings.json")
        with open(settings_path, "w", encoding="utf-8") as handle:
            json.dump(sample, handle, indent=4)
            handle.write("\n")
        first_color = mod.apply_title_bar_color(settings_path, branch)
        text_after_first = open(settings_path, encoding="utf-8").read()
        assert '"window.titleBarStyle": "custom"' in text_after_first
        assert MAIN_GREEN not in text_after_first
        assert f'"titleBar.activeBackground": "{first_color}"' in text_after_first
        second_color = mod.apply_title_bar_color(settings_path, branch)
        text_after_second = open(settings_path, encoding="utf-8").read()
        assert first_color == second_color
        assert text_after_first == text_after_second


def test_apply_color_uses_holodeck_worktree_color_rules_when_present():
    mod = _load()
    branch = "feature/holodeck-start"
    with tempfile.TemporaryDirectory() as tmp:
        colors_dir = os.path.join(tmp, "apps", "holodeck")
        os.makedirs(colors_dir)
        colors_path = os.path.join(colors_dir, "worktree-colors.yaml")
        with open(colors_path, "w", encoding="utf-8") as handle:
            handle.write(
                "\n".join([
                    "foreground: '#ffffff'",
                    "rules:",
                    "  - id: holodeck",
                    "    name_contains: holodeck",
                    "    background: '#2696d3'",
                ])
            )
            handle.write("\n")
        settings_path = os.path.join(tmp, "settings.json")
        with open(settings_path, "w", encoding="utf-8") as handle:
            json.dump({"workbench.colorCustomizations": {"editor.background": "#151515"}}, handle, indent=4)
            handle.write("\n")
        color = mod.apply_title_bar_color(settings_path, branch, repo_root=tmp)
        assert color == "#2696d3"
        text = open(settings_path, encoding="utf-8").read()
        assert '"titleBar.activeBackground": "#2696d3"' in text
        assert '"titleBar.inactiveBackground": "#2696d3"' in text
