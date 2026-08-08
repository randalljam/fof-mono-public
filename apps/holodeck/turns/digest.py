"""LLM digest generation for Holodeck exchanges."""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from apps.holodeck.turns import db
except ImportError:
    from turns import db

ANTHROPIC_MODEL = "claude-sonnet-5"
OPENAI_MODEL = "gpt-5-mini"
SYSTEM_PROMPT = "You summarize one AI-coding exchange for the repo owner's dashboard"
USER_TEXT_LIMIT = 6000
RESPONSE_TEXT_LIMIT = 24000
RESPONSE_HEAD_LIMIT = 6000
RESPONSE_TAIL_LIMIT = 18000
AUTO_DIGEST_HOURS = 48
AUTO_DIGEST_LIMIT = 25

### Errors
class DigestError(Exception):
    pass
class DigestConfigError(DigestError):
    pass
class DigestParseError(DigestError):
    pass
class DigestProviderError(DigestError):
    pass

### Prompting
def load_local_env(root=None):
    if load_dotenv is None:
        return
    root_path = Path(root or db.repo_root())
    load_dotenv(root_path / ".env", override=False)
def env_value(name, env=None):
    if env is not None:
        return env.get(name)
    return os.environ.get(name)
def provider_config(root=None, env=None):
    load_local_env(root)
    anthropic_key = env_value("ANTHROPIC_API_KEY_LOCAL", env)
    if anthropic_key:
        return {"provider": "anthropic", "api_key": anthropic_key, "model": ANTHROPIC_MODEL}
    openai_key = env_value("OPENAI_API_KEY_LOCAL", env)
    if openai_key:
        return {"provider": "openai", "api_key": openai_key, "model": OPENAI_MODEL}
    raise DigestConfigError("No digest API key found. Set ANTHROPIC_API_KEY_LOCAL or OPENAI_API_KEY_LOCAL in repo .env.")
def truncate_user_text(text):
    text = str(text or "")
    if len(text) <= USER_TEXT_LIMIT:
        return text
    return text[:USER_TEXT_LIMIT]
def truncate_response_text(text):
    text = str(text or "")
    if len(text) <= RESPONSE_TEXT_LIMIT:
        return text
    return text[:RESPONSE_HEAD_LIMIT] + "\n\n[...middle truncated for digest...]\n\n" + text[-RESPONSE_TAIL_LIMIT:]
def digest_prompt(user_text, response_text, retry=False):
    nudge = ""
    if retry:
        nudge = "\nReturn ONLY the JSON object. Do not wrap it in markdown."
    return "\n".join([
        "Produce strict JSON with exactly these keys:",
        '{"title": "<3-7 word work title>", "asked": ["<bullet>", "..."], "notes": ["<bullet>", "..."], "recap": "<1-2 sentences>"}',
        "",
        "Rules:",
        "- title is a 3-7 word name for the work built or changed, not a transcription snippet.",
        "- asked has 3-6 terse bullets describing what Randy asked for: features, fixes, or changes.",
        "- notes has 0-5 terse bullets for important non-obvious response details: build decisions, caveats, test results, or follow-up risks.",
        "- recap is 1-2 sentences. Prefer a recap/TL;DR from the response when it exists; extract and tighten it instead of re-summarizing from scratch.",
        "- Keep everything concrete and digestible at a glance.",
        nudge,
        "",
        "USER PROMPT:",
        truncate_user_text(user_text),
        "",
        "AI RESPONSE:",
        truncate_response_text(response_text),
    ])

### JSON parsing
def strip_json_fence(text):
    value = str(text or "").strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    return value
def normalize_digest(value):
    if not isinstance(value, dict):
        raise DigestParseError("digest response was not an object")
    title = value.get("title")
    asked = value.get("asked")
    notes = value.get("notes")
    recap = value.get("recap")
    if not isinstance(title, str) or not title.strip():
        raise DigestParseError("digest title must be a non-empty string")
    if not isinstance(asked, list) or not all(isinstance(item, str) for item in asked):
        raise DigestParseError("digest asked must be a string list")
    if not isinstance(notes, list) or not all(isinstance(item, str) for item in notes):
        raise DigestParseError("digest notes must be a string list")
    if not isinstance(recap, str):
        raise DigestParseError("digest recap must be a string")
    return {"title": " ".join(title.split())[:120], "asked": asked[:6], "notes": notes[:5], "recap": recap}
def parse_digest_json(text):
    try:
        value = json.loads(strip_json_fence(text))
    except json.JSONDecodeError as exc:
        raise DigestParseError("digest response was not valid JSON: " + str(exc))
    return normalize_digest(value)

### SDK calls
def anthropic_response_text(response):
    parts = []
    for item in getattr(response, "content", []) or []:
        text = getattr(item, "text", None)
        if text is None and isinstance(item, dict):
            text = item.get("text")
        if text:
            parts.append(text)
    return "\n".join(parts)
def openai_response_text(response):
    text = getattr(response, "output_text", None)
    if text:
        return text
    choices = getattr(response, "choices", None)
    if choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if content:
            return content
    if isinstance(response, dict):
        return response.get("output_text") or response.get("content") or ""
    return ""
def call_anthropic(config, prompt, client_factory=None):
    if client_factory is None:
        from anthropic import Anthropic
        client_factory = Anthropic
    client = client_factory(api_key=config["api_key"])
    response = client.messages.create(
        model=config["model"],
        max_tokens=900,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return anthropic_response_text(response)
def call_openai(config, prompt, client_factory=None):
    if client_factory is None:
        from openai import OpenAI
        client_factory = OpenAI
    client = client_factory(api_key=config["api_key"])
    if hasattr(client, "responses"):
        response = client.responses.create(
            model=config["model"],
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return openai_response_text(response)
    response = client.chat.completions.create(
        model=config["model"],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return openai_response_text(response)
def call_provider(config, prompt, anthropic_client_factory=None, openai_client_factory=None):
    if config["provider"] == "anthropic":
        return call_anthropic(config, prompt, client_factory=anthropic_client_factory)
    return call_openai(config, prompt, client_factory=openai_client_factory)
def generate_digest(user_text, response_text, root=None, env=None, anthropic_client_factory=None, openai_client_factory=None):
    config = provider_config(root=root, env=env)
    last_error = None
    for retry in (False, True):
        prompt = digest_prompt(user_text, response_text, retry=retry)
        try:
            text = call_provider(config, prompt, anthropic_client_factory=anthropic_client_factory, openai_client_factory=openai_client_factory)
        except Exception as exc:
            raise DigestProviderError("Digest API call failed: " + str(exc))
        try:
            digest = parse_digest_json(text)
            digest["model_used"] = config["model"]
            digest["created_at"] = db.now_iso()
            return digest
        except DigestParseError as exc:
            last_error = exc
    raise DigestParseError(str(last_error))

### DB integration
def digest_exchange(conn, exchange_id, root=None, force=False, env=None, anthropic_client_factory=None, openai_client_factory=None):
    existing = db.exchange_digest_row(conn, exchange_id)
    if existing and not force:
        return db.digest_from_row(existing)
    exchange = db.get_exchange(conn, exchange_id)
    if not exchange:
        raise KeyError(exchange_id)
    digest = generate_digest(
        exchange.get("user_text") or "",
        exchange.get("response_text") or "",
        root=root,
        env=env,
        anthropic_client_factory=anthropic_client_factory,
        openai_client_factory=openai_client_factory,
    )
    db.upsert_digest(conn, exchange_id, digest)
    conn.commit()
    return digest
def digest_missing(conn, limit=20, root=None, env=None, since=None, operator_only=True):
    generated = []
    skipped = []
    for row in db.missing_digest_exchanges(conn, limit=limit, since=since, operator_only=operator_only):
        try:
            digest_exchange(conn, row["id"], root=root, env=env)
            generated.append(row["id"])
        except (DigestConfigError, DigestProviderError, DigestParseError) as exc:
            skipped.append(str(exc))
            break
    return {"generated": generated, "skipped": skipped}
def auto_digest_cutoff(now=None, hours=AUTO_DIGEST_HOURS):
    now_dt = now or datetime.now().astimezone()
    return (now_dt - timedelta(hours=hours)).isoformat()
def auto_digest_recent(conn, limit=AUTO_DIGEST_LIMIT, root=None, env=None, now=None):
    return digest_missing(
        conn,
        limit=limit,
        root=root,
        env=env,
        since=auto_digest_cutoff(now=now),
        operator_only=True,
    )
