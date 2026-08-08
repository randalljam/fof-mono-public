# Mastery session state and exercise scheduling for the autolearner.
# Pure logic, no API calls: tracks per-concept attempts and scores, decides which
# exercise comes next, and drives the multi-pass loop — round 1 covers every
# concept, later rounds revisit only the concepts below the mastery threshold
# (with targeted exercises generated from the gaps found earlier) until every
# concept is mastered.

import json
import os
import uuid
from datetime import datetime

DEFAULT_THRESHOLD = 85


### Concepts
def load_concepts(concepts_path):
    """Load the concepts + exercises catalog JSON."""
    with open(concepts_path) as f:
        return json.load(f)

### Session lifecycle
def new_session(unit_name=""):
    """Create a fresh session dict."""
    return {
        "session_id": uuid.uuid4().hex[:12],
        "created": datetime.now().isoformat(timespec="seconds"),
        "unit": unit_name,
        "round": 1,
        "concepts": {},
        "attempt_log": [],
    }
def session_path(data_dir, session_id):
    """Path of a session JSON file."""
    return os.path.join(data_dir, "sessions", f"{session_id}.json")
def save_session(session, data_dir):
    """Persist a session dict to disk."""
    path = session_path(data_dir, session["session_id"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(session, f, indent=2)
    return path
def load_session(data_dir, session_id):
    """Load a session dict from disk, or None if missing."""
    path = session_path(data_dir, session_id)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)
def latest_session(data_dir):
    """Load the most recently modified session on disk, or None."""
    folder = os.path.join(data_dir, "sessions")
    if not os.path.isdir(folder):
        return None
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".json")]
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    with open(files[0]) as f:
        return json.load(f)

### Per-concept state
def concept_state(session, concept_id):
    """Get (creating if needed) the mutable per-concept state dict."""
    if concept_id not in session["concepts"]:
        session["concepts"][concept_id] = {
            "attempts": [],
            "used_exercise_ids": [],
            "generated_exercises": [],
            "gap_history": [],
            "lessons": [],
        }
    return session["concepts"][concept_id]
def record_attempt(session, concept_id, attempt):
    """
    Record a completed+assessed attempt on a concept.

    :param attempt: dict with at least exercise_id and mastery_score; gaps optional
    """
    state = concept_state(session, concept_id)
    attempt = dict(attempt)
    attempt["round"] = session["round"]
    attempt["timestamp"] = datetime.now().isoformat(timespec="seconds")
    state["attempts"].append(attempt)
    if attempt.get("exercise_id") and attempt["exercise_id"] not in state["used_exercise_ids"]:
        state["used_exercise_ids"].append(attempt["exercise_id"])
    for gap in attempt.get("gaps", []):
        state["gap_history"].append({"round": session["round"], "gap": gap})
    session["attempt_log"].append({
        "concept_id": concept_id,
        "exercise_id": attempt.get("exercise_id"),
        "round": session["round"],
        "mastery_score": attempt.get("mastery_score"),
        "timestamp": attempt["timestamp"],
    })
    return attempt
def latest_score(session, concept_id):
    """Most recent mastery score for a concept, or None if unattempted."""
    state = session["concepts"].get(concept_id)
    if not state or not state["attempts"]:
        return None
    return state["attempts"][-1].get("mastery_score")
def is_mastered(session, concept_id, threshold=DEFAULT_THRESHOLD):
    """A concept is mastered when its most recent attempt meets the threshold."""
    score = latest_score(session, concept_id)
    return score is not None and score >= threshold
def open_gaps(session, concept_id):
    """Gaps recorded on the most recent attempt of a concept (the live holes)."""
    state = session["concepts"].get(concept_id)
    if not state or not state["attempts"]:
        return []
    return state["attempts"][-1].get("gaps", [])
def add_generated_exercise(session, concept_id, exercise):
    """Store an LLM-generated targeted exercise for a concept."""
    state = concept_state(session, concept_id)
    if not exercise.get("id"):
        exercise["id"] = f"{concept_id}-gen{len(state['generated_exercises']) + 1}"
    exercise["generated"] = True
    exercise["round"] = session["round"]
    state["generated_exercises"].append(exercise)
    return exercise

### Scheduling
def attempted_in_round(session, concept_id, round_num):
    """Whether a concept has at least one attempt in the given round."""
    state = session["concepts"].get(concept_id)
    if not state:
        return False
    return any(a.get("round") == round_num for a in state["attempts"])
def concepts_needing_work(session, concepts, threshold=DEFAULT_THRESHOLD):
    """Concept ids that are not yet mastered."""
    return [c["id"] for c in concepts["concepts"] if not is_mastered(session, c["id"], threshold)]
def round_targets(session, concepts, threshold=DEFAULT_THRESHOLD):
    """Concept ids in scope for the current round: everything in round 1, only the unmastered after."""
    if session["round"] == 1:
        return [c["id"] for c in concepts["concepts"]]
    return concepts_needing_work(session, concepts, threshold)
def round_complete(session, concepts, threshold=DEFAULT_THRESHOLD):
    """The current round is complete when every target concept has an attempt in it."""
    targets = round_targets(session, concepts, threshold)
    return all(attempted_in_round(session, cid, session["round"]) for cid in targets)
def advance_round_if_needed(session, concepts, threshold=DEFAULT_THRESHOLD):
    """If the round is complete and unmastered concepts remain, move to the next round."""
    if not round_complete(session, concepts, threshold):
        return False
    if not concepts_needing_work(session, concepts, threshold):
        return False
    session["round"] += 1
    return True
def pick_exercise(session, concept):
    """
    Choose the next exercise for a concept: prefer an unused targeted (generated)
    exercise, then an unused seed exercise, else recycle the least-recently-used seed.
    """
    state = concept_state(session, concept["id"])
    used = state["used_exercise_ids"]
    for ex in reversed(state["generated_exercises"]):
        if ex["id"] not in used:
            return ex
    for ex in concept["exercises"]:
        if ex["id"] not in used:
            return ex
    pool = concept["exercises"] + state["generated_exercises"]
    for ex_id in used:
        pool_match = [ex for ex in pool if ex["id"] == ex_id]
        if pool_match:
            return pool_match[0]
    return concept["exercises"][0]
def next_item(session, concepts, threshold=DEFAULT_THRESHOLD):
    """
    The scheduler: return {done: True} when everything is mastered, otherwise the
    next {concept, exercise, round, needs_generation} to put in front of the student.
    needs_generation flags that this concept is on a repeat round and has no unused
    targeted exercise yet (the caller should generate one from the gap history).
    """
    advance_round_if_needed(session, concepts, threshold)
    remaining = concepts_needing_work(session, concepts, threshold)
    if not remaining:
        return {"done": True}
    by_id = {c["id"]: c for c in concepts["concepts"]}
    targets = [cid for cid in round_targets(session, concepts, threshold)
               if not attempted_in_round(session, cid, session["round"])]
    if not targets:
        targets = [cid for cid in remaining]
    concept = by_id[targets[0]]
    state = concept_state(session, concept["id"])
    has_unused_generated = any(ex["id"] not in state["used_exercise_ids"]
                               for ex in state["generated_exercises"])
    needs_generation = session["round"] > 1 and not has_unused_generated
    return {
        "done": False,
        "concept_id": concept["id"],
        "concept_title": concept["title"],
        "round": session["round"],
        "exercise": pick_exercise(session, concept),
        "needs_generation": needs_generation,
        "prior_gaps": open_gaps(session, concept["id"]),
    }

### Summary for the dashboard
def session_summary(session, concepts, threshold=DEFAULT_THRESHOLD):
    """Per-concept status rows + overall progress for the dashboard."""
    rows = []
    mastered_count = 0
    for c in concepts["concepts"]:
        score = latest_score(session, c["id"])
        mastered = is_mastered(session, c["id"], threshold)
        if mastered:
            mastered_count += 1
        state = session["concepts"].get(c["id"], {})
        rows.append({
            "concept_id": c["id"],
            "title": c["title"],
            "section": c["section"],
            "latest_score": score,
            "mastered": mastered,
            "attempts": len(state.get("attempts", [])),
            "open_gaps": open_gaps(session, c["id"]),
            "lessons": len(state.get("lessons", [])),
        })
    return {
        "session_id": session["session_id"],
        "round": session["round"],
        "threshold": threshold,
        "mastered_count": mastered_count,
        "concept_count": len(concepts["concepts"]),
        "all_mastered": mastered_count == len(concepts["concepts"]),
        "concepts": rows,
    }
