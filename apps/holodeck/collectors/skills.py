"""Collect shared and platform skill facts."""

from pathlib import Path

### Parsing
def description_from_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.strip().startswith("description:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'") or None
    return None
def description_from_skill_text(text):
    frontmatter = description_from_frontmatter(text)
    if frontmatter:
        return frontmatter
    for line in text.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if not stripped:
            continue
        if lowered.startswith("description:"):
            return stripped.split(":", 1)[1].strip() or None
        if stripped.startswith("#") or stripped.startswith("|") or stripped.startswith("---"):
            continue
        if lowered.startswith(("file:", "title:", "source-", "history:", "last-updated:", "ai:", "session:")):
            continue
        return stripped
    return None

### Gathering
def collect_shared_skills(repo_root):
    items = []
    root = Path(repo_root) / "skills"
    for readme in sorted(root.glob("*/*/README.md")):
        category = readme.parent.parent.name
        name = readme.parent.name
        items.append({
            "category": category,
            "name": name,
            "description": description_from_skill_text(readme.read_text(encoding="utf-8", errors="replace")),
            "path": str(readme.relative_to(repo_root)),
            "source": "shared",
        })
    return items
def collect_claude_skills(repo_root):
    items = []
    root = Path(repo_root) / ".claude/skills"
    if not root.exists():
        return items
    for skill in sorted(root.glob("*/SKILL.md")):
        items.append({
            "category": "skills",
            "name": skill.parent.name,
            "description": description_from_skill_text(skill.read_text(encoding="utf-8", errors="replace")),
            "path": str(skill.relative_to(repo_root)),
            "source": "claude-skill",
        })
    return items
def collect_claude_commands(repo_root):
    items = []
    root = Path(repo_root) / ".claude/commands"
    if not root.exists():
        return items
    for command in sorted(root.glob("*.md")):
        items.append({
            "category": "commands",
            "name": command.stem,
            "description": description_from_skill_text(command.read_text(encoding="utf-8", errors="replace")),
            "path": str(command.relative_to(repo_root)),
            "source": "claude-command",
        })
    return items
def collect_hermes_skills(repo_root):
    items = []
    root = Path(repo_root) / "agents/hermes/skills"
    if not root.exists():
        return items
    for skill in sorted(root.glob("*/*/SKILL.md")):
        items.append({
            "category": skill.parent.parent.name,
            "name": skill.parent.name,
            "description": description_from_skill_text(skill.read_text(encoding="utf-8", errors="replace")),
            "path": str(skill.relative_to(repo_root)),
            "source": "hermes",
        })
    return items
def collect_skills(repo_root):
    repo_root = Path(repo_root)
    items = []
    items.extend(collect_shared_skills(repo_root))
    items.extend(collect_claude_skills(repo_root))
    items.extend(collect_claude_commands(repo_root))
    items.extend(collect_hermes_skills(repo_root))
    return items
