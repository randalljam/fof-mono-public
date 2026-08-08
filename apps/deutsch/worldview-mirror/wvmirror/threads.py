"""Conversation threads as local JSON files under data/threads/ (gitignored).
This is the v1 placeholder for real multi-user accounts + server-side thread
storage — the file format is deliberately simple so a future backend can import it."""
import datetime
import json
import os
import uuid
from . import config

def _threads_dir(threads_dir=None):
    """Resolve the threads directory."""
    return threads_dir or config.THREADS_DIR
def _path(thread_id, threads_dir=None):
    """Path of one thread file."""
    return os.path.join(_threads_dir(threads_dir), thread_id + ".json")
def _now():
    """ISO-8601 local timestamp to the second."""
    return datetime.datetime.now().isoformat(timespec="seconds")
def create_thread(title="New thread", tone=config.DEFAULT_TONE, lens=config.DEFAULT_LENS, threads_dir=None):
    """Create and persist a new thread; returns the thread dict."""
    thread = {"id": "thread-" + uuid.uuid4().hex[:12], "title": title, "created": _now(), "updated": _now(),
              "settings": {"tone": tone, "lens": lens}, "messages": []}
    save_thread(thread, threads_dir)
    return thread
def save_thread(thread, threads_dir=None):
    """Persist a thread to its JSON file."""
    thread["updated"] = _now()
    os.makedirs(_threads_dir(threads_dir), exist_ok=True)
    with open(_path(thread["id"], threads_dir), "w", encoding="utf-8") as f:
        json.dump(thread, f, indent=2, ensure_ascii=False)
def load_thread(thread_id, threads_dir=None):
    """Load one thread, or None when absent."""
    path = _path(thread_id, threads_dir)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)
def list_threads(threads_dir=None):
    """Thread summaries (id, title, updated, message count), newest first."""
    folder = _threads_dir(threads_dir)
    out = []
    if not os.path.isdir(folder):
        return out
    for fname in os.listdir(folder):
        if fname.endswith(".json"):
            with open(os.path.join(folder, fname), encoding="utf-8") as f:
                t = json.load(f)
            out.append({"id": t["id"], "title": t["title"], "updated": t["updated"], "messages": len(t["messages"])})
    out.sort(key=lambda t: t["updated"], reverse=True)
    return out
def append_message(thread, role, content, meta=None, threads_dir=None):
    """Append one message and persist; returns the message dict."""
    message = {"role": role, "content": content, "date": _now()}
    if meta:
        message["meta"] = meta
    thread["messages"].append(message)
    if role == "user" and thread["title"] == "New thread":
        thread["title"] = content[:60] + ("..." if len(content) > 60 else "")
    save_thread(thread, threads_dir)
    return message
def delete_thread(thread_id, threads_dir=None):
    """Delete a thread file; returns True when it existed."""
    path = _path(thread_id, threads_dir)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False
