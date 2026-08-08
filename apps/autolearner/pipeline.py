# Service pipeline for the autolearner: Deepgram transcription, LLM structured
# assessment (transcript + pacing + photo of written work), targeted exercise
# generation, and lesson generation with TTS audio.
#
# Reuses core/transcribe.py (Deepgram, word-level timestamps) and core/llm.py
# (provider-swappable LLM calls). Both of those modules require API keys in the
# environment at import time, so imports here are lazy and every service
# degrades to a clearly-labeled mock mode when its key or dependency is missing —
# the whole app stays runnable end-to-end with no keys for local development.

import base64
import hashlib
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from apps.autolearner import pacing

PLACEHOLDER = "MISSING-set-in-.env"
DEEPGRAM_MODEL = "nova-2-general"
IMAGE_MEDIA_TYPES = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif"}


### Environment and service modes
def _load_dotenv_if_available():
    """Load repo-root .env first so keys work regardless of process cwd."""
    try:
        from dotenv import load_dotenv
        dotenv_path = os.path.join(REPO_ROOT, ".env")
        if os.path.isfile(dotenv_path):
            load_dotenv(dotenv_path, override=True)
        else:
            load_dotenv(override=True)
    except ImportError:
        pass
def ensure_env_placeholders():
    """
    core/llm.py and core/transcribe.py read several env keys with os.environ[...]
    at import time. Map available fallbacks (OPENAI_API_KEY -> OPENAI_API_KEY_LOCAL)
    and fill anything still missing with a placeholder so the imports succeed;
    real availability is tracked separately by service_modes().
    """
    _load_dotenv_if_available()
    if not os.environ.get("OPENAI_API_KEY_LOCAL") and os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY_LOCAL"] = os.environ["OPENAI_API_KEY"]
    if not os.environ.get("ANTHROPIC_API_KEY_LOCAL") and os.environ.get("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY_LOCAL"] = os.environ["ANTHROPIC_API_KEY"]
    for key in ["OPENAI_API_KEY_LOCAL", "OPENAI_API_KEY_T5", "ANTHROPIC_API_KEY_LOCAL",
                "DEEPSEEK_API_KEY_LOCAL", "DEEPGRAM_API_KEY", "YOUTUBE_API_KEY"]:
        os.environ.setdefault(key, PLACEHOLDER)
def _has_real_key(name):
    """A key is real when present and not the placeholder."""
    value = os.environ.get(name, "")
    return bool(value) and value != PLACEHOLDER
def service_modes():
    """Report which backend each service will actually use right now."""
    ensure_env_placeholders()
    transcription = "deepgram" if _has_real_key("DEEPGRAM_API_KEY") else "mock"
    if _has_real_key("ANTHROPIC_API_KEY_LOCAL"):
        assessment = "anthropic"
    elif _has_real_key("OPENAI_API_KEY_LOCAL"):
        assessment = "openai"
    else:
        assessment = "mock"
    tts = "openai" if (_has_real_key("OPENAI_API_KEY_TTS") or _has_real_key("OPENAI_API_KEY_LOCAL")) else "mock"
    return {"transcription": transcription, "assessment": assessment, "tts": tts}

### Transcription (Deepgram word-level timestamps)
def transcribe_audio(audio_file_path):
    """
    Transcribe a student recording, returning (deepgram_response_dict, mode).
    Primary path is core.transcribe.transcribe_deepgram_sync; falls back to a
    direct Deepgram REST call (handles containers mutagen can't read, e.g. webm
    from MediaRecorder), then to a mock transcript when no key is available.
    """
    ensure_env_placeholders()
    if not _has_real_key("DEEPGRAM_API_KEY"):
        return _mock_transcription(audio_file_path), "mock"
    try:
        from core.transcribe import transcribe_deepgram_sync
        json_file_path = transcribe_deepgram_sync(audio_file_path, DEEPGRAM_MODEL)
        if json_file_path and os.path.exists(json_file_path):
            with open(json_file_path) as f:
                return json.load(f), "deepgram"
    except Exception as e:
        print(f"core.transcribe path failed ({e}); falling back to Deepgram REST")
    try:
        return _transcribe_deepgram_rest(audio_file_path), "deepgram"
    except Exception as e:
        print(f"Deepgram REST fallback failed ({e}); using mock transcription")
        return _mock_transcription(audio_file_path), "mock"
def _transcribe_deepgram_rest(audio_file_path):
    """Direct Deepgram prerecorded REST call with word timestamps (same options as core.transcribe)."""
    import requests
    ext = audio_file_path.rsplit(".", 1)[-1].lower()
    with open(audio_file_path, "rb") as f:
        audio_bytes = f.read()
    response = requests.post(
        "https://api.deepgram.com/v1/listen",
        params={"punctuate": "true", "diarize": "true", "model": DEEPGRAM_MODEL, "smart_format": "true"},
        headers={"Authorization": f"Token {os.environ['DEEPGRAM_API_KEY']}", "Content-Type": f"audio/{ext}"},
        data=audio_bytes,
        timeout=600,
    )
    response.raise_for_status()
    result = response.json()
    json_file_path = audio_file_path.rsplit(".", 1)[0] + "_dg.json"
    with open(json_file_path, "w") as f:
        json.dump(result, f, indent=2)
    return result
def _mock_transcription(audio_file_path):
    """Fabricate a plausible think-aloud Deepgram response so the app runs with no keys."""
    seed = int(hashlib.sha256(os.path.basename(audio_file_path).encode()).hexdigest(), 16)
    script = ("Okay so first I'm going to write down what I know. We have two points here. "
              "So the slope is the change in y over the change in x. Let me compute that. "
              "Hmm, wait, I need to double check the subtraction order. Okay so that gives me the slope. "
              "Now I plug in the first point to find b. So the answer is y equals m x plus b with those values. "
              "Let me check it with the second point. Yes, that works out.").split()
    words = []
    t = 1.5
    for i, w in enumerate(script):
        dur = 0.28 + (seed >> (i % 20) & 3) * 0.05
        words.append({"word": w.strip(".,"), "punctuated_word": w, "start": round(t, 2), "end": round(t + dur, 2), "confidence": 0.99})
        t += dur + 0.12
        if w.endswith("."):
            t += 0.8
        if i == len(script) // 2:
            t += 6.0
    return {
        "metadata": {"mock": True},
        "results": {"channels": [{"alternatives": [{
            "transcript": " ".join(script),
            "confidence": 0.99,
            "words": words,
        }]}]},
    }

### LLM plumbing
def _import_core_llm():
    """Lazy import of core.llm (requires env placeholders to be set first)."""
    ensure_env_placeholders()
    import core.llm as llm
    return llm
def _extract_tool_input_anthropic(response):
    """Pull the tool_use input dict out of an Anthropic message response."""
    if not response:
        return None
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", None) == "tool_use":
            return dict(block.input)
    return None
def _extract_tool_input_openai(response):
    """Pull the function-call arguments dict out of an OpenAI SDK chat response."""
    try:
        call = response.choices[0].message.tool_calls[0]
        return json.loads(call.function.arguments)
    except (AttributeError, IndexError, TypeError, json.JSONDecodeError):
        return None
def _image_block_anthropic(image_path):
    """Build an Anthropic base64 image content block from a file."""
    ext = image_path.rsplit(".", 1)[-1].lower()
    media_type = IMAGE_MEDIA_TYPES.get(ext, "image/jpeg")
    with open(image_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode()
    return {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}}
def _image_block_openai(image_path):
    """Build an OpenAI image_url content part (data URL) from a file."""
    ext = image_path.rsplit(".", 1)[-1].lower()
    media_type = IMAGE_MEDIA_TYPES.get(ext, "image/jpeg")
    with open(image_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode()
    return {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{data}"}}
def _structured_llm_call(system_prompt, content_text, tool, image_path=None):
    """
    One structured-output LLM call: provider-swappable (Anthropic first, then
    OpenAI), forcing the given tool and returning its parsed input dict.
    `tool` uses the Anthropic shape {name, description, input_schema}.
    """
    modes = service_modes()
    llm = _import_core_llm()
    if modes["assessment"] == "anthropic":
        content = [{"type": "text", "text": content_text}]
        if image_path:
            content.insert(0, _image_block_anthropic(image_path))
        try:
            response = llm.anthropic_chat_completion_request(
                messages=[{"role": "user", "content": content}],
                system=system_prompt + "\nYou MUST respond by calling the provided tool.",
                tools=[tool],
                tool_choice={"type": "tool", "name": tool["name"]},
                max_tokens=4096,
                temperature=0.2,
            )
            result = _extract_tool_input_anthropic(response)
            if result:
                return result, "anthropic"
        except Exception as e:
            print(f"Anthropic structured call failed ({e}); trying OpenAI fallback if available")
    if modes["assessment"] in ("anthropic", "openai") and _has_real_key("OPENAI_API_KEY_LOCAL"):
        content = [{"type": "text", "text": content_text}]
        if image_path:
            content.append(_image_block_openai(image_path))
        openai_tool = {"type": "function", "function": {"name": tool["name"], "description": tool["description"], "parameters": tool["input_schema"]}}
        try:
            response = llm.openai_chat_completion_request_sdk(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": content}],
                model=llm.OPENAI_MODEL,
                tools=[openai_tool],
                tool_choice={"type": "function", "function": {"name": tool["name"]}},
            )
            result = _extract_tool_input_openai(response)
            if result:
                return result, "openai"
        except Exception as e:
            print(f"OpenAI structured call fallback failed ({e})")
    return None, "mock"

### Structured assessment
ASSESSMENT_TOOL = {
    "name": "assess_student_attempt",
    "description": "Record a structured mastery assessment of a student's think-aloud problem-solving attempt, based on the spoken transcript with timing data and the photo of their written work.",
    "input_schema": {
        "type": "object",
        "properties": {
            "correctness": {
                "type": "string",
                "enum": ["correct", "minor_errors", "major_errors", "incorrect", "incomplete"],
                "description": "Overall correctness of the final answer and written work.",
            },
            "correctness_notes": {
                "type": "string",
                "description": "Specific notes on what was right and wrong in the answer and the written work, referencing what is visible in the photo.",
            },
            "mastery_score": {
                "type": "integer",
                "description": "0-100 mastery score for this concept. Weigh correctness, quality of spoken reasoning, and pacing: a student who has mastered the concept moves at a steady pace with confident reasoning; long unexplained pauses, backtracking, and stated confusion lower the score even when the final answer is right.",
            },
            "reasoning_quality": {
                "type": "string",
                "description": "Assessment of the spoken think-aloud reasoning: was the approach sound, systematic, and self-checked?",
            },
            "pacing_assessment": {
                "type": "string",
                "description": "What the timing data says: steady mastery-level progress vs hesitation, where the long pauses happened and what step they correspond to.",
            },
            "confusion_flags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Moments where the student said they were confused, unsure, or asked for a lesson, quoted or paraphrased from the transcript.",
            },
            "gaps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string", "description": "The specific understanding hole, stated precisely."},
                        "severity": {"type": "string", "enum": ["minor", "moderate", "major"]},
                        "evidence": {"type": "string", "description": "The transcript moment or written-work detail showing this gap."},
                    },
                    "required": ["description", "severity"],
                },
                "description": "Specific holes in understanding to target in the next round of exercises.",
            },
            "strengths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "What the student did well and should keep doing.",
            },
            "overall_assessment": {
                "type": "string",
                "description": "2-4 sentence overall assessment written directly to the student, encouraging and specific.",
            },
            "recommendation": {
                "type": "string",
                "description": "The single most useful next step for this student on this concept.",
            },
        },
        "required": ["correctness", "correctness_notes", "mastery_score", "reasoning_quality",
                     "pacing_assessment", "gaps", "strengths", "overall_assessment", "recommendation"],
    },
}
ASSESSMENT_SYSTEM_PROMPT = (
    "You are an expert precalculus tutor assessing a student's mastery of one concept. "
    "The student was told to think aloud the entire time while solving one problem on paper, "
    "then photograph their written work. You receive: the problem with its reference solution, "
    "the full spoken transcript with word-level timing (pacing metrics and a timeline), and the photo. "
    "Assess mastery, not just correctness: mastery shows up as steady pacing, confident systematic reasoning, "
    "and self-checking; hesitation, long silent stretches at key steps, and stated confusion reveal gaps even "
    "when the answer is right. Be specific and evidence-based; quote the transcript and cite the written work. "
    "Be encouraging but honest — the gaps you list drive the student's next round of targeted practice."
)
def build_assessment_content(concept, exercise, transcript_text, pacing_text, prior_gaps=None):
    """Assemble the text part of the assessment prompt."""
    parts = [
        f"CONCEPT: {concept['title']} (section {concept['section']})",
        f"CONCEPT SUMMARY: {concept['summary']}",
        "",
        f"PROBLEM GIVEN TO THE STUDENT:\n{exercise['prompt']}",
        "",
        f"REFERENCE SOLUTION (for you only):\n{exercise.get('reference_solution', 'n/a')}",
        "",
        f"SPOKEN TRANSCRIPT (think-aloud):\n{transcript_text or '(no speech detected)'}",
        "",
        pacing_text,
    ]
    if prior_gaps:
        gap_lines = "\n".join(f"- {g.get('description', g)}" for g in prior_gaps)
        parts += ["", f"GAPS IDENTIFIED ON THIS CONCEPT IN THE PREVIOUS ROUND (check whether they are closed now):\n{gap_lines}"]
    parts += ["", "The photo of the student's written work is attached. Assess the attempt now by calling assess_student_attempt."]
    return "\n".join(parts)
def assess_attempt(concept, exercise, dg_response, image_path=None, prior_gaps=None):
    """
    Full assessment of one attempt: pacing analysis from the Deepgram word
    timestamps, then a structured LLM call with the transcript, timing report,
    and the photo of written work. Returns (assessment_dict, mode).
    """
    words = pacing.extract_words(dg_response)
    transcript_text = pacing.extract_transcript(dg_response)
    metrics = pacing.compute_pacing_metrics(words)
    timeline = pacing.build_timeline(words)
    pacing_text = pacing.pacing_report_text(metrics, timeline)
    content_text = build_assessment_content(concept, exercise, transcript_text, pacing_text, prior_gaps)
    modes = service_modes()
    result, mode = None, "mock"
    mock_reason = None
    if modes["assessment"] == "mock":
        mock_reason = "no_llm_key"
    else:
        try:
            result, mode = _structured_llm_call(ASSESSMENT_SYSTEM_PROMPT, content_text, ASSESSMENT_TOOL, image_path)
        except Exception as e:
            mock_reason = f"llm_call_failed: {e}"
            print(f"Assessment LLM call failed ({e}); using mock assessment")
        if not result and not mock_reason:
            mock_reason = "llm_no_tool_response"
    if not result:
        result = _mock_assessment(concept, exercise, transcript_text, metrics, mock_reason=mock_reason)
        mode = "mock"
    result["pacing_metrics"] = metrics
    result["transcript"] = transcript_text
    result["mode"] = mode
    return result, mode
def _mock_assessment(concept, exercise, transcript_text, metrics, mock_reason=None):
    """Heuristic assessment so the full loop works without a live LLM (clearly labeled)."""
    seed = int(hashlib.sha256(exercise["id"].encode()).hexdigest(), 16)
    score = 55 + seed % 41
    confusion = [w for w in ["confused", "don't know", "not sure", "stuck"] if w in (transcript_text or "").lower()]
    if confusion:
        score = max(30, score - 20)
    if metrics["longest_pause_s"] > 10:
        score = max(25, score - 10)
    if mock_reason == "no_llm_key":
        reason_text = ("Mock mode — no LLM API key configured. "
                       "Set ANTHROPIC_API_KEY_LOCAL (or OPENAI_API_KEY_LOCAL) in the repo-root .env.")
        recommendation = "Configure API keys to get real assessments."
    else:
        reason_text = ("Mock mode — the LLM call did not return a structured assessment "
                       f"({mock_reason or 'unknown failure'}). This score is a placeholder, not AI feedback.")
        recommendation = "Restart the server after fixing .env or LLM errors, then submit again."
    gaps = []
    if score < 85:
        gaps.append({"description": f"(mock) Needs another pass on: {concept['summary'][:80]}", "severity": "moderate",
                     "evidence": reason_text})
    return {
        "correctness": "minor_errors" if score < 85 else "correct",
        "correctness_notes": f"MOCK MODE: {reason_text}",
        "mastery_score": score,
        "reasoning_quality": f"Mock: {metrics['total_words']} words spoken at {metrics['words_per_minute']} wpm.",
        "pacing_assessment": f"Mock: {metrics['pause_count']} notable pauses, longest {metrics['longest_pause_s']}s.",
        "confusion_flags": confusion,
        "gaps": gaps,
        "strengths": ["Completed the attempt and recorded a think-aloud."],
        "overall_assessment": reason_text,
        "recommendation": recommendation,
        "mock_reason": mock_reason or "unknown",
    }

### Targeted exercise generation (round 2+)
EXERCISE_TOOL = {
    "name": "create_targeted_exercises",
    "description": "Create new practice exercises that specifically target a student's identified gaps on a concept.",
    "input_schema": {
        "type": "object",
        "properties": {
            "exercises": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "The full problem statement, self-contained, at test difficulty. Plain text with inline LaTeX allowed using $...$."},
                        "reference_solution": {"type": "string", "description": "Complete worked solution with the final answer."},
                        "targets_gap": {"type": "string", "description": "Which identified gap this exercise attacks."},
                    },
                    "required": ["prompt", "reference_solution", "targets_gap"],
                },
                "description": "1-3 new exercises, each aimed squarely at the identified gaps.",
            }
        },
        "required": ["exercises"],
    },
}
def generate_targeted_exercises(concept, gaps, count=2):
    """
    Generate new exercises aimed at a concept's open gaps for the next round.
    Returns (list_of_exercises, mode); falls back to unused seed style in mock mode.
    """
    gap_lines = "\n".join(f"- {g.get('description', g)} (severity: {g.get('severity', '?')})" for g in gaps) or "- general shakiness on the concept"
    content_text = (
        f"CONCEPT: {concept['title']} (section {concept['section']})\n"
        f"CONCEPT SUMMARY: {concept['summary']}\n\n"
        f"THE STUDENT'S IDENTIFIED GAPS FROM THEIR LAST ATTEMPT:\n{gap_lines}\n\n"
        f"EXAMPLE EXERCISES ALREADY USED (write DIFFERENT problems, same difficulty):\n"
        + "\n".join(f"- {ex['prompt'][:140]}" for ex in concept["exercises"])
        + f"\n\nCreate {count} new exercises that force the student to confront exactly these gaps. Call create_targeted_exercises."
    )
    system = ("You are an expert precalculus tutor writing targeted practice problems. "
              "Each problem must attack the student's specific gaps, be fully self-contained, "
              "and match the difficulty of the examples.")
    try:
        result, mode = _structured_llm_call(system, content_text, EXERCISE_TOOL)
        if result and result.get("exercises"):
            return result["exercises"][:count], mode
    except Exception as e:
        print(f"Exercise generation failed ({e}); using mock exercises")
    mocked = [{
        "prompt": f"(mock retry) {concept['exercises'][i % len(concept['exercises'])]['prompt']}",
        "reference_solution": concept["exercises"][i % len(concept["exercises"])]["reference_solution"],
        "targets_gap": "mock mode — reusing a seed exercise",
    } for i in range(count)]
    return mocked, "mock"

### Lesson generation (audio + rich page)
LESSON_TOOL = {
    "name": "create_lesson",
    "description": "Create a short, focused remediation lesson for a student on a precalculus concept, addressing their specific confusion.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short lesson title."},
            "lesson_html": {"type": "string", "description": "The lesson body as clean HTML (use <h3>, <p>, <ul>, and inline LaTeX with $...$ which will be rendered by MathJax). 300-600 words: explain the idea from the ground up, address the student's specific confusion directly, include one fully worked example."},
            "key_points": {"type": "array", "items": {"type": "string"}, "description": "3-5 one-line takeaways."},
            "audio_script": {"type": "string", "description": "The same lesson as a natural spoken script for text-to-speech: conversational, no notation — say 'y equals m x plus b' style words instead of symbols. 250-450 words."},
        },
        "required": ["title", "lesson_html", "key_points", "audio_script"],
    },
}
def generate_lesson(concept, gaps, confusion_notes="", exercise=None):
    """
    Generate a remediation lesson for a concept from the student's gaps and any
    stated confusion. Returns (lesson_dict, mode). Lesson has title, lesson_html,
    key_points, audio_script.
    """
    gap_lines = "\n".join(f"- {g.get('description', g)}" for g in gaps) or "- general uncertainty on this concept"
    parts = [
        f"CONCEPT: {concept['title']} (section {concept['section']})",
        f"CONCEPT SUMMARY: {concept['summary']}",
        f"STUDENT'S GAPS:\n{gap_lines}",
    ]
    if confusion_notes:
        parts.append(f"WHAT THE STUDENT SAID WHEN ASKING FOR THIS LESSON (their own words, address it directly):\n{confusion_notes}")
    if exercise:
        parts.append(f"THE PROBLEM THEY WERE WORKING ON:\n{exercise['prompt']}")
    parts.append("Create the lesson now by calling create_lesson.")
    system = ("You are a warm, expert precalculus tutor creating a short remediation lesson for one student. "
              "Teach to their exact confusion, not generically. Build intuition first, then the procedure, "
              "then one fully worked example.")
    try:
        result, mode = _structured_llm_call(system, "\n\n".join(parts), LESSON_TOOL)
        if result:
            return result, mode
    except Exception as e:
        print(f"Lesson generation failed ({e}); using mock lesson")
    return {
        "title": f"Refresher: {concept['title']}",
        "lesson_html": (f"<h3>{concept['title']}</h3><p><b>Mock lesson</b> (no LLM key configured). "
                        f"Core idea: {concept['summary']}</p><p>Worked example: {concept['exercises'][0]['prompt']}</p>"
                        f"<p>Solution: {concept['exercises'][0]['reference_solution']}</p>"),
        "key_points": [concept["summary"]],
        "audio_script": f"Here is a quick refresher on {concept['title']}. {concept['summary']}",
    }, "mock"
def tts_lesson_audio(text, output_file_path):
    """
    Render a lesson audio_script to an mp3 with OpenAI TTS (same service as
    apps/voice/tts.py). Returns the file path, or None in mock mode / on failure.
    """
    ensure_env_placeholders()
    api_key = None
    for key_name in ["OPENAI_API_KEY_TTS", "OPENAI_API_KEY_LOCAL"]:
        if _has_real_key(key_name):
            api_key = os.environ[key_name]
            break
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        with client.audio.speech.with_streaming_response.create(
            model="tts-1", voice="nova", input=text[:4000],
        ) as response:
            response.stream_to_file(output_file_path)
        return output_file_path
    except Exception as e:
        print(f"TTS failed ({e}); lesson will be text-only")
        return None
