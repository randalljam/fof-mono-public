"""Focus already-open macOS application windows and browser tabs.

This module is intentionally independent of any web application. Callers supply
semantic match values; only reviewed AppleScript adapters are executable.
"""

from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path
import platform
import subprocess
from typing import Sequence


OSASCRIPT = Path("/usr/bin/osascript")
SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"
SCRIPT_PATHS = {
    "cursor": SCRIPTS_DIR / "focus_cursor.applescript",
    "chrome": SCRIPTS_DIR / "focus_chrome.applescript",
    "safari": SCRIPTS_DIR / "focus_safari.applescript",
}
MAX_MATCH_LENGTH = 4096
MAX_TITLE_CANDIDATES = 32
MAX_DOCUMENT_ROOTS = 64
MAX_TIMEOUT_SECONDS = 30.0
MAX_PROTOCOL_OUTPUT = 4096


class FocusErrorCode(str, Enum):
    INVALID_REQUEST = "invalid_request"
    UNSUPPORTED_PLATFORM = "unsupported_platform"
    APP_NOT_RUNNING = "app_not_running"
    TARGET_NOT_FOUND = "target_not_found"
    AMBIGUOUS_MATCH = "ambiguous_match"
    PERMISSION_REQUIRED = "permission_required"
    AUTOMATION_TIMEOUT = "automation_timeout"
    AUTOMATION_FAILED = "automation_failed"


ERROR_MESSAGES = {
    FocusErrorCode.INVALID_REQUEST: "The window focus request is invalid.",
    FocusErrorCode.UNSUPPORTED_PLATFORM: "Window focusing is supported only on macOS.",
    FocusErrorCode.APP_NOT_RUNNING: "The target application is not running.",
    FocusErrorCode.TARGET_NOT_FOUND: "No open window or tab matched the target.",
    FocusErrorCode.AMBIGUOUS_MATCH: "More than one open window or tab matched the target.",
    FocusErrorCode.PERMISSION_REQUIRED: "macOS Accessibility or Automation permission is required.",
    FocusErrorCode.AUTOMATION_TIMEOUT: "The macOS focus action timed out.",
    FocusErrorCode.AUTOMATION_FAILED: "macOS could not focus the requested target.",
}


@dataclass(frozen=True)
class FocusResult:
    """Privacy-safe success result returned by a focus adapter."""

    target: str
    matched_by: str

    def to_dict(self):
        return {
            "ok": True,
            "target": self.target,
            "status": "focused",
            "matched_by": self.matched_by,
        }


class FocusError(RuntimeError):
    """Stable, privacy-safe activation failure."""

    def __init__(self, code, message=None, *, target=None, match_count=None):
        try:
            self.code = FocusErrorCode(code)
        except ValueError:
            self.code = FocusErrorCode.AUTOMATION_FAILED
        self.message = message or ERROR_MESSAGES[self.code]
        self.target = target
        self.match_count = match_count
        super().__init__(self.message)

    def to_dict(self):
        error = {"code": self.code.value, "message": self.message}
        if self.match_count is not None:
            error["match_count"] = self.match_count
        payload = {"ok": False, "error": error}
        if self.target:
            payload["target"] = self.target
        return payload


def _invalid(message=None):
    raise FocusError(FocusErrorCode.INVALID_REQUEST, message)


def _validate_text(value, name, *, allow_empty=False, max_length=MAX_MATCH_LENGTH):
    if value is None and allow_empty:
        return ""
    if not isinstance(value, str):
        _invalid(f"{name} must be a string.")
    if not value and not allow_empty:
        _invalid(f"{name} is required.")
    if len(value) > max_length:
        _invalid(f"{name} is too long.")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        _invalid(f"{name} contains control characters.")
    return value


def _validate_timeout(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _invalid("timeout must be a number.")
    timeout = float(value)
    if timeout <= 0 or timeout > MAX_TIMEOUT_SECONDS:
        _invalid(f"timeout must be greater than zero and at most {int(MAX_TIMEOUT_SECONDS)} seconds.")
    return timeout


def _require_macos(target):
    if platform.system() != "Darwin":
        raise FocusError(FocusErrorCode.UNSUPPORTED_PLATFORM, target=target)


def _canonical_path(value):
    if not isinstance(value, (str, os.PathLike)):
        _invalid("worktree_path must be a path.")
    raw = Path(value).expanduser()
    if not raw.is_absolute():
        _invalid("worktree_path must be absolute.")
    text = _validate_text(str(raw), "worktree_path")
    return str(Path(text).resolve(strict=False))


def _title_candidates(path, values):
    if values is None:
        candidates = [Path(path).name]
    else:
        if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
            _invalid("title_candidates must be a sequence of strings.")
        candidates = list(values)
    if len(candidates) > MAX_TITLE_CANDIDATES:
        _invalid(f"title_candidates must contain at most {MAX_TITLE_CANDIDATES} values.")
    normalized = []
    seen = set()
    for value in candidates:
        candidate = _validate_text(value, "title candidate", max_length=512)
        key = candidate.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(candidate)
    return normalized


def _document_roots(path, values):
    if values is None:
        roots = [path]
    else:
        if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
            _invalid("document_roots must be a sequence of absolute paths.")
        roots = [path, *values]
    if len(roots) > MAX_DOCUMENT_ROOTS:
        _invalid(f"document_roots must contain at most {MAX_DOCUMENT_ROOTS} values.")
    normalized = []
    seen = set()
    for value in roots:
        root = _canonical_path(value)
        key = root.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(root)
    return normalized


def _permission_failure(stderr):
    text = (stderr or "").lower()
    markers = (
        "not authorized to send apple events",
        "not allowed assistive access",
        "accessibility permission",
        "(-1743)",
        "(-1719)",
        "(-25211)",
    )
    return any(marker in text for marker in markers)


def _run_adapter(target, args, timeout):
    _require_macos(target)
    script_path = SCRIPT_PATHS[target]
    if not script_path.is_file() or not OSASCRIPT.is_file():
        raise FocusError(FocusErrorCode.AUTOMATION_FAILED, target=target)
    command = [str(OSASCRIPT), str(script_path), *args]
    try:
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise FocusError(FocusErrorCode.AUTOMATION_TIMEOUT, target=target) from exc
    except OSError as exc:
        raise FocusError(FocusErrorCode.AUTOMATION_FAILED, target=target) from exc
    stdout = (completed.stdout or "")[:MAX_PROTOCOL_OUTPUT].strip()
    stderr = (completed.stderr or "")[:MAX_PROTOCOL_OUTPUT]
    if completed.returncode != 0:
        code = FocusErrorCode.PERMISSION_REQUIRED if _permission_failure(stderr) else FocusErrorCode.AUTOMATION_FAILED
        raise FocusError(code, target=target)
    return _parse_protocol(target, stdout)


def _parse_protocol(target, output):
    parts = output.split("\t") if output else []
    status = parts[0] if parts else ""
    if status == "FOCUSED" and len(parts) == 2 and parts[1] in {"path", "title", "url", "url_title"}:
        return FocusResult(target=target, matched_by=parts[1])
    if status == "APP_NOT_RUNNING":
        raise FocusError(FocusErrorCode.APP_NOT_RUNNING, target=target)
    if status == "TARGET_NOT_FOUND":
        raise FocusError(FocusErrorCode.TARGET_NOT_FOUND, target=target)
    if status == "AMBIGUOUS":
        match_count = None
        if len(parts) == 2:
            try:
                match_count = int(parts[1])
            except ValueError:
                match_count = None
        raise FocusError(FocusErrorCode.AMBIGUOUS_MATCH, target=target, match_count=match_count)
    if status == "PERMISSION_REQUIRED":
        raise FocusError(FocusErrorCode.PERMISSION_REQUIRED, target=target)
    raise FocusError(FocusErrorCode.AUTOMATION_FAILED, target=target)


def focus_cursor_window(worktree_path, title_candidates=None, timeout=15, document_roots=None):
    """Focus the one open Cursor window matching a canonical worktree path/name."""

    target = "cursor"
    path = _canonical_path(worktree_path)
    candidates = _title_candidates(path, title_candidates)
    roots = _document_roots(path, document_roots)
    root_args = []
    for root in roots:
        root_args.extend([root, Path(root).as_uri()])
    return _run_adapter(target, [path, str(len(roots)), *root_args, *candidates], _validate_timeout(timeout))


def focus_browser_tab(browser, url=None, title=None, timeout=5):
    """Focus one already-open Chrome or Safari tab using exact URL/title values."""

    if not isinstance(browser, str) or browser.lower() not in {"chrome", "safari"}:
        _invalid("browser must be chrome or safari.")
    target = browser.lower()
    url_value = _validate_text(url, "url", allow_empty=True)
    title_value = _validate_text(title, "title", allow_empty=True)
    if not url_value and not title_value:
        _invalid("url or title is required.")
    return _run_adapter(target, [url_value, title_value], _validate_timeout(timeout))
