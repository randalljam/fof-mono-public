# START OF FILE core/denovo.py
# De novo transcript cleanup pipeline for Stellar Transcriber (M3)

import copy
import json
import os
import re

DENOVO_PIPELINE_VERSION = "0.1.0"
DEFAULT_DENOVO_CONFIG_REL = os.path.join(
    "apps", "transcription", "stellar-transcriber", "config", "denovo-pipeline.json"
)
TERMINAL_PUNCT = re.compile(r'(?:[.!?]["\']?|…|\.\.\.)\s*$')  # ellipsis marks an intentional segment-continuation break
LOWERCASE_START = re.compile(r'^[a-z]')
SHORT_ANSWER = re.compile(r'^(?:yes|yeah|yep|no|nope|right|okay|ok|sure|exactly)[.!?]*$', re.I)
ANSWER_START = re.compile(r'^(?:yes|yeah|yep|no|nope|so|well|right|okay|ok|sure|exactly|i mean)\b', re.I)
QUESTION_TAIL_START = re.compile(r'^(?:(?:yes|yeah|right|okay|ok)[.!?]?\s+)?(?:so\s+)?(?:what|what\'s|why|how|do you think|is there|are there)\b', re.I)
GENERIC_LEADING_QUESTION = re.compile(
    r"^(?:why is (?:that|this)|what does that mean|what do you mean|why)\?$",
    re.I,
)
CONNECTOR_FRAGMENT_END = re.compile(r'\b(?:if|because if|because|when|while|that)$', re.I)
LEADING_COMPLETION_BEFORE_SHORT_ANSWER = re.compile(
    r"^((?:[a-z][\w'-]*\s+){1,3})((?i:yes|yeah|yep|no|nope|right|okay|ok|sure|exactly)(?:[.!?]|$).*)$"
)
CUTOFF_CONNECTOR_BEFORE_CAPITALIZED = re.compile(
    r'^((?:And|But|So|Then|Because)(?:\s+then)?)(\s+([A-Z][^\s]*(?:\s+[A-Z]?[^\s]*){0,5}))$'
)
CAPITALIZED_TURN_OPENER_END = re.compile(r'^(.*\S)\s+([A-Z][A-Za-z\'-]*)$')
SHORT_MEANINGFUL_RESPONSE = re.compile(
    r"^(?:i(?:'m| am) not sure|i (?:don't|do not) know|not sure|i (?:think|guess|suppose) so|maybe)$",
    re.I,
)
COLLAPSIBLE_DISCOURSE_BLIP = re.compile(r'^(?:but|and|so)(?:\s+(?:yes|yeah|yep|right|okay|ok|then))*$', re.I)
DISCOURSE_OPENER = re.compile(
    r'^(?:whereas|well|so|but|and|however|now|look|okay|ok|right|because|although|though|or|then|actually|i mean)\b',
    re.I,
)


### Config
def find_denovo_repo_root(start_dir=None):
    """Walk up from start_dir to find repo root containing denovo config."""
    start_dir = start_dir or os.path.dirname(os.path.abspath(__file__))
    current = os.path.abspath(start_dir)
    while True:
        if os.path.isfile(os.path.join(current, DEFAULT_DENOVO_CONFIG_REL)):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent
def load_denovo_pipeline_config(config_path=None, repo_root=None):
    """Load denovo pipeline config JSON."""
    if config_path is None:
        repo_root = repo_root or find_denovo_repo_root()
        if repo_root is None:
            return {
                "pipeline_version": DENOVO_PIPELINE_VERSION,
                "prompts_version": "denovo-v1",
                "model_tiers": {"cheap": {"openai": "gpt-4o-mini", "anthropic": "claude-3-5-haiku-20241022"}},
                "default_model_tier": "cheap",
                "chunk_token_cap": 1000,
                "adjacent_context_segments": 2,
                "max_island_segments": 20,
                "draft_suffixes": {
                    "single_deterministic": "_draftds",
                    "single_llm": "_draftls",
                    "dual_deterministic": "_draftdd",
                    "dual_llm": "_draftld",
                },
            }
        config_path = os.path.join(repo_root, DEFAULT_DENOVO_CONFIG_REL)
    with open(config_path) as f:
        return json.load(f)
def resolve_denovo_model(model_tier, config=None, provider=None):
    """Resolve model name from tier and available API keys."""
    import os as _os
    from core.llm import OPENAI_API_KEY, ANTHROPIC_API_KEY

    config = config or load_denovo_pipeline_config()
    tier = model_tier or config.get("default_model_tier", "cheap")
    tiers = config.get("model_tiers", {})
    tier_cfg = tiers.get(tier) or tiers.get("cheap") or {}
    if provider is None:
        if OPENAI_API_KEY and tier_cfg.get("openai"):
            provider = "openai"
        elif ANTHROPIC_API_KEY and tier_cfg.get("anthropic"):
            provider = "anthropic"
        else:
            provider = "openai"
    model = tier_cfg.get(provider) or tier_cfg.get("openai") or "gpt-5-mini"
    return model, provider
def preview_dual_llm_islands(path_a, path_b, profile=None):
    """Detect anchors/islands for dual LLM merge without API calls."""
    config = load_denovo_pipeline_config()
    policy = resolve_profile_policy(profile)
    segs_a = load_segments_from_md(path_a)
    segs_b = load_segments_from_md(path_b)
    cleaned_a, _ = apply_deterministic_cleanup(segs_a, policy=policy)
    cleaned_b, _ = apply_deterministic_cleanup(segs_b, policy=policy)
    anchors = find_anchors_between_transcripts(
        cleaned_a, cleaned_b,
        timestamp_threshold=config.get("anchor_timestamp_threshold", 1),
        sim_ratio_threshold=config.get("anchor_sim_ratio_threshold", 0.75),
        normalization_policy=policy,
    )
    islands = find_islands_from_anchors(
        cleaned_a, cleaned_b, anchors,
        max_island_segments=config.get("max_island_segments", 20),
    )
    return {
        "anchors": anchors,
        "islands": islands,
        "segment_count_a": len(cleaned_a),
        "segment_count_b": len(cleaned_b),
    }
def preview_dual_llm_chunks(path_a, path_b, profile=None):
    """Word-anchored chunk decomposition for a dual pair without API calls."""
    config = load_denovo_pipeline_config()
    policy = resolve_profile_policy(profile)
    segs_a = load_segments_from_md(path_a)
    segs_b = load_segments_from_md(path_b)
    cleaned_a, _ = apply_deterministic_cleanup(segs_a, policy=policy)
    cleaned_b, _ = apply_deterministic_cleanup(segs_b, policy=policy)
    chunks = build_dual_decision_chunks(
        cleaned_a, cleaned_b,
        min_anchor_words=config.get("dual_min_anchor_words", 6),
        edge_words=config.get("dual_anchor_edge_words", 3),
        decision_max_words=config.get("dual_decision_max_words", 160),
        decision_max_segments=config.get("dual_decision_max_segments", 6),
        internal_min_anchor_words=config.get("dual_internal_min_anchor_words", 3),
        internal_edge_words=config.get("dual_internal_edge_words", 1),
        match_sim_threshold=config.get("dual_match_sim_threshold", 0.98),
        position_sim_threshold=config.get("dual_position_sim_threshold", 0.8),
    )
    return {
        "chunks": chunks,
        "parent_chunk_count": len({c["parent_chunk_id"] for c in chunks}),
        "diff_chunk_count": sum(1 for c in chunks if c["kind"] == "diff"),
        "segment_count_a": len(cleaned_a),
        "segment_count_b": len(cleaned_b),
    }
def estimate_dual_llm_cost(path_a, path_b, profile=None, model_tier=None, output_tokens_ratio=1.0):
    """
    Estimate token usage and USD cost for merge_dual_llm on one episode pair.

    Uses diff-chunk content token counts and output_tokens_ratio heuristic (default 1:1).
    """
    from core.llm import TOKEN_PRICE_DICT, compute_cost_from_tokens, count_tokens, segments_to_block_text

    config = load_denovo_pipeline_config()
    model, provider = resolve_denovo_model(model_tier, config)
    _, dual_prompt = resolve_denovo_prompts(config)
    preview = preview_dual_llm_chunks(path_a, path_b, profile=profile)
    diff_chunks = [c for c in preview["chunks"] if c["kind"] == "diff"]
    prompt_tokens = count_tokens(dual_prompt)
    total_input = 0
    total_output = 0
    for chunk in diff_chunks:
        content = (
            segments_to_block_text(chunk["segments_a"], "version A")
            + "\n\n" + segments_to_block_text(chunk["segments_b"], "version B")
        )
        chunk_input = prompt_tokens + count_tokens(content)
        total_input += chunk_input
        total_output += int(chunk_input * output_tokens_ratio)
    costs = compute_cost_from_tokens(total_input, total_output, model, TOKEN_PRICE_DICT)
    return {
        "model": model,
        "provider": provider,
        "chunk_count": len(preview["chunks"]),
        "parent_chunk_count": preview["parent_chunk_count"],
        "diff_chunk_count": len(diff_chunks),
        "estimated_api_calls": len(diff_chunks),
        **costs,
    }
def estimate_dual_llm_cost_for_stems(stems, raw_folder, ref_folder=None, profile="deutsch", model_tier=None):
    """Sum cost estimates for a list of episode title stems."""
    totals = {
        "episode_count": 0,
        "diff_chunk_count": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_cost_usd": 0.0,
        "per_episode": [],
    }
    for stem in stems:
        path_a = os.path.join(raw_folder, stem + "_nova2gen.md")
        path_b = os.path.join(raw_folder, stem + "_dgwhspm.md")
        if not os.path.isfile(path_a) or not os.path.isfile(path_b):
            continue
        est = estimate_dual_llm_cost(path_a, path_b, profile=profile, model_tier=model_tier)
        totals["episode_count"] += 1
        totals["diff_chunk_count"] += est["diff_chunk_count"]
        totals["input_tokens"] += est["input_tokens"]
        totals["output_tokens"] += est["output_tokens"]
        totals["total_cost_usd"] += est["total_cost_usd"]
        totals["per_episode"].append({"stem": stem, **est})
    return totals
def resolve_denovo_prompts(config=None):
    """Return (single_prompt, dual_prompt) for the configured prompts version."""
    from core.llm import (
        PROMPT_DENOVO_DUAL_V1,
        PROMPT_DENOVO_DUAL_V2,
        PROMPT_DENOVO_DUAL_V3,
        PROMPT_DENOVO_DUAL_V4,
        PROMPT_DENOVO_SINGLE_V1,
        PROMPT_DENOVO_SINGLE_V2,
    )

    config = config or load_denovo_pipeline_config()
    version = config.get("prompts_version", "denovo-v4")
    if version == "denovo-v1":
        return PROMPT_DENOVO_SINGLE_V1, PROMPT_DENOVO_DUAL_V1
    if version == "denovo-v2":
        return PROMPT_DENOVO_SINGLE_V2, PROMPT_DENOVO_DUAL_V2
    if version == "denovo-v3":
        return PROMPT_DENOVO_SINGLE_V2, PROMPT_DENOVO_DUAL_V3
    return PROMPT_DENOVO_SINGLE_V2, PROMPT_DENOVO_DUAL_V4
def resolve_profile_policy(profile):
    """Resolve normalization policy from corpus profile name or dict."""
    from core.transcript_eval import get_corpus_profile, get_normalization_policy, load_eval_corpus_config

    if isinstance(profile, dict):
        policy_id = profile.get("policy_id")
        if policy_id:
            return get_normalization_policy(policy_id)
        return profile.get("policy")
    if profile:
        cfg = load_eval_corpus_config()
        corp = get_corpus_profile(profile, cfg)
        return get_normalization_policy(corp.get("policy_id", "keep-all"), cfg)
    return get_normalization_policy("keep-all")
def draft_suffix_for(mode, method, config=None):
    """Return output suffix for mode/method pair."""
    config = config or load_denovo_pipeline_config()
    suffixes = config.get("draft_suffixes", {})
    key = f"{mode}_{method}"
    return suffixes.get(key, f"_draft{mode[0]}{method[0]}")


### Segment I/O
def load_segments_from_md(md_path):
    """Load segment list from a transcript markdown file."""
    from core.transcript_eval import extract_transcript_data

    data = extract_transcript_data(md_path)
    if data is None:
        raise ValueError(f"No transcript content in {md_path}")
    return data
def segments_to_md_content(segments):
    """Render segments as transcript markdown content section."""
    lines = []
    for seg in segments:
        speaker = seg.get("speaker_full") or seg.get("speaker_name") or "Speaker 0"
        ts = seg.get("timestamp")
        link = seg.get("timestamp_link")
        if ts:
            if link:
                header = f"{speaker}  [{ts}]({link})"
            else:
                header = f"{speaker}  {ts}"
        else:
            header = f"{speaker}:"
        lines.append(header)
        lines.append(seg.get("dialogue") or "")
        lines.append("")
    body = "\n".join(lines).rstrip() + "\n"
    return "## content\n\n### transcript\n\n" + body
def write_draft_md(segments, source_md_path, suffix, metadata_extra=None, overwrite="no"):
    """Write draft transcript file with provenance metadata."""
    from core.fileops import read_metadata_and_content, set_metadata_field, write_metadata_and_content

    metadata, _ = read_metadata_and_content(source_md_path)
    if metadata is None:
        from core.fileops import create_initial_metadata
        metadata = create_initial_metadata()
    config = load_denovo_pipeline_config()
    metadata = set_metadata_field(metadata, "denovo pipeline version", config.get("pipeline_version", DENOVO_PIPELINE_VERSION))
    if metadata_extra:
        for key, val in metadata_extra.items():
            metadata = set_metadata_field(metadata, key, val)
    content = segments_to_md_content(segments)
    return write_metadata_and_content(source_md_path, metadata, content, suffix_new=suffix, overwrite=overwrite)
def _segment_echoes_context(seg, ctx_seg, sim_threshold=0.8):
    """True when an LLM output segment repeats a read-only context segment."""
    from core.transcript_eval import calc_lev_dist_ratio, normalize_dialogue

    if (seg.get("timestamp") or "") != (ctx_seg.get("timestamp") or ""):
        return False
    norm_out = normalize_dialogue(seg.get("dialogue"), None)
    norm_ctx = normalize_dialogue(ctx_seg.get("dialogue"), None)
    if not norm_out or not norm_ctx:
        return norm_out == norm_ctx
    return calc_lev_dist_ratio(norm_out, norm_ctx) >= sim_threshold
def strip_context_echo(result_segments, context_before, context_after):
    """
    Drop leading/trailing LLM output segments that echo the read-only context blocks.

    Models sometimes return the 'context before'/'context after' segments despite the
    prompt; unchecked, each echo duplicates dialogue at every chunk join.
    """
    out = list(result_segments)
    stripped = 0
    for ctx_seg in reversed(context_before or []):
        if out and _segment_echoes_context(out[0], ctx_seg):
            out.pop(0)
            stripped += 1
    for ctx_seg in (context_after or []):
        if out and _segment_echoes_context(out[-1], ctx_seg):
            out.pop()
            stripped += 1
    return out, stripped
def llm_segments_to_internal(segments, source_segments=None):
    """Convert LLM output segment dicts to internal extract_transcript_data shape."""
    timestamp_links = {}
    for src in source_segments or []:
        ts = src.get("timestamp")
        link = src.get("timestamp_link")
        if ts and link and ts not in timestamp_links:
            timestamp_links[ts] = link
    result = []
    for seg in segments:
        speaker = seg.get("speaker") or "Speaker 0"
        timestamp = seg.get("timestamp")
        result.append({
            "speaker_full": speaker,
            "speaker_name": speaker,
            "speaker_role": None,
            "timestamp": timestamp,
            "timestamp_link": timestamp_links.get(timestamp),
            "dialogue": seg.get("dialogue") or "",
        })
    return result


### Deterministic cleanup
def _speaker_key(seg):
    return seg.get("speaker_name") or seg.get("speaker_full") or ""
def is_unassigned_speaker_label(seg):
    """True for generic diarization labels left in otherwise speaker-assigned transcripts."""
    speaker = _speaker_key(seg).strip()
    return bool(re.match(r'^Speaker\s+\d+$', speaker))
def is_assigned_speaker_label(seg):
    """True when a segment has a human speaker label rather than a generic Speaker N."""
    speaker = _speaker_key(seg).strip()
    return bool(speaker) and not is_unassigned_speaker_label(seg)
def is_unassigned_blip_between_same_assigned_speaker(prev_seg, blip_seg, next_seg):
    """True when a remaining Speaker N is sandwiched inside one named speaker's turn."""
    return (
        is_assigned_speaker_label(prev_seg)
        and is_unassigned_speaker_label(blip_seg)
        and _speaker_key(prev_seg) == _speaker_key(next_seg)
    )
def is_broken_sentence_transition(prev_seg, next_seg):
    """True when prev lacks terminal punct and next dialogue starts lowercase."""
    prev_dialogue = (prev_seg.get("dialogue") or "").rstrip()
    next_dialogue = (next_seg.get("dialogue") or "").lstrip()
    if not prev_dialogue or not next_dialogue:
        return False
    if TERMINAL_PUNCT.search(prev_dialogue):
        return False
    return bool(LOWERCASE_START.match(next_dialogue))
def split_short_trailing_fragment(dialogue, max_words=5):
    """Return (body, tail) when dialogue ends with a short fragment after a full sentence."""
    text = (dialogue or "").rstrip()
    matches = list(re.finditer(r'[.!?]["\']?\s+', text))
    if not matches:
        return None, None
    split_at = matches[-1].end()
    body = text[:split_at].rstrip()
    tail = text[split_at:].strip()
    if not tail or TERMINAL_PUNCT.search(tail):
        return None, None
    if len(tail.split()) > max_words:
        return None, None
    if len(matches) >= 2:
        prev_split_at = matches[-2].end()
        leading_body = text[:prev_split_at].rstrip()
        trailing_sentence = text[prev_split_at:split_at].strip()
        expanded_tail = (trailing_sentence + " " + tail).strip()
        if (
            leading_body
            and is_short_acknowledgement_block(trailing_sentence)
            and not is_short_acknowledgement_block(leading_body)
            and len(expanded_tail.split()) <= max_words
        ):
            return leading_body, expanded_tail
    return body, tail
def split_short_answer_after_question(dialogue, max_words=3):
    """Return (question_text, answer_tail) for endings like '...? Yes.'."""
    text = (dialogue or "").rstrip()
    match = re.search(r'^(.*\?["\']?)\s+([^.!?]+[.!?]?)$', text)
    if not match:
        return None, None
    body = match.group(1).rstrip()
    tail = match.group(2).strip()
    if len(tail.split()) > max_words or not SHORT_ANSWER.match(tail):
        return None, None
    return body, tail
def split_question_tail_for_next_speaker(dialogue, max_words=6):
    """Return (body, tail) when a segment ends with the start of another speaker's question."""
    text = (dialogue or "").rstrip()
    for match in re.finditer(r'[.!?]["\']?\s+', text):
        split_at = match.end()
        body = text[:split_at].rstrip()
        tail = text[split_at:].strip()
        if not body or not tail:
            continue
        if is_short_acknowledgement_block(body):
            continue
        if len(tail.split()) > max_words:
            continue
        if QUESTION_TAIL_START.match(tail):
            return body, tail
    return None, None
def split_short_leading_question_before_answer(dialogue, max_words=6):
    """Return (question, rest) for starts like 'Why is that? Yeah, so ...'."""
    text = (dialogue or "").lstrip()
    match = re.match(r'^([^?]+\?)\s+(.+)$', text)
    if not match:
        return None, None
    question = match.group(1).strip()
    rest = match.group(2).lstrip()
    if len(question.rstrip("?").split()) > max_words:
        return None, None
    if not GENERIC_LEADING_QUESTION.match(question):
        return None, None
    if not ANSWER_START.match(rest):
        return None, None
    return question, rest
def append_cutoff_ellipsis(dialogue):
    """Mark an interrupted speaker turn with transcript ellipsis at the segment end."""
    text = (dialogue or "").rstrip()
    if not text or TERMINAL_PUNCT.search(text):
        return text
    return text + "..."
def normalize_terminal_cutoff_dash(dialogue):
    """Replace an ASR terminal cutoff dash with transcript ellipsis."""
    text = (dialogue or "").rstrip()
    if not re.search(r'\s*[-–—]+\s*$', text):
        return text, False
    body = re.sub(r'\s*[-–—]+\s*$', "", text).rstrip()
    if not body:
        return text, False
    return body + "...", True
def split_trailing_comma_acknowledgement(dialogue):
    """Return (body, acknowledgement) for a misplaced tail such as ``Okay. Yeah,``."""
    text = (dialogue or "").rstrip()
    matches = list(re.finditer(r'[.!?]["\']?\s+', text))
    if not matches:
        return None, None
    split_at = matches[-1].end()
    body = text[:split_at].rstrip()
    tail = text[split_at:].strip()
    if not body or not tail.endswith(","):
        return None, None
    acknowledgement = tail[:-1].strip()
    if not SHORT_ANSWER.fullmatch(acknowledgement):
        return None, None
    return body, tail
def mark_interrupted_turn_ellipsis(segments):
    """Mark unpunctuated turns with ... when the next different speaker starts a capitalized turn."""
    marked = copy.deepcopy(segments)
    logs = []
    for i in range(len(marked) - 1):
        prev = marked[i]
        nxt = marked[i + 1]
        prev_dialogue = (prev.get("dialogue") or "").rstrip()
        next_dialogue = (nxt.get("dialogue") or "").lstrip()
        short_answer = SHORT_ANSWER.fullmatch(prev_dialogue.strip()) if prev_dialogue else None
        short_discourse_overlap = (
            is_discourse_opener(next_dialogue)
            and len(next_dialogue.rstrip(".!?").split()) <= 2
        )
        if (
            _speaker_key(prev) != _speaker_key(nxt)
            and prev_dialogue
            and not TERMINAL_PUNCT.search(prev_dialogue)
            and not re.search(r'[,;:]\s*$', prev_dialogue)
            and re.match(r'^[A-Z]', next_dialogue)
            and not is_short_meaningful_response(prev_dialogue)
            and not short_answer
            and not short_discourse_overlap
        ):
            prev["dialogue"] = append_cutoff_ellipsis(prev_dialogue)
            logs.append({
                "type": "interrupted_turn_ellipsis",
                "speaker": _speaker_key(prev),
                "next_speaker": _speaker_key(nxt),
            })
    return marked, logs
def split_leading_completion_before_short_answer(dialogue):
    """Return (completion, rest) for meeting cutoffs like 'to Yeah. ...'."""
    text = (dialogue or "").lstrip()
    match = LEADING_COMPLETION_BEFORE_SHORT_ANSWER.match(text)
    if not match:
        return None, None
    return match.group(1).strip(), match.group(2).lstrip()
def split_leading_completion_before_capitalized_start(dialogue, max_words=3):
    """Return (completion, rest) for cutoffs like 'to We've already ...'."""
    words = (dialogue or "").lstrip().split()
    if len(words) < 2:
        return None, None
    moved = []
    for word in words[:max_words]:
        if not LOWERCASE_START.match(word):
            break
        moved.append(word)
    if not moved or len(moved) >= len(words):
        return None, None
    if moved[0].lower().rstrip(",") not in {"to", "of", "in", "on", "for", "with", "at", "by"}:
        return None, None
    rest = " ".join(words[len(moved):])
    if not rest or not re.match(r'^[A-Z]', rest):
        return None, None
    return " ".join(moved), rest
def split_trailing_cutoff_before_next_start(dialogue, next_dialogue):
    """Return (body, cutoff_tail, moved_start) for 'And then That's...' overlap."""
    body, tail = split_short_trailing_fragment(dialogue, max_words=8)
    if not body or not tail:
        return None, None, None
    match = CUTOFF_CONNECTOR_BEFORE_CAPITALIZED.match(tail)
    if not match:
        return None, None, None
    cutoff_tail = match.group(1).strip()
    moved_start = match.group(3).strip()
    nxt = (next_dialogue or "").lstrip().lower()
    if not nxt.startswith(moved_start.lower()):
        return None, None, None
    return body, cutoff_tail, moved_start
def split_stranded_turn_opener_for_next_speaker(dialogue, next_dialogue):
    """Return (body, opener) when prev ends with next speaker's capitalized opener."""
    text = (dialogue or "").rstrip()
    match = CAPITALIZED_TURN_OPENER_END.match(text)
    if not match:
        return None, None
    body = match.group(1).rstrip()
    opener = match.group(2).strip()
    if not is_discourse_opener(opener):
        return None, None
    nxt = (next_dialogue or "").lstrip().lower()
    if not re.match(rf'^{re.escape(opener.lower())}\b', nxt):
        return None, None
    return body, opener
def is_short_incomplete_fragment(seg, max_words=4):
    """True for tiny fragments like 'Do you think' that are unlikely complete turns."""
    dialogue = (seg.get("dialogue") or "").strip()
    if not dialogue or TERMINAL_PUNCT.search(dialogue):
        return False
    body, tail = split_short_trailing_fragment(dialogue)
    if body and tail:
        return False
    if is_short_meaningful_response(dialogue):
        return False
    return len(dialogue.split()) <= max_words
def is_short_meaningful_response(dialogue):
    """True for complete short responses that often lack terminal punctuation in ASR."""
    text = (dialogue or "").strip().rstrip(".!?")
    if not text:
        return False
    return bool(SHORT_MEANINGFUL_RESPONSE.match(text))
def is_short_terminal_continuation_fragment(prev_seg, blip_seg, max_words=6):
    """True when a short middle segment completes the previous incomplete sentence."""
    prev_dialogue = (prev_seg.get("dialogue") or "").strip()
    dialogue = (blip_seg.get("dialogue") or "").strip()
    if not prev_dialogue or not dialogue:
        return False
    if TERMINAL_PUNCT.search(prev_dialogue):
        return False
    if not LOWERCASE_START.match(dialogue):
        return False
    if not TERMINAL_PUNCT.search(dialogue):
        return False
    return len(dialogue.split()) <= max_words
def is_short_overlap_noise_fragment(seg, max_words=6):
    """True for short crosstalk fragments like 'by some way if it' between same-speaker turns."""
    return is_short_incomplete_fragment(seg, max_words=max_words)
def is_discourse_opener(dialogue):
    """True for short turn-openers like 'Whereas' that should stay on their speaker."""
    text = (dialogue or "").strip()
    if not text:
        return False
    return bool(DISCOURSE_OPENER.match(text))
def is_collapsible_discourse_blip(dialogue):
    """True for discourse fragments like 'But yeah' that continue into lowercase text."""
    text = (dialogue or "").strip().rstrip(".!?")
    if not text:
        return False
    return bool(COLLAPSIBLE_DISCOURSE_BLIP.match(text))
def blip_echoes_start_of_next(blip_dialogue, next_dialogue):
    """True when the next turn repeats the middle fragment (answer echo, not a blip)."""
    blip = (blip_dialogue or "").strip().rstrip(".!?,").lower()
    nxt = (next_dialogue or "").lstrip().lower()
    if not blip or not nxt:
        return False
    return nxt.startswith(blip)
def is_connector_fragment(seg, max_words=4):
    """True for tiny connector fragments like 'Because if' that continue into next text."""
    dialogue = (seg.get("dialogue") or "").strip()
    if not dialogue or TERMINAL_PUNCT.search(dialogue):
        return False
    if len(dialogue.split()) > max_words:
        return False
    return bool(CONNECTOR_FRAGMENT_END.search(dialogue))
def is_short_acknowledgement_block(dialogue, max_words=4):
    """True for short standalone acknowledgement turns like 'Yeah. Yeah.'."""
    text = (dialogue or "").strip()
    if not text or not TERMINAL_PUNCT.search(text):
        return False
    words = text.split()
    if len(words) > max_words:
        return False
    parts = [p.strip() for p in re.split(r'[.!?]+', text) if p.strip()]
    return bool(parts) and all(SHORT_ANSWER.match(part) for part in parts)
def repair_short_speaker_blip_tail(prev_seg, blip_seg, next_seg):
    """
    Preserve a valid short middle acknowledgement while moving its dangling tail.

    Example:
    A: ... worldview.
    B: Yeah. Yeah. I'm so
    A: curious ...
    """
    if _speaker_key(prev_seg) != _speaker_key(next_seg):
        return None, None, None
    if _speaker_key(prev_seg) == _speaker_key(blip_seg):
        return None, None, None
    body, tail = split_short_trailing_fragment(blip_seg.get("dialogue"), max_words=3)
    if not body or not tail or not is_short_acknowledgement_block(body):
        return None, None, None
    if QUESTION_TAIL_START.match(tail):
        return None, None, None
    next_dialogue = (next_seg.get("dialogue") or "").lstrip()
    if not LOWERCASE_START.match(next_dialogue):
        return None, None, None
    kept_blip = copy.deepcopy(blip_seg)
    kept_blip["dialogue"] = body
    repaired_next = copy.deepcopy(next_seg)
    repaired_next["dialogue"] = (tail + " " + next_dialogue).strip()
    log = {
        "type": "short_speaker_blip_tail",
        "kept_speaker": _speaker_key(blip_seg),
        "tail_to_speaker": _speaker_key(next_seg),
        "moved_words": tail.split(),
    }
    return kept_blip, repaired_next, log
def repair_short_speaker_blip(prev_seg, blip_seg, next_seg):
    """
    Collapse A-B-A where B is a tiny incomplete fragment and next continues it.

    This targets diarization blips such as:
    Speaker 0: ...?
    Speaker 1: Do you think
    Speaker 0: that's something ...?
    """
    if _speaker_key(prev_seg) != _speaker_key(next_seg):
        return None, None
    if _speaker_key(prev_seg) == _speaker_key(blip_seg):
        return None, None
    terminal_continuation = is_short_terminal_continuation_fragment(prev_seg, blip_seg)
    next_dialogue = (next_seg.get("dialogue") or "").lstrip()
    overlap_continuation = (
        is_short_overlap_noise_fragment(blip_seg)
        and bool(LOWERCASE_START.match(next_dialogue))
    )
    unassigned_between_named = (
        is_unassigned_blip_between_same_assigned_speaker(prev_seg, blip_seg, next_seg)
        and LOWERCASE_START.match(next_dialogue)
        and len((blip_seg.get("dialogue") or "").split()) <= 8
    )
    if (
        not is_short_incomplete_fragment(blip_seg)
        and not overlap_continuation
        and not terminal_continuation
        and not unassigned_between_named
    ):
        return None, None
    if (
        is_discourse_opener(blip_seg.get("dialogue"))
        and not is_connector_fragment(blip_seg)
        and not (LOWERCASE_START.match(next_dialogue) and is_collapsible_discourse_blip(blip_seg.get("dialogue")))
        and not unassigned_between_named
    ):
        return None, None
    if (
        is_discourse_opener(prev_seg.get("dialogue"))
        and is_short_incomplete_fragment(prev_seg)
    ):
        return None, None
    if blip_echoes_start_of_next(blip_seg.get("dialogue"), next_dialogue):
        return None, None
    if not LOWERCASE_START.match(next_dialogue) and not is_connector_fragment(blip_seg) and not terminal_continuation and not unassigned_between_named:
        return None, None
    repaired = copy.deepcopy(prev_seg)
    middle = (blip_seg.get("dialogue") or "").strip()
    repaired["dialogue"] = (
        (repaired.get("dialogue") or "").rstrip() + " " + middle + " " + next_dialogue
    ).strip()
    log = {
        "type": "short_speaker_blip",
        "removed_speaker": _speaker_key(blip_seg),
        "kept_speaker": _speaker_key(prev_seg),
        "moved_words": (middle + " " + next_dialogue).split(),
    }
    return repaired, log
def repair_speaker_blip_pass(segments, logs, verbose=False):
    """Run one content-preserving A-B-A repair pass."""
    i = 0
    while i < len(segments) - 2:
        kept_blip, repaired_next, tail_log = repair_short_speaker_blip_tail(
            segments[i], segments[i + 1], segments[i + 2]
        )
        if tail_log:
            segments[i + 1] = kept_blip
            segments[i + 2] = repaired_next
            logs.append(tail_log)
            if verbose:
                print(f"  repair: moved short blip tail to {tail_log['tail_to_speaker']}")
            i += 1
            continue
        repaired, log = repair_short_speaker_blip(
            segments[i], segments[i + 1], segments[i + 2]
        )
        if log:
            segments[i] = repaired
            del segments[i + 1:i + 3]
            logs.append(log)
            if verbose:
                print(f"  repair: collapsed short speaker blip from {log['removed_speaker']}")
            continue
        i += 1
    return segments
def merge_phrase_only_transition(prev_seg, next_seg, max_phrase_words=8):
    """
    Merge adjacent turns when one is only a short phrase completing the other.

    The longer turn supplies the speaker label; the earlier turn supplies timestamp
    provenance regardless of which side contains the short phrase.
    """
    prev_dialogue = (prev_seg.get("dialogue") or "").strip()
    next_dialogue = (next_seg.get("dialogue") or "").strip()
    if _speaker_key(prev_seg) == _speaker_key(next_seg):
        return None, None
    if not prev_dialogue or not next_dialogue or not LOWERCASE_START.match(next_dialogue):
        return None, None
    if TERMINAL_PUNCT.search(prev_dialogue):
        return None, None
    prev_words = len(prev_dialogue.split())
    next_words = len(next_dialogue.split())
    prev_is_phrase = prev_words <= max_phrase_words and next_words >= prev_words * 2
    next_is_phrase = (
        next_words <= max_phrase_words
        and prev_words >= next_words * 2
        and bool(TERMINAL_PUNCT.search(next_dialogue))
    )
    if not prev_is_phrase and not next_is_phrase:
        return None, None
    longer = next_seg if prev_is_phrase else prev_seg
    merged = copy.deepcopy(longer)
    merged["timestamp"] = prev_seg.get("timestamp")
    merged["timestamp_link"] = prev_seg.get("timestamp_link")
    merged["dialogue"] = (prev_dialogue + " " + next_dialogue).strip()
    log = {
        "type": "merge_phrase_only_transition",
        "kept_speaker": _speaker_key(longer),
        "phrase_speaker": _speaker_key(prev_seg if prev_is_phrase else next_seg),
        "timestamp": prev_seg.get("timestamp"),
    }
    return merged, log
def repair_question_tail_to_next(prev_seg, next_seg):
    """Move a dangling question opener from current segment onto the next speaker."""
    if _speaker_key(prev_seg) == _speaker_key(next_seg):
        return None, None, None
    body, tail = split_question_tail_for_next_speaker(prev_seg.get("dialogue"))
    if not tail:
        return None, None, None
    next_dialogue = (next_seg.get("dialogue") or "").lstrip()
    if not next_dialogue or not LOWERCASE_START.match(next_dialogue):
        return None, None, None
    repaired_prev = copy.deepcopy(prev_seg)
    repaired_next = copy.deepcopy(next_seg)
    repaired_prev["dialogue"] = body
    repaired_next["dialogue"] = (tail + " " + next_dialogue).strip()
    log = {
        "type": "question_tail_to_next",
        "from_speaker": _speaker_key(prev_seg),
        "to_speaker": _speaker_key(next_seg),
        "moved_words": tail.split(),
    }
    return repaired_prev, repaired_next, log
def repair_broken_sentence_transition(prev_seg, next_seg, max_words=6):
    """
    Repair small speaker-boundary sentence fragments.

    Prefer moving a short dangling tail from prev to next when prev already contains a
    complete sentence. Otherwise move leading words from next to prev only when terminal
    punctuation appears quickly; abort instead of pulling a long chunk across speakers.

    :return: (prev_seg, next_seg, repair_log dict or None)
    """
    prev = copy.deepcopy(prev_seg)
    nxt = copy.deepcopy(next_seg)
    if is_short_meaningful_response(prev.get("dialogue")):
        return prev, nxt, None
    if blip_echoes_start_of_next(prev.get("dialogue"), nxt.get("dialogue")):
        return prev, nxt, None
    prev_answer_body, prev_answer_tail = split_short_answer_after_question(prev.get("dialogue"))
    if prev_answer_tail:
        prev["dialogue"] = prev_answer_body
        nxt["dialogue"] = (prev_answer_tail + " " + (nxt.get("dialogue") or "").lstrip()).strip()
        log = {
            "type": "broken_sentence_transition",
            "direction": "prev_to_next",
            "moved_words": prev_answer_tail.split(),
            "from_speaker": _speaker_key(prev),
            "to_speaker": _speaker_key(nxt),
        }
        return prev, nxt, log
    next_question, next_rest = split_short_leading_question_before_answer(nxt.get("dialogue"))
    if next_question:
        prev["dialogue"] = ((prev.get("dialogue") or "").rstrip() + " " + next_question).strip()
        nxt["dialogue"] = next_rest
        log = {
            "type": "broken_sentence_transition",
            "direction": "next_to_prev",
            "moved_words": next_question.split(),
            "from_speaker": _speaker_key(nxt),
            "to_speaker": _speaker_key(prev),
        }
        return prev, nxt, log
    prev_body, trailing_ack = split_trailing_comma_acknowledgement(prev.get("dialogue"))
    next_dialogue = (nxt.get("dialogue") or "").lstrip()
    if (
        trailing_ack
        and _speaker_key(prev) != _speaker_key(nxt)
        and re.match(r'^[A-Z]', next_dialogue)
    ):
        prev["dialogue"] = prev_body
        nxt["dialogue"] = (trailing_ack + " " + next_dialogue).strip()
        log = {
            "type": "trailing_acknowledgement_to_next",
            "direction": "prev_to_next",
            "moved_words": [trailing_ack],
            "from_speaker": _speaker_key(prev),
            "to_speaker": _speaker_key(nxt),
        }
        return prev, nxt, log
    if not is_broken_sentence_transition(prev, nxt):
        return prev, nxt, None
    prev_body, stranded_opener = split_stranded_turn_opener_for_next_speaker(
        prev.get("dialogue"),
        nxt.get("dialogue"),
    )
    if stranded_opener:
        prev["dialogue"] = append_cutoff_ellipsis(prev_body)
        nxt["dialogue"] = (stranded_opener + " " + (nxt.get("dialogue") or "").lstrip()).strip()
        log = {
            "type": "stranded_turn_opener_to_next",
            "direction": "prev_to_next",
            "moved_words": stranded_opener.split(),
            "from_speaker": _speaker_key(prev),
            "to_speaker": _speaker_key(nxt),
        }
        return prev, nxt, log
    next_completion, next_rest = split_leading_completion_before_short_answer(nxt.get("dialogue"))
    if next_completion:
        prev["dialogue"] = append_cutoff_ellipsis(((prev.get("dialogue") or "").rstrip() + " " + next_completion).strip())
        nxt["dialogue"] = next_rest
        log = {
            "type": "cutoff_transition",
            "direction": "next_to_prev",
            "moved_words": next_completion.split(),
            "from_speaker": _speaker_key(nxt),
            "to_speaker": _speaker_key(prev),
        }
        return prev, nxt, log
    cutoff_body, cutoff_tail, moved_start = split_trailing_cutoff_before_next_start(
        prev.get("dialogue"),
        nxt.get("dialogue"),
    )
    if cutoff_tail:
        prev["dialogue"] = (cutoff_body + " " + append_cutoff_ellipsis(cutoff_tail)).strip()
        nxt["dialogue"] = (moved_start + " " + (nxt.get("dialogue") or "").lstrip()).strip()
        log = {
            "type": "trailing_cutoff_before_next_start",
            "direction": "prev_to_next",
            "moved_words": moved_start.split(),
            "from_speaker": _speaker_key(prev),
            "to_speaker": _speaker_key(nxt),
        }
        return prev, nxt, log
    prev_body, prev_tail = split_short_trailing_fragment(prev.get("dialogue"), max_words=6)
    if prev_tail:
        if is_short_acknowledgement_block(prev_body) and QUESTION_TAIL_START.match(prev_tail):
            prev_tail = None
        else:
            next_completion, next_rest = split_leading_completion_before_capitalized_start(nxt.get("dialogue"))
            if next_completion:
                prev["dialogue"] = (prev_body + " " + append_cutoff_ellipsis((prev_tail + " " + next_completion).strip())).strip()
                nxt["dialogue"] = next_rest
                log = {
                    "type": "cutoff_transition",
                    "direction": "next_to_prev",
                    "moved_words": next_completion.split(),
                    "from_speaker": _speaker_key(nxt),
                    "to_speaker": _speaker_key(prev),
                }
                return prev, nxt, log
            prev["dialogue"] = prev_body
            nxt["dialogue"] = (prev_tail + " " + (nxt.get("dialogue") or "").lstrip()).strip()
            log = {
                "type": "broken_sentence_transition",
                "direction": "prev_to_next",
                "moved_words": prev_tail.split(),
                "from_speaker": _speaker_key(prev),
                "to_speaker": _speaker_key(nxt),
            }
            return prev, nxt, log
    next_words = (nxt.get("dialogue") or "").split()
    moved = []
    reached_terminal = False
    for _ in range(min(max_words, len(next_words))):
        if not next_words:
            break
        if TERMINAL_PUNCT.search(prev.get("dialogue") or ""):
            reached_terminal = True
            break
        word = next_words.pop(0)
        moved.append(word)
        prev["dialogue"] = ((prev.get("dialogue") or "").rstrip() + " " + word).strip()
        if TERMINAL_PUNCT.search(prev.get("dialogue") or ""):
            reached_terminal = True
            break
    if not reached_terminal or not next_words:
        # Repair would swallow the whole next segment, eliminating it. That is a merge
        # decision, not a boundary repair. Likewise, moving up to the cap without finding
        # sentence-ending punctuation is too speculative — abort and keep the originals.
        return copy.deepcopy(prev_seg), copy.deepcopy(next_seg), None
    nxt["dialogue"] = " ".join(next_words).strip()
    if not moved:
        return prev, nxt, None
    log = {
        "type": "broken_sentence_transition",
        "direction": "next_to_prev",
        "moved_words": moved,
        "from_speaker": _speaker_key(nxt),
        "to_speaker": _speaker_key(prev),
    }
    return prev, nxt, log
def merge_consecutive_same_speaker(segments, require_continuation=False):
    """
    Merge consecutive segments with the same speaker.

    With require_continuation=True, merge only when the earlier segment ends without
    terminal punctuation (the spurious-split signature). References legitimately contain
    consecutive same-speaker segments; merging those eliminates real segments.
    """
    if not segments:
        return segments, []
    merged = [copy.deepcopy(segments[0])]
    logs = []
    for seg in segments[1:]:
        same_speaker = _speaker_key(seg) == _speaker_key(merged[-1])
        continuation_ok = not require_continuation or not TERMINAL_PUNCT.search((merged[-1].get("dialogue") or "").rstrip())
        if same_speaker and continuation_ok:
            merged[-1]["dialogue"] = ((merged[-1].get("dialogue") or "") + " " + (seg.get("dialogue") or "")).strip()
            logs.append({"type": "merge_same_speaker", "speaker": _speaker_key(seg)})
        else:
            merged.append(copy.deepcopy(seg))
    return merged, logs
def normalize_segments_dialogue(segments, policy):
    """Apply normalize_dialogue to each segment's dialogue field."""
    from core.transcript_eval import normalize_dialogue

    result = []
    for seg in segments:
        s = copy.deepcopy(seg)
        s["dialogue"] = normalize_dialogue(s.get("dialogue"), policy)
        result.append(s)
    return result
def apply_deterministic_cleanup(segments, policy=None, verbose=False):
    """
    Apply all deterministic cleanup steps in order.

    The policy is intentionally NOT applied to the returned dialogue text: normalization
    (lowercase, strip punctuation/fillers) is a comparison-time transform for eval and
    anchor matching only. Persisting it destroys the draft transcript (case, punctuation)
    and starves LLM repair of the sentence-boundary signal it needs. The policy parameter
    is retained for call-site compatibility and future comparison-only uses.

    :return: (cleaned_segments, repair_logs)
    """
    logs = []
    segs = copy.deepcopy(segments)
    for seg in segs:
        normalized, changed = normalize_terminal_cutoff_dash(seg.get("dialogue"))
        if changed:
            seg["dialogue"] = normalized
            logs.append({
                "type": "terminal_cutoff_dash",
                "speaker": _speaker_key(seg),
            })
    i = 0
    while i < len(segs) - 1:
        repaired_prev, repaired_next, log = repair_question_tail_to_next(segs[i], segs[i + 1])
        if log:
            segs[i] = repaired_prev
            segs[i + 1] = repaired_next
            logs.append(log)
            if verbose:
                print(f"  repair: moved question tail to {log['to_speaker']}")
            if i > 0:
                i -= 1
            continue
        i += 1
    segs = repair_speaker_blip_pass(segs, logs, verbose=verbose)
    # Repair broken-sentence transitions BEFORE same-speaker merging: a segment whose
    # trailing words sit at the start of the next segment ends mid-sentence, and merging
    # on that signal would eliminate a real segment instead of moving the words back.
    i = 0
    while i < len(segs) - 1:
        prev, nxt, log = repair_broken_sentence_transition(segs[i], segs[i + 1])
        segs[i] = prev
        segs[i + 1] = nxt
        if log:
            logs.append(log)
            if verbose:
                print(f"  repair: moved {log['moved_words']} to {log['to_speaker']}")
        if not (nxt.get("dialogue") or "").strip():
            segs.pop(i + 1)
            logs.append({"type": "drop_empty_segment", "index": i + 1})
            continue
        i += 1
    i = 0
    while i < len(segs) - 1:
        outer_match_before = (
            i > 0
            and _speaker_key(segs[i - 1]) == _speaker_key(segs[i + 1])
        )
        outer_match_after = (
            i + 2 < len(segs)
            and _speaker_key(segs[i]) == _speaker_key(segs[i + 2])
        )
        if outer_match_before or outer_match_after:
            i += 1
            continue
        merged, log = merge_phrase_only_transition(segs[i], segs[i + 1])
        if log:
            segs[i] = merged
            segs.pop(i + 1)
            logs.append(log)
            if verbose:
                print(
                    f"  repair: merged phrase-only segment from {log['phrase_speaker']} "
                    f"into {log['kept_speaker']}"
                )
            if i > 0:
                i -= 1
            continue
        i += 1
    segs = repair_speaker_blip_pass(segs, logs, verbose=verbose)
    segs, merge_logs = merge_consecutive_same_speaker(segs, require_continuation=False)
    logs.extend(merge_logs)
    segs, cutoff_logs = mark_interrupted_turn_ellipsis(segs)
    logs.extend(cutoff_logs)
    if verbose:
        for log in cutoff_logs:
            print(f"  repair: marked cutoff for {log['speaker']} before {log['next_speaker']}")
    return segs, logs
def create_draft_deterministic(raw_md_path, profile=None, output_path=None, verbose=False):
    """
    Deterministic cleanup pass on one raw diarized transcript.

    :return: path to written draft file
    """
    from core.transcribe import convert_nums_to_words

    config = load_denovo_pipeline_config()
    suffix = draft_suffix_for("single", "deterministic", config)
    policy = resolve_profile_policy(profile)
    segments = load_segments_from_md(raw_md_path)
    cleaned, logs = apply_deterministic_cleanup(segments, policy=policy, verbose=verbose)
    metadata_extra = {
        "denovo method": "deterministic",
        "denovo mode": "single",
        "denovo repair count": str(len(logs)),
    }
    out = write_draft_md(cleaned, raw_md_path, suffix, metadata_extra=metadata_extra, overwrite="yes" if output_path else "no")
    if policy and policy.get("numerals") == "normalize-to-words":
        convert_nums_to_words(out, verbose=verbose)
    if output_path:
        import shutil
        shutil.copy2(out, output_path)
        return output_path
    return out


### Anchor / island detection (dual mode)
def _segment_seconds(seg):
    from core.fileops import convert_timestamp_to_seconds
    ts = seg.get("timestamp")
    if not ts:
        return None
    return convert_timestamp_to_seconds(ts)
def _timestamp_gap_ok(segments, index, threshold):
    """True if segment at index has gap > threshold to neighbors."""
    n = len(segments)
    if n <= 1:
        return True
    ts = _segment_seconds(segments[index])
    if ts is None:
        return False
    if index == 0:
        next_ts = _segment_seconds(segments[index + 1])
        return next_ts is not None and (next_ts - ts) > threshold
    if index == n - 1:
        prev_ts = _segment_seconds(segments[index - 1])
        return prev_ts is not None and (ts - prev_ts) > threshold
    prev_ts = _segment_seconds(segments[index - 1])
    next_ts = _segment_seconds(segments[index + 1])
    if prev_ts is None or next_ts is None:
        return False
    return (ts - prev_ts) > threshold and (next_ts - ts) > threshold
def _find_timestamp_matches(segments, timestamp):
    return [i for i, s in enumerate(segments) if s.get("timestamp") == timestamp]
def find_anchors_between_transcripts(segments_a, segments_b, timestamp_threshold=1, sim_ratio_threshold=0.75, normalization_policy=None):
    """
    Find anchor pairs between two transcript segment lists.

    :return: list of {'a_index': int, 'b_index': int}
    """
    from core.transcript_eval import calc_lev_dist_ratio, normalize_dialogue

    ts_counts_a = {}
    for seg in segments_a:
        ts = seg.get("timestamp")
        ts_counts_a[ts] = ts_counts_a.get(ts, 0) + 1
    anchors = []
    for ai, seg_a in enumerate(segments_a):
        if ts_counts_a.get(seg_a.get("timestamp"), 0) != 1:
            continue
        if not _timestamp_gap_ok(segments_a, ai, timestamp_threshold):
            continue
        ts = seg_a.get("timestamp")
        b_matches = _find_timestamp_matches(segments_b, ts)
        if len(b_matches) != 1:
            continue
        bi = b_matches[0]
        norm_a = normalize_dialogue(seg_a.get("dialogue"), normalization_policy)
        norm_b = normalize_dialogue(segments_b[bi].get("dialogue"), normalization_policy)
        if norm_a == norm_b:
            anchors.append({"a_index": ai, "b_index": bi})
            continue
        ratio = calc_lev_dist_ratio(norm_a, norm_b)
        if ratio >= sim_ratio_threshold:
            anchors.append({"a_index": ai, "b_index": bi})
    return anchors
def find_islands_from_anchors(segments_a, segments_b, anchors, max_island_segments=20):
    """
    Build island dicts between consecutive anchors.

    :return: list of {'a_start', 'a_end', 'b_start', 'b_end', 'segments_a', 'segments_b'}
    """
    anchors = sorted(anchors, key=lambda x: x["a_index"])
    islands = []
    bounds = [{"a_index": -1, "b_index": -1}] + anchors + [
        {"a_index": len(segments_a), "b_index": len(segments_b)}
    ]
    for i in range(len(bounds) - 1):
        a_start = bounds[i]["a_index"] + 1
        a_end = bounds[i + 1]["a_index"]
        b_start = bounds[i]["b_index"] + 1
        b_end = bounds[i + 1]["b_index"]
        if a_start >= a_end and b_start >= b_end:
            continue
        slice_a = segments_a[a_start:a_end]
        slice_b = segments_b[b_start:b_end]
        max_len = max(len(slice_a), len(slice_b))
        if max_len == 0:
            continue
        if max_len <= max_island_segments:
            islands.append({
                "a_start": a_start, "a_end": a_end,
                "b_start": b_start, "b_end": b_end,
                "segments_a": slice_a, "segments_b": slice_b,
            })
        else:
            # Non-overlapping windows: an overlapping step duplicates every segment
            # of a large island into two islands, doubling dialogue on reassembly.
            step = max(1, max_island_segments)
            for j in range(0, max_len, step):
                sub_a = slice_a[j:j + max_island_segments]
                sub_b = slice_b[j:j + max_island_segments]
                if sub_a or sub_b:
                    islands.append({
                        "a_start": a_start + j,
                        "a_end": min(a_start + j + len(sub_a), a_end),
                        "b_start": b_start + j,
                        "b_end": min(b_start + j + len(sub_b), b_end),
                        "segments_a": sub_a,
                        "segments_b": sub_b,
                    })
    return islands
def reassemble_dual_segments(segments_a, anchors, island_results):
    """
    Reassemble full segment list from anchors and per-island consensus segments.
    """
    anchors = sorted(anchors, key=lambda x: x["a_index"])
    islands_sorted = sorted(island_results, key=lambda x: x.get("a_start", 0))
    result = []
    prev_end = 0
    island_i = 0
    for anch in anchors:
        ai = anch["a_index"]
        while island_i < len(islands_sorted) and islands_sorted[island_i]["a_start"] < ai:
            isl = islands_sorted[island_i]
            if isl.get("consensus"):
                result.extend(isl["consensus"])
            else:
                result.extend(segments_a[isl["a_start"]:isl["a_end"]])
            island_i += 1
        if ai >= prev_end:
            result.append(copy.deepcopy(segments_a[ai]))
            prev_end = ai + 1
    while island_i < len(islands_sorted):
        isl = islands_sorted[island_i]
        if isl.get("consensus"):
            result.extend(isl["consensus"])
        else:
            result.extend(segments_a[isl["a_start"]:isl["a_end"]])
        island_i += 1
    if not anchors and not islands_sorted:
        return copy.deepcopy(segments_a)
    return result


### Word-anchored dual chunking (dual merge v2)
# Replaces timestamp-based anchor/island pairing for the LLM dual path. Two different
# ASR models almost never emit identical timestamps, so timestamp anchors are too sparse
# on real pairs and islands degenerate into index-parallel slices covering different
# audio. Word-level anchoring instead finds runs of matching words, and cuts chunks only
# where BOTH transcripts start a segment at the same matched word — so every chunk pairs
# the same underlying speech and chunk seams sit on segmentation both sources agree on.
WORD_NORM_STRIP = re.compile(r"[^a-z0-9']")
def build_word_stream(segments):
    """
    Flatten segments into a word stream for alignment.

    Each entry: {'norm', 'orig', 'seg_index', 'seg_start'}. Tokens that normalize to
    nothing (pure punctuation) are skipped, so joining 'orig' loses them — display only.
    """
    stream = []
    for si, seg in enumerate(segments):
        first = True
        for tok in (seg.get("dialogue") or "").split():
            norm = WORD_NORM_STRIP.sub("", tok.lower())
            if not norm:
                continue
            stream.append({"norm": norm, "orig": tok, "seg_index": si, "seg_start": first})
            first = False
    return stream
def find_word_match_blocks(stream_a, stream_b, min_words=6):
    """Matching normalized-word runs between two streams — the confident dual anchors."""
    import difflib

    matcher = difflib.SequenceMatcher(
        None, [w["norm"] for w in stream_a], [w["norm"] for w in stream_b], autojunk=False)
    return [b for b in matcher.get_matching_blocks() if b.size >= min_words]
def find_dual_cut_points(stream_a, stream_b, blocks, edge_words=3):
    """
    Chunk boundaries: matched word positions where BOTH transcripts start a segment,
    with >= edge_words matched words on each side inside the same anchor block.

    :return: list of {'a_word', 'b_word', 'a_seg', 'b_seg'}, monotonic in both transcripts
    """
    cuts = []
    for block in blocks:
        for k in range(edge_words, block.size - edge_words + 1):
            pa = block.a + k
            pb = block.b + k
            if pa >= len(stream_a) or pb >= len(stream_b):
                continue
            if not (stream_a[pa]["seg_start"] and stream_b[pb]["seg_start"]):
                continue
            cut = {"a_word": pa, "b_word": pb,
                   "a_seg": stream_a[pa]["seg_index"], "b_seg": stream_b[pb]["seg_index"]}
            if cuts and (cut["a_seg"] <= cuts[-1]["a_seg"] or cut["b_seg"] <= cuts[-1]["b_seg"]):
                continue
            cuts.append(cut)
    return cuts
def _positions_agree(slice_a, slice_b, sim_threshold):
    """True when every aligned segment pair is textually similar (wording-only diffs)."""
    from core.transcript_eval import calc_lev_dist_ratio, normalize_dialogue

    for seg_a, seg_b in zip(slice_a, slice_b):
        norm_a = normalize_dialogue(seg_a.get("dialogue"), None)
        norm_b = normalize_dialogue(seg_b.get("dialogue"), None)
        if not norm_a and not norm_b:
            continue
        if calc_lev_dist_ratio(norm_a, norm_b) < sim_threshold:
            return False
    return True
def build_dual_chunks(segments_a, segments_b, min_anchor_words=6, edge_words=3, match_sim_threshold=0.98, position_sim_threshold=0.8):
    """
    Partition two transcripts of the same audio into aligned chunk pairs.

    Chunks tile both transcripts completely: chunk i covers segments_a[a_start:a_end]
    and segments_b[b_start:b_end] with no gaps or overlaps. kind 'match' = the sides
    agree; 'wording' = same turn structure, ASR wording differs (both pass through);
    'diff' = segmentation structure disagrees (arbitration candidates).
    :return: list of chunk dicts
    """
    from core.transcript_eval import calc_lev_dist_ratio, normalize_dialogue

    stream_a = build_word_stream(segments_a)
    stream_b = build_word_stream(segments_b)
    blocks = find_word_match_blocks(stream_a, stream_b, min_words=min_anchor_words)
    cuts = find_dual_cut_points(stream_a, stream_b, blocks, edge_words=edge_words)
    bounds = [{"a_seg": 0, "b_seg": 0}] + cuts + [{"a_seg": len(segments_a), "b_seg": len(segments_b)}]
    chunks = []
    for i in range(len(bounds) - 1):
        a_start, b_start = bounds[i]["a_seg"], bounds[i]["b_seg"]
        a_end, b_end = bounds[i + 1]["a_seg"], bounds[i + 1]["b_seg"]
        if a_start >= a_end and b_start >= b_end:
            continue
        slice_a = segments_a[a_start:a_end]
        slice_b = segments_b[b_start:b_end]
        norm_a = " ".join(normalize_dialogue(seg.get("dialogue"), None) for seg in slice_a).strip()
        norm_b = " ".join(normalize_dialogue(seg.get("dialogue"), None) for seg in slice_b).strip()
        similarity = calc_lev_dist_ratio(norm_a, norm_b) if (norm_a or norm_b) else 1.0
        if similarity >= match_sim_threshold and len(slice_a) == len(slice_b):
            kind = "match"
        elif len(slice_a) == len(slice_b) and _positions_agree(slice_a, slice_b, position_sim_threshold):
            # Same turn structure, only ASR wording differs — segmentation needs no
            # arbitration, so the base side passes through and keeps its wording.
            kind = "wording"
        else:
            kind = "diff"
        chunks.append({
            "a_start": a_start, "a_end": a_end, "b_start": b_start, "b_end": b_end,
            "segments_a": slice_a, "segments_b": slice_b,
            "kind": kind, "similarity": round(similarity, 4),
            "a_word_count": sum(len((s.get("dialogue") or "").split()) for s in slice_a),
            "b_word_count": sum(len((s.get("dialogue") or "").split()) for s in slice_b),
        })
    return chunks
def subdivide_dual_diff_chunk(chunk, max_words=160, max_segments=6, internal_min_anchor_words=3, internal_edge_words=1, match_sim_threshold=0.98, position_sim_threshold=0.8):
    """
    Split an oversized diff chunk only at relaxed, aligned dual segment starts.

    If no safe internal cut exists, return the original chunk unchanged.
    """
    oversized = (
        max(chunk.get("a_word_count", 0), chunk.get("b_word_count", 0)) > max_words
        or max(len(chunk.get("segments_a", [])), len(chunk.get("segments_b", []))) > max_segments
    )
    if chunk.get("kind") != "diff" or not oversized:
        return [chunk]
    local_chunks = build_dual_chunks(
        chunk["segments_a"], chunk["segments_b"],
        min_anchor_words=internal_min_anchor_words,
        edge_words=internal_edge_words,
        match_sim_threshold=match_sim_threshold,
        position_sim_threshold=position_sim_threshold,
    )
    if len(local_chunks) <= 1:
        return [chunk]
    units = []
    for local in local_chunks:
        unit = copy.deepcopy(local)
        unit["a_start"] += chunk["a_start"]
        unit["a_end"] += chunk["a_start"]
        unit["b_start"] += chunk["b_start"]
        unit["b_end"] += chunk["b_start"]
        units.append(unit)
    return units
def build_dual_decision_chunks(segments_a, segments_b, min_anchor_words=6, edge_words=3, decision_max_words=160, decision_max_segments=6, internal_min_anchor_words=3, internal_edge_words=1, match_sim_threshold=0.98, position_sim_threshold=0.8):
    """Build top-level chunks, then safely subdivide oversized structural differences."""
    parent_chunks = build_dual_chunks(
        segments_a, segments_b,
        min_anchor_words=min_anchor_words,
        edge_words=edge_words,
        match_sim_threshold=match_sim_threshold,
        position_sim_threshold=position_sim_threshold,
    )
    decision_chunks = []
    for parent_id, parent in enumerate(parent_chunks):
        units = subdivide_dual_diff_chunk(
            parent,
            max_words=decision_max_words,
            max_segments=decision_max_segments,
            internal_min_anchor_words=internal_min_anchor_words,
            internal_edge_words=internal_edge_words,
            match_sim_threshold=match_sim_threshold,
            position_sim_threshold=position_sim_threshold,
        )
        for sub_id, unit in enumerate(units):
            item = copy.deepcopy(unit)
            item["parent_chunk_id"] = parent_id
            item["decision_sub_id"] = sub_id
            decision_chunks.append(item)
    return decision_chunks
def project_positions_to_ref(stream_base, stream_ref, base_positions):
    """
    Map base-transcript word positions onto reference word positions via word alignment.

    Positions outside any matching block snap to the start of the next matched region;
    output is forced monotonic so ref slices tile the reference without overlap.
    """
    import difflib

    matcher = difflib.SequenceMatcher(
        None, [w["norm"] for w in stream_base], [w["norm"] for w in stream_ref], autojunk=False)
    blocks = matcher.get_matching_blocks()
    ref_positions = []
    prev = 0
    for pos in base_positions:
        ref_pos = None
        for block in blocks:
            if block.a <= pos < block.a + block.size:
                ref_pos = block.b + (pos - block.a)
                break
            if block.a > pos:
                ref_pos = block.b
                break
        if ref_pos is None:
            ref_pos = len(stream_ref)
        ref_pos = max(ref_pos, prev)
        ref_positions.append(ref_pos)
        prev = ref_pos
    return ref_positions
def render_stream_slice_segments(stream, segments, lo, hi):
    """Render a word range of a transcript as plain segment dicts (edges may be partial segments)."""
    out = []
    current_index = None
    for w in stream[lo:hi]:
        if current_index != w["seg_index"]:
            current_index = w["seg_index"]
            seg = segments[current_index]
            out.append({
                "speaker": seg.get("speaker_name") or seg.get("speaker_full") or "Speaker 0",
                "timestamp": seg.get("timestamp"),
                "words": [],
            })
        out[-1]["words"].append(w["orig"])
    for seg in out:
        seg["dialogue"] = " ".join(seg.pop("words"))
    return out
def _chunk_start_word_position(stream, seg_index):
    """First stream position at or after the given segment index."""
    for pos, w in enumerate(stream):
        if w["seg_index"] >= seg_index:
            return pos
    return len(stream)
def _segments_public(segments):
    """Reduce internal segment dicts to the public speaker/timestamp/dialogue shape."""
    return [{
        "speaker": seg.get("speaker_name") or seg.get("speaker_full") or "Speaker 0",
        "timestamp": seg.get("timestamp"),
        "dialogue": seg.get("dialogue") or "",
    } for seg in segments]
def extract_dual_chunk_triples(path_a, path_b, ref_path=None, profile=None, out_path=None, min_anchor_words=None, edge_words=None, verbose=False):
    """
    Write the word-anchored chunk decomposition of a dual pair as a JSON list of dicts,
    optionally with the human reference projected onto the same chunks — the prompt
    exploration artifact: each chunk pairs raw A, raw B, and reference for the same speech.

    :return: (out_path, summary dict)
    """
    config = load_denovo_pipeline_config()
    policy = resolve_profile_policy(profile)
    min_anchor_words = min_anchor_words or config.get("dual_min_anchor_words", 6)
    edge_words = edge_words or config.get("dual_anchor_edge_words", 3)
    segs_a = load_segments_from_md(path_a)
    segs_b = load_segments_from_md(path_b)
    cleaned_a, _ = apply_deterministic_cleanup(segs_a, policy=policy, verbose=verbose)
    cleaned_b, _ = apply_deterministic_cleanup(segs_b, policy=policy, verbose=verbose)
    chunks = build_dual_decision_chunks(
        cleaned_a, cleaned_b,
        min_anchor_words=min_anchor_words, edge_words=edge_words,
        decision_max_words=config.get("dual_decision_max_words", 160),
        decision_max_segments=config.get("dual_decision_max_segments", 6),
        internal_min_anchor_words=config.get("dual_internal_min_anchor_words", 3),
        internal_edge_words=config.get("dual_internal_edge_words", 1),
        match_sim_threshold=config.get("dual_match_sim_threshold", 0.98),
        position_sim_threshold=config.get("dual_position_sim_threshold", 0.8),
    )
    ref_slices = None
    if ref_path:
        stream_a = build_word_stream(cleaned_a)
        ref_segments = load_segments_from_md(ref_path)
        stream_ref = build_word_stream(ref_segments)
        starts = [_chunk_start_word_position(stream_a, c["a_start"]) for c in chunks]
        ref_starts = project_positions_to_ref(stream_a, stream_ref, starts)
        ref_bounds = ref_starts + [len(stream_ref)]
        ref_slices = [
            render_stream_slice_segments(stream_ref, ref_segments, ref_bounds[i], ref_bounds[i + 1])
            for i in range(len(chunks))
        ]
    records = []
    for i, chunk in enumerate(chunks):
        record = {
            "chunk_id": i,
            "parent_chunk_id": chunk["parent_chunk_id"],
            "decision_sub_id": chunk["decision_sub_id"],
            "kind": chunk["kind"],
            "similarity": chunk["similarity"],
            "a_word_count": chunk["a_word_count"],
            "b_word_count": chunk["b_word_count"],
            "a": {"seg_range": [chunk["a_start"], chunk["a_end"]], "segments": _segments_public(chunk["segments_a"])},
            "b": {"seg_range": [chunk["b_start"], chunk["b_end"]], "segments": _segments_public(chunk["segments_b"])},
            "ref": {"segments": ref_slices[i]} if ref_slices is not None else None,
        }
        records.append(record)
    if out_path is None:
        repo_root = find_denovo_repo_root() or os.getcwd()
        stem = os.path.basename(path_a)
        for suf in config.get("dual_source_suffixes", ["_nova2gen", "_dgwhspm"]):
            stem = stem.replace(suf + ".md", "").replace(suf, "")
        stem = stem.replace(".md", "")
        out_dir = os.path.join(repo_root, "data", "stellar-eval", "dual-chunks")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{stem}_dual-chunks.json")
    payload = {
        "source_a": os.path.basename(path_a),
        "source_b": os.path.basename(path_b),
        "reference": os.path.basename(ref_path) if ref_path else None,
        "profile": profile if isinstance(profile, str) else None,
        "min_anchor_words": min_anchor_words,
        "edge_words": edge_words,
        "decision_max_words": config.get("dual_decision_max_words", 160),
        "decision_max_segments": config.get("dual_decision_max_segments", 6),
        "internal_min_anchor_words": config.get("dual_internal_min_anchor_words", 3),
        "internal_edge_words": config.get("dual_internal_edge_words", 1),
        "chunks": records,
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    diff_chunks = [c for c in chunks if c["kind"] == "diff"]
    summary = {
        "out_path": out_path,
        "chunk_count": len(chunks),
        "parent_chunk_count": len({c["parent_chunk_id"] for c in chunks}),
        "match_chunk_count": sum(1 for c in chunks if c["kind"] == "match"),
        "wording_chunk_count": sum(1 for c in chunks if c["kind"] == "wording"),
        "diff_chunk_count": len(diff_chunks),
        "diff_word_count_a": sum(c["a_word_count"] for c in diff_chunks),
        "total_word_count_a": sum(c["a_word_count"] for c in chunks),
    }
    return out_path, summary


### Dual deterministic arbitration
def arbitrate_island_deterministic(segments_a, segments_b, prefer="a"):
    """Simple rule-based island arbitration — prefer longer normalized dialogue per position."""
    from core.transcript_eval import normalize_dialogue

    policy = resolve_profile_policy(None)
    if len(segments_a) >= len(segments_b):
        primary, secondary = segments_a, segments_b
    else:
        primary, secondary = segments_b, segments_a
        prefer = "b" if prefer == "a" else "a"
    result = []
    for i, seg in enumerate(primary):
        chosen = copy.deepcopy(seg)
        if i < len(secondary):
            alt = secondary[i]
            norm_p = normalize_dialogue(seg.get("dialogue"), policy)
            norm_s = normalize_dialogue(alt.get("dialogue"), policy)
            if len(norm_s) > len(norm_p) * 1.2:
                chosen = copy.deepcopy(alt)
        result.append(chosen)
    return result
def merge_dual_deterministic(path_a, path_b, profile=None, verbose=False):
    """
    Deterministic dual-transcript merge via anchor/island detection.

    :return: path to written draft file
    """
    config = load_denovo_pipeline_config()
    suffix = draft_suffix_for("dual", "deterministic", config)
    policy = resolve_profile_policy(profile)
    segs_a = load_segments_from_md(path_a)
    segs_b = load_segments_from_md(path_b)
    cleaned_a, _ = apply_deterministic_cleanup(segs_a, policy=policy, verbose=verbose)
    cleaned_b, _ = apply_deterministic_cleanup(segs_b, policy=policy, verbose=verbose)
    anchors = find_anchors_between_transcripts(
        cleaned_a, cleaned_b,
        timestamp_threshold=config.get("anchor_timestamp_threshold", 1),
        sim_ratio_threshold=config.get("anchor_sim_ratio_threshold", 0.75),
        normalization_policy=policy,
    )
    islands = find_islands_from_anchors(
        cleaned_a, cleaned_b, anchors,
        max_island_segments=config.get("max_island_segments", 20),
    )
    island_results = []
    for isl in islands:
        consensus = arbitrate_island_deterministic(isl["segments_a"], isl["segments_b"])
        island_results.append({**isl, "consensus": consensus})
    merged = reassemble_dual_segments(cleaned_a, anchors, island_results)
    metadata_extra = {
        "denovo method": "deterministic",
        "denovo mode": "dual",
        "denovo sources": f"{os.path.basename(path_a)} + {os.path.basename(path_b)}",
        "denovo anchor count": str(len(anchors)),
    }
    return write_draft_md(merged, path_a, suffix, metadata_extra=metadata_extra)


### LLM cleanup
def create_draft_llm(raw_md_path, profile=None, model_tier=None, verbose=False):
    """
    LLM single-transcript cleanup: deterministic pre-pass then chunked LLM repair.

    :return: path to written draft file
    """
    from core.llm import (
        chunk_segments_for_llm,
        llm_correct_transcript_segments,
    )

    config = load_denovo_pipeline_config()
    suffix = draft_suffix_for("single", "llm", config)
    policy = resolve_profile_policy(profile)
    model, provider = resolve_denovo_model(model_tier, config)
    single_prompt, _ = resolve_denovo_prompts(config)
    prepped_path = create_draft_deterministic(raw_md_path, profile=profile, verbose=verbose)
    segments = load_segments_from_md(prepped_path)
    chunks = chunk_segments_for_llm(
        segments,
        token_cap=config.get("chunk_token_cap", 1000),
        adjacent_context=config.get("adjacent_context_segments", 2),
    )
    corrected = []
    for chunk in chunks:
        result = llm_correct_transcript_segments(
            chunk["segments"],
            single_prompt,
            model,
            provider=provider,
            context_before=chunk.get("context_before"),
            context_after=chunk.get("context_after"),
            max_retries=config.get("llm_max_retries", 3),
            verbose=verbose,
        )
        if result is None:
            corrected.extend(chunk["segments"])
        else:
            result, stripped = strip_context_echo(result, chunk.get("context_before"), chunk.get("context_after"))
            if stripped and verbose:
                print(f"  stripped {stripped} context-echo segment(s) from LLM output")
            corrected.extend(llm_segments_to_internal(result, source_segments=chunk["segments"]))
    metadata_extra = {
        "denovo method": "llm",
        "denovo mode": "single",
        "denovo model": model,
        "denovo prompts version": config.get("prompts_version", "denovo-v1"),
    }
    return write_draft_md(corrected, raw_md_path, suffix, metadata_extra=metadata_extra, overwrite="no")
def merge_dual_llm(path_a, path_b, profile=None, model_tier=None, provider=None, verbose=False, return_summary=False):
    """
    LLM dual-transcript merge via word-anchored chunking.

    Both inputs get deterministic cleanup, then the pair is partitioned into aligned
    chunks bounded by dual segment-start word anchors. Matched chunks pass through from
    the base side verbatim. For disagreement chunks, denovo-v4 asks the LLM only to
    select A or B, then copies that source chunk verbatim; it cannot generate transcript
    text or invent boundaries. Invalid selections fall back to the configured base side.
    :return: path to written draft file, or (path, cost_summary) when return_summary=True
    """
    from core.llm import LlmUsageAccumulator, llm_arbitrate_dual_chunk, llm_select_dual_chunk_side

    config = load_denovo_pipeline_config()
    suffix = draft_suffix_for("dual", "llm", config)
    _, dual_prompt = resolve_denovo_prompts(config)
    policy = resolve_profile_policy(profile)
    model, provider = resolve_denovo_model(model_tier, config, provider=provider)
    usage_acc = LlmUsageAccumulator(model)
    segs_a = load_segments_from_md(path_a)
    segs_b = load_segments_from_md(path_b)
    cleaned_a, _ = apply_deterministic_cleanup(segs_a, policy=policy, verbose=verbose)
    cleaned_b, _ = apply_deterministic_cleanup(segs_b, policy=policy, verbose=verbose)
    chunks = build_dual_decision_chunks(
        cleaned_a, cleaned_b,
        min_anchor_words=config.get("dual_min_anchor_words", 6),
        edge_words=config.get("dual_anchor_edge_words", 3),
        decision_max_words=config.get("dual_decision_max_words", 160),
        decision_max_segments=config.get("dual_decision_max_segments", 6),
        internal_min_anchor_words=config.get("dual_internal_min_anchor_words", 3),
        internal_edge_words=config.get("dual_internal_edge_words", 1),
        match_sim_threshold=config.get("dual_match_sim_threshold", 0.98),
        position_sim_threshold=config.get("dual_position_sim_threshold", 0.8),
    )
    base_side = config.get("dual_base_side", "b")
    base_cleaned = cleaned_b if base_side == "b" else cleaned_a
    base_seg_key = "segments_" + base_side
    base_start_key, base_end_key = base_side + "_start", base_side + "_end"
    selector_only = config.get("prompts_version") == "denovo-v4"
    context_n = config.get("adjacent_context_segments", 2)
    merged = []
    diff_count = 0
    fallback_count = 0
    for chunk in chunks:
        if chunk["kind"] != "diff":
            merged.extend(copy.deepcopy(chunk[base_seg_key]))
            continue
        diff_count += 1
        context_before = base_cleaned[max(0, chunk[base_start_key] - context_n):chunk[base_start_key]]
        context_after = base_cleaned[chunk[base_end_key]:chunk[base_end_key] + context_n]
        if selector_only:
            selected_side = llm_select_dual_chunk_side(
                chunk["segments_a"], chunk["segments_b"],
                dual_prompt, model, provider=provider,
                context_before=context_before, context_after=context_after,
                max_retries=config.get("llm_max_retries", 3),
                verbose=verbose,
                usage_accumulator=usage_acc,
            )
            if selected_side is None:
                usage_acc.add_fallback()
                fallback_count += 1
                selected_side = base_side
            merged.extend(copy.deepcopy(chunk["segments_" + selected_side]))
        else:
            result = llm_arbitrate_dual_chunk(
                chunk["segments_a"], chunk["segments_b"],
                dual_prompt, model, provider=provider,
                context_before=context_before, context_after=context_after,
                max_retries=config.get("llm_max_retries", 3),
                conservation_min=config.get("dual_conservation_min", 0.9),
                verbose=verbose,
                usage_accumulator=usage_acc,
            )
            if result is None:
                usage_acc.add_fallback()
                fallback_count += 1
                merged.extend(copy.deepcopy(chunk[base_seg_key]))
            else:
                merged.extend(llm_segments_to_internal(result, source_segments=chunk["segments_a"] + chunk["segments_b"]))
    cost_summary = usage_acc.summary()
    cost_summary["chunk_count"] = len(chunks)
    cost_summary["parent_chunk_count"] = len({chunk["parent_chunk_id"] for chunk in chunks})
    cost_summary["diff_chunk_count"] = diff_count
    cost_summary["provider"] = provider
    metadata_extra = {
        "denovo method": "llm",
        "denovo mode": "dual",
        "denovo model": model,
        "denovo prompts version": config.get("prompts_version", "denovo-v1"),
        "denovo sources": f"{os.path.basename(path_a)} + {os.path.basename(path_b)}",
        "denovo base side": base_side,
        "denovo dual strategy": "verbatim-side-selector" if selector_only else "generated-consensus",
        "denovo parent chunk count": str(cost_summary["parent_chunk_count"]),
        "denovo chunk count": str(len(chunks)),
        "denovo diff chunk count": str(diff_count),
        "denovo llm api calls": str(cost_summary.get("api_calls", 0)),
        "denovo input tokens": str(cost_summary.get("input_tokens", 0)),
        "denovo output tokens": str(cost_summary.get("output_tokens", 0)),
        "denovo cost usd": f"{cost_summary.get('total_cost_usd', 0):.4f}",
    }
    out_path = write_draft_md(merged, path_a, suffix, metadata_extra=metadata_extra)
    if verbose:
        print(f"merge_dual_llm cost: ${cost_summary.get('total_cost_usd', 0):.4f} "
              f"({cost_summary.get('input_tokens', 0)} in / {cost_summary.get('output_tokens', 0)} out tokens, "
              f"{diff_count}/{len(chunks)} diff chunks, {fallback_count} fallbacks)")
    if return_summary:
        return out_path, cost_summary
    return out_path


### End-to-end entry point
def process_denovo(audio_or_link, mode="single", method="deterministic", output_dir="data/audio_inbox", model_tier=None, profile=None, title=None, verbose=False):
    """
    End-to-end: ingest audio/link → Deepgram → raw md(s) → cleanup draft.

    :param mode: 'single' or 'dual'
    :param method: 'deterministic' or 'llm'
    :return: path to draft md (dual: path based on primary raw)
    """
    from core.transcribe import (
        DG_MODEL_SUFFIX_MAP,
        create_transcript_md_from_json,
        process_deepgram_transcription_sync,
        transcribe_deepgram_sync,
    )

    if mode not in ("single", "dual"):
        raise ValueError("mode must be 'single' or 'dual'")
    if method not in ("deterministic", "llm"):
        raise ValueError("method must be 'deterministic' or 'llm'")
    is_link = audio_or_link.startswith("http://") or audio_or_link.startswith("https://")
    if is_link:
        if not title:
            title = "denovo_smoke"
        if mode == "single":
            raw_path = process_deepgram_transcription_sync(title, audio_or_link, "nova-2-general", output_dir=output_dir)
            if raw_path is None:
                raise RuntimeError("Deepgram transcription failed")
            if method == "deterministic":
                return create_draft_deterministic(raw_path, profile=profile, verbose=verbose)
            return create_draft_llm(raw_path, profile=profile, model_tier=model_tier, verbose=verbose)
        raw_a = process_deepgram_transcription_sync(title, audio_or_link, "nova-2-general", output_dir=output_dir)
        raw_b = process_deepgram_transcription_sync(title + "_b", audio_or_link, "whisper-medium", output_dir=output_dir)
        if raw_a is None or raw_b is None:
            raise RuntimeError("Deepgram dual transcription failed")
        if method == "deterministic":
            return merge_dual_deterministic(raw_a, raw_b, profile=profile, verbose=verbose)
        return merge_dual_llm(raw_a, raw_b, profile=profile, model_tier=model_tier, verbose=verbose)
    if not os.path.isfile(audio_or_link):
        raise ValueError(f"Not a file or URL: {audio_or_link}")
    if mode == "single":
        json_path = transcribe_deepgram_sync(audio_or_link, "nova-2-general")
        raw_path = create_transcript_md_from_json(json_path)
        if method == "deterministic":
            return create_draft_deterministic(raw_path, profile=profile, verbose=verbose)
        return create_draft_llm(raw_path, profile=profile, model_tier=model_tier, verbose=verbose)
    json_a = transcribe_deepgram_sync(audio_or_link, "nova-2-general")
    json_b = transcribe_deepgram_sync(audio_or_link, "whisper-medium")
    raw_a = create_transcript_md_from_json(json_a)
    raw_b = create_transcript_md_from_json(json_b)
    if method == "deterministic":
        return merge_dual_deterministic(raw_a, raw_b, profile=profile, verbose=verbose)
    return merge_dual_llm(raw_a, raw_b, profile=profile, model_tier=model_tier, verbose=verbose)

# END OF FILE core/denovo.py
