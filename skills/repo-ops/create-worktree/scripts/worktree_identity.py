#!/usr/bin/env python3
"""Deterministic identity, ancestry, path, and color helpers for create-worktree."""
import colorsys
import hashlib
import json
import os
import re
import sys
import uuid
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

MAIN_GREEN = (0x06, 0x81, 0x02)
WORKTREE_COLORS_REL = Path("apps/holodeck/worktree-colors.yaml")
TITLEBAR_KEYS = (
    "titleBar.activeBackground",
    "titleBar.activeForeground",
    "titleBar.inactiveBackground",
    "titleBar.inactiveForeground",
)
TITLEBAR_COLOR_LINE = re.compile(r'^\s*"titleBar\.[^"]+"\s*:')
WINDOW_TITLEBAR_STYLE_LINE = re.compile(r'^\s*"window\.titleBarStyle"\s*:')
COLOR_CUSTOMIZATIONS_OPEN = re.compile(r'"workbench\.colorCustomizations"\s*:\s*\{')
BRANCH_IDENTITY_TOKEN = re.compile(r"^[a-z0-9][a-z0-9._/-]*$")
FULL_SHA_TOKEN = re.compile(r"^[0-9a-f]{40}$")


def slug(branch):
    """Branch name with slashes replaced by dashes (Worktree Manager convention)."""
    return branch.replace("/", "-")


def worktree_path(parent_repo, branch):
    """Sibling worktree folder next to the main checkout."""
    parent_dir = os.path.dirname(os.path.abspath(parent_repo.rstrip(os.sep)))
    return os.path.join(parent_dir, slug(branch))


def clean_parent_name(parent):
    """Canonical branch name stored in a branch-start Parent trailer."""
    value = str(parent or "").strip()
    for prefix in ("refs/remotes/origin/", "refs/heads/", "origin/"):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    return value


def canonical_uuid(value, label):
    text = str(value or "").strip()
    try:
        parsed = uuid.UUID(text)
    except (ValueError, AttributeError):
        raise ValueError(f"{label} must be a canonical lowercase UUID")
    if str(parsed) != text:
        raise ValueError(f"{label} must be a canonical lowercase UUID")
    return text


def branch_lineage_start_message(
    branch,
    parent,
    purpose,
    fork_commit,
    fork_subject,
    created_by,
    lineage_id,
    record_id,
    related_work=None,
):
    """Return the canonical v2 branch-start lineage commit message."""
    branch_name = str(branch or "").strip()
    parent_name = clean_parent_name(parent)
    purpose_text = str(purpose or "").strip()
    fork_sha = str(fork_commit or "").strip()
    fork_subject_text = str(fork_subject or "").strip()
    created_by_text = str(created_by or "").strip()
    related_work_text = str(related_work or "").strip()
    fields = {
        "branch": branch_name,
        "parent": parent_name,
        "purpose": purpose_text,
        "fork subject": fork_subject_text,
        "created by": created_by_text,
    }
    for label, value in fields.items():
        if not value:
            raise ValueError(f"{label} must not be empty")
        if "\n" in value or "\r" in value:
            raise ValueError(f"{label} must be one line")
    if not BRANCH_IDENTITY_TOKEN.fullmatch(branch_name):
        raise ValueError("branch must be an exact conventional branch name")
    if not BRANCH_IDENTITY_TOKEN.fullmatch(parent_name):
        raise ValueError("parent must be an exact conventional branch name")
    if branch_name == parent_name:
        raise ValueError("branch and parent must differ")
    if not FULL_SHA_TOKEN.fullmatch(fork_sha):
        raise ValueError("fork commit must be a full lowercase commit SHA")
    if related_work_text and ("\n" in related_work_text or "\r" in related_work_text):
        raise ValueError("related work must be one line")
    lineage_uuid = canonical_uuid(lineage_id, "lineage id")
    record_uuid = canonical_uuid(record_id, "record id")
    if lineage_uuid == record_uuid:
        raise ValueError("lineage id and record id must differ")
    lines = [
        f"chore(repo): record branch lineage at branch start for {branch_name}",
        "",
        "Record-Type: branch-lineage",
        "Lineage-Type: branch-start",
        f"Lineage-ID: {lineage_uuid}",
        f"Record-ID: {record_uuid}",
        "Relationship: created-from",
        "Update-Reason: initial",
        f"Created-By: {created_by_text}",
        f"Branch: {branch_name}",
        f"Parent-Branch: {parent_name}",
        f"Fork-Commit: {fork_sha}",
        f"Fork-Subject: {fork_subject_text}",
        f"Branch-Purpose: {purpose_text}",
    ]
    if related_work_text:
        lines.append(f"Related-Work: {related_work_text}")
    lines.append("Lineage-Version: 2")
    return "\n".join(lines)


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


def find_holodeck_colors_repo_root(start_path):
    current = Path(start_path).resolve()
    if current.is_file():
        current = current.parent
    for _ in range(12):
        if (current / WORKTREE_COLORS_REL).is_file():
            return current
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def load_worktree_color_rules(repo_root):
    if yaml is None or not repo_root:
        return None
    path = Path(repo_root) / WORKTREE_COLORS_REL
    if not path.is_file():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None


def title_bar_colors_from_registry(branch, repo_root=None, display_name=None):
    if not repo_root:
        return None
    rules_doc = load_worktree_color_rules(repo_root)
    if not rules_doc:
        return None
    name = display_name or slug(branch)
    foreground = rules_doc.get("foreground") or "#ffffff"
    for rule in rules_doc.get("rules") or []:
        if not isinstance(rule, dict):
            continue
        if not worktree_name_matches_rule(name, branch, rule):
            continue
        background = rule.get("background")
        if not background:
            continue
        return {
            "titleBar.activeBackground": background,
            "titleBar.activeForeground": rule.get("foreground") or foreground,
            "titleBar.inactiveBackground": background,
            "titleBar.inactiveForeground": "#eeeeeecc",
        }
    return None


def resolve_title_bar_colors(branch, repo_root=None, display_name=None):
    registry = title_bar_colors_from_registry(branch, repo_root=repo_root, display_name=display_name)
    if registry:
        return registry
    return title_bar_color(branch)


def _is_too_green(red, green, blue):
    """True when a color is in the main-green band or reads as green."""
    hue, lightness, saturation = colorsys.rgb_to_hls(red / 255, green / 255, blue / 255)
    hue_deg = hue * 360
    if 60 <= hue_deg <= 160 and saturation > 0.3:
        return True
    distance = abs(red - MAIN_GREEN[0]) + abs(green - MAIN_GREEN[1]) + abs(blue - MAIN_GREEN[2])
    return distance < 80


def title_bar_color(branch):
    """Deterministic title-bar colors for branch; never matches main green #068102."""
    digest = hashlib.sha256(branch.encode("utf-8")).digest()
    for offset in range(256):
        hue_idx = (digest[0] + offset) % 240
        hue = hue_idx / 240.0
        hue_deg = hue * 360
        if 60 <= hue_deg <= 160:
            continue
        saturation = 0.55 + (digest[1] % 30) / 100.0
        lightness = 0.35 + (digest[2] % 20) / 100.0
        red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
        red_i, green_i, blue_i = int(red * 255), int(green * 255), int(blue * 255)
        if _is_too_green(red_i, green_i, blue_i):
            continue
        background = f"#{red_i:02x}{green_i:02x}{blue_i:02x}"
        return {
            "titleBar.activeBackground": background,
            "titleBar.activeForeground": "#ffffff",
            "titleBar.inactiveBackground": background,
            "titleBar.inactiveForeground": "#eeeeeecc",
        }
    return {
        "titleBar.activeBackground": "#4a0082",
        "titleBar.activeForeground": "#ffffff",
        "titleBar.inactiveBackground": "#4a0082",
        "titleBar.inactiveForeground": "#eeeeeecc",
    }


def _split_lines(text):
    return text.splitlines()


def _normalize_titlebar_color_line(key, value):
    if isinstance(value, str):
        rendered = json.dumps(value)
    else:
        rendered = json.dumps(value)
    return f'        "{key}": {rendered},'


def _remove_titlebar_overrides(lines):
    return [
        line
        for line in lines
        if not TITLEBAR_COLOR_LINE.match(line)
        and not WINDOW_TITLEBAR_STYLE_LINE.match(line)
    ]


def apply_title_bar_color(settings_path, branch, repo_root=None):
    """Rewrite titleBar.* hexes in settings.json; ensure window.titleBarStyle is custom."""
    path = Path(settings_path)
    if not path.is_file():
        raise FileNotFoundError(f"settings not found: {settings_path}")
    if repo_root is None:
        repo_root = find_holodeck_colors_repo_root(settings_path)
    colors = resolve_title_bar_colors(branch, repo_root=repo_root)
    text = path.read_text(encoding="utf-8")
    lines = _split_lines(text)
    cleaned = _remove_titlebar_overrides(lines)
    merged = []
    inserted = False
    for line in cleaned:
        merged.append(line)
        if not inserted and COLOR_CUSTOMIZATIONS_OPEN.search(line):
            for key in TITLEBAR_KEYS:
                merged.append(_normalize_titlebar_color_line(key, colors[key]))
            inserted = True
    if not inserted:
        raise ValueError("workbench.colorCustomizations block not found in settings.json")
    style_line = '    "window.titleBarStyle": "custom",'
    insert_at = None
    for idx, line in enumerate(merged):
        if COLOR_CUSTOMIZATIONS_OPEN.search(line):
            insert_at = idx
            break
    if insert_at is not None:
        merged.insert(insert_at, style_line)
    else:
        merged.append(style_line)
    path.write_text("\n".join(merged) + "\n", encoding="utf-8")
    return colors["titleBar.activeBackground"]


def print_plan(branch, parent_repo=None):
    """Print slug, sibling path, and title-bar background hex."""
    repo = parent_repo or os.getcwd()
    colors = resolve_title_bar_colors(branch, repo_root=repo)
    print(f"branch: {branch}")
    print(f"slug: {slug(branch)}")
    print(f"path: {worktree_path(repo, branch)}")
    print(f"color: {colors['titleBar.activeBackground']}")


def main():
    if len(sys.argv) < 2:
        print(
            "usage: worktree_identity.py "
            "<slug|path|lineage-message|color|apply-color|plan> ...",
            file=sys.stderr,
        )
        sys.exit(1)
    command = sys.argv[1]
    if command == "slug":
        if len(sys.argv) != 3:
            print("usage: worktree_identity.py slug <branch>", file=sys.stderr)
            sys.exit(1)
        print(slug(sys.argv[2]))
        return
    if command == "path":
        if len(sys.argv) != 4:
            print("usage: worktree_identity.py path <parent_repo> <branch>", file=sys.stderr)
            sys.exit(1)
        print(worktree_path(sys.argv[2], sys.argv[3]))
        return
    if command == "lineage-message":
        if len(sys.argv) < 3:
            print(
                "usage: worktree_identity.py lineage-message <branch> "
                "--parent <branch> --purpose <text> --fork-commit <sha> "
                "--fork-subject <text> --created-by <label> "
                "--lineage-id <uuid> --record-id <uuid> [--related-work <text>]",
                file=sys.stderr,
            )
            sys.exit(1)
        branch = sys.argv[2]
        values = {}
        args = sys.argv[3:]
        idx = 0
        while idx < len(args):
            option = args[idx]
            if option not in (
                "--parent",
                "--purpose",
                "--fork-commit",
                "--fork-subject",
                "--created-by",
                "--lineage-id",
                "--record-id",
                "--related-work",
            ) or idx + 1 >= len(args):
                print(f"error: invalid lineage-message argument: {option}", file=sys.stderr)
                sys.exit(1)
            values[option[2:].replace("-", "_")] = args[idx + 1]
            idx += 2
        required = {
            "parent",
            "purpose",
            "fork_commit",
            "fork_subject",
            "created_by",
            "lineage_id",
            "record_id",
        }
        missing = sorted(required - set(values))
        if missing:
            print("error: missing lineage-message options: " + ", ".join(missing), file=sys.stderr)
            sys.exit(1)
        try:
            print(branch_lineage_start_message(branch, **values))
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            sys.exit(1)
        return
    if command == "color":
        if len(sys.argv) != 3:
            print("usage: worktree_identity.py color <branch>", file=sys.stderr)
            sys.exit(1)
        repo_root = find_holodeck_colors_repo_root(os.getcwd())
        print(resolve_title_bar_colors(sys.argv[2], repo_root=repo_root)["titleBar.activeBackground"])
        return
    if command == "apply-color":
        if len(sys.argv) < 4:
            print(
                "usage: worktree_identity.py apply-color <settings.json> <branch> [--parent <repo>]",
                file=sys.stderr,
            )
            sys.exit(1)
        settings_path = sys.argv[2]
        branch = sys.argv[3]
        repo_root = None
        args = sys.argv[4:]
        idx = 0
        while idx < len(args):
            if args[idx] == "--parent":
                if idx + 1 >= len(args):
                    print("error: --parent requires a path", file=sys.stderr)
                    sys.exit(1)
                repo_root = args[idx + 1]
                idx += 2
                continue
            idx += 1
        if repo_root is None:
            repo_root = find_holodeck_colors_repo_root(settings_path)
        color = apply_title_bar_color(settings_path, branch, repo_root=repo_root)
        print(color)
        return
    if command == "plan":
        if len(sys.argv) < 3:
            print("usage: worktree_identity.py plan <branch> [--parent <repo>]", file=sys.stderr)
            sys.exit(1)
        branch = None
        parent_repo = None
        args = sys.argv[2:]
        idx = 0
        while idx < len(args):
            if args[idx] == "--parent":
                if idx + 1 >= len(args):
                    print("error: --parent requires a path", file=sys.stderr)
                    sys.exit(1)
                parent_repo = args[idx + 1]
                idx += 2
                continue
            if branch is None:
                branch = args[idx]
            idx += 1
        if not branch:
            print("usage: worktree_identity.py plan <branch> [--parent <repo>]", file=sys.stderr)
            sys.exit(1)
        print_plan(branch, parent_repo)
        return
    print(f"error: unknown command: {command}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
