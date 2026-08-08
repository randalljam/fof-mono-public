# Local dev server for the autolearner AI practice app.
# Run from the repo root:  .venv/bin/python3 apps/autolearner/server.py
# Then open http://localhost:5055
#
# Serves the practice UI and the interactive study guide, and exposes the
# assessment pipeline: audio (think-aloud recording) + photo of written work
# -> Deepgram word-level transcription -> pacing analysis -> structured LLM
# assessment -> mastery tracking across rounds until every concept is mastered.

import json
import os
import sys
import time

APP_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(APP_DIR))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from flask import Flask, jsonify, request, send_from_directory

from apps.autolearner import mastery, pacing, pipeline

CONCEPTS_PATH = os.path.join(APP_DIR, "content", "concepts.json")
DATA_DIR = os.environ.get("AUTOLEARNER_DATA_DIR", os.path.join(APP_DIR, "data"))
WEB_DIR = os.path.join(APP_DIR, "web")

app = Flask(__name__)
CONCEPTS = mastery.load_concepts(CONCEPTS_PATH)
THRESHOLD = CONCEPTS.get("mastery_threshold", mastery.DEFAULT_THRESHOLD)


### Session helpers
def get_session():
    """Load the latest session from disk or start a new one."""
    session = mastery.latest_session(DATA_DIR)
    if session is None:
        session = mastery.new_session(CONCEPTS.get("unit", ""))
        mastery.save_session(session, DATA_DIR)
    return session
def concept_by_id(concept_id):
    """Look up a concept from the catalog."""
    for c in CONCEPTS["concepts"]:
        if c["id"] == concept_id:
            return c
    return None
def find_exercise(session, concept, exercise_id):
    """Find an exercise by id among a concept's seed and generated exercises."""
    state = mastery.concept_state(session, concept["id"])
    for ex in concept["exercises"] + state["generated_exercises"]:
        if ex["id"] == exercise_id:
            return ex
    return None
def upload_dir_for(session):
    """Directory where a session's attempt uploads are stored."""
    return os.path.join(DATA_DIR, "uploads", session["session_id"])
def resolve_attempt_image_file(session, attempt):
    """
    Pick a browser/API-friendly image filename for an attempt.
    Prefer a sibling .jpg when the stored file is .heic (common from iPhone uploads).
    """
    image_file = attempt.get("image_file")
    if not image_file:
        return None
    folder = upload_dir_for(session)
    image_path = os.path.join(folder, image_file)
    if os.path.isfile(image_path) and not image_file.lower().endswith(".heic"):
        return image_file
    stem = image_file.rsplit(".", 1)[0]
    for ext in ("jpg", "jpeg", "png", "webp"):
        alt = f"{stem}.{ext}"
        if os.path.isfile(os.path.join(folder, alt)):
            return alt
    return image_file if os.path.isfile(image_path) else None
def build_attempt_review(session, concept_id, attempt_index=-1):
    """Assemble attempt + assessment + media URLs for the review UI."""
    concept = concept_by_id(concept_id)
    if not concept:
        return None
    state = session["concepts"].get(concept_id)
    if not state or not state.get("attempts"):
        return None
    if attempt_index < 0:
        attempt_index = len(state["attempts"]) + attempt_index
    if attempt_index < 0 or attempt_index >= len(state["attempts"]):
        return None
    attempt = state["attempts"][attempt_index]
    exercise = find_exercise(session, concept, attempt.get("exercise_id"))
    if not exercise:
        return None
    sid = session["session_id"]
    audio_file = attempt.get("audio_file")
    image_file = resolve_attempt_image_file(session, attempt)
    return {
        "concept_id": concept_id,
        "concept_title": concept["title"],
        "section": concept["section"],
        "attempt_index": attempt_index,
        "exercise": exercise,
        "attempt": attempt,
        "assessment": attempt.get("assessment") or {},
        "audio_url": f"/api/uploads/{sid}/{audio_file}" if audio_file else None,
        "image_url": f"/api/uploads/{sid}/{image_file}" if image_file else None,
    }
def resolve_next_item(session):
    """
    Get the next scheduled item, transparently generating targeted exercises
    when a repeat round needs them (based on the gaps found last round).
    """
    item = mastery.next_item(session, CONCEPTS, THRESHOLD)
    if item.get("done") or not item.get("needs_generation"):
        return item
    concept = concept_by_id(item["concept_id"])
    gaps = item.get("prior_gaps", [])
    exercises, mode = pipeline.generate_targeted_exercises(concept, gaps)
    for ex in exercises:
        mastery.add_generated_exercise(session, item["concept_id"], ex)
    mastery.save_session(session, DATA_DIR)
    item = mastery.next_item(session, CONCEPTS, THRESHOLD)
    item["generation_mode"] = mode
    return item

### Pages
@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")
@app.route("/guide")
def guide():
    return send_from_directory(WEB_DIR, "study-guide.html")
@app.route("/web/<path:filename>")
def web_files(filename):
    return send_from_directory(WEB_DIR, filename)

### API: state and scheduling
@app.route("/api/state")
def api_state():
    session = get_session()
    summary = mastery.session_summary(session, CONCEPTS, THRESHOLD)
    next_item = resolve_next_item(session)
    return jsonify({"summary": summary, "next": next_item, "modes": pipeline.service_modes()})
@app.route("/api/reset", methods=["POST"])
def api_reset():
    session = mastery.new_session(CONCEPTS.get("unit", ""))
    mastery.save_session(session, DATA_DIR)
    summary = mastery.session_summary(session, CONCEPTS, THRESHOLD)
    return jsonify({"summary": summary, "next": resolve_next_item(session), "modes": pipeline.service_modes()})
@app.route("/api/attempt/<concept_id>")
def api_attempt(concept_id):
    """Return a past attempt with assessment and media URLs for the review UI."""
    session = get_session()
    attempt_index = request.args.get("index", -1, type=int)
    review = build_attempt_review(session, concept_id, attempt_index)
    if not review:
        return jsonify({"error": f"no attempt found for concept {concept_id}"}), 404
    return jsonify(review)
@app.route("/api/uploads/<session_id>/<filename>")
def api_uploads(session_id, filename):
    """Serve uploaded attempt audio/photos for playback in the review UI."""
    session = get_session()
    if session_id != session["session_id"]:
        return jsonify({"error": "upload not in the active session"}), 404
    folder = upload_dir_for(session)
    if not os.path.isfile(os.path.join(folder, filename)):
        return jsonify({"error": "file not found"}), 404
    return send_from_directory(folder, filename)

### API: submit an attempt (audio + photo)
@app.route("/api/submit", methods=["POST"])
def api_submit():
    session = get_session()
    concept_id = request.form.get("concept_id", "")
    exercise_id = request.form.get("exercise_id", "")
    concept = concept_by_id(concept_id)
    if not concept:
        return jsonify({"error": f"unknown concept_id {concept_id}"}), 400
    exercise = find_exercise(session, concept, exercise_id)
    if not exercise:
        return jsonify({"error": f"unknown exercise_id {exercise_id}"}), 400
    audio_file = request.files.get("audio")
    if not audio_file:
        return jsonify({"error": "no audio recording attached — record your think-aloud first"}), 400
    stamp = time.strftime("%Y%m%d-%H%M%S")
    upload_dir = os.path.join(DATA_DIR, "uploads", session["session_id"])
    os.makedirs(upload_dir, exist_ok=True)
    audio_ext = (audio_file.filename or "recording.webm").rsplit(".", 1)[-1].lower() or "webm"
    audio_path = os.path.join(upload_dir, f"{stamp}_{exercise_id}.{audio_ext}")
    audio_file.save(audio_path)
    image_path = None
    photo_file = request.files.get("photo")
    if photo_file and photo_file.filename:
        photo_ext = photo_file.filename.rsplit(".", 1)[-1].lower() or "jpg"
        image_path = os.path.join(upload_dir, f"{stamp}_{exercise_id}.{photo_ext}")
        photo_file.save(image_path)
        if photo_ext == "heic":
            jpg_path = os.path.join(upload_dir, f"{stamp}_{exercise_id}.jpg")
            if not os.path.isfile(jpg_path):
                try:
                    from PIL import Image
                    with Image.open(image_path) as img:
                        img.convert("RGB").save(jpg_path, "JPEG")
                except Exception as e:
                    print(f"HEIC→JPG conversion skipped ({e}); assessment may use HEIC if supported")
    dg_response, transcription_mode = pipeline.transcribe_audio(audio_path)
    prior_gaps = mastery.open_gaps(session, concept_id)
    assess_image_path = image_path
    if image_path and image_path.lower().endswith(".heic"):
        jpg_path = image_path.rsplit(".", 1)[0] + ".jpg"
        if os.path.isfile(jpg_path):
            assess_image_path = jpg_path
    assessment, assessment_mode = pipeline.assess_attempt(concept, exercise, dg_response, assess_image_path, prior_gaps)
    stored_image_file = os.path.basename(image_path) if image_path else None
    if image_path and image_path.lower().endswith(".heic"):
        jpg_path = image_path.rsplit(".", 1)[0] + ".jpg"
        if os.path.isfile(jpg_path):
            stored_image_file = os.path.basename(jpg_path)
    mastery.record_attempt(session, concept_id, {
        "exercise_id": exercise_id,
        "mastery_score": assessment.get("mastery_score", 0),
        "correctness": assessment.get("correctness"),
        "gaps": assessment.get("gaps", []),
        "assessment": assessment,
        "audio_file": os.path.basename(audio_path),
        "image_file": stored_image_file,
        "transcription_mode": transcription_mode,
        "assessment_mode": assessment_mode,
    })
    mastery.save_session(session, DATA_DIR)
    summary = mastery.session_summary(session, CONCEPTS, THRESHOLD)
    review = build_attempt_review(session, concept_id, -1)
    return jsonify({
        "assessment": assessment,
        "summary": summary,
        "next": resolve_next_item(session),
        "modes": {"transcription": transcription_mode, "assessment": assessment_mode},
        "media": {
            "audio_url": review["audio_url"] if review else None,
            "image_url": review["image_url"] if review else None,
            "concept_title": concept["title"],
            "exercise_prompt": exercise["prompt"],
        },
    })

### API: teach-me lessons
@app.route("/api/teach-me", methods=["POST"])
def api_teach_me():
    session = get_session()
    payload = request.get_json(force=True, silent=True) or {}
    concept_id = payload.get("concept_id", "")
    concept = concept_by_id(concept_id)
    if not concept:
        return jsonify({"error": f"unknown concept_id {concept_id}"}), 400
    confusion_text = payload.get("confusion_text", "")
    exercise = None
    if payload.get("exercise_id"):
        exercise = find_exercise(session, concept, payload["exercise_id"])
    gaps = mastery.open_gaps(session, concept_id)
    lesson, lesson_mode = pipeline.generate_lesson(concept, gaps, confusion_text, exercise)
    audio_name = f"lesson_{concept_id}_{time.strftime('%Y%m%d-%H%M%S')}.mp3"
    audio_path = os.path.join(DATA_DIR, "lessons", session["session_id"], audio_name)
    audio_result = pipeline.tts_lesson_audio(lesson.get("audio_script", ""), audio_path)
    lesson["mode"] = lesson_mode
    lesson["audio_url"] = f"/api/lesson-audio/{session['session_id']}/{audio_name}" if audio_result else None
    state = mastery.concept_state(session, concept_id)
    state["lessons"].append({
        "title": lesson.get("title"),
        "audio_file": audio_name if audio_result else None,
        "confusion_text": confusion_text,
        "round": session["round"],
        "mode": lesson_mode,
    })
    mastery.save_session(session, DATA_DIR)
    return jsonify({"lesson": lesson})
@app.route("/api/lesson-audio/<session_id>/<filename>")
def api_lesson_audio(session_id, filename):
    return send_from_directory(os.path.join(DATA_DIR, "lessons", session_id), filename)

### Main
if __name__ == "__main__":
    pipeline.ensure_env_placeholders()
    modes = pipeline.service_modes()
    print(f"AutoLearner dev server — service modes: {json.dumps(modes)}")
    if "mock" in modes.values():
        print("  (mock services are placeholders; set DEEPGRAM_API_KEY / ANTHROPIC_API_KEY_LOCAL / OPENAI_API_KEY_LOCAL in .env for the real pipeline)")
    port = int(os.environ.get("AUTOLEARNER_PORT", "5055"))
    print(f"Open http://localhost:{port}  (practice app)  ·  http://localhost:{port}/guide  (study guide)")
    app.run(host="127.0.0.1", port=port, debug=True)
