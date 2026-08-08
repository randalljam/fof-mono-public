"""Shared LLM plumbing for Deutsch graph services.

The core.llm dependency is imported lazily so this module is import-safe without
API keys and without network access."""
import json
import os
import re

### Chat
def chat(messages, model=None, temperature=None):
    """One OpenAI chat call via core.llm; returns the reply text."""
    from core import llm
    selected_model = model or os.environ.get("DG_OPENAI_MODEL") or llm.OPENAI_MODEL
    response = llm.openai_chat_completion_request(messages, model=selected_model, temperature=temperature)
    if isinstance(response, Exception):
        raise RuntimeError("LLM call failed: %s" % response)
    data = response.json()
    if "error" in data:
        raise RuntimeError("LLM call failed: %s" % data["error"].get("message", data["error"]))
    return data["choices"][0]["message"]["content"]
def json_from(text):
    """Parse JSON out of an LLM reply, tolerating code fences and prose margins."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return json.loads(text)
