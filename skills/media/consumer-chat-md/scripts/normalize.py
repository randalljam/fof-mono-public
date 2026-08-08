"""Normalize consumer chat sources into thread dicts."""

import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

def repo_root(start=None):
    """Find monorepo root by walking up for AGENTS.md."""
    path = Path(start or os.getcwd()).resolve()
    for candidate in [path, *path.parents]:
        if (candidate / "AGENTS.md").is_file():
            return candidate
    return Path(start or os.getcwd()).resolve()
def ensure_core_import():
    """Import core.conversion after putting repo root on sys.path."""
    root = repo_root()
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    from core import conversion
    return conversion
def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def make_thread(source, title, messages, source_ref=None, date=None, exported_at=None):
    return {
        "source": source,
        "title": title or "Untitled chat",
        "date": date,
        "source_ref": source_ref,
        "exported_at": exported_at or utc_now_iso(),
        "messages": messages or [],
    }
def parse_numbered_markdown(md_text):
    """Parse ## N. User / ## N. Assistant markdown into messages."""
    lines = md_text.splitlines()
    title = None
    date_str = None
    source_ref = None
    if lines and lines[0].startswith("# "):
        header = lines[0][2:].strip()
        if " — " in header:
            date_str, title = header.split(" — ", 1)
        else:
            title = header
    messages = []
    current_role = None
    current_lines = []
    header_re = re.compile(r"^##\s+(\d+)\.\s+(User|Assistant)\s*$", re.I)
    def flush():
        nonlocal current_role, current_lines
        if current_role is None:
            return
        text = "\n".join(current_lines).strip()
        if text:
            messages.append({"role": current_role, "text": text})
        current_role = None
        current_lines = []
    for line in lines[1:]:
        if line.startswith("Source URL:"):
            source_ref = line.split(":", 1)[1].strip()
            continue
        if line.startswith("Source URL / id:"):
            source_ref = line.split(":", 1)[1].strip()
            continue
        if line.startswith("Source:") or line.startswith("Exported:"):
            continue
        match = header_re.match(line.strip())
        if match:
            flush()
            current_role = "user" if match.group(2).lower() == "user" else "assistant"
            continue
        if current_role is not None:
            current_lines.append(line)
    flush()
    return title, date_str, source_ref, messages
def parse_chatgpt_markdown_file(path):
    """Parse existing ChatGPT/Hermes markdown export."""
    text = Path(path).read_text(encoding="utf-8")
    title, date_str, source_ref, messages = parse_numbered_markdown(text)
    return make_thread(
        "chatgpt",
        title,
        messages,
        source_ref=source_ref,
        date=date_str,
    )
def parse_chatgpt_share_html(path):
    """Parse saved ChatGPT share HTML via core.conversion."""
    conversion = ensure_core_import()
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path = conversion.convert_chatgpt_share_html_to_md(str(path), suffix_new="_chatmd")
        try:
            thread = parse_chatgpt_markdown_file(md_path)
        finally:
            if os.path.exists(md_path):
                os.unlink(md_path)
    thread["source_ref"] = thread.get("source_ref") or f"file://{Path(path).resolve()}"
    return thread
def parse_chatgpt_share_url(url, output_dir=None):
    """Fetch ChatGPT share URL and normalize to thread."""
    conversion = ensure_core_import()
    out_dir = output_dir or tempfile.mkdtemp(prefix="consumer-chat-md-")
    _html_path, md_path = conversion.convert_chatgpt_share_url_to_md(url, output_dir=out_dir)
    try:
        thread = parse_chatgpt_markdown_file(md_path)
    finally:
        for candidate in (_html_path, md_path):
            if candidate and os.path.exists(candidate):
                os.unlink(candidate)
    thread["source_ref"] = url
    return thread
def _claude_text(value):
    """Extract plain text from Claude message content blocks."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if item.get("type") == "text" and item.get("text"):
                    parts.append(str(item.get("text")))
                elif item.get("text"):
                    parts.append(str(item.get("text")))
        return "\n\n".join(part.strip() for part in parts if part and str(part).strip()).strip()
    if isinstance(value, dict):
        if value.get("text"):
            return str(value.get("text")).strip()
        if value.get("content") is not None:
            return _claude_text(value.get("content"))
    return str(value).strip()
def _claude_role(sender):
    sender = (sender or "").lower()
    if sender in ("human", "user"):
        return "user"
    return "assistant"
def _flatten_claude_chat_messages(chat_messages):
    """Flatten Claude chat_messages tree into ordered role/text pairs."""
    if not chat_messages:
        return []
    by_uuid = {}
    for item in chat_messages:
        if not isinstance(item, dict):
            continue
        uuid = item.get("uuid") or item.get("id")
        if uuid:
            by_uuid[uuid] = item
    if not by_uuid:
        messages = []
        for item in chat_messages:
            if not isinstance(item, dict):
                continue
            text = _claude_text(item.get("text") or item.get("content"))
            if text:
                messages.append({"role": _claude_role(item.get("sender")), "text": text})
        return messages
    children_map = {}
    roots = []
    for item in by_uuid.values():
        parent = item.get("parent_uuid")
        if parent and parent in by_uuid:
            children_map.setdefault(parent, []).append(item)
        else:
            roots.append(item)
    ordered = []
    def walk(node):
        text = _claude_text(node.get("text") or node.get("content"))
        if text:
            ordered.append({"role": _claude_role(node.get("sender")), "text": text})
        child_key = node.get("uuid") or node.get("id")
        for child in sorted(children_map.get(child_key, []), key=lambda row: row.get("created_at") or ""):
            walk(child)
    start_nodes = roots or list(by_uuid.values())
    for node in sorted(start_nodes, key=lambda row: row.get("created_at") or ""):
        walk(node)
    return ordered
def _thread_from_claude_conversation(conversation):
    """Build thread dict from one holodeck or raw Claude conversation object."""
    if not isinstance(conversation, dict):
        return None
    messages = conversation.get("messages")
    if messages is None and conversation.get("chat_messages") is not None:
        messages = _flatten_claude_chat_messages(conversation.get("chat_messages"))
    if messages is None:
        messages = []
    title = (
        conversation.get("title")
        or conversation.get("name")
        or conversation.get("summary")
        or "Untitled chat"
    )
    conv_id = conversation.get("id") or conversation.get("uuid")
    source_ref = conversation.get("source_url") or conversation.get("source_ref")
    if not source_ref and conv_id:
        source_ref = str(conv_id)
    date = conversation.get("date")
    if not date:
        for key in ("created_at", "updated_at"):
            value = conversation.get(key)
            if value and isinstance(value, str) and len(value) >= 10:
                date = value[:10]
                break
    return make_thread(
        "claude",
        title,
        messages,
        source_ref=source_ref,
        date=date,
        exported_at=conversation.get("exported_at"),
    )
def _matches_select(conversation, select_terms):
    if not select_terms:
        return True
    haystack = " ".join(
        str(conversation.get(key) or "")
        for key in ("title", "name", "summary", "id", "uuid")
    ).lower()
    return any(term.lower() in haystack for term in select_terms)
def parse_claude_json_file(path, select=None, ids=None):
    """Parse holodeck Claude export JSON into one or more threads."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    select_terms = [part.strip() for part in (select or "").split(",") if part.strip()]
    id_set = set(ids or [])
    threads = []
    exported_at = payload.get("exported_at") if isinstance(payload, dict) else None
    conversations = []
    if isinstance(payload, dict):
        if payload.get("conversations"):
            conversations = payload.get("conversations") or []
        elif payload.get("chat_messages") or payload.get("messages"):
            conversations = [payload]
        elif payload.get("id") or payload.get("uuid") or payload.get("name") or payload.get("title"):
            conversations = [payload]
    elif isinstance(payload, list):
        conversations = payload
    for conversation in conversations:
        if id_set:
            conv_id = str(conversation.get("id") or conversation.get("uuid") or "")
            if conv_id not in id_set:
                continue
        if select_terms and not _matches_select(conversation, select_terms):
            continue
        thread = _thread_from_claude_conversation(conversation)
        if not thread:
            continue
        if exported_at and not thread.get("exported_at"):
            thread["exported_at"] = exported_at
        if thread.get("messages"):
            threads.append(thread)
    if not threads:
        raise ValueError(f"No Claude conversations matched in {path}")
    return threads
def parse_pasted_markdown_file(path, source="chatgpt"):
    """Parse pasted markdown in house or Hermes export shape."""
    title, date_str, source_ref, messages = parse_numbered_markdown(Path(path).read_text(encoding="utf-8"))
    if not messages:
        raise ValueError(f"No numbered User/Assistant sections found in {path}")
    return make_thread(source, title, messages, source_ref=source_ref, date=date_str)
