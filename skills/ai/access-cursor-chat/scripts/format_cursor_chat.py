#!/usr/bin/env python3
"""Format Cursor chat transcripts as repo-standard markdown."""

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

TEXT_KEYS = ("text", "content", "message")
MODEL_KEYS = ("model", "modelName", "model_name", "aiModel", "ai_model")
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)


### Helpers: paths
def _project_token(worktree):
    """Return Cursor's project-folder token for a worktree path."""
    return str(Path(worktree).expanduser().resolve()).strip("/").replace("/", "-")
def _default_transcripts_dir(worktree):
    """Return the default Cursor agent-transcripts folder for a worktree."""
    return Path.home() / ".cursor" / "projects" / _project_token(worktree) / "agent-transcripts"
def _list_jsonl_files(folder):
    """Return transcript JSONL files under a folder, newest first."""
    if not folder.exists():
        return []
    return sorted(folder.rglob("*.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)
def _default_state_db():
    """Return Cursor's global state.vscdb path when it exists."""
    if sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
    else:
        path = Path.home() / ".config" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
    return path if path.exists() else None
def _composer_id_from_path(path):
    """Extract a composer UUID from a transcript path when possible."""
    for part in reversed(Path(path).parts):
        match = UUID_RE.fullmatch(part)
        if match:
            return match.group(0).lower()
    match = UUID_RE.search(str(path))
    return match.group(0).lower() if match else ""


### Helpers: text
def _slugify(value):
    """Create a compact file slug."""
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "cursor_chat"
def _clean_text(value):
    """Normalize Cursor transcript text."""
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"\n?\[REDACTED\]\n?", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()
def _extract_user_query(value, keep_context=False):
    """Extract the visible user prompt from Cursor's attached-context wrapper."""
    if keep_context:
        return _clean_text(value)
    match = re.search(r"<user_query>\s*(.*?)\s*</user_query>", value, flags=re.S)
    if match:
        return _clean_text(match.group(1))
    return _clean_text(re.sub(r"<timestamp>.*?</timestamp>\s*", "", value, flags=re.S))
def _first_text_from_content(content):
    """Extract text blocks from Cursor JSON content arrays."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            elif isinstance(item, str):
                parts.append(item)
        return "\n\n".join(part for part in parts if part)
    if isinstance(content, dict):
        for key in TEXT_KEYS:
            if key in content:
                return _first_text_from_content(content[key])
    return ""
def _bubble_model_name(bubble, session_model=""):
    """Return a bubble's model name when Cursor stored one."""
    model_info = bubble.get("modelInfo") or {}
    if model_info.get("modelName"):
        return str(model_info["modelName"])
    return _find_model(bubble) or session_model or "unknown"
def _find_model(value):
    """Find a model field anywhere in a Cursor JSON object."""
    if isinstance(value, dict):
        for key in MODEL_KEYS:
            if value.get(key):
                return str(value[key])
        for nested in value.values():
            found = _find_model(nested)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _find_model(item)
            if found:
                return found
    return ""


### Metadata: SQLite
def _load_composer_metadata(composer_id, state_db_path=""):
    """Load session and per-turn model metadata from Cursor state.vscdb."""
    if not composer_id:
        return {}
    state_db_path = Path(state_db_path).expanduser() if state_db_path else _default_state_db()
    if not state_db_path or not Path(state_db_path).exists():
        return {}
    connection = sqlite3.connect(f"file:{state_db_path}?mode=ro", uri=True)
    try:
        cursor = connection.execute(
            "SELECT value FROM cursorDiskKV WHERE key = ?",
            (f"composerData:{composer_id}",),
        )
        row = cursor.fetchone()
        if not row:
            return {}
        composer = json.loads(row[0])
        model_config = composer.get("modelConfig") or {}
        session_model = str(model_config.get("modelName") or "")
        bubble_rows = connection.execute(
            "SELECT key, value FROM cursorDiskKV WHERE key LIKE ?",
            (f"bubbleId:{composer_id}:%",),
        )
        bubble_map = {}
        for key, value in bubble_rows:
            bubble_id = key.rsplit(":", 1)[-1]
            bubble_map[bubble_id] = json.loads(value)
        assistant_models = _assistant_models_from_headers(
            composer.get("fullConversationHeadersOnly") or [],
            bubble_map,
            session_model,
        )
        return {
            "title": composer.get("name") or "",
            "session_model": session_model or "unknown",
            "assistant_models": assistant_models,
        }
    finally:
        connection.close()
def _assistant_models_from_headers(headers, bubble_map, session_model):
    """Return one model per assistant reply grouped between user turns."""
    grouped = []
    current = []
    for header in headers:
        bubble_type = header.get("type")
        bubble_id = header.get("bubbleId")
        if bubble_type == 1:
            if current:
                grouped.append(_pick_model(current))
                current = []
            continue
        if bubble_type != 2:
            continue
        bubble = bubble_map.get(bubble_id, {})
        current.append(_bubble_model_name(bubble, session_model))
    if current:
        grouped.append(_pick_model(current))
    return grouped
def _pick_model(models):
    """Prefer the first explicit bubble model over unknown/session fallback."""
    for model in models:
        if model and model != "unknown":
            return model
    return models[0] if models else "unknown"
def _apply_metadata_to_turns(turns, metadata):
    """Attach SQLite model metadata to consolidated assistant turns."""
    if not metadata:
        return turns
    assistant_models = list(metadata.get("assistant_models") or [])
    session_model = metadata.get("session_model") or "unknown"
    assistant_index = 0
    for turn in turns:
        if turn["role"] != "assistant":
            continue
        if turn.get("model") and turn.get("model") != "unknown":
            assistant_index += 1
            continue
        if assistant_index < len(assistant_models):
            turn["model"] = assistant_models[assistant_index]
        elif session_model != "unknown":
            turn["model"] = session_model
        assistant_index += 1
    return turns


### Parsing: JSONL
def _parse_jsonl(path, keep_user_context=False):
    """Parse Cursor agent-transcripts JSONL."""
    turns = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            role = data.get("role")
            if role not in ("user", "assistant"):
                continue
            message = data.get("message", {})
            text = _first_text_from_content(message.get("content", message))
            if role == "user":
                text = _extract_user_query(text, keep_user_context)
            else:
                text = _clean_text(text)
            if not text:
                continue
            model = _find_model(data) if role == "assistant" else ""
            turns.append({"role": role, "text": text, "model": model or "unknown"})
    return _consolidate_turns(turns)
def _consolidate_turns(turns):
    """Merge adjacent same-speaker entries into readable chat turns."""
    merged = []
    for turn in turns:
        if merged and merged[-1]["role"] == turn["role"]:
            merged[-1]["text"] = _clean_text(merged[-1]["text"] + "\n\n" + turn["text"])
            if merged[-1].get("model") == "unknown" and turn.get("model") != "unknown":
                merged[-1]["model"] = turn["model"]
        else:
            merged.append(dict(turn))
    return merged


### Parsing: exported markdown
def _parse_exported_markdown(path):
    """Parse Cursor's built-in markdown export format."""
    raw = Path(path).read_text(encoding="utf-8")
    lines = raw.splitlines()
    title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("# ") else ""
    exported = ""
    for line in lines[:8]:
        if line.startswith("_Exported on "):
            exported = line.strip()
            break
    body = "\n".join(lines)
    pieces = re.split(r"(?m)^---\n\n\*\*(User|Cursor)\*\*\n\n", body)
    turns = []
    for index in range(1, len(pieces), 2):
        speaker = pieces[index]
        text = _clean_text(pieces[index + 1])
        if not text:
            continue
        role = "user" if speaker == "User" else "assistant"
        turns.append({"role": role, "text": text, "model": "unknown"})
    return title, exported, turns
def _parse_input(path, keep_user_context=False, state_db_path=""):
    """Parse a supported Cursor transcript input."""
    suffix = Path(path).suffix.lower()
    if suffix == ".jsonl":
        turns = _parse_jsonl(path, keep_user_context)
        composer_id = _composer_id_from_path(path)
        metadata = _load_composer_metadata(composer_id, state_db_path)
        turns = _apply_metadata_to_turns(turns, metadata)
        return metadata.get("title") or "", "", turns
    if suffix in (".md", ".markdown"):
        title, exported, turns = _parse_exported_markdown(path)
        metadata = _lookup_metadata_by_title(title, state_db_path)
        turns = _apply_metadata_to_turns(turns, metadata)
        return title, exported, turns
    raise ValueError(f"Unsupported input type: {path}")
def _lookup_metadata_by_title(title, state_db_path=""):
    """Find composer metadata by exact session title when no UUID is available."""
    if not title:
        return {}
    state_db_path = Path(state_db_path).expanduser() if state_db_path else _default_state_db()
    if not state_db_path or not Path(state_db_path).exists():
        return {}
    connection = sqlite3.connect(f"file:{state_db_path}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT key, value FROM cursorDiskKV WHERE key LIKE 'composerData:%' ORDER BY rowid DESC"
        )
        for key, value in rows:
            if not value:
                continue
            composer = json.loads(value)
            if composer.get("name") == title:
                composer_id = key.split(":", 1)[-1]
                return _load_composer_metadata(composer_id, state_db_path)
    finally:
        connection.close()
    return {}


### Rendering
def _title_from_turns(title, turns):
    """Choose a readable title."""
    if title:
        return title
    for turn in turns:
        if turn["role"] == "user":
            text = re.sub(r"\s+", " ", turn["text"]).strip()
            words = text.split()[:7]
            return " ".join(words).rstrip(".,:;") or "Cursor chat"
    return "Cursor chat"
def _last_updated(path, explicit_value=""):
    """Use explicit timestamp or input mtime as the last-change timestamp."""
    if explicit_value:
        return explicit_value
    modified = datetime.fromtimestamp(Path(path).stat().st_mtime)
    return modified.strftime("%Y-%m-%d_%H%M")
def _exported_line(exported, explicit_value=""):
    """Return an export provenance line."""
    if explicit_value:
        return explicit_value
    return exported
def _render_markdown(path, turns, title="", session="", last_updated="", exported=""):
    """Render repo-preferred Cursor chat markdown."""
    title = _title_from_turns(title, turns)
    last_updated = _last_updated(path, last_updated)
    session = session or title
    output = [
        f"file: {last_updated}_{_slugify(title)}.md",
        f"title: {title}",
        f"last-updated: {last_updated}",
        f"session: `{session}`",
    ]
    exported = _exported_line(exported)
    if exported:
        output.append(exported)
    output.append("")
    for turn in turns:
        if turn["role"] == "user":
            output.append("# User")
            output.append(turn["text"])
        else:
            output.append("# Cursor")
            output.append(f"ai: {turn.get('model') or 'unknown'}")
            output.append(turn["text"])
        output.append("")
    return "\n".join(output).rstrip() + "\n"
def _write_output(markdown, output_path, title, last_updated):
    """Write or print rendered markdown."""
    if not output_path:
        sys.stdout.write(markdown)
        return None
    output_path = Path(output_path)
    if output_path.is_dir() or output_path.suffix.lower() not in (".md", ".markdown"):
        output_path = output_path / f"{last_updated}_{_slugify(title)}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


### Selection
def _resolve_input(args):
    """Resolve explicit, latest, or query-selected transcript input."""
    if args.input:
        return Path(args.input).expanduser()
    transcripts_dir = Path(args.transcripts_dir).expanduser() if args.transcripts_dir else _default_transcripts_dir(args.worktree)
    files = _list_jsonl_files(transcripts_dir)
    if not files:
        raise FileNotFoundError(f"No Cursor transcript JSONL files found under {transcripts_dir}")
    if args.query:
        query = args.query.lower()
        for path in files:
            if query in path.name.lower() or query in path.read_text(encoding="utf-8", errors="ignore").lower():
                return path
        raise FileNotFoundError(f"No transcript under {transcripts_dir} matched query: {args.query}")
    return files[0]


### CLI
def main(argv=None):
    """Run the formatter."""
    parser = argparse.ArgumentParser(description="Format Cursor chat JSONL or markdown export as repo-standard markdown.")
    parser.add_argument("--input", help="Transcript JSONL or Cursor markdown export to format.")
    parser.add_argument("--output", help="Output markdown file or directory. Omit to print to stdout.")
    parser.add_argument("--worktree", default=os.getcwd(), help="Worktree used to find Cursor agent-transcripts when --input is omitted.")
    parser.add_argument("--transcripts-dir", help="Override Cursor agent-transcripts folder.")
    parser.add_argument("--latest", action="store_true", help="Use latest transcript in the worktree. This is the default when --input is omitted.")
    parser.add_argument("--query", help="Pick the newest transcript whose filename or content contains this text.")
    parser.add_argument("--title", help="Override output title.")
    parser.add_argument("--session", help="Override session metadata.")
    parser.add_argument("--last-updated", help="Override last-updated metadata as YYYY-MM-DD_HHMM.")
    parser.add_argument("--exported-line", help="Override or supply the Cursor export provenance line.")
    parser.add_argument("--raw-user-context", action="store_true", help="Keep Cursor's attached user context wrappers instead of extracting <user_query>.")
    parser.add_argument("--state-db", help="Override Cursor globalStorage/state.vscdb path for model metadata lookup.")
    args = parser.parse_args(argv)
    input_path = _resolve_input(args)
    parsed_title, parsed_exported, turns = _parse_input(input_path, args.raw_user_context, args.state_db or "")
    title = args.title or parsed_title
    exported = args.exported_line or parsed_exported
    markdown = _render_markdown(input_path, turns, title=title, session=args.session or title, last_updated=args.last_updated or "", exported=exported)
    output_path = _write_output(markdown, args.output, _title_from_turns(title, turns), _last_updated(input_path, args.last_updated or ""))
    if output_path:
        print(output_path)
if __name__ == "__main__":
    main()
