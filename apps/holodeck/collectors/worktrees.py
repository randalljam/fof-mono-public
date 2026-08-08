"""Collect git worktree state."""

import importlib.util
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlparse

try:
    import yaml
except ImportError:
    yaml = None

try:
    from apps.holodeck.collectors import apps as apps_collector
except ImportError:
    from collectors import apps as apps_collector

CURSOR_STORAGE = Path.home() / "Library/Application Support/Cursor/User/globalStorage/storage.json"
WORKTREE_COLORS_REL = Path("apps/holodeck/worktree-colors.yaml")
DEFAULT_TITLE_BAR_FOREGROUND = "#ffffff"
TITLEBAR_BACKGROUND_RE = re.compile(r'"titleBar\.activeBackground"\s*:\s*"([^"]+)"')
TITLEBAR_FOREGROUND_RE = re.compile(r'"titleBar\.activeForeground"\s*:\s*"([^"]+)"')

### Parsing
def short_sha(value):
    if not value:
        return None
    return value[:7]
def normalize_branch(ref):
    if not ref:
        return "detached"
    prefixes = ("refs/heads/", "refs/remotes/")
    for prefix in prefixes:
        if ref.startswith(prefix):
            return ref[len(prefix):]
    return ref
def path_exists(path, existing_paths):
    if existing_paths is None:
        return Path(path).exists()
    return str(path) in existing_paths
def parse_worktree_porcelain(text, current_path=None, existing_paths=None):
    entries = []
    current = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")
        if not line:
            continue
        if line.startswith("worktree "):
            if current:
                entries.append(current)
            path = line[len("worktree "):]
            current = {
                "path": path,
                "branch": "detached",
                "head": None,
                "is_current": False,
                "missing": not path_exists(path, existing_paths),
            }
            if current_path and Path(path).expanduser().resolve() == Path(current_path).expanduser().resolve():
                current["is_current"] = True
            continue
        if current is None:
            continue
        if line.startswith("HEAD "):
            current["head"] = short_sha(line[len("HEAD "):])
        elif line.startswith("branch "):
            current["branch"] = normalize_branch(line[len("branch "):])
        elif line == "detached":
            current["branch"] = "detached"
    if current:
        entries.append(current)
    return entries
def parse_status_counts(text):
    dirty = 0
    untracked = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.startswith("??"):
            untracked += 1
        else:
            dirty += 1
    return dirty, untracked
def parse_left_right_counts(text):
    parts = text.strip().split()
    if len(parts) != 2:
        return 0, 0
    return int(parts[0]), int(parts[1])
def parse_last_commit(text, fallback_sha=None):
    parts = text.rstrip("\n").split("\x1f")
    if len(parts) != 4:
        return {"sha": fallback_sha, "subject": None, "date": None, "author": None}
    return {"sha": parts[0], "subject": parts[1], "date": parts[2], "author": parts[3]}
def parse_status_paths(text):
    paths = []
    for raw_line in text.splitlines():
        if len(raw_line) < 4:
            continue
        path = raw_line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path:
            paths.append(path.strip('"'))
    return paths
def app_slugs_touched_by_paths(paths, discovered_slugs):
    return apps_collector.app_slugs_for_paths(paths, discovered_slugs)

### Identity and Cursor windows
def branch_slug(branch):
    if not branch or branch == "detached":
        return ""
    return branch.replace("/", "-")
def worktree_folder_name(path):
    name = Path(path).name
    return name or str(path)
def is_detached_branch(branch):
    return not branch or branch == "detached"
def workspace_stem_matches_folder(workspace_path, worktree_path):
    folder = normalize_match_token(worktree_folder_name(worktree_path)).replace("_", "-")
    if not folder:
        return False
    stem = normalize_match_token(Path(workspace_path).stem).replace("_", "-")
    folder_tokens = [token for token in folder.split("-") if token]
    stem_tokens = [token for token in stem.split("-") if token]
    if not folder_tokens:
        return False
    span = len(folder_tokens)
    for index in range(len(stem_tokens) - span + 1):
        if stem_tokens[index:index + span] == folder_tokens:
            return True
    return False
def find_codex_workspace_file(worktree_path, branch):
    root = Path(worktree_path)
    if not root.is_dir():
        return None
    slug = branch_slug(branch)
    if slug:
        exact = root / ("codex-" + slug + ".code-workspace")
        if exact.is_file():
            return exact
    matches = sorted(root.glob("codex-*.code-workspace"))
    if not matches:
        return None
    if slug:
        for path in matches:
            if slug in path.stem:
                return path
        return None
    # Detached: only trust a lone workspace whose stem still matches this folder.
    if len(matches) == 1 and workspace_stem_matches_folder(matches[0], worktree_path):
        return matches[0]
    return None
def worktree_display_name(path, branch):
    # Detached checkouts keep the folder name so leftover workspace files cannot
    # rename deutsch/dragon-baby/etc. as an old feature identity.
    if is_detached_branch(branch):
        return worktree_folder_name(path)
    workspace = find_codex_workspace_file(path, branch)
    if workspace:
        return workspace.stem
    return worktree_folder_name(path)
def normalize_file_uri(uri):
    if not uri:
        return None
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return None
    return str(Path(unquote(parsed.path)).expanduser().resolve())
def strip_jsonc(text):
    without_comments = []
    index = 0
    in_string = False
    escaped = False
    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if in_string:
            without_comments.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            without_comments.append(char)
            index += 1
            continue
        if char == "/" and following == "/":
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            continue
        if char == "/" and following == "*":
            index += 2
            while index + 1 < len(text) and text[index:index + 2] != "*/":
                if text[index] in "\r\n":
                    without_comments.append(text[index])
                index += 1
            index += 2
            continue
        without_comments.append(char)
        index += 1

    text = "".join(without_comments)
    without_trailing_commas = []
    index = 0
    in_string = False
    escaped = False
    while index < len(text):
        char = text[index]
        if in_string:
            without_trailing_commas.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            without_trailing_commas.append(char)
            index += 1
            continue
        if char == ",":
            following_index = index + 1
            while following_index < len(text) and text[following_index].isspace():
                following_index += 1
            if following_index < len(text) and text[following_index] in "}]":
                index += 1
                continue
        without_trailing_commas.append(char)
        index += 1
    return "".join(without_trailing_commas)
def load_jsonc(text):
    return json.loads(strip_jsonc(text))
def workspace_paths_from_config(config_path):
    path = Path(config_path)
    paths = {str(path.parent.resolve())}
    if not path.is_file():
        return paths
    try:
        data = load_jsonc(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return paths
    for entry in data.get("folders") or []:
        folder = entry.get("path") or entry.get("uri")
        if not folder:
            continue
        if str(folder).startswith("file:"):
            resolved = normalize_file_uri(folder)
        else:
            resolved = str((path.parent / folder).resolve())
        if resolved:
            paths.add(resolved)
    return paths
def cursor_paths_from_opened_windows(opened_windows):
    paths = set()
    for window in opened_windows:
        folder_uri = window.get("folder")
        if folder_uri:
            resolved = normalize_file_uri(folder_uri)
            if resolved:
                paths.add(resolved)
        workspace = window.get("workspaceIdentifier") or {}
        config_uri = workspace.get("configURIPath")
        if config_uri:
            resolved = normalize_file_uri(config_uri)
            if resolved:
                paths.update(workspace_paths_from_config(resolved))
    return paths
def cursor_paths_from_backup_workspaces(backup):
    paths = set()
    for folder in backup.get("folders") or []:
        resolved = normalize_file_uri(folder.get("folderUri"))
        if resolved:
            paths.add(resolved)
    for workspace in backup.get("workspaces") or []:
        resolved = normalize_file_uri(workspace.get("configURIPath"))
        if resolved:
            paths.update(workspace_paths_from_config(resolved))
    return paths
def collect_cursor_open_paths():
    if not CURSOR_STORAGE.is_file():
        return set()
    try:
        data = json.loads(CURSOR_STORAGE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    opened_windows = (data.get("windowsState") or {}).get("openedWindows") or []
    if opened_windows:
        return cursor_paths_from_opened_windows(opened_windows)
    return cursor_paths_from_backup_workspaces(data.get("backupWorkspaces") or {})
def path_is_cursor_open(worktree_path, open_paths):
    return str(Path(worktree_path).expanduser().resolve()) in open_paths
def parse_title_bar_settings(settings_path):
    try:
        text = Path(settings_path).read_text(encoding="utf-8")
    except OSError:
        return None
    background_match = TITLEBAR_BACKGROUND_RE.search(text)
    if not background_match:
        return None
    foreground_match = TITLEBAR_FOREGROUND_RE.search(text)
    foreground = foreground_match.group(1) if foreground_match else DEFAULT_TITLE_BAR_FOREGROUND
    return {"background": background_match.group(1), "foreground": foreground}
def parse_title_bar_workspace(workspace_path):
    try:
        data = load_jsonc(Path(workspace_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    custom = ((data.get("settings") or {}).get("workbench.colorCustomizations") or {})
    background = custom.get("titleBar.activeBackground")
    if not background:
        return None
    foreground = custom.get("titleBar.activeForeground") or DEFAULT_TITLE_BAR_FOREGROUND
    return {"background": background, "foreground": foreground}
def load_title_bar_fallback(branch, repo_root):
    script = Path(repo_root) / "skills/repo-ops/create-worktree/scripts/worktree_identity.py"
    if not script.is_file():
        return {"background": "#245f99", "foreground": DEFAULT_TITLE_BAR_FOREGROUND}
    spec = importlib.util.spec_from_file_location("worktree_identity", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    colors = module.title_bar_color(branch or "detached")
    return {
        "background": colors.get("titleBar.activeBackground") or "#245f99",
        "foreground": colors.get("titleBar.activeForeground") or DEFAULT_TITLE_BAR_FOREGROUND,
    }
def load_worktree_color_rules(repo_root):
    if yaml is None:
        return {"foreground": DEFAULT_TITLE_BAR_FOREGROUND, "fallback_background": "#245f99", "rules": []}
    path = Path(repo_root) / WORKTREE_COLORS_REL
    if not path.is_file():
        return {"foreground": DEFAULT_TITLE_BAR_FOREGROUND, "fallback_background": "#245f99", "rules": []}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {"foreground": DEFAULT_TITLE_BAR_FOREGROUND, "fallback_background": "#245f99", "rules": []}
    return {
        "foreground": data.get("foreground") or DEFAULT_TITLE_BAR_FOREGROUND,
        "fallback_background": data.get("fallback_background") or "#245f99",
        "rules": data.get("rules") or [],
    }
def normalize_match_token(value):
    return str(value or "").strip().lower()
def worktree_name_matches_rule(display_name, branch, rule):
    name = normalize_match_token(display_name)
    branch_name = normalize_match_token(branch)
    exact = rule.get("name_exact")
    if exact and name != normalize_match_token(exact):
        return False
    branch_exact = rule.get("branch")
    if branch_exact and branch_name != normalize_match_token(branch_exact):
        return False
    contains = rule.get("name_contains")
    if contains and normalize_match_token(contains) not in name:
        return False
    for token in rule.get("name_contains_all") or []:
        if normalize_match_token(token) not in name:
            return False
    return True
def title_bar_from_color_rules(display_name, branch, color_rules):
    foreground = color_rules.get("foreground") or DEFAULT_TITLE_BAR_FOREGROUND
    for rule in color_rules.get("rules") or []:
        if not isinstance(rule, dict):
            continue
        if not worktree_name_matches_rule(display_name, branch, rule):
            continue
        background = rule.get("background")
        if background:
            return {"background": background, "foreground": rule.get("foreground") or foreground}
    return None
def color_for_branch_name(branch, color_rules):
    """Resolve YAML title-bar colors for a branch name (no worktree required)."""
    name = str(branch or "").strip()
    if not name:
        return None
    bare = name[len("origin/"):] if name.startswith("origin/") else name
    for display in (bare, bare.replace("/", "-")):
        matched = title_bar_from_color_rules(display, bare, color_rules)
        if matched:
            return matched
    if normalize_match_token(bare) == "main":
        foreground = color_rules.get("foreground") or DEFAULT_TITLE_BAR_FOREGROUND
        for rule in color_rules.get("rules") or []:
            if not isinstance(rule, dict):
                continue
            if normalize_match_token(rule.get("branch")) != "main":
                continue
            background = rule.get("background")
            if background:
                return {"background": background, "foreground": rule.get("foreground") or foreground}
    return None
def title_bar_for_branch(branch_name, worktrees, color_rules):
    """Prefer checked-out worktree title_bar; else match branch name against YAML rules."""
    name = str(branch_name or "").strip()
    if name.startswith("origin/"):
        name = name[len("origin/"):]
    for worktree in worktrees or []:
        if worktree.get("branch") == name and worktree.get("title_bar"):
            return worktree.get("title_bar")
    return color_for_branch_name(name, color_rules)
def title_bar_for_worktree(worktree_path, branch, repo_root, display_name=None):
    name = display_name or worktree_display_name(worktree_path, branch)
    registry_colors = title_bar_from_color_rules(name, branch, load_worktree_color_rules(repo_root))
    if registry_colors:
        return registry_colors
    workspace = find_codex_workspace_file(worktree_path, branch)
    if workspace:
        colors = parse_title_bar_workspace(workspace)
        if colors:
            return colors
    settings_path = Path(worktree_path) / ".vscode" / "settings.json"
    if settings_path.is_file():
        colors = parse_title_bar_settings(settings_path)
        if colors:
            return colors
    return load_title_bar_fallback(branch, repo_root)

### Gathering
def run_git(repo_root, args, timeout=15):
    return subprocess.run(
        ["git", "-C", str(repo_root)] + args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
def run_git_path(path, args, timeout=15):
    return run_git(path, args, timeout=timeout)
def safe_stdout(command):
    if command.returncode != 0:
        return None
    return command.stdout
def collect_worktrees(repo_root):
    command = run_git(repo_root, ["worktree", "list", "--porcelain"])
    if command.returncode != 0:
        raise RuntimeError(command.stderr.strip() or "git worktree list failed")
    entries = parse_worktree_porcelain(command.stdout, current_path=str(repo_root))
    discovered_slugs = apps_collector.discover_app_slugs(Path(repo_root) / "apps")
    cursor_open_paths = collect_cursor_open_paths()
    for entry in entries:
        fill_worktree_details(entry, discovered_slugs, repo_root=repo_root, cursor_open_paths=cursor_open_paths)
    return entries
def fill_worktree_details(entry, discovered_slugs=None, repo_root=None, cursor_open_paths=None):
    path = entry.get("path")
    branch = entry.get("branch")
    entry["name"] = worktree_display_name(path, branch)
    entry["cursor_open"] = False
    entry["title_bar"] = {"background": "#245f99", "foreground": DEFAULT_TITLE_BAR_FOREGROUND}
    entry["last_commit"] = {"sha": entry.get("head"), "subject": None, "date": None, "author": None}
    entry["dirty"] = 0
    entry["untracked"] = 0
    entry["ahead_main"] = 0
    entry["behind_main"] = 0
    entry["upstream"] = None
    entry["unpushed"] = None
    entry["apps_touched"] = []
    if repo_root:
        entry["title_bar"] = title_bar_for_worktree(path, branch, repo_root, display_name=entry["name"])
    if entry.get("missing"):
        return entry
    status = run_git_path(path, ["status", "--porcelain"])
    if status.returncode == 0:
        entry["dirty"], entry["untracked"] = parse_status_counts(status.stdout)
    counts = run_git_path(path, ["rev-list", "--left-right", "--count", "origin/main...HEAD"])
    if counts.returncode == 0:
        entry["behind_main"], entry["ahead_main"] = parse_left_right_counts(counts.stdout)
    upstream = run_git_path(path, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"])
    if upstream.returncode == 0 and upstream.stdout.strip():
        entry["upstream"] = upstream.stdout.strip()
        unpushed = run_git_path(path, ["rev-list", "--count", "@{upstream}..HEAD"])
        if unpushed.returncode == 0 and unpushed.stdout.strip().isdigit():
            entry["unpushed"] = int(unpushed.stdout.strip())
    commit = run_git_path(path, ["log", "-1", "--format=%h%x1f%s%x1f%cI%x1f%an"])
    if commit.returncode == 0:
        entry["last_commit"] = parse_last_commit(commit.stdout, fallback_sha=entry.get("head"))
    entry["apps_touched"] = collect_apps_touched(path, entry.get("branch"), discovered_slugs or [])
    if cursor_open_paths is not None:
        entry["cursor_open"] = path_is_cursor_open(path, cursor_open_paths)
    return entry
def collect_apps_touched(path, branch, discovered_slugs):
    if branch == "main":
        return []
    paths = []
    diff = run_git_path(path, ["diff", "--name-only", "origin/main...HEAD", "--", "apps/"])
    if diff.returncode == 0:
        paths.extend(line.strip() for line in diff.stdout.splitlines() if line.strip())
    status = run_git_path(path, ["status", "--porcelain", "--", "apps/"])
    if status.returncode == 0:
        paths.extend(parse_status_paths(status.stdout))
    return app_slugs_touched_by_paths(paths, discovered_slugs)
