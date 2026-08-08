# ===== START OF FILE apps/content_studio/prompts.py =====
# Prompts and prompt-augmentation for the content studio's visual verifier.
#
# The verifier system prompt is the heart of the app: it tells the vision model
# exactly what "janky" looks like so it reliably flags extra/duplicated limbs,
# melted faces, and identity drift instead of waving the clip through.


### Verifier rubric
VERIFIER_SYSTEM_PROMPT = """\
You are a meticulous animation/video quality inspector. You are shown a verbal
description of an intended clip, several OUTPUT FRAMES sampled in order from a
generated clip, and — when the clip was generated from a source image — a
REFERENCE image of the character/scene. Your job is to decide whether the
generated clip is good enough to ship, and to catch the specific failure modes
that image-to-video and text-to-video models produce.

Be skeptical and literal. It is far better to flag a real problem than to wave a
broken clip through. Image-to-video models frequently produce grotesque defects
that a casual glance misses, so inspect every frame carefully.

Judge these dimensions independently:

1. ANATOMY / STRUCTURE (the most important). Look hard for:
   - extra or duplicated limbs, arms, hands, fingers, legs, feet, wings, tails,
     heads, eyes, or mouths that the reference does not have;
   - missing limbs or features that the reference does have;
   - fused, melted, smeared, or "candle-wax" body parts;
   - limbs bending the wrong way or attached at impossible places;
   - disconnected or floating body parts;
   - malformed, asymmetric, or collapsing faces.
   If you see ANY of these, set extra_limbs_detected appropriately and lower the
   anatomy score sharply. This is the failure this whole pipeline exists to catch.

2. IDENTITY PRESERVATION. Does the character in the output frames still match the
   reference — same species, same color palette, same proportions, same defining
   features? A character that morphs into a different creature fails identity.
   If NO reference image was provided (text-to-video), judge identity as internal
   consistency instead: the subject must remain the same entity throughout the
   clip and match the description.

3. TEMPORAL CONSISTENCY. Across the sampled frames, is it the SAME character with
   stable colors, shapes, and proportions, or does it flicker between forms?

4. MOTION / ARTIFACTS. Warping, ghosting, smearing, texture crawl, background
   tearing, flicker, or jelly-like wobble.

5. PROMPT ADHERENCE. Does the visible motion and content match the intended
   animation description?

Score each dimension 0-10 (10 = flawless). Give an overall_score 0-100. List
every issue you find with a severity: "critical" for anything grotesque or
identity-breaking, "major" for clearly visible flaws, "minor" for small nits.
For each issue, set frame_index to the 0-based index of the worst offending
sampled frame, or null if it spans the whole clip.

Finally, write a recommended_negative_prompt: a short comma-separated phrase that
should be ADDED to the next generation attempt to steer away from the problems
you saw (e.g. "extra arms, duplicated limbs, deformed hands, melted face"). If
the clip is clean, leave it empty.

Always answer by calling the report_animation_quality tool. Do not answer in prose.
"""

# JSON-schema tool the verifier model is forced to call. Using a forced tool call
# (rather than free-form text) guarantees a machine-readable, policy-checkable
# verdict every time.
VERIFIER_TOOL = {
    "name": "report_animation_quality",
    "description": "Report the structured quality assessment of the generated animation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "overall_pass": {
                "type": "boolean",
                "description": "Your holistic call on whether the clip is shippable.",
            },
            "overall_score": {
                "type": "integer",
                "description": "Overall quality 0-100.",
            },
            "scores": {
                "type": "object",
                "description": "Per-dimension scores, each 0-10.",
                "properties": {
                    "anatomy": {"type": "integer"},
                    "identity": {"type": "integer"},
                    "temporal": {"type": "integer"},
                    "artifacts": {"type": "integer"},
                    "adherence": {"type": "integer"},
                },
                "required": ["anatomy", "identity", "temporal", "artifacts", "adherence"],
            },
            "extra_limbs_detected": {
                "type": "boolean",
                "description": "True if any extra/duplicated/fused/missing limb or "
                               "grotesque anatomical defect appears in any frame.",
            },
            "issues": {
                "type": "array",
                "description": "Every problem found, most severe first.",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "major", "minor"],
                        },
                        "description": {"type": "string"},
                        "frame_index": {
                            "type": ["integer", "null"],
                            "description": "0-based index of the worst sampled frame, "
                                           "or null if the issue spans the clip.",
                        },
                    },
                    "required": ["category", "severity", "description"],
                },
            },
            "summary": {
                "type": "string",
                "description": "One or two sentence summary of the verdict.",
            },
            "recommended_negative_prompt": {
                "type": "string",
                "description": "Comma-separated terms to add to the next attempt to "
                               "avoid the problems found; empty if the clip is clean.",
            },
        },
        "required": [
            "overall_pass", "overall_score", "scores", "extra_limbs_detected",
            "issues", "summary", "recommended_negative_prompt",
        ],
    },
}

### Negative-prompt augmentation
# Baseline anti-jank guidance folded into every generation request. This is the
# first line of defense; the verifier's per-run feedback is the second.
BASE_NEGATIVE_PROMPT = (
    "extra limbs, extra arms, extra legs, extra fingers, duplicated body parts, "
    "fused limbs, melted features, deformed anatomy, mutated hands, malformed face, "
    "disconnected body parts, morphing into a different character, flicker, warping"
)
def augment_negative_prompt(current, recommended):
    """Merge a recommended negative prompt into the current one, de-duplicated.

    Terms are comma-separated. Order is preserved (current terms first), and
    case-insensitive duplicates are dropped so the prompt does not balloon across
    retry rounds.

    :param current: the existing negative prompt string (may be empty).
    :param recommended: the verifier's recommended additions (may be empty).
    :return: the merged negative prompt string.
    """
    terms = []
    seen = set()
    for chunk in [current or "", recommended or ""]:
        for term in chunk.split(","):
            term = term.strip()
            if not term:
                continue
            key = term.lower()
            if key in seen:
                continue
            seen.add(key)
            terms.append(term)
    return ", ".join(terms)

# ===== END OF FILE apps/content_studio/prompts.py =====
