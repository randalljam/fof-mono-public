"""Render normalized consumer chat threads to house markdown."""

import re
from datetime import datetime, timezone

SOURCE_LABELS = {
    "chatgpt": "ChatGPT",
    "claude": "Claude",
}
ROLE_LABELS = {
    "user": "User",
    "assistant": "Assistant",
}
def slugify(text, max_len=48):
    """Turn title text into a filesystem-safe slug."""
    if not text:
        return "untitled"
    clean = re.sub(r"[^\w\s-]", "", str(text)).strip().lower()
    clean = re.sub(r"[-\s]+", "-", clean).strip("-")
    return (clean or "untitled")[:max_len]
def thread_date(thread):
    """Best date string for filenames and headers."""
    for key in ("date", "exported_at", "started"):
        value = thread.get(key)
        if not value:
            continue
        text = str(value)
        if len(text) >= 10 and text[4] == "-" and text[7] == "-":
            return text[:10]
        if "T" in text:
            return text.split("T", 1)[0]
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
def output_basename(thread):
    """Build YYYY-MM-DD_<source>_<slug> without extension."""
    source = thread.get("source") or "chat"
    title = thread.get("title") or "untitled"
    return f"{thread_date(thread)}_{source}_{slugify(title)}"
def render_messages(messages):
    """Render message list as numbered User/Assistant sections."""
    lines = []
    exchange_num = 0
    pending_user = None
    pending_assistant_parts = []
    def flush_exchange():
        nonlocal exchange_num, pending_user, pending_assistant_parts
        if pending_user is None and not pending_assistant_parts:
            return
        exchange_num += 1
        user_text = (pending_user or "").strip()
        assistant_text = "\n\n".join(part.strip() for part in pending_assistant_parts if part and part.strip()).strip()
        lines.append(f"## {exchange_num}. User")
        lines.append(user_text if user_text else "_(no user message captured)_")
        lines.append("")
        lines.append(f"## {exchange_num}. Assistant")
        lines.append(assistant_text if assistant_text else "_(no assistant message captured)_")
        lines.append("")
        pending_user = None
        pending_assistant_parts = []
    for message in messages or []:
        role = (message.get("role") or "assistant").lower()
        text = message.get("text") or ""
        if role == "user":
            if pending_user is not None or pending_assistant_parts:
                flush_exchange()
            pending_user = text
        else:
            pending_assistant_parts.append(text)
    flush_exchange()
    return "\n".join(lines).strip()
def render_thread_header(thread):
    """Render title block and provenance lines for one thread."""
    title = thread.get("title") or "Untitled chat"
    date_str = thread_date(thread)
    source = thread.get("source") or "unknown"
    lines = [f"# {date_str} — {title}", f"Source: {source}"]
    source_ref = thread.get("source_ref")
    if source_ref:
        lines.append(f"Source URL / id: {source_ref}")
    exported_at = thread.get("exported_at")
    if exported_at:
        lines.append(f"Exported: {exported_at}")
    lines.append("")
    return "\n".join(lines)
def render_single(thread):
    """Render one thread to house markdown."""
    parts = [render_thread_header(thread), render_messages(thread.get("messages") or [])]
    return "\n".join(part for part in parts if part).strip() + "\n"
def render_combined(threads, topic=None):
    """Render multiple threads into one markdown document."""
    topic_title = topic or "combined consumer chats"
    lines = [f"# {topic_title}", ""]
    for thread in threads:
        source = thread.get("source") or "unknown"
        label = SOURCE_LABELS.get(source, source.title())
        title = thread.get("title") or "Untitled chat"
        lines.append(f"## {label} — {title}")
        source_ref = thread.get("source_ref")
        if source_ref:
            lines.append(f"Source URL / id: {source_ref}")
        lines.append("")
        lines.append(render_messages(thread.get("messages") or []))
        lines.append("")
    return "\n".join(lines).strip() + "\n"
def write_outputs(threads, out_dir, combine=False, topic=None):
    """Write per-thread markdown files and optional combined file."""
    from pathlib import Path
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    written = []
    for thread in threads:
        filename = output_basename(thread) + ".md"
        target = out_path / filename
        target.write_text(render_single(thread), encoding="utf-8")
        written.append(str(target))
    if combine and threads:
        combined_name = f"{thread_date(threads[0])}_{slugify(topic or 'combined')}_combined.md"
        combined_path = out_path / combined_name
        combined_path.write_text(render_combined(threads, topic=topic), encoding="utf-8")
        written.append(str(combined_path))
    return written
