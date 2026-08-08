import json
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from apps.holodeck import server as holodeck_server
from apps.holodeck import state as holodeck_state
from apps.holodeck.collect import empty_snapshot, merge_snapshot
from apps.holodeck.collectors import sessions as sessions_collector
from apps.holodeck.collectors.apps import app_slug_for_path, discover_app_slugs_from_names, infer_app_kind, merge_registry_apps
from apps.holodeck.collectors.branches import (
    collect_branches,
    human_age,
    lineage_parent_projection,
    load_prs,
    parse_branch_commit_log,
    parse_for_each_ref,
    pr_list_error_note,
    pr_stale_note,
)
from apps.holodeck.collectors.deploy import parse_chalice_config, parse_fly_toml
from apps.holodeck.collectors.sessions import claude_messages_from_lines, codex_entrypoint_from_meta, parse_claude_jsonl_lines, parse_codex_jsonl_lines, parse_cursor_composer_data
from apps.holodeck.collectors.specs import count_tasks
from apps.holodeck.collectors.worktrees import (
    collect_cursor_open_paths,
    color_for_branch_name,
    cursor_paths_from_opened_windows,
    find_codex_workspace_file,
    load_worktree_color_rules,
    normalize_file_uri,
    parse_title_bar_settings,
    parse_title_bar_workspace,
    parse_worktree_porcelain,
    path_is_cursor_open,
    title_bar_for_branch,
    title_bar_for_worktree,
    title_bar_from_color_rules,
    worktree_display_name,
    worktree_folder_name,
    worktree_name_matches_rule,
    workspace_paths_from_config,
)
from apps.holodeck.server import validate_file_read_path, validate_file_write_path
from apps.holodeck.turns import db as turns_db

### Fixtures
def repo_worktrees():
    return [{"path": "/repo/main", "branch": "feature/test"}]
def json_line(value):
    import json
    return json.dumps(value)

### Tests
def test_worktree_porcelain_parsing_multi_worktree_detached_missing():
    text = "\n".join([
        "worktree /repo/main",
        "HEAD abcdef123456",
        "branch refs/heads/main",
        "",
        "worktree /repo/missing",
        "HEAD 111111122222",
        "branch refs/heads/feature/missing",
        "",
        "worktree /repo/detached",
        "HEAD 999999988888",
        "detached",
    ])
    entries = parse_worktree_porcelain(text, current_path="/repo/main", existing_paths={"/repo/main", "/repo/detached"})
    assert entries[0]["path"] == "/repo/main"
    assert entries[0]["branch"] == "main"
    assert entries[0]["head"] == "abcdef1"
    assert entries[0]["is_current"] is True
    assert entries[1]["missing"] is True
    assert entries[2]["branch"] == "detached"
def test_worktree_folder_name_uses_path_basename():
    assert worktree_folder_name("/Users/me/Code/feature-holodeck-start") == "feature-holodeck-start"
def test_codex_workspace_display_name_and_title_bar(tmp_path):
    worktree = tmp_path / "fof-mono"
    worktree.mkdir()
    workspace = worktree / "codex-feature-minecraft-mod-build-local.code-workspace"
    workspace.write_text(
        json.dumps({
            "folders": [{"path": "."}],
            "settings": {
                "workbench.colorCustomizations": {
                    "titleBar.activeBackground": "#800000",
                    "titleBar.activeForeground": "#ffffff",
                }
            },
        }),
        encoding="utf-8",
    )
    (worktree / ".vscode").mkdir()
    (worktree / ".vscode/settings.json").write_text(
        '{"workbench.colorCustomizations":{"titleBar.activeBackground":"#87CEEB"}}',
        encoding="utf-8",
    )
    assert find_codex_workspace_file(str(worktree), "feature/minecraft-mod-build-local") == workspace
    assert worktree_display_name(str(worktree), "feature/minecraft-mod-build-local") == "codex-feature-minecraft-mod-build-local"
    assert parse_title_bar_workspace(workspace) == {"background": "#800000", "foreground": "#ffffff"}
def test_unrelated_lone_workspace_does_not_override_main_identity_or_color(tmp_path):
    worktree = tmp_path / "fof-mono"
    worktree.mkdir()
    workspace = worktree / "codex-feature-minecraft-mod-build-local.code-workspace"
    workspace.write_text(
        json.dumps({
            "folders": [{"path": "."}],
            "settings": {
                "workbench.colorCustomizations": {
                    "titleBar.activeBackground": "#800000",
                    "titleBar.activeForeground": "#ffffff",
                }
            },
        }),
        encoding="utf-8",
    )
    colors = worktree / "apps/holodeck/worktree-colors.yaml"
    colors.parent.mkdir(parents=True)
    colors.write_text(
        """foreground: "#ffffff"
rules:
  - id: minecraft
    name_contains: minecraft
    background: "#800000"
  - id: fof-mono-main
    name_exact: fof-mono
    branch: main
    background: "#068102"
""",
        encoding="utf-8",
    )
    assert find_codex_workspace_file(str(worktree), "main") is None
    assert worktree_display_name(str(worktree), "main") == "fof-mono"
    assert title_bar_for_worktree(str(worktree), "main", worktree) == {
        "background": "#068102",
        "foreground": "#ffffff",
    }
def test_detached_worktree_ignores_unrelated_workspace_identity(tmp_path):
    """Regression: leftover minecraft workspace must not rename deutsch when detached."""
    worktree = tmp_path / "deutsch"
    worktree.mkdir()
    workspace = worktree / "codex-feature-minecraft-mod-build-local.code-workspace"
    workspace.write_text('{"folders":[{"path":"."}]}', encoding="utf-8")
    assert find_codex_workspace_file(str(worktree), "detached") is None
    assert worktree_display_name(str(worktree), "detached") == "deutsch"
def test_detached_worktree_keeps_folder_name_with_matching_workspace(tmp_path):
    """Regression: even a matching minecraft workspace keeps detached display as folder name."""
    worktree = tmp_path / "minecraft"
    worktree.mkdir()
    workspace = worktree / "codex-feature-minecraft-mod-build-local.code-workspace"
    workspace.write_text('{"folders":[{"path":"."}]}', encoding="utf-8")
    assert find_codex_workspace_file(str(worktree), "detached") == workspace
    assert worktree_display_name(str(worktree), "detached") == "minecraft"
def _write_worktree_color_rules(repo_root, body):
    colors = repo_root / "apps/holodeck/worktree-colors.yaml"
    colors.parent.mkdir(parents=True)
    colors.write_text(body, encoding="utf-8")
def test_detached_worktree_color_uses_folder_not_stray_workspace(tmp_path):
    """Regression: dragon-baby must keep purple even with a leftover minecraft workspace."""
    worktree = tmp_path / "dragon-baby"
    worktree.mkdir()
    workspace = worktree / "codex-feature-minecraft-mod-build-local.code-workspace"
    workspace.write_text(
        json.dumps({
            "folders": [{"path": "."}],
            "settings": {
                "workbench.colorCustomizations": {
                    "titleBar.activeBackground": "#800000",
                    "titleBar.activeForeground": "#ffffff",
                }
            },
        }),
        encoding="utf-8",
    )
    _write_worktree_color_rules(
        worktree,
        """foreground: "#ffffff"
rules:
  - id: minecraft
    name_contains: minecraft
    background: "#800000"
  - id: dragon-baby
    name_contains: dragon-baby
    background: "#8625ab"
""",
    )
    assert find_codex_workspace_file(str(worktree), "detached") is None
    assert worktree_display_name(str(worktree), "detached") == "dragon-baby"
    assert title_bar_for_worktree(str(worktree), "detached", worktree) == {
        "background": "#8625ab",
        "foreground": "#ffffff",
    }
def test_detached_deutsch_keeps_yaml_color_despite_minecraft_settings(tmp_path):
    """Regression: deutsch green must win over leftover minecraft-red .vscode settings."""
    worktree = tmp_path / "deutsch"
    worktree.mkdir()
    (worktree / ".vscode").mkdir()
    (worktree / ".vscode/settings.json").write_text(
        json.dumps({
            "workbench.colorCustomizations": {
                "titleBar.activeBackground": "#800000",
                "titleBar.activeForeground": "#ffffff",
            }
        }),
        encoding="utf-8",
    )
    (worktree / "codex-feature-minecraft-mod-build-local.code-workspace").write_text(
        '{"folders":[{"path":"."}]}',
        encoding="utf-8",
    )
    _write_worktree_color_rules(
        worktree,
        """foreground: "#ffffff"
rules:
  - id: minecraft
    name_contains: minecraft
    background: "#800000"
  - id: deutsch
    name_contains: deutsch
    background: "#c2185b"
""",
    )
    assert worktree_display_name(str(worktree), "detached") == "deutsch"
    assert find_codex_workspace_file(str(worktree), "detached") is None
    assert title_bar_for_worktree(str(worktree), "detached", worktree) == {
        "background": "#c2185b",
        "foreground": "#ffffff",
    }
    # Guard the failure mode that painted three parked cards Minecraft-red:
    # matching the stale workspace stem against YAML must not be used for detached.
    assert title_bar_from_color_rules(
        "codex-feature-minecraft-mod-build-local",
        "detached",
        load_worktree_color_rules(worktree),
    )["background"] == "#800000"
    assert title_bar_from_color_rules("deutsch", "detached", load_worktree_color_rules(worktree))["background"] == "#c2185b"
def test_normalize_file_uri_decodes_cursor_folder_uri():
    uri = "file:///Users/randytrue/Documents/Code/feature-web-site-redo-fof"
    assert normalize_file_uri(uri) == str(Path(uri.replace("file://", "")).resolve())
def test_workspace_paths_accept_jsonc_comments_and_trailing_commas(tmp_path):
    worktree = tmp_path / "feature demo"
    shared = tmp_path / "shared # ü"
    worktree.mkdir()
    shared.mkdir()
    workspace = worktree / "codex-feature-demo.code-workspace"
    workspace.write_text(
        """{
            // Cursor workspace folders may use JSONC.
            "folders": [
                {"path": "."},
                {"path": "../shared # ü"}, /* external workspace folder */
            ],
            "settings": {
                "example.url": "https://example.test/a//b",
                "workbench.colorCustomizations": {
                    "titleBar.activeBackground": "#123456",
                },
            },
        }""",
        encoding="utf-8",
    )

    assert workspace_paths_from_config(workspace) == {
        str(worktree.resolve()),
        str(shared.resolve()),
    }
    assert parse_title_bar_workspace(workspace) == {
        "background": "#123456",
        "foreground": "#ffffff",
    }
def test_path_is_cursor_open_matches_exact_paths_only(tmp_path):
    worktree = tmp_path / "feature-demo"
    worktree.mkdir()
    parent = tmp_path / "Code"
    parent.mkdir()
    open_paths = {str(worktree.resolve())}
    assert path_is_cursor_open(str(worktree), open_paths) is True
    assert path_is_cursor_open(str(parent), open_paths) is False
    assert path_is_cursor_open(str(tmp_path / "other"), open_paths) is False
def test_parse_title_bar_settings_reads_workbench_colors(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(
        '\n'.join([
            "{",
            '    // title bar identity',
            '    "workbench.colorCustomizations": {',
            '        "titleBar.activeBackground": "#a25605",',
            '        "titleBar.activeForeground": "#ffffff"',
            "    }",
            "}",
        ]),
        encoding="utf-8",
    )
    assert parse_title_bar_settings(settings) == {"background": "#a25605", "foreground": "#ffffff"}
def test_collect_cursor_open_paths_prefers_windows_state(tmp_path, monkeypatch):
    storage = tmp_path / "storage.json"
    storage.write_text(
        json.dumps({
            "windowsState": {
                "openedWindows": [
                    {"folder": "file:///tmp/feature-holodeck-start"},
                    {"workspaceIdentifier": {"configURIPath": "file:///tmp/codex/codex-feature-demo.code-workspace"}},
                ]
            },
            "backupWorkspaces": {
                "folders": [{"folderUri": "file:///tmp/feature-autolearner"}],
                "workspaces": [],
            },
        }),
        encoding="utf-8",
    )
    (tmp_path / "codex").mkdir()
    (tmp_path / "codex/codex-feature-demo.code-workspace").write_text(
        json.dumps({"folders": [{"path": "."}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr("apps.holodeck.collectors.worktrees.CURSOR_STORAGE", storage)
    paths = collect_cursor_open_paths()
    assert str(Path("/tmp/feature-holodeck-start").resolve()) in paths
    assert str(Path("/tmp/codex").resolve()) in paths
    assert str(Path("/tmp/feature-autolearner").resolve()) not in paths
def test_worktree_color_rules_match_display_names(tmp_path):
    colors_path = tmp_path / "apps/holodeck/worktree-colors.yaml"
    colors_path.parent.mkdir(parents=True)
    colors_path.write_text(
        "\n".join([
            "foreground: '#ffffff'",
            "rules:",
            "  - id: holodeck",
            "    name_contains: holodeck",
            "    background: '#2696d3'",
            "  - id: minecraft",
            "    name_contains: minecraft",
            "    background: '#800000'",
            "  - id: fof-mono-main",
            "    name_exact: fof-mono",
            "    branch: main",
            "    background: '#068102'",
            "  - id: web-site-fof",
            "    name_contains_all: [website, fof]",
            "    background: '#a25605'",
        ]),
        encoding="utf-8",
    )
    rules = load_worktree_color_rules(tmp_path)
    assert title_bar_from_color_rules("feature-holodeck-start", "feature/holodeck-start", rules)["background"] == "#2696d3"
    assert title_bar_from_color_rules("codex-feature-minecraft-mod-build-local", "feature/minecraft-mod-build-local", rules)["background"] == "#800000"
    assert title_bar_from_color_rules("fof-mono", "main", rules)["background"] == "#068102"
    assert title_bar_from_color_rules("fof-website", "feature/foo", rules)["background"] == "#a25605"
    assert title_bar_from_color_rules("feature-autolearner", "feature/autolearner", rules) is None
def test_color_for_branch_name_matches_yaml_without_worktree(tmp_path):
    colors_path = tmp_path / "apps/holodeck/worktree-colors.yaml"
    colors_path.parent.mkdir(parents=True)
    colors_path.write_text(
        "\n".join([
            "foreground: '#ffffff'",
            "rules:",
            "  - id: holodeck",
            "    name_contains: holodeck",
            "    background: '#2696d3'",
            "  - id: minecraft",
            "    name_contains: minecraft",
            "    background: '#800000'",
            "  - id: deutsch",
            "    name_contains: deutsch",
            "    background: '#c2185b'",
            "  - id: fof-mono-main",
            "    name_exact: fof-mono",
            "    branch: main",
            "    background: '#068102'",
        ]),
        encoding="utf-8",
    )
    rules = load_worktree_color_rules(tmp_path)
    assert color_for_branch_name("feature/holodeck-start", rules)["background"] == "#2696d3"
    assert color_for_branch_name("feature/minecraft-tp-credits", rules)["background"] == "#800000"
    assert color_for_branch_name("feature/deutsch-graph", rules)["background"] == "#c2185b"
    assert color_for_branch_name("main", rules)["background"] == "#068102"
    assert color_for_branch_name("origin/main", rules)["background"] == "#068102"
    assert color_for_branch_name("feature/admin-automation-skills", rules) is None
    worktrees = [{"branch": "diarz-landscape", "title_bar": {"background": "#22ae96", "foreground": "#ffffff"}}]
    assert title_bar_for_branch("diarz-landscape", worktrees, rules)["background"] == "#22ae96"
    assert title_bar_for_branch("feature/holodeck-start", worktrees, rules)["background"] == "#2696d3"
def test_branch_commit_log_parsing_multiline_messages():
    text = "".join([
        "\x1eabc1234\x00Ada Lovelace\x002026-07-12T05:01:00-07:00\x00Add branch drawer\n\nBody line one\nBody line two\x00\n",
        "\x1edef5678\x00Grace Hopper\x002026-07-12T05:02:00-07:00\x00Fix paging\x00\n",
    ])
    commits = parse_branch_commit_log(text)
    assert commits == [
        {
            "sha": "abc1234",
            "author": "Ada Lovelace",
            "date": "2026-07-12T05:01:00-07:00",
            "subject": "Add branch drawer",
            "body": "Body line one\nBody line two",
        },
        {
            "sha": "def5678",
            "author": "Grace Hopper",
            "date": "2026-07-12T05:02:00-07:00",
            "subject": "Fix paging",
            "body": "",
        },
    ]
def test_branch_ref_parsing_preserves_full_local_and_remote_tips():
    local_tip = "1" * 40
    remote_tip = "2" * 40
    text = "\n".join([
        "refs/remotes/origin/feature/demo\x1f" + remote_tip + "\x1fRemote\x1f2026-07-30T01:00:00-07:00\x1fAda",
        "refs/heads/feature/demo\x1f" + local_tip + "\x1fLocal\x1f2026-07-30T02:00:00-07:00\x1fGrace",
    ])
    branch = parse_for_each_ref(text)[0]
    assert branch["tip"] == local_tip[:7]
    assert branch["local_tip"] == local_tip
    assert branch["remote_tip"] == remote_tip
    assert branch["subject"] == "Local"
def _fixture_git(repo, *args, check=True):
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return result.stdout.strip()
def _fixture_repo(tmp_path):
    repo = tmp_path / "branch-repo"
    repo.mkdir()
    _fixture_git(repo, "init", "-b", "main")
    _fixture_git(repo, "config", "user.name", "Holodeck Test")
    _fixture_git(repo, "config", "user.email", "holodeck@example.test")
    _fixture_commit(repo, "chore: seed repository")
    return repo
def _fixture_commit(repo, subject, body=None, filename="history.txt"):
    path = repo / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    prior = path.read_text(encoding="utf-8") if path.exists() else ""
    serial = _fixture_git(repo, "rev-list", "--all", "--count") or "0"
    path.write_text(prior + serial + " " + subject + "\n", encoding="utf-8")
    _fixture_git(repo, "add", filename)
    args = ["commit", "-m", subject]
    if body is not None:
        args.extend(["-m", body])
    _fixture_git(repo, *args)
    return _fixture_git(repo, "rev-parse", "HEAD")
def test_parent_projection_uses_only_authoritative_lineage(tmp_path):
    repo = _fixture_repo(tmp_path)
    fork = _fixture_git(repo, "rev-parse", "HEAD")
    accepted = {
        "status": "evidence-validated",
        "authoritative": True,
        "parent_branch": "main",
        "fork_commit": fork,
        "fork_date": "2026-06-12T09:30:00-07:00",
    }
    projected = lineage_parent_projection(repo, accepted)
    assert projected["name"] == "main"
    assert projected["fork_base"] == fork[:7]
    assert projected["fork_commit"] == fork
    assert projected["fork_base_date"] == "2026-06-12T09:30:00-07:00"
    assert projected["source"] == "branch-lineage"
    for status in ("pending", "invalid", "unsupported", "missing", "parent-ref-missing", "ref-diverged"):
        assert lineage_parent_projection(repo, {
            **accepted,
            "status": status,
            "authoritative": False,
        }) is None
def test_pr_list_error_note_rewrites_github_rate_limit():
    note = pr_list_error_note("GraphQL: API rate limit already exceeded for user ID 18576005")
    assert note.startswith("PR data unavailable")
    assert "rate limit" in note.lower()
    assert "Branch names and commits" in note
    assert "18576005" not in note
    other = pr_list_error_note("HTTP 403: Forbidden", previous_pr_fetched_at="2026-07-26T01:00:00-07:00")
    assert other.startswith("PR data unavailable")
    assert "HTTP 403: Forbidden" in other
    assert "PR badges last updated" in other
def test_pr_stale_note_timeout_includes_age():
    note = pr_stale_note("timed out after 15 seconds", previous_pr_fetched_at="2026-07-26T01:00:00-07:00", attempts=3)
    assert "PR data is stale" in note
    assert "timed out after 3 tries" in note
    assert "Branch names and commits" in note
    assert "PR badges last updated" in note
    assert "2026-07-26" in note
def test_human_age_zero_minutes():
    now = datetime.fromisoformat("2026-07-26T01:00:30-07:00")
    assert human_age("2026-07-26T01:00:00-07:00", now=now) == "0m ago"
def test_load_prs_timeout_retries_then_soft_fails():
    import subprocess
    calls = {"n": 0}
    def fake_runner(*args, **kwargs):
        calls["n"] += 1
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout") or 15)
    sleeps = []
    prs, error = load_prs("/repo", attempts=3, timeout=15, sleep_fn=lambda seconds: sleeps.append(seconds), runner=fake_runner)
    assert prs == {}
    assert "timed out" in error
    assert calls["n"] == 3
    assert sleeps == [5, 5]
def test_collect_branches_keeps_previous_prs_when_pr_lookup_fails(monkeypatch):
    class Result:
        def __init__(self, stdout="", returncode=0):
            self.stdout = stdout
            self.stderr = ""
            self.returncode = returncode
    ref_line = "refs/heads/feature/demo\x1fabc1234\x1fSubject\x1f2026-07-26T02:00:00-07:00\x1fAda"
    def fake_run_git(repo_root, args, timeout=15):
        joined = " ".join(args)
        if "for-each-ref" in joined:
            return Result(ref_line)
        if "--is-ancestor" in joined:
            return Result("", returncode=1)
        if args[:1] == ["log"]:
            return Result("2026-07-26T02:00:00-07:00\n")
        if args[:1] == ["merge-base"]:
            return Result("abc1234def\n")
        return Result("0\t0")
    monkeypatch.setattr("apps.holodeck.collectors.branches.run_git", fake_run_git)
    monkeypatch.setattr(
        "apps.holodeck.collectors.branches.load_prs",
        lambda repo_root, **kwargs: ({}, "timed out after 15 seconds"),
    )
    previous = [{
        "name": "feature/demo",
        "pr": {"number": 12, "state": "OPEN", "url": "https://example.test/pr/12"},
    }]
    branches, note, meta = collect_branches(
        "/repo",
        previous_branches=previous,
        previous_meta={"pr_fetched_at": "2026-07-26T01:00:00-07:00"},
    )
    assert len(branches) == 1
    assert branches[0]["pr"]["number"] == 12
    assert "lineage" in branches[0]
    assert "legacy_parent" not in branches[0]
    assert "lineage_parity" not in branches[0]
    assert "PR data is stale" in note
    assert meta["pr_fetched_at"] == "2026-07-26T01:00:00-07:00"
def test_tasks_checkbox_counting_nested_and_uppercase():
    text = "\n".join([
        "- [ ] parent task",
        "  - [x] nested done",
        "  - [X] nested uppercase done",
        "- [ ] another task",
        "- [-] ignored",
    ])
    total, done = count_tasks(text)
    assert total == 4
    assert done == 2
def test_registry_merge_registered_unregistered_and_umbrella_discovery():
    discovered = discover_app_slugs_from_names(["holodeck", "minecraft", "qrag"], {"minecraft": ["mods", "prism-sync"], "qrag": ["api", "web"]})
    registry = [{"slug": "holodeck", "name": "Holodeck"}, {"slug": "qrag/api/qrag-llm", "name": "QRAG"}]
    merged = {item["slug"]: item for item in merge_registry_apps(registry, discovered)}
    assert "minecraft" not in merged
    assert merged["minecraft/mods"]["registered"] is False
    assert merged["holodeck"]["registered"] is True
    assert merged["qrag/api/qrag-llm"]["registered"] is True
def test_claude_code_jsonl_parsing_skips_injected_user_for_preview():
    lines = [
        json_line({"type": "user", "cwd": None, "message": {"content": "<command-message>stub</command-message>"}}),
        json_line({"type": "user", "cwd": "/repo/main", "gitBranch": "feature/test", "timestamp": "2026-07-09T20:00:00-07:00", "message": {"content": "<system-reminder>ignore</system-reminder>"}}),
        json_line({"type": "assistant", "cwd": "/repo/main", "gitBranch": "feature/test", "timestamp": "2026-07-09T20:01:00-07:00", "message": {"content": "ok"}}),
        json_line({"type": "user", "cwd": "/repo/main", "gitBranch": "feature/test", "timestamp": "2026-07-09T20:02:00-07:00", "entrypoint": "cli", "message": {"content": [{"type": "text", "text": "Build the backend"}]}}),
        json_line({"type": "ai-title", "title": "Backend work"}),
    ]
    session = parse_claude_jsonl_lines(lines, source_path="/tmp/abc123.jsonl", fallback_mtime="mtime", worktrees=repo_worktrees())
    assert session["id"] == "abc123"
    assert session["title"] == "Backend work"
    assert session["first_user"] == "Build the backend"
    assert session["last_user"] == "Build the backend"
    assert session["entrypoint"] == "cli"
    assert session["worktree"] == "/repo/main"
def test_codex_session_meta_and_user_message_extraction():
    lines = [
        json_line({"type": "session_meta", "payload": {"id": "sess1", "timestamp": "2026-07-09T19:00:00-07:00", "cwd": "/repo/main", "git": {"branch": "feature/test"}, "source": "exec", "originator": "codex_exec", "thread_source": "user"}}),
        json_line({"type": "response_item", "payload": {"role": "user", "content": [{"text": "<context>ignore</context>"}]}}),
        json_line({"type": "response_item", "payload": {"role": "assistant", "content": [{"text": "ok"}]}}),
        json_line({"type": "response_item", "payload": {"role": "user", "content": [{"text": "Implement collect.py"}]}}),
    ]
    session = parse_codex_jsonl_lines(lines, source_path="/tmp/rollout.jsonl", fallback_mtime="2026-07-09T19:30:00-07:00", titles={"sess1": {"title": "Codex title"}}, worktrees=repo_worktrees())
    assert session["id"] == "sess1"
    assert session["title"] == "Codex title"
    assert session["first_user"] == "Implement collect.py"
    assert session["branch"] == "feature/test"
    assert session["entrypoint"] == "cli"
def test_codex_entrypoint_maps_desktop_and_subagent():
    assert codex_entrypoint_from_meta({"source": "vscode", "originator": "Codex Desktop", "thread_source": "user"}) == "app"
    assert codex_entrypoint_from_meta({"source": "vscode", "originator": "codex_work_desktop", "thread_source": "user"}) == "app"
    assert codex_entrypoint_from_meta({"source": {"subagent": {"other": "guardian"}}, "originator": "Codex Desktop", "thread_source": "subagent"}) == "subagent"
def test_codex_tui_cli_source_maps_to_cli_not_app():
    # Regression: interactive Codex CLI (TUI) uses source=cli / originator=codex-tui.
    # Older mapping only recognized exec/codex_exec and mislabeled these as Codex App.
    # TUI sessions are operator CLI (visible in AI Sessions), not fable5 delegated machinery.
    assert codex_entrypoint_from_meta({"source": "cli", "originator": "codex-tui", "thread_source": "user"}) == "cli"
    lines = [
        json_line({"type": "session_meta", "payload": {"id": "tui1", "timestamp": "2026-07-28T04:53:21.824Z", "cwd": "/repo/main", "git": {"branch": "feature/test"}, "source": "cli", "originator": "codex-tui", "thread_source": "user", "cli_version": "0.145.0"}}),
        json_line({"type": "turn_context", "payload": {"model": "gpt-5.6-sol", "effort": "xhigh"}}),
        json_line({"type": "response_item", "payload": {"role": "user", "content": [{"text": "Build the Minecraft mod"}]}}),
    ]
    session = parse_codex_jsonl_lines(lines, source_path="/tmp/rollout-tui.jsonl", fallback_mtime="2026-07-28T05:43:30-07:00", worktrees=repo_worktrees())
    assert session["entrypoint"] == "cli"
    assert session["originator"] == "codex-tui"
    assert session["interface"] == "Codex CLI"
    assert session["label"] == "Codex CLI - GPT 5.6 Sol xhigh"
    assert session["origin"] == "operator"
def test_cursor_composer_data_row_to_session_dict():
    data = {
        "composerId": "composer-1",
        "name": "Cursor plan",
        "workspaceIdentifier": {"uri": {"path": "/repo/main/apps/holodeck"}},
        "createdAt": 1000,
        "lastUpdatedAt": 2000,
        "fullConversationHeadersOnly": [{"type": 1, "bubbleId": "u1"}, {"type": 2, "bubbleId": "a1"}],
    }
    session = parse_cursor_composer_data(data, worktrees=repo_worktrees())
    assert session["id"] == "composer-1"
    assert session["title"] == "Cursor plan"
    assert session["worktree"] == "/repo/main"
    assert session["branch"] == "feature/test"
    assert session["messages"] == 2
    assert session["entrypoint"] == "app"
def test_fly_toml_and_chalice_config_parsing():
    assert parse_fly_toml('app = "fof-lesson-dash"\n') == "fof-lesson-dash"
    config = parse_chalice_config('{"app_name":"qrag-llm","stages":{"api":{},"dev":{}}}')
    assert config == {"name": "qrag-llm", "stages": ["api", "dev"]}
def test_snapshot_merge_logic_for_partial_refresh():
    snapshot = empty_snapshot("/repo/main")
    snapshot["layers"]["worktrees"] = [{"path": "/repo/main"}]
    snapshot["layer_meta"]["worktrees"] = {"generated_at": "old", "took_s": 1.0, "error": None}
    updates = {"sessions": {"items": [{"id": "s1"}], "generated_at": "new", "took_s": 0.2, "error": None}}
    merged = merge_snapshot(snapshot, updates, "/repo/main", generated_at="top")
    assert merged["generated_at"] == "top"
    assert merged["layers"]["worktrees"] == [{"path": "/repo/main"}]
    assert merged["layer_meta"]["worktrees"]["generated_at"] == "old"
    assert merged["layers"]["sessions"] == [{"id": "s1"}]
def test_session_snapshot_adds_subagent_counts_from_turns_db(tmp_path):
    db_path = tmp_path / "apps/holodeck/data/turns.db"
    conn = turns_db.connect(db_path)
    turns_db.init_db(conn)
    parent = {"id": "codex:parent", "platform": "codex", "entrypoint": "app", "host": "local", "source_path": "parent", "source_url": None, "project": "/repo/main", "worktree": "/repo/main", "branch": "feature/test", "label": "Codex App", "model": None, "interface": "Codex App", "origin": "operator", "title": None, "started": "2026-07-20T10:00:00-07:00", "last_activity": "2026-07-20T10:30:00-07:00", "ingested_at": "now"}
    child = dict(parent, id="codex:child", origin="delegated", parent_session_id="codex:parent")
    turns_db.upsert_session(conn, parent)
    turns_db.upsert_session(conn, child)
    conn.commit()
    conn.close()
    items = [{"platform": "codex", "id": "parent", "origin": "operator"}, {"platform": "codex", "id": "child", "origin": "delegated"}]
    sessions_collector.add_subagent_counts(tmp_path, items)
    assert items[0]["subagent_count"] == 1
    assert items[1]["subagent_count"] == 0
def test_state_worktree_merge_defaults_and_next_steps_crud():
    state = holodeck_state.empty_state()
    state, entry = holodeck_state.merge_worktree_state(state, "feature/demo", {"next_step": "Review backend", "last_done_status": "needs-review"}, updated_at="2026-07-11T07:00:00-07:00")
    assert entry == {
        "active": True,
        "order": None,
        "next_step": "Review backend",
        "last_done": None,
        "last_done_status": "needs-review",
        "notes": None,
        "submitted_via": None,
        "submitted_at": None,
        "ai_responded": False,
        "primary_interface": None,
        "steps": [],
        "deactivated_at": None,
    }
    with pytest.raises(ValueError):
        holodeck_state.merge_worktree_state(state, "feature/demo", {"bogus": True})
    state, item = holodeck_state.create_next_step(state, "Ship API", created_at="2026-07-11T07:01:00-07:00", id_value="abc123")
    assert item == {"id": "abc123", "text": "Ship API", "done": False, "created_at": "2026-07-11T07:01:00-07:00", "source": None}
    state, newer = holodeck_state.create_next_step(state, "Write docs", created_at="2026-07-11T07:01:30-07:00", id_value="def456")
    assert [step["id"] for step in state["next_steps"]] == ["def456", "abc123"]
    assert newer["id"] == "def456"
    state, item = holodeck_state.update_next_step(state, "abc123", {"done": True, "text": "Ship API tests"}, updated_at="2026-07-11T07:02:00-07:00")
    assert item["done"] is True
    assert item["text"] == "Ship API tests"
    state, deleted = holodeck_state.delete_next_step(state, "abc123", updated_at="2026-07-11T07:03:00-07:00")
    assert deleted["id"] == "abc123"
    assert [step["id"] for step in state["next_steps"]] == ["def456"]
    state, deleted = holodeck_state.delete_next_step(state, "def456", updated_at="2026-07-11T07:03:30-07:00")
    assert deleted["id"] == "def456"
    assert state["next_steps"] == []
def test_state_submitted_via_accepts_enum_and_null_rejects_junk():
    for submitted_via in ("cursor", "claude-cli", "claude-app", "codex-cli", "codex-app", None):
        state = holodeck_state.empty_state()
        state, entry = holodeck_state.merge_worktree_state(
            state,
            "feature/demo",
            {"submitted_via": submitted_via, "submitted_at": "2026-07-12T05:50:00.000Z", "ai_responded": False},
            updated_at="now",
        )
        assert entry["submitted_via"] == submitted_via
        assert entry["primary_interface"] == submitted_via
        assert entry["submitted_at"] == "2026-07-12T05:50:00.000Z"
        assert entry["ai_responded"] is False
    with pytest.raises(ValueError):
        holodeck_state.merge_worktree_state(holodeck_state.empty_state(), "feature/demo", {"submitted_via": "email"})
    with pytest.raises(ValueError):
        holodeck_state.merge_worktree_state(holodeck_state.empty_state(), "feature/demo", {"submitted_at": "not-a-date"})
    with pytest.raises(ValueError):
        holodeck_state.merge_worktree_state(holodeck_state.empty_state(), "feature/demo", {"ai_responded": "yes"})
def test_state_primary_interface_migrates_from_legacy_and_validates_steps():
    raw = {
        "worktrees": {
            "feature/demo": {
                "submitted_via": "codex-cli",
                "steps": [{"id": "s1", "text": "Review backend", "done": False, "created_at": "2026-07-12T08:00:00-07:00"}],
                "deactivated_at": "2026-07-12T08:10:00-07:00",
            }
        }
    }
    entry = holodeck_state.normalize_state(raw)["worktrees"]["feature/demo"]
    assert entry["primary_interface"] == "codex-cli"
    assert entry["steps"][0]["id"] == "s1"
    assert entry["deactivated_at"] == "2026-07-12T08:10:00-07:00"
    state = holodeck_state.empty_state()
    state, entry = holodeck_state.merge_worktree_state(state, "feature/demo", {"primary_interface": "cursor"}, updated_at="now")
    assert entry["primary_interface"] == "cursor"
    with pytest.raises(ValueError):
        holodeck_state.merge_worktree_state(state, "feature/demo", {"primary_interface": "email"})
    with pytest.raises(ValueError):
        holodeck_state.merge_worktree_state(state, "feature/demo", {"steps": "Review backend"})
    with pytest.raises(ValueError):
        holodeck_state.merge_worktree_state(state, "feature/demo", {"steps": [{"id": "", "text": "bad", "done": False, "created_at": None}]})
    with pytest.raises(ValueError):
        holodeck_state.merge_worktree_state(state, "feature/demo", {"deactivated_at": "not-a-date"})
def test_next_steps_order_route_reorders_missing_tail_and_rejects_unknown(tmp_path, monkeypatch):
    state = holodeck_state.empty_state()
    for step_id, text in (("a", "First"), ("b", "Second"), ("c", "Third")):
        state, item = holodeck_state.create_next_step(state, text, created_at="2026-07-12T08:00:00-07:00", id_value=step_id)
    monkeypatch.setattr(holodeck_server, "STATE_PATH", tmp_path / "state.json")
    holodeck_state.write_state(holodeck_server.STATE_PATH, state)
    items = holodeck_server.next_steps_order_put({"order": ["c", "a"]})
    assert [item["id"] for item in items] == ["c", "a", "b"]
    assert [item["id"] for item in holodeck_state.load_state(holodeck_server.STATE_PATH)["next_steps"]] == ["c", "a", "b"]
    with pytest.raises(holodeck_server.HTTPException) as exc:
        holodeck_server.next_steps_order_put({"order": ["missing"]})
    assert exc.value.status_code == 400
def test_next_steps_archive_route_creates_archive_and_removes_state(tmp_path, monkeypatch):
    class FixedDatetime:
        @classmethod
        def now(cls):
            return datetime.fromisoformat("2026-07-12T08:35:00-07:00")
    state = holodeck_state.empty_state()
    state, item = holodeck_state.create_next_step(state, "Ship API", created_at="2026-07-11T07:01:00-07:00", id_value="abc123")
    state, item = holodeck_state.update_next_step(state, "abc123", {"done": True}, updated_at="2026-07-12T08:00:00-07:00")
    monkeypatch.setattr(holodeck_server, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(holodeck_server, "TODO_ARCHIVE_PATH", tmp_path / "todo-archive.md")
    monkeypatch.setattr(holodeck_server, "datetime", FixedDatetime)
    holodeck_state.write_state(holodeck_server.STATE_PATH, state)
    assert holodeck_server.next_steps_archive_post("abc123") == {"ok": True}
    assert holodeck_state.load_state(holodeck_server.STATE_PATH)["next_steps"] == []
    assert holodeck_server.TODO_ARCHIVE_PATH.read_text(encoding="utf-8") == "\n".join([
        "# Holodeck to-do archive",
        "",
        "## 2026-07-12",
        "- [x] Ship API (added 2026-07-11, archived 08:35)",
    ]) + "\n"
def test_next_steps_archive_route_appends_to_existing_today_section(tmp_path, monkeypatch):
    class FixedDatetime:
        @classmethod
        def now(cls):
            return datetime.fromisoformat("2026-07-12T09:05:00-07:00")
    archive_path = tmp_path / "todo-archive.md"
    archive_path.write_text("\n".join([
        "# Holodeck to-do archive",
        "",
        "## 2026-07-12",
        "- [ ] Existing item (added 2026-07-10, archived 08:00)",
        "",
        "## 2026-07-11",
        "- [x] Older item (added 2026-07-09, archived 10:00)",
        "",
    ]), encoding="utf-8")
    state = holodeck_state.empty_state()
    state, item = holodeck_state.create_next_step(state, "Archive me", created_at="2026-07-12T08:59:00-07:00", id_value="abc123")
    monkeypatch.setattr(holodeck_server, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(holodeck_server, "TODO_ARCHIVE_PATH", archive_path)
    monkeypatch.setattr(holodeck_server, "datetime", FixedDatetime)
    holodeck_state.write_state(holodeck_server.STATE_PATH, state)
    assert holodeck_server.next_steps_archive_post("abc123") == {"ok": True}
    text = archive_path.read_text(encoding="utf-8")
    assert "## 2026-07-12\n- [ ] Existing item (added 2026-07-10, archived 08:00)\n- [ ] Archive me (added 2026-07-12, archived 09:05)\n\n## 2026-07-11" in text
    with pytest.raises(holodeck_server.HTTPException) as exc:
        holodeck_server.next_steps_archive_post("missing")
    assert exc.value.status_code == 404
def test_parse_todo_archive_returns_most_recent_first():
    content = "\n".join([
        "# Holodeck to-do archive",
        "",
        "## 2026-07-12",
        "- [ ] Older today (added 2026-07-10, archived 08:00)",
        "- [x] Newer today (added 2026-07-12, archived 09:05)",
        "",
        "## 2026-07-11",
        "- [x] Yesterday (added 2026-07-09, archived 10:00)",
        "",
    ])
    items = holodeck_server.parse_todo_archive(content)
    assert [item["text"] for item in items] == ["Newer today", "Older today", "Yesterday"]
    assert items[0]["done"] is True
    assert items[0]["archived_at"] == "2026-07-12T09:05"
    assert items[1]["done"] is False
def test_next_steps_archive_get_route_reads_file(tmp_path, monkeypatch):
    archive_path = tmp_path / "todo-archive.md"
    archive_path.write_text("\n".join([
        "# Holodeck to-do archive",
        "",
        "## 2026-07-12",
        "- [ ] First (added 2026-07-10, archived 08:00)",
        "- [x] Second (added 2026-07-12, archived 09:05)",
        "",
    ]) + "\n", encoding="utf-8")
    monkeypatch.setattr(holodeck_server, "TODO_ARCHIVE_PATH", archive_path)
    payload = holodeck_server.next_steps_archive_get()
    assert [item["text"] for item in payload["items"]] == ["Second", "First"]
    missing = tmp_path / "missing-todo-archive.md"
    monkeypatch.setattr(holodeck_server, "TODO_ARCHIVE_PATH", missing)
    assert holodeck_server.next_steps_archive_get() == {"items": []}
def test_session_detail_messages_are_not_truncated():
    long_text = "A" * 2500
    lines = [json_line({"type": "assistant", "timestamp": "2026-07-12T08:00:00-07:00", "message": {"content": long_text}})]
    messages = claude_messages_from_lines(lines)
    assert messages == [{"role": "assistant", "text": long_text, "ts": "2026-07-12T08:00:00-07:00"}]
def test_state_worktree_order_assignment_sets_unlisted_to_null():
    state = holodeck_state.empty_state()
    state, entry = holodeck_state.merge_worktree_state(state, "feature/a", {"order": 9}, updated_at="old")
    state, entry = holodeck_state.merge_worktree_state(state, "feature/b", {"order": 8}, updated_at="old")
    state, worktrees = holodeck_state.assign_worktree_order(state, ["feature/b", "feature/c"], updated_at="new")
    assert worktrees["feature/b"]["order"] == 0
    assert worktrees["feature/c"]["order"] == 1
    assert worktrees["feature/a"]["order"] is None
def test_apps_touched_path_to_slug_mapping_uses_longest_prefix():
    slugs = ["minecraft", "minecraft/prism-sync", "holodeck"]
    assert app_slug_for_path("apps/minecraft/prism-sync/server/main.py", slugs) == "minecraft/prism-sync"
    assert app_slug_for_path("apps/holodeck/server.py", slugs) == "holodeck"
    assert app_slug_for_path("core/fileops.py", slugs) is None
def test_kind_fallback_inference(tmp_path):
    chalice = tmp_path / "chalice-app"
    chalice.mkdir()
    (chalice / ".chalice").mkdir()
    web = tmp_path / "web-app"
    web.mkdir()
    (web / "index.html").write_text("<h1>hi</h1>", encoding="utf-8")
    cli = tmp_path / "cli-app"
    cli.mkdir()
    (cli / "run.py").write_text("print('hi')\n", encoding="utf-8")
    docs = tmp_path / "docs-app"
    docs.mkdir()
    (docs / "README.md").write_text("# Docs\n", encoding="utf-8")
    scripts = tmp_path / "scripts-app"
    scripts.mkdir()
    assert infer_app_kind(chalice) == "chalice"
    assert infer_app_kind(web) == "web"
    assert infer_app_kind(cli) == "cli"
    assert infer_app_kind(docs) == "docs"
    assert infer_app_kind(scripts) == "scripts"
def test_file_path_safety_read_roots_and_write_allowlist(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    readme = repo / "README.md"
    readme.write_text("# Repo\n", encoding="utf-8")
    outside = tmp_path / "outside.md"
    outside.write_text("# Outside\n", encoding="utf-8")
    non_openspec = repo / "notes.md"
    non_openspec.write_text("# Notes\n", encoding="utf-8")
    spec_path = worktree / "apps/demo/openspec/specs/app/spec.md"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_text("# Spec\n", encoding="utf-8")
    snapshot = {"layers": {"worktrees": [{"path": str(worktree), "branch": "feature/demo"}]}}
    assert validate_file_read_path("README.md", repo, snapshot) == readme.resolve()
    assert validate_file_write_path(str(spec_path), repo, snapshot) == spec_path.resolve()
    with pytest.raises(ValueError):
        validate_file_read_path("../outside.md", repo, snapshot)
    with pytest.raises(PermissionError):
        validate_file_write_path(str(non_openspec), repo, snapshot)
    colors = repo / "apps/holodeck/worktree-colors.yaml"
    colors.parent.mkdir(parents=True)
    colors.write_text("rules: []\n", encoding="utf-8")
    assert validate_file_write_path(str(colors), repo, snapshot) == colors.resolve()
def test_branch_commits_route_uses_snapshot_branch_guard_and_pages(monkeypatch):
    commits = [
        {"sha": str(index), "author": "Author", "date": "2026-07-12T05:00:00-07:00", "subject": "Subject", "body": ""}
        for index in range(150)
    ]
    monkeypatch.setattr(holodeck_server, "load_snapshot", lambda: {"layers": {"branches": [{"name": "feature/demo"}]}})
    monkeypatch.setattr(holodeck_server.branches_collector, "resolve_branch_ref", lambda repo_root, branch: "refs/heads/" + branch)
    monkeypatch.setattr(holodeck_server.branches_collector, "load_branch_commits", lambda repo_root, ref, skip, limit: commits[skip:skip + limit + 1])
    payload = holodeck_server.branch_commits("feature/demo", skip="2", limit="200")
    assert payload["branch"] == "feature/demo"
    assert payload["commits"][0]["sha"] == "2"
    assert len(payload["commits"]) == 100
    assert payload["has_more"] is True
    with pytest.raises(holodeck_server.HTTPException) as exc:
        holodeck_server.branch_commits("feature/missing")
    assert exc.value.status_code == 404
