"""External-content parsing and claim segmentation for Deutsch graph consumers."""
import json
import re
from . import llm_util

TIMESTAMP_RE = re.compile(r"^\s*(?:\[(\d{1,2}:\d{2}(?::\d{2})?)\]|\((\d{1,2}:\d{2}(?::\d{2})?)\)|(\d{1,2}:\d{2}(?::\d{2})?))\s+")
BOLD_SPEAKER_RE = re.compile(r"^\*\*([^:*]{1,80}):\*\*\s*(.*)$")
SPEAKER_RE = re.compile(r"^([A-Z][A-Za-z0-9 ._'-]{0,79}):\s*(.*)$")

### Content parsing
def _without_header_block(lines):
    """Drop a leading repo markdown header block when it starts with file:."""
    idx = 0
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    if idx >= len(lines) or not lines[idx].lstrip().startswith("file:"):
        return lines
    while idx < len(lines) and lines[idx].strip():
        idx += 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    return lines[idx:]
def _add_turn(turns, speaker, text, timestamp):
    """Append one normalized turn when text is non-empty."""
    text = " ".join(text.split())
    if not text:
        return
    turns.append({"speaker": speaker, "text": text, "index": len(turns), "timestamp": timestamp})
def _parse_speaker_line(line):
    """Parse optional leading timestamp plus speaker marker from one line."""
    timestamp = None
    match = TIMESTAMP_RE.match(line)
    if match:
        timestamp = next(g for g in match.groups() if g)
        line = line[match.end():]
    match = BOLD_SPEAKER_RE.match(line)
    if match:
        return match.group(1).strip(), match.group(2).strip(), timestamp
    match = SPEAKER_RE.match(line)
    if match:
        return match.group(1).strip(), match.group(2).strip(), timestamp
    return None, None, timestamp
def parse_content(text):
    """Parse transcript/prose content into normalized turns."""
    turns = []
    plain = []
    active_idx = None
    for raw_line in _without_header_block(text.splitlines()):
        line = raw_line.strip()
        if not line:
            if plain:
                _add_turn(turns, None, " ".join(plain), None)
                plain = []
            active_idx = None
            continue
        if line.startswith("#"):
            if plain:
                _add_turn(turns, None, " ".join(plain), None)
                plain = []
            active_idx = None
            continue
        speaker, turn_text, timestamp = _parse_speaker_line(line)
        if speaker:
            if plain:
                _add_turn(turns, None, " ".join(plain), None)
                plain = []
            _add_turn(turns, speaker, turn_text, timestamp)
            active_idx = len(turns) - 1 if turns else None
        elif active_idx is not None:
            turns[active_idx]["text"] = (turns[active_idx]["text"] + " " + line).strip()
        else:
            plain.append(line)
    if plain:
        _add_turn(turns, None, " ".join(plain), None)
    return turns

### Claim segmentation
def _chunk_turns(turns, max_chars=6000):
    """Yield chunks of turns capped by approximate text characters."""
    chunk, total = [], 0
    for turn in turns:
        size = len(turn.get("text", ""))
        if chunk and total + size > max_chars:
            yield chunk
            chunk, total = [], 0
        chunk.append(turn)
        total += size + 1
    if chunk:
        yield chunk
def _turns_prompt_payload(turns):
    """Compact JSON payload for the segmentation prompt."""
    payload = []
    for turn in turns:
        payload.append({"index": turn["index"], "speaker": turn.get("speaker"),
                        "timestamp": turn.get("timestamp"), "text": turn.get("text", "")})
    return json.dumps(payload, ensure_ascii=True)
def _is_verbatim_quote(quote, source):
    """Accept a non-empty quote only when its normalized words occur in the source."""
    quote = " ".join(quote.split())
    source = " ".join((source or "").split())
    return bool(quote) and quote in source
def _parse_claim_rows(data, turn_by_index, next_num):
    """Normalize claim rows from the model, skipping malformed rows."""
    claims = []
    rows = data.get("claims", []) if isinstance(data, dict) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        text = row.get("text") or row.get("claim")
        quote = row.get("quote")
        try:
            turn_index = int(row.get("turn_index"))
        except (TypeError, ValueError):
            continue
        if not isinstance(text, str) or not text.strip() or not isinstance(quote, str) or turn_index not in turn_by_index:
            continue
        turn = turn_by_index[turn_index]
        if not _is_verbatim_quote(quote, turn.get("text")):
            continue
        claims.append({"id": "clm:%03d" % next_num, "text": text.strip(), "speaker": turn.get("speaker"),
                       "turn_index": turn_index, "quote": quote.strip()})
        next_num += 1
    return claims, next_num
def segment_claims(turns, model=None, chat=None):
    """Extract atomic third-person claims from parsed turns via injectable LLM chat."""
    chat = chat or llm_util.chat
    all_claims = []
    next_num = 1
    for chunk in _chunk_turns(turns):
        prompt = (
            "Extract substantive claims/assertions about how the world works from these transcript/content turns. "
            "Do not extract greetings, questions, logistics, jokes without asserted content, or purely personal scheduling. "
            "Each claim must be atomic, one sentence, and written in third person. The quote must be verbatim source words "
            "from the turn. Use the original turn_index.\n\nTURNS JSON:\n%s\n\n"
            "Return ONLY JSON: {\"claims\": [{\"text\": \"...\", \"turn_index\": 0, \"quote\": \"...\"}]}"
        ) % _turns_prompt_payload(chunk)
        data = llm_util.json_from(chat([{"role": "user", "content": prompt}], model=model))
        turn_by_index = {turn["index"]: turn for turn in chunk}
        claims, next_num = _parse_claim_rows(data, turn_by_index, next_num)
        all_claims.extend(claims)
    return all_claims
