"""Local FastAPI server for Worldview Mirror. Security posture (v1 "basic"):
binds 127.0.0.1 only, every /api/ call requires the per-run session token that is
injected into the served page, and all user data stays in local files under the
app's gitignored data/ dir. Accounts, server-side thread storage, client-side
encryption, and no-retention inference are deliberate placeholders — see README
"Security posture". Run via: python apps/deutsch/worldview-mirror/run_mirror.py serve"""
import math
import os
import secrets
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from . import atlas as atlas_mod
from . import compare
from . import config
from . import engine
from . import graph_access
from . import profile_store
from . import threads as threads_mod

SESSION_TOKEN = os.environ.get("WVM_TOKEN") or secrets.token_urlsafe(24)
app = FastAPI(title="Worldview Mirror", docs_url=None, redoc_url=None)
STATE = {}

### Startup and auth
def _tone(value):
    """Return a supported tone level or a client-facing validation error."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise HTTPException(400, "invalid tone")
    if value not in config.TONES:
        raise HTTPException(400, "invalid tone")
    return value
def _lens(value):
    """Return a known atlas profile id or a client-facing validation error."""
    if value not in STATE["atlas"]["profiles"]:
        raise HTTPException(400, "invalid lens")
    return value
def _bounded_float(value, name, low, high):
    """Parse a finite number constrained to an inclusive range."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise HTTPException(400, "invalid %s" % name)
    if not math.isfinite(value) or value < low or value > high:
        raise HTTPException(400, "%s must be between %s and %s" % (name, low, high))
    return value
@app.on_event("startup")
def startup():
    """Load the graph, atlas, and citation index once."""
    STATE["graph"] = graph_access.load_graph()
    STATE["atlas"] = atlas_mod.load_atlas()
    STATE["cite_index"] = graph_access.citation_index(STATE["graph"])
    errors = atlas_mod.validate_atlas(STATE["atlas"], STATE["graph"]["nodes"])
    if errors:
        raise RuntimeError("taxonomy invalid: " + "; ".join(errors[:5]))
@app.middleware("http")
async def require_token(request, call_next):
    """Reject /api/ requests without the session token (basic local security)."""
    if request.url.path.startswith("/api/") and request.headers.get("x-wvm-token") != SESSION_TOKEN:
        return JSONResponse({"error": "missing or invalid session token"}, status_code=401)
    return await call_next(request)

### Page
@app.get("/", response_class=HTMLResponse)
def index():
    """Serve the hand-authored UI with the session token injected."""
    with open(os.path.join(config.WEB_DIR, "worldview-mirror.html"), encoding="utf-8") as f:
        return f.read().replace("__WVM_TOKEN__", SESSION_TOKEN)

### State and atlas
@app.get("/api/state")
def get_state():
    """Everything the UI needs to boot."""
    a = STATE["atlas"]
    return {"axes": a["axes"],
            "profiles": [{"id": p["id"], "label": p["label"], "summary": p["summary"],
                          "cited_from_graph": p.get("cited_from_graph", False)} for p in a["profiles"].values()],
            "threads": threads_mod.list_threads(),
            "tones": [{"level": k, "label": v["label"]} for k, v in sorted(config.TONES.items())],
            "defaults": {"tone": config.DEFAULT_TONE, "lens": config.DEFAULT_LENS},
            "corpus_available": graph_access.corpus_available(),
            "profile": profile_store.load_profile()}
@app.get("/api/atlas")
def get_atlas():
    """Full atlas: axes and complete profiles with positions and evidence."""
    return {"axes": STATE["atlas"]["axes"], "profiles": list(STATE["atlas"]["profiles"].values())}
@app.get("/api/atlas/compare")
def atlas_compare(a, b):
    """Compare two atlas profiles axis by axis."""
    profiles = STATE["atlas"]["profiles"]
    if a not in profiles or b not in profiles:
        raise HTTPException(404, "unknown profile id")
    return {"rows": compare.compare_profiles(profiles[a], profiles[b], STATE["atlas"]["axes"])}

### Chat
@app.post("/api/chat")
async def chat(request: Request):
    """One conversation turn: {thread_id?, message, tone?, lens?} -> reply + mirror data."""
    payload = await request.json()
    message = (payload.get("message") or "").strip()
    if not message:
        raise HTTPException(400, "empty message")
    tone = _tone(payload["tone"]) if payload.get("tone") is not None else None
    lens = _lens(payload["lens"]) if payload.get("lens") else None
    thread = threads_mod.load_thread(payload.get("thread_id") or "") or threads_mod.create_thread()
    if tone is not None:
        thread["settings"]["tone"] = tone
    if lens:
        thread["settings"]["lens"] = lens
    profile = profile_store.load_profile()
    try:
        result = engine.answer_turn(STATE["graph"], STATE["atlas"], STATE["cite_index"], thread, message, profile)
    except Exception as e:
        raise HTTPException(502, "engine error: %s" % e)
    threads_mod.append_message(thread, "user", message)
    threads_mod.append_message(thread, "assistant", result["reply"],
                               meta={"citations": result["citations"], "mirror": result["mirror"]})
    for belief in result["observed"]:
        if belief["axis"]:
            profile_store.add_observation(profile, belief["belief"], belief["axis"], belief["position"],
                                          belief["confidence"], quote=belief["quote"], thread=thread["id"])
    profile_store.save_profile(profile, axes=STATE["atlas"]["axes"])
    return {"thread": thread, "reply": result["reply"], "citations": result["citations"],
            "mirror": result["mirror"], "observed": result["observed"], "profile": profile}

### Threads
@app.get("/api/threads")
def get_threads():
    """Thread summaries, newest first."""
    return {"threads": threads_mod.list_threads()}
@app.get("/api/threads/{thread_id}")
def get_thread(thread_id):
    """One full thread."""
    thread = threads_mod.load_thread(thread_id)
    if thread is None:
        raise HTTPException(404, "unknown thread")
    return thread
@app.post("/api/threads")
async def new_thread(request: Request):
    """Create a thread: {tone?, lens?}."""
    payload = await request.json() if int(request.headers.get("content-length") or 0) else {}
    return threads_mod.create_thread(tone=_tone(payload.get("tone", config.DEFAULT_TONE)),
                                     lens=_lens(payload.get("lens", config.DEFAULT_LENS)))
@app.delete("/api/threads/{thread_id}")
def remove_thread(thread_id):
    """Delete a thread file."""
    if not threads_mod.delete_thread(thread_id):
        raise HTTPException(404, "unknown thread")
    return {"deleted": thread_id}

### Profile (fully user-visible and editable)
@app.get("/api/profile")
def get_profile():
    """The user's profile plus aggregated axis positions."""
    profile = profile_store.load_profile()
    return {"profile": profile, "positions": profile_store.aggregate_positions(profile)}
@app.post("/api/profile/observation")
async def add_observation(request: Request):
    """Manually add a belief observation: {belief, axis, position, confidence?, quote?}."""
    payload = await request.json()
    profile = profile_store.load_profile()
    if payload.get("axis") not in {a["id"] for a in STATE["atlas"]["axes"]}:
        raise HTTPException(400, "unknown axis")
    belief = payload.get("belief")
    if not isinstance(belief, str) or not belief.strip():
        raise HTTPException(400, "empty belief")
    obs = profile_store.add_observation(profile, belief.strip(), payload["axis"],
                                        _bounded_float(payload.get("position"), "position", -2.0, 2.0),
                                        _bounded_float(payload.get("confidence", 1.0), "confidence", 0.0, 1.0),
                                        quote=payload.get("quote", ""), source="manual")
    profile_store.save_profile(profile, axes=STATE["atlas"]["axes"])
    return {"observation": obs, "profile": profile}
@app.delete("/api/profile/observation/{obs_id}")
def remove_observation(obs_id):
    """Delete one observation."""
    profile = profile_store.load_profile()
    if not profile_store.delete_observation(profile, obs_id):
        raise HTTPException(404, "unknown observation")
    profile_store.save_profile(profile, axes=STATE["atlas"]["axes"])
    return {"profile": profile}
@app.post("/api/profile/axis")
async def set_axis(request: Request):
    """Directly assert (or clear) the user's position on an axis: {axis, position|null, note?}."""
    payload = await request.json()
    profile = profile_store.load_profile()
    if payload.get("axis") not in {a["id"] for a in STATE["atlas"]["axes"]}:
        raise HTTPException(400, "unknown axis")
    if payload.get("position") is None:
        profile_store.clear_axis_override(profile, payload["axis"])
    else:
        position = _bounded_float(payload["position"], "position", -2.0, 2.0)
        profile_store.set_axis_override(profile, payload["axis"], position, payload.get("note", ""))
    profile_store.save_profile(profile, axes=STATE["atlas"]["axes"])
    return {"profile": profile, "positions": profile_store.aggregate_positions(profile)}
@app.delete("/api/profile")
def clear_profile():
    """Delete the entire user profile (right to erase)."""
    profile_store.delete_profile()
    return {"profile": profile_store.load_profile()}

### Mirror comparison
@app.get("/api/compare")
def get_compare(lens=config.DEFAULT_LENS):
    """User vs lens profile, axis by axis."""
    lens_profile = STATE["atlas"]["profiles"].get(lens)
    if lens_profile is None:
        raise HTTPException(404, "unknown lens profile")
    profile = profile_store.load_profile()
    return {"lens": {"id": lens_profile["id"], "label": lens_profile["label"]},
            "rows": compare.compare_user_to_profile(profile, lens_profile, STATE["atlas"]["axes"])}
