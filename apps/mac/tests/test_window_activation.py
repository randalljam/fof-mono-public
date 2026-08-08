import subprocess

import pytest

from apps.mac import window_activation as activation


class Completed:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def darwin(monkeypatch):
    monkeypatch.setattr(activation.platform, "system", lambda: "Darwin")


def test_cursor_focus_uses_fixed_script_and_separate_arguments(tmp_path, monkeypatch):
    darwin(monkeypatch)
    worktree = tmp_path / "feature-demo"
    worktree.mkdir()
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return Completed("FOCUSED\ttitle\n")

    monkeypatch.setattr(activation.subprocess, "run", fake_run)
    result = activation.focus_cursor_window(worktree, ["feature-demo", "value'; do shell script \"bad\""])

    assert result.to_dict() == {"ok": True, "target": "cursor", "status": "focused", "matched_by": "title"}
    command, kwargs = calls[0]
    assert command[:2] == [str(activation.OSASCRIPT), str(activation.SCRIPT_PATHS["cursor"])]
    assert command[2] == str(worktree.resolve())
    assert command[3:] == [
        "1",
        str(worktree.resolve()),
        worktree.resolve().as_uri(),
        "feature-demo",
        "value'; do shell script \"bad\"",
    ]
    assert kwargs["shell"] is False
    assert kwargs["timeout"] == 15.0


def test_explicit_cursor_candidates_replace_ambiguous_path_basename(tmp_path, monkeypatch):
    darwin(monkeypatch)
    worktree = tmp_path / "fof-mono"
    worktree.mkdir()
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return Completed("FOCUSED\ttitle\n")

    monkeypatch.setattr(activation.subprocess, "run", fake_run)
    activation.focus_cursor_window(worktree, ["codex-feature-minecraft-mod-build-local"])

    assert calls[0][2:] == [
        str(worktree.resolve()),
        "1",
        str(worktree.resolve()),
        worktree.resolve().as_uri(),
        "codex-feature-minecraft-mod-build-local",
    ]


def test_explicit_empty_cursor_candidates_use_path_only(tmp_path, monkeypatch):
    darwin(monkeypatch)
    worktree = tmp_path / "fof-mono"
    worktree.mkdir()
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return Completed("FOCUSED\tpath\n")

    monkeypatch.setattr(activation.subprocess, "run", fake_run)
    result = activation.focus_cursor_window(worktree, [])

    assert result.matched_by == "path"
    assert calls[0][2:] == [
        str(worktree.resolve()),
        "1",
        str(worktree.resolve()),
        worktree.resolve().as_uri(),
    ]


def test_cursor_timeout_remains_the_third_positional_argument(tmp_path, monkeypatch):
    darwin(monkeypatch)
    worktree = tmp_path / "feature-demo"
    worktree.mkdir()
    calls = []

    def fake_run(command, **kwargs):
        calls.append(kwargs)
        return Completed("FOCUSED\tpath\n")

    monkeypatch.setattr(activation.subprocess, "run", fake_run)
    activation.focus_cursor_window(worktree, [], 7)

    assert calls[0]["timeout"] == 7.0


def test_cursor_candidate_defaults_to_path_basename(tmp_path, monkeypatch):
    darwin(monkeypatch)
    worktree = tmp_path / "feature-demo"
    worktree.mkdir()
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return Completed("FOCUSED\ttitle\n")

    monkeypatch.setattr(activation.subprocess, "run", fake_run)
    activation.focus_cursor_window(worktree)

    assert calls[0][2:] == [
        str(worktree.resolve()),
        "1",
        str(worktree.resolve()),
        worktree.resolve().as_uri(),
        "feature-demo",
    ]


def test_cursor_document_roots_are_canonical_separate_arguments(tmp_path, monkeypatch):
    darwin(monkeypatch)
    worktree = tmp_path / "workspace"
    shared = tmp_path / "shared # ü"
    worktree.mkdir()
    shared.mkdir()
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return Completed("FOCUSED\ttitle\n")

    monkeypatch.setattr(activation.subprocess, "run", fake_run)
    activation.focus_cursor_window(
        worktree,
        ["multi-root"],
        document_roots=[shared, worktree],
    )

    assert calls[0][2:] == [
        str(worktree.resolve()),
        "2",
        str(worktree.resolve()),
        worktree.resolve().as_uri(),
        str(shared.resolve()),
        shared.resolve().as_uri(),
        "multi-root",
    ]


@pytest.mark.parametrize(
    ("output", "code", "match_count"),
    [
        ("APP_NOT_RUNNING", activation.FocusErrorCode.APP_NOT_RUNNING, None),
        ("TARGET_NOT_FOUND", activation.FocusErrorCode.TARGET_NOT_FOUND, None),
        ("AMBIGUOUS\t3", activation.FocusErrorCode.AMBIGUOUS_MATCH, 3),
        ("PERMISSION_REQUIRED", activation.FocusErrorCode.PERMISSION_REQUIRED, None),
        ("unexpected", activation.FocusErrorCode.AUTOMATION_FAILED, None),
    ],
)
def test_adapter_protocol_errors(output, code, match_count, tmp_path, monkeypatch):
    darwin(monkeypatch)
    worktree = tmp_path / "feature-demo"
    worktree.mkdir()
    monkeypatch.setattr(activation.subprocess, "run", lambda *args, **kwargs: Completed(output))

    with pytest.raises(activation.FocusError) as caught:
        activation.focus_cursor_window(worktree)

    assert caught.value.code == code
    assert caught.value.match_count == match_count


def test_permission_stderr_is_redacted(monkeypatch):
    darwin(monkeypatch)
    private_stderr = "private window title: osascript is not allowed assistive access. (-1719)"
    monkeypatch.setattr(
        activation.subprocess,
        "run",
        lambda *args, **kwargs: Completed(stderr=private_stderr, returncode=1),
    )

    with pytest.raises(activation.FocusError) as caught:
        activation.focus_browser_tab("chrome", url="https://example.test/private-token")

    assert caught.value.code == activation.FocusErrorCode.PERMISSION_REQUIRED
    assert private_stderr not in str(caught.value)
    assert private_stderr not in str(caught.value.to_dict())


def test_subprocess_timeout_maps_to_stable_error(monkeypatch):
    darwin(monkeypatch)

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(activation.subprocess, "run", timeout)
    with pytest.raises(activation.FocusError) as caught:
        activation.focus_browser_tab("safari", title="Example")
    assert caught.value.code == activation.FocusErrorCode.AUTOMATION_TIMEOUT


def test_browser_exact_match_arguments_and_result(monkeypatch):
    darwin(monkeypatch)
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return Completed("FOCUSED\turl_title")

    monkeypatch.setattr(activation.subprocess, "run", fake_run)
    result = activation.focus_browser_tab("Chrome", url="https://example.test/a/", title="Example")
    assert result.matched_by == "url_title"
    assert calls[0][-2:] == ["https://example.test/a/", "Example"]


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: activation.focus_cursor_window("relative/path"), "absolute"),
        (lambda: activation.focus_cursor_window("/tmp/demo", title_candidates="demo"), "sequence"),
        (lambda: activation.focus_cursor_window("/tmp/demo", document_roots="/tmp/shared"), "sequence"),
        (lambda: activation.focus_cursor_window("/tmp/demo", document_roots=["relative"]), "absolute"),
        (lambda: activation.focus_browser_tab("firefox", url="https://example.test"), "chrome or safari"),
        (lambda: activation.focus_browser_tab("chrome"), "url or title"),
        (lambda: activation.focus_browser_tab("chrome", title="bad\nvalue"), "control"),
        (lambda: activation.focus_browser_tab("chrome", title="Example", timeout=0), "greater than zero"),
    ],
)
def test_invalid_requests_fail_before_subprocess(call, message, monkeypatch):
    monkeypatch.setattr(
        activation.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("subprocess must not run"),
    )
    with pytest.raises(activation.FocusError, match=message):
        call()


def test_non_macos_fails_before_subprocess(tmp_path, monkeypatch):
    worktree = tmp_path / "feature-demo"
    worktree.mkdir()
    monkeypatch.setattr(activation.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        activation.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("subprocess must not run"),
    )

    with pytest.raises(activation.FocusError) as caught:
        activation.focus_cursor_window(worktree)
    assert caught.value.code == activation.FocusErrorCode.UNSUPPORTED_PLATFORM


def test_checked_in_scripts_exist():
    assert set(activation.SCRIPT_PATHS) == {"cursor", "chrome", "safari"}
    assert all(path.is_file() for path in activation.SCRIPT_PATHS.values())


def test_cursor_title_fallback_does_not_match_a_same_named_file_prefix():
    source = activation.SCRIPT_PATHS["cursor"].read_text(encoding="utf-8")
    assert "windowTitle ends with (separatorValue & candidateText)" in source
    assert 'windowTitle ends with (separatorValue & candidateText & " (Workspace)")' in source
    assert "windowTitle starts with (candidateText & separatorValue)" not in source
    assert "windowTitle contains (separatorValue & candidateText" not in source


def test_cursor_script_focuses_after_activation_and_verifies_the_result():
    source = activation.SCRIPT_PATHS["cursor"].read_text(encoding="utf-8")
    activate_at = source.index("set frontmost to true")
    enumerate_at = source.index("set cursorWindows to every window")
    first_raise_at = source.index('perform action "AXRaise" of targetWindow')
    verify_at = source.index("repeat with verificationAttempt from 1 to 8")

    assert activate_at < enumerate_at < first_raise_at < verify_at
    assert source.count("delay 1.0") == 1
    assert source.count("delay 0.5") == 1
    assert source.count('perform action "AXRaise" of targetWindow') == 2
    assert 'is not "AXStandardWindow" then return ""' in source
    assert 'if windowTitle is "" or windowTitle is "Window" then return ""' in source
    document_at = source.index('set documentValue to value of attribute "AXDocument"')
    workspace_fallback_at = source.index("if workspaceTitleMatched and documentInAuthorizedRoot then return")
    assert document_at < workspace_fallback_at
    assert "set hasUsableDocument to false" in source
    assert "set documentInAuthorizedRoot to false" in source
    assert "set documentInAuthorizedRoot to my documentMatchesAnyRoot" in source
    assert "documentText starts with (targetURI & \"/\")" in source
    assert "if hasUsableDocument then" in source
    assert 'if titleMatched then return "title"' in source
    assert "set focusedWindow to first window" not in source
    assert "if (count verifiedMatches) is 1 then" in source
    assert 'set focusedWindowIsMain to value of attribute "AXMain" of focusedWindow' in source
    assert 'if focusedWindowIsMain is true then' in source
    assert "if frontmost is not true then return \"AUTOMATION_FAILED\"" in source
    assert "set currentKind to my matchKindForWindow(verifiedWindow" in source
    assert 'if verifiedKind is "" then return "AUTOMATION_FAILED"' in source


def test_cursor_script_distinguishes_enumeration_error_from_no_windows():
    source = activation.SCRIPT_PATHS["cursor"].read_text(encoding="utf-8")
    assert "set cursorWindows to every window" in source
    assert "on isPermissionError(errorNumber)" in source
    assert "errorNumber is -1719 or errorNumber is -1743 or errorNumber is -25211" in source
    assert 'if my isPermissionError(errorNumber) then return "PERMISSION_REQUIRED"' in source
    assert '(count cursorWindows) is 0 then return "TARGET_NOT_FOUND"' in source
