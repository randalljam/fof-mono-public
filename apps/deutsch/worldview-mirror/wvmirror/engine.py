"""Conversation engine: one turn = route+extract (structured LLM call) -> graph
grounding -> mirrored reply (chat LLM call). The reply cites graph node ids in
square brackets; the caller renders them as links. All OpenAI traffic goes through
core/llm.py (provider-swappable); core.llm is imported lazily so this module loads
without API keys (tests stub `_chat`)."""
import json
import re
from . import atlas as atlas_mod
from . import compare
from . import config
from . import graph_access
from . import profile_store

SAFETY_PREAMBLE = (
    "You are Worldview Mirror, a self-reflection tool. You are NOT a therapist or medical "
    "professional and must never present yourself as one. If the person expresses crisis-level "
    "distress or intent to harm themselves or others, gently urge them to contact local emergency "
    "services or a crisis line (in the US: call or text 988) and keep your reply brief. "
    "Everything you infer about the person is shown to them openly — never analyze covertly.")
MIRROR_DUTY = (
    "Your job is to MIRROR, not preach: reflect the person's own worldview back to them next to the "
    "lens worldview. When they express a belief, compare it with the lens position and say plainly "
    "where they agree, where they diverge, and what the lens's best counter-argument or supporting "
    "argument is. Ground every claim about the lens worldview in the provided source material and cite "
    "node ids in square brackets, e.g. [qa:2013-06-25_nautilus-why-its-good-to-be-wrong:000]. Quote "
    "verbatim only text that appears in the source material. If the sources don't cover the topic, say "
    "the lens has no recorded position on it — never invent one. Always stay user-directed: follow the "
    "problems the person says they are working on.")
CITE_RE = re.compile(r"\[((?:qa|concept|chapter|claim|excerpt|category|topic|work|book):[^\]\s]+)\]")

### LLM plumbing
def _chat(messages, model=None, temperature=None):
    """One OpenAI chat call via core.llm; returns the reply text. Lazy import keeps
    this module importable without API keys; tests monkeypatch this function.
    Uses the raw-requests function (not *_sdk): the installed openai SDK is
    incompatible with httpx>=0.28 in the shared venv as of 2026-07."""
    from core import llm
    response = llm.openai_chat_completion_request(messages, model=model or config.default_model(), temperature=temperature)
    if isinstance(response, Exception):
        raise RuntimeError("LLM call failed: %s" % response)
    data = response.json()
    if "error" in data:
        raise RuntimeError("LLM call failed: %s" % data["error"].get("message", data["error"]))
    return data["choices"][0]["message"]["content"]
def _json_from(text):
    """Parse JSON out of an LLM reply, tolerating code fences and prose margins."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return json.loads(text)

### Routing + belief extraction (one structured call)
def _axes_brief(axes):
    """Compact axis list for prompts."""
    return "\n".join("%s | %s | -2=%s ... +2=%s" % (a["id"], a["label"], a["pole_neg"]["label"], a["pole_pos"]["label"]) for a in axes)
def route_and_extract(user_message, catalog, axes, model=None):
    """Classify one user message -> {topics, categories, concept_needles, beliefs}.
    Topics/categories are ids from the graph catalog; beliefs map onto taxonomy axes."""
    topic_labels = ", ".join(t["label"] for t in catalog["topics"])
    category_labels = ", ".join(c["label"] for c in catalog["categories"])
    prompt = (
        "You classify a message from someone exploring their worldview.\n\n"
        "MESSAGE:\n%s\n\n"
        "1. Pick up to 5 TOPICS from this list (exact labels, most relevant first):\n%s\n\n"
        "2. Pick up to 2 CATEGORIES from this list (exact labels):\n%s\n\n"
        "3. List up to 3 CONCEPT_NEEDLES: short book-term keywords worth looking up (e.g. 'optimism', 'wealth').\n\n"
        "4. Extract BELIEFS the person actually asserts about the world or themselves (not questions, not hypotheticals). "
        "For each: belief (one sentence, third person), axis (an axis id below or null if none fits), "
        "position (-2.0 to +2.0 on that axis), confidence (0.0-1.0 that they hold it), quote (their words, verbatim).\n"
        "AXES:\n%s\n\n"
        "Return ONLY JSON: {\"topics\": [..], \"categories\": [..], \"concept_needles\": [..], "
        "\"beliefs\": [{\"belief\":..., \"axis\":..., \"position\":..., \"confidence\":..., \"quote\":...}]}"
    ) % (user_message, topic_labels, category_labels, _axes_brief(axes))
    data = _json_from(_chat([{"role": "user", "content": prompt}], model=model))
    topic_ids = {t["label"]: t["id"] for t in catalog["topics"]}
    category_ids = {c["label"]: c["id"] for c in catalog["categories"]}
    axis_ids = {a["id"] for a in axes}
    beliefs = []
    for b in data.get("beliefs", []):
        axis = b.get("axis") if b.get("axis") in axis_ids else None
        try:
            position = max(-2.0, min(2.0, float(b.get("position", 0))))
            confidence = max(0.0, min(1.0, float(b.get("confidence", 0.5))))
        except (TypeError, ValueError):
            continue
        if b.get("belief"):
            beliefs.append({"belief": b["belief"], "axis": axis, "position": position,
                            "confidence": confidence, "quote": b.get("quote", "")})
    return {"topics": [topic_ids[l] for l in data.get("topics", []) if l in topic_ids],
            "categories": [category_ids[l] for l in data.get("categories", []) if l in category_ids],
            "concept_needles": [n for n in data.get("concept_needles", []) if isinstance(n, str)][:3],
            "beliefs": beliefs}

### Prompt assembly
def _grounding_text(grounding):
    """Render the grounding package as prompt source material."""
    parts = []
    for item in grounding["qa"]:
        parts.append("SOURCE %s (from: %s, stars: %d)\nQ: %s\nA: %s" % (
            item["id"], item["work_label"], item["stars"], item["question"],
            item["answer"] or "(verbatim answer unavailable — corpus not fetched; question and metadata only)"))
    for claim in grounding["claims"]:
        text = "SOURCE %s\nCLAIM: %s" % (claim["id"], claim["claim"])
        for ex in claim["excerpts"]:
            text += "\nEXCERPT %s: %s" % (ex["id"], ex["text"])
        parts.append(text)
    for concept in grounding["concepts"]:
        parts.append("SOURCE %s\nTERM: %s\nDEFINITION: %s" % (concept["id"], concept["label"], concept["definition"]))
    return "\n\n".join(parts) if parts else "(no source material matched this message)"
def _lens_text(lens_profile, axes_by_id):
    """Render the lens profile's positions for the system prompt."""
    lines = ["LENS WORLDVIEW: %s" % lens_profile["label"], lens_profile["summary"], ""]
    for pos in lens_profile.get("positions", []):
        axis = axes_by_id.get(pos["axis"], {})
        lines.append("- %s (%+.1f, -2=%s +2=%s): %s" % (
            axis.get("label", pos["axis"]), pos["position"],
            axis.get("pole_neg", {}).get("label", "?"), axis.get("pole_pos", {}).get("label", "?"), pos["summary"]))
    return "\n".join(lines)
def _user_profile_text(user_profile, axes_by_id):
    """Render the user's aggregated positions and recent observations."""
    agg = profile_store.aggregate_positions(user_profile)
    if not agg and not user_profile["observations"]:
        return "USER PROFILE: empty so far — nothing has been recorded yet."
    lines = ["USER PROFILE (fully visible to the user):"]
    for axis_id, info in sorted(agg.items()):
        axis = axes_by_id.get(axis_id, {})
        lines.append("- %s: %+.2f (%s, %d observations)" % (axis.get("label", axis_id), info["position"], info["basis"], info["count"]))
    recent = user_profile["observations"][-5:]
    if recent:
        lines.append("Recent observed beliefs:")
        lines.extend("- %s" % o["belief"] for o in recent)
    return "\n".join(lines)
def build_system_prompt(lens_profile, user_profile, grounding, tone, axes):
    """Assemble the full system prompt for the reply call."""
    axes_by_id = {a["id"]: a for a in axes}
    tone_cfg = config.TONES.get(int(tone), config.TONES[config.DEFAULT_TONE])
    return "\n\n".join([
        SAFETY_PREAMBLE, MIRROR_DUTY,
        "TONE (%s): %s" % (tone_cfg["label"], tone_cfg["instruction"]),
        _lens_text(lens_profile, axes_by_id),
        _user_profile_text(user_profile, axes_by_id),
        "SOURCE MATERIAL:\n\n" + _grounding_text(grounding)])

### Turn orchestration
def extract_citations(reply, cite_index):
    """Node ids cited in the reply -> renderable citation dicts (order preserved, deduped)."""
    out, seen = [], set()
    for node_id in CITE_RE.findall(reply):
        if node_id in seen or node_id not in cite_index:
            continue
        seen.add(node_id)
        out.append(cite_index[node_id])
    return out
def answer_turn(graph, atlas_data, cite_index, thread, user_message, user_profile, model=None):
    """Run one full conversation turn. Returns {reply, citations, observed, mirror, routing}.
    Does not persist anything — the caller owns thread/profile writes."""
    axes = atlas_data["axes"]
    lens_id = thread["settings"].get("lens", config.DEFAULT_LENS)
    lens_profile = atlas_data["profiles"].get(lens_id) or atlas_data["profiles"][config.DEFAULT_LENS]
    routing = route_and_extract(user_message, graph_access.topic_catalog(graph), axes, model=model)
    grounding = graph_access.build_grounding(graph, routing["topics"], routing["categories"], routing["concept_needles"])
    system_prompt = build_system_prompt(lens_profile, user_profile, grounding, thread["settings"].get("tone", config.DEFAULT_TONE), axes)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in thread["messages"][-12:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})
    reply = _chat(messages, model=model)
    observed = [b for b in routing["beliefs"] if b["axis"]]
    touched = {b["axis"] for b in observed}
    projected = json.loads(json.dumps(user_profile))
    for b in observed:
        profile_store.add_observation(projected, b["belief"], b["axis"], b["position"], b["confidence"])
    mirror = [row for row in compare.compare_user_to_profile(projected, lens_profile, axes) if row["axis"] in touched]
    return {"reply": reply, "citations": extract_citations(reply, cite_index),
            "observed": routing["beliefs"], "mirror": mirror,
            "routing": {"topics": routing["topics"], "categories": routing["categories"]}}
