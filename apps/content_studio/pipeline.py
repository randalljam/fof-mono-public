# ===== START OF FILE apps/content_studio/pipeline.py =====
# The orchestration loop: generate -> verify -> regenerate.
#
# This is what turns a one-shot, occasionally-broken generator into something
# that reliably ships clean media: every candidate is inspected by a verifier
# appropriate to its media kind, bad ones are rejected, and the next attempt is
# regenerated — for visual media, with the verifier's specific complaints folded
# into the negative prompt. The best candidate seen is always kept, even if none
# fully passes.

from apps.content_studio import config
from apps.content_studio.models import PipelineResult, VISUAL_KINDS
from apps.content_studio.prompts import BASE_NEGATIVE_PROMPT, augment_negative_prompt


### Verifier selection
def default_verifier_for(request):
    """Construct the default verifier for a request's media kind.

    :param request: a MediaRequest.
    :return: a verifier object with an assess(result, request) method.
    """
    if request.media_kind == "audio":
        from apps.content_studio.verify_audio import AudioVerifier
        return AudioVerifier()
    from apps.content_studio.verify import VisualVerifier
    return VisualVerifier()

### Main loop
def generate_and_verify(provider, request, verifier=None, max_attempts=None,
                        candidates_per_attempt=None):
    """Generate, verify, and regenerate until a candidate passes or attempts run out.

    :param provider: a MediaProvider.
    :param request: the MediaRequest (animation / video / audio).
    :param verifier: an object with assess(result, request) -> VerifyResult;
                     default picks VisualVerifier or AudioVerifier by media kind.
    :param max_attempts: regenerate rounds before giving up (default from config).
    :param candidates_per_attempt: best-of-N within a round (default from config).
    :return: a PipelineResult (best media + verdict + full attempt history).
    """
    verifier = verifier or default_verifier_for(request)
    max_attempts = (config.DEFAULT_MAX_ATTEMPTS
                    if max_attempts is None else max_attempts)
    candidates_per_attempt = (config.DEFAULT_CANDIDATES_PER_ATTEMPT
                              if candidates_per_attempt is None
                              else candidates_per_attempt)
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1.")
    if candidates_per_attempt < 1:
        raise ValueError("candidates_per_attempt must be at least 1.")

    # Seed visual generations with the baseline anti-jank negative prompt.
    visual = request.media_kind in VISUAL_KINDS
    current = request
    if visual:
        current = request.copy_with(
            negative_prompt=augment_negative_prompt(request.negative_prompt,
                                                    BASE_NEGATIVE_PROMPT))

    attempts = []
    best = None  # (result, verdict)
    for attempt_i in range(max_attempts):
        last_fail = None
        for cand_i in range(candidates_per_attempt):
            candidate_i = attempt_i * candidates_per_attempt + cand_i
            req = current.copy_with(seed=_vary_seed(request.seed, candidate_i))
            result = provider.generate(req)
            verdict = verifier.assess(result, req)
            attempts.append((result, verdict))
            best = _pick_better(best, (result, verdict))
            if verdict.passed:
                return PipelineResult(result, verdict, True, attempts)
            last_fail = verdict
        # Whole round failed: strengthen the negative prompt (visual) and retry.
        if visual and last_fail and last_fail.recommended_negative_prompt:
            current = current.copy_with(
                negative_prompt=augment_negative_prompt(
                    current.negative_prompt, last_fail.recommended_negative_prompt))

    best_result, best_verdict = best
    return PipelineResult(best_result, best_verdict, best_verdict.passed, attempts)

### Helpers
def _pick_better(current_best, candidate):
    """Return whichever (result, verdict) pair is better.

    A passing candidate always beats a failing one; otherwise higher score wins.
    """
    if current_best is None:
        return candidate
    cb_verdict = current_best[1]
    cand_verdict = candidate[1]
    if cand_verdict.passed and not cb_verdict.passed:
        return candidate
    if cb_verdict.passed and not cand_verdict.passed:
        return current_best
    return candidate if cand_verdict.score > cb_verdict.score else current_best
def _vary_seed(seed, candidate_i):
    """Derive a distinct seed while preserving the caller's first seed."""
    if candidate_i == 0:
        return seed
    base = 0 if seed is None else int(seed)
    return base + candidate_i

# ===== END OF FILE apps/content_studio/pipeline.py =====
