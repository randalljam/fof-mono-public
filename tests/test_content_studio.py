# Run with: .venv/bin/python -m unittest tests.test_content_studio
#
# Offline tests for the content studio. The pure-logic tests (sampling, the
# visual and audio pass/fail policies, negative-prompt augmentation, provider
# dispatch, and the generate->verify->retry loop) run with no image or audio
# libraries via in-memory stubs; mock-audio tests use only the stdlib. The
# visual end-to-end tests are gated on Pillow; a final optional live-vision
# test runs the REAL Claude verifier only when CONTENT_STUDIO_LIVE_VISION=1
# and an Anthropic key is set.

import os
import sys
import tempfile
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.content_studio.frames import evenly_spaced_indices
from apps.content_studio.prompts import augment_negative_prompt, BASE_NEGATIVE_PROMPT
from apps.content_studio.verify import apply_policy, VisualVerifier
from apps.content_studio.verify_audio import (
    AudioVerifier, audio_policy, text_similarity, normalize_text, wav_duration_s,
)
from apps.content_studio.models import (
    AnimationRequest, VideoRequest, AudioRequest, MediaResult, VerifyResult,
)
from apps.content_studio.pipeline import generate_and_verify, default_verifier_for
from apps.content_studio.providers.base import MediaProvider, ProviderError
from apps.content_studio.providers.mock import MockProvider


### Shared fakes / fixtures
def clean_assessment(**over):
    """A raw assessment dict for a flawless clip; override fields via kwargs."""
    raw = dict(
        overall_pass=True, overall_score=88,
        scores=dict(anatomy=9, identity=9, temporal=8, artifacts=8, adherence=8),
        extra_limbs_detected=False, issues=[], summary="clean",
        recommended_negative_prompt="",
    )
    raw.update(over)
    return raw
class StubCodec:
    """In-memory codec: frames are plain strings, encoding is identity-ish."""
    def read_frames(self, result):
        return list(result.frames)
    def frame_png_b64(self, frame):
        return f"B64({frame})"
    def image_png_b64(self, path):
        return f"REF({path})"
class StubProvider(MediaProvider):
    """Records every request and returns a fixed number of in-memory frames."""
    name = "stub"
    def __init__(self, frame_count=10):
        self.frame_count = frame_count
        self.requests = []
    def _make(self, request):
        self.requests.append(request)
        frames = [f"frame{i}" for i in range(self.frame_count)]
        return MediaResult(frames=frames, provider=self.name, request=request)
    def generate_animation(self, request):
        return self._make(request)
    def generate_video(self, request):
        return self._make(request)
class ScriptedVerifier:
    """Returns a scripted list of VerifyResults and records what it saw."""
    def __init__(self, verdicts):
        self.verdicts = list(verdicts)
        self.seen = []
        self.calls = 0
    def assess(self, result, request):
        self.seen.append((result, request))
        v = self.verdicts[min(self.calls, len(self.verdicts) - 1)]
        self.calls += 1
        return v

### Frame sampling
class TestFrameSampling(unittest.TestCase):
    def test_count_geq_total_returns_all(self):
        self.assertEqual(evenly_spaced_indices(4, 6), [0, 1, 2, 3])
    def test_includes_endpoints(self):
        idx = evenly_spaced_indices(10, 4)
        self.assertEqual(idx[0], 0)
        self.assertEqual(idx[-1], 9)
        self.assertEqual(len(idx), 4)
    def test_single_count_picks_middle(self):
        self.assertEqual(evenly_spaced_indices(10, 1), [5])
    def test_ascending_and_unique(self):
        idx = evenly_spaced_indices(7, 5)
        self.assertEqual(idx, sorted(idx))
        self.assertEqual(len(idx), len(set(idx)))
    def test_degenerate_inputs(self):
        self.assertEqual(evenly_spaced_indices(0, 5), [])
        self.assertEqual(evenly_spaced_indices(5, 0), [])

### Negative-prompt augmentation
class TestNegativePrompt(unittest.TestCase):
    def test_merge_dedups_case_insensitively(self):
        merged = augment_negative_prompt("extra arms, flicker", "Extra Arms, melted face")
        parts = [p.strip() for p in merged.split(",")]
        self.assertEqual(parts, ["extra arms", "flicker", "melted face"])
    def test_empty_inputs(self):
        self.assertEqual(augment_negative_prompt("", ""), "")
        self.assertEqual(augment_negative_prompt("warping", ""), "warping")
        self.assertEqual(augment_negative_prompt("", "warping"), "warping")
    def test_base_prompt_is_nonempty(self):
        self.assertIn("extra arms", BASE_NEGATIVE_PROMPT)

### Requests and dispatch
class TestRequestsAndDispatch(unittest.TestCase):
    def test_copy_with_preserves_subclass_and_fields(self):
        r = VideoRequest(prompt="a dragon", resolution="480p", seed=7)
        r2 = r.copy_with(seed=42)
        self.assertIsInstance(r2, VideoRequest)
        self.assertEqual(r2.seed, 42)
        self.assertEqual(r2.resolution, "480p")
        self.assertEqual(r2.media_kind, "video")
    def test_audio_request_validation(self):
        with self.assertRaises(ValueError):
            AudioRequest(audio_kind="speech")           # speech needs text
        with self.assertRaises(ValueError):
            AudioRequest(audio_kind="music")            # music needs prompt
        with self.assertRaises(ValueError):
            AudioRequest(text="hi", audio_kind="noise") # unknown kind
    def test_audio_description_property(self):
        speech = AudioRequest(text="hello world", audio_kind="speech")
        sfx = AudioRequest(prompt="a door slam", audio_kind="sfx")
        self.assertEqual(speech.description, "hello world")
        self.assertEqual(sfx.description, "a door slam")
    def test_dispatch_unsupported_kind_raises(self):
        provider = StubProvider()  # no generate_audio
        with self.assertRaises(ProviderError):
            provider.generate(AudioRequest(text="hi"))
        self.assertEqual(provider.supported_kinds(), ("animation", "video"))
    def test_default_verifier_selection(self):
        from apps.content_studio.verify_audio import AudioVerifier as AV
        from apps.content_studio.verify import VisualVerifier as VV
        self.assertIsInstance(default_verifier_for(AudioRequest(text="hi")), AV)
        self.assertIsInstance(default_verifier_for(VideoRequest(prompt="x")), VV)
        self.assertIsInstance(
            default_verifier_for(AnimationRequest(image_path="a.png", prompt="x")), VV)

### Visual verifier policy
class TestVisualPolicy(unittest.TestCase):
    def test_clean_passes(self):
        self.assertTrue(apply_policy(clean_assessment()).passed)
    def test_extra_limbs_fail_even_if_high_score(self):
        r = apply_policy(clean_assessment(extra_limbs_detected=True))
        self.assertFalse(r.passed)
        self.assertTrue(r.extra_limbs)
    def test_critical_issue_fails(self):
        issues = [dict(category="anatomy", severity="critical", description="3 arms")]
        r = apply_policy(clean_assessment(issues=issues))
        self.assertFalse(r.passed)
        self.assertEqual(len(r.critical_issues()), 1)
    def test_low_anatomy_fails(self):
        r = apply_policy(clean_assessment(scores=dict(
            anatomy=5, identity=9, temporal=8, artifacts=8, adherence=8)))
        self.assertFalse(r.passed)
    def test_low_identity_fails(self):
        r = apply_policy(clean_assessment(scores=dict(
            anatomy=9, identity=4, temporal=8, artifacts=8, adherence=8)))
        self.assertFalse(r.passed)
    def test_low_temporal_fails(self):
        r = apply_policy(clean_assessment(scores=dict(
            anatomy=9, identity=9, temporal=3, artifacts=8, adherence=8)))
        self.assertFalse(r.passed)
    def test_low_overall_fails(self):
        self.assertFalse(apply_policy(clean_assessment(overall_score=50)).passed)
    def test_thresholds_are_configurable(self):
        # A strict anatomy floor of 10 should fail an otherwise-clean clip.
        r = apply_policy(clean_assessment(), min_anatomy=10)
        self.assertFalse(r.passed)
    def test_visual_verifier_samples_and_passes_reference(self):
        seen = {}
        def asker(ref, frames, desc):
            seen.update(ref=ref, frames=list(frames), desc=desc)
            return clean_assessment()
        verifier = VisualVerifier(asker=asker, codec=StubCodec(), sample_frames=4)
        result = MediaResult(frames=[f"f{i}" for i in range(9)])
        req = AnimationRequest(image_path="dragon.png", prompt="the dragon waves")
        verdict = verifier.assess(result, req)
        self.assertTrue(verdict.passed)
        self.assertEqual(len(seen["frames"]), 4)
        self.assertEqual(seen["ref"], "REF(dragon.png)")
        self.assertEqual(seen["desc"], "the dragon waves")
    def test_visual_verifier_t2v_has_no_reference(self):
        seen = {}
        def asker(ref, frames, desc):
            seen["ref"] = ref
            return clean_assessment()
        verifier = VisualVerifier(asker=asker, codec=StubCodec(), sample_frames=2)
        result = MediaResult(frames=["a", "b", "c"])
        verdict = verifier.assess(result, VideoRequest(prompt="a castle at dusk"))
        self.assertTrue(verdict.passed)
        self.assertIsNone(seen["ref"])  # text-to-video: no reference image
    def test_visual_verifier_rejects_empty_candidate_without_calling_model(self):
        def asker(ref, frames, desc):
            raise AssertionError("empty candidates should fail before model call")
        verifier = VisualVerifier(asker=asker, codec=StubCodec())
        result = MediaResult(frames=[])
        verdict = verifier.assess(result, VideoRequest(prompt="a castle at dusk"))
        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.score, 0)
        self.assertEqual(verdict.critical_issues()[0].category, "output")

### Audio verifier policy
class TestAudioPolicy(unittest.TestCase):
    def test_normalize_and_similarity(self):
        self.assertEqual(normalize_text("  Hello,   World! "), "hello world")
        self.assertEqual(text_similarity("Hello world", "hello, WORLD!"), 1.0)
        self.assertLess(text_similarity("hello world", "goodbye moon"), 0.5)
    def test_similarity_preserves_multilingual_text(self):
        self.assertEqual(normalize_text("Grüße!"), "grusse")
        self.assertEqual(text_similarity("Grüße", "GRUSSE"), 1.0)
        self.assertEqual(text_similarity("你好，世界", "你好 世界"), 1.0)
        self.assertLess(text_similarity("你好", "再见"), 0.5)
    def test_speech_similarity_pass_and_fail(self):
        good = audio_policy("speech", similarity=0.95, transcript="hello")
        self.assertTrue(good.passed)
        self.assertEqual(good.score, 95)
        bad = audio_policy("speech", similarity=0.40, transcript="gargle blargh")
        self.assertFalse(bad.passed)
        self.assertTrue(any(i.severity == "critical" for i in bad.issues))
    def test_missing_file_is_critical(self):
        r = audio_policy("music", file_ok=False)
        self.assertFalse(r.passed)
        self.assertEqual(r.score, 0)
    def test_duration_mismatch_fails(self):
        r = audio_policy("sfx", duration_s=8.0, expected_duration_s=3.0,
                         duration_tolerance_s=1.5)
        self.assertFalse(r.passed)
        self.assertTrue(any(i.category == "duration" for i in r.issues))
    def test_duration_within_tolerance_passes(self):
        r = audio_policy("sfx", duration_s=3.9, expected_duration_s=3.0,
                         duration_tolerance_s=1.5)
        self.assertTrue(r.passed)
    def test_unverified_speech_is_lenient_by_default(self):
        r = audio_policy("speech", similarity=None, transcription_available=False)
        self.assertTrue(r.passed)
        self.assertTrue(any(i.severity == "minor" for i in r.issues))
    def test_unverified_speech_fails_when_required(self):
        r = audio_policy("speech", similarity=None, transcription_available=False,
                         require_transcription=True)
        self.assertFalse(r.passed)
    def test_wav_duration_of_mock_output(self):
        provider = MockProvider(output_dir=tempfile.mkdtemp())
        result = provider.generate(AudioRequest(prompt="a chime", audio_kind="sfx",
                                                duration_s=2.0))
        self.assertTrue(os.path.exists(result.output_path))
        duration = wav_duration_s(result.output_path)
        self.assertIsNotNone(duration)
        self.assertAlmostEqual(duration, 2.0, delta=0.1)
    def test_audio_verifier_with_fake_transcriber(self):
        provider = MockProvider(output_dir=tempfile.mkdtemp())
        req = AudioRequest(text="welcome back adventurer", audio_kind="speech")
        result = provider.generate(req)
        good = AudioVerifier(transcriber=lambda p: "Welcome back, adventurer!")
        self.assertTrue(good.assess(result, req).passed)
        bad = AudioVerifier(transcriber=lambda p: "completely different words entirely")
        verdict = bad.assess(result, req)
        self.assertFalse(verdict.passed)
        self.assertIn("similarity", verdict.scores)

### Pipeline orchestration
def _fail(rec=""):
    return VerifyResult(passed=False, score=30, scores=dict(anatomy=3),
                        extra_limbs=True, recommended_negative_prompt=rec)
def _pass():
    return VerifyResult(passed=True, score=90)
def _anim_req():
    return AnimationRequest(image_path="dragon.png", prompt="the dragon waves")
class TestPipeline(unittest.TestCase):
    def test_passes_first_attempt(self):
        provider = StubProvider()
        verifier = ScriptedVerifier([_pass()])
        pr = generate_and_verify(provider, _anim_req(), verifier=verifier,
                                 max_attempts=3)
        self.assertTrue(pr.passed)
        self.assertEqual(len(pr.attempts), 1)
        self.assertEqual(len(provider.requests), 1)
    def test_retries_then_passes_and_strengthens_negative(self):
        provider = StubProvider()
        verifier = ScriptedVerifier([_fail(rec="duplicated tail"), _pass()])
        pr = generate_and_verify(provider, _anim_req(), verifier=verifier,
                                 max_attempts=3)
        self.assertTrue(pr.passed)
        self.assertEqual(len(pr.attempts), 2)
        # The first request seeds the base negative prompt; the second adds the
        # verifier's specific complaint.
        self.assertNotIn("duplicated tail", provider.requests[0].negative_prompt)
        self.assertIn("duplicated tail", provider.requests[1].negative_prompt)
        self.assertIn("extra arms", provider.requests[0].negative_prompt)
    def test_never_passes_returns_best_effort(self):
        provider = StubProvider()
        # Scores 30, 55, 40 across three rounds -> best is the score-55 one.
        verifier = ScriptedVerifier([
            VerifyResult(passed=False, score=30, recommended_negative_prompt="a"),
            VerifyResult(passed=False, score=55, recommended_negative_prompt="b"),
            VerifyResult(passed=False, score=40, recommended_negative_prompt="c"),
        ])
        pr = generate_and_verify(provider, _anim_req(), verifier=verifier,
                                 max_attempts=3)
        self.assertFalse(pr.passed)
        self.assertEqual(len(pr.attempts), 3)
        self.assertEqual(pr.verdict.score, 55)  # kept the best-scoring candidate
    def test_best_of_n_candidates_per_attempt(self):
        provider = StubProvider()
        # Round 1 has two candidates: first fails, second passes -> stop in round 1.
        verifier = ScriptedVerifier([_fail(), _pass()])
        pr = generate_and_verify(provider, _anim_req(), verifier=verifier,
                                 max_attempts=3, candidates_per_attempt=2)
        self.assertTrue(pr.passed)
        self.assertEqual(len(provider.requests), 2)  # both candidates generated
    def test_retries_preserve_initial_seed_and_candidate_files(self):
        provider = MockProvider(output_dir=tempfile.mkdtemp())
        verifier = ScriptedVerifier([
            VerifyResult(passed=False, score=90),
            VerifyResult(passed=False, score=10),
        ])
        req = AudioRequest(text="hello there", audio_kind="speech", seed=17)
        pr = generate_and_verify(provider, req, verifier=verifier, max_attempts=2)
        first_result = pr.attempts[0][0]
        second_result = pr.attempts[1][0]
        self.assertEqual(first_result.request.seed, 17)
        self.assertEqual(second_result.request.seed, 18)
        self.assertNotEqual(first_result.output_path, second_result.output_path)
        self.assertTrue(os.path.exists(first_result.output_path))
        self.assertTrue(os.path.exists(second_result.output_path))
        self.assertEqual(pr.output_path, first_result.output_path)
    def test_nonpositive_attempt_counts_are_rejected(self):
        provider = StubProvider()
        verifier = ScriptedVerifier([_pass()])
        with self.assertRaisesRegex(ValueError, "max_attempts"):
            generate_and_verify(
                provider, _anim_req(), verifier=verifier, max_attempts=0)
        with self.assertRaisesRegex(ValueError, "candidates_per_attempt"):
            generate_and_verify(
                provider, _anim_req(), verifier=verifier,
                candidates_per_attempt=0)
    def test_audio_pipeline_no_negative_prompt_seeding(self):
        # Audio requests must not get the visual anti-jank negative prompt.
        provider = MockProvider(output_dir=tempfile.mkdtemp())
        verifier = ScriptedVerifier([_pass()])
        req = AudioRequest(text="hello there", audio_kind="speech")
        pr = generate_and_verify(provider, req, verifier=verifier, max_attempts=2)
        self.assertTrue(pr.passed)
        _, seen_req = verifier.seen[0]
        self.assertEqual(seen_req.negative_prompt, "")
    def test_video_pipeline_with_stub(self):
        provider = StubProvider()
        verifier = ScriptedVerifier([_pass()])
        pr = generate_and_verify(provider, VideoRequest(prompt="a castle at dusk"),
                                 verifier=verifier, max_attempts=2)
        self.assertTrue(pr.passed)
        self.assertIn("extra arms", provider.requests[0].negative_prompt)

### Mock audio synthesis (stdlib only, no PIL needed)
class TestMockAudio(unittest.TestCase):
    def test_speech_duration_scales_with_words(self):
        provider = MockProvider(output_dir=tempfile.mkdtemp())
        short = provider.generate(AudioRequest(text="hi", audio_kind="speech"))
        long = provider.generate(AudioRequest(
            text="one two three four five six seven eight", audio_kind="speech"))
        self.assertLess(wav_duration_s(short.output_path),
                        wav_duration_s(long.output_path))
    def test_all_kinds_produce_nonempty_wavs(self):
        provider = MockProvider(output_dir=tempfile.mkdtemp())
        for req in (AudioRequest(text="hello", audio_kind="speech"),
                    AudioRequest(prompt="calm melody", audio_kind="music",
                                 duration_s=1.0),
                    AudioRequest(prompt="a whoosh", audio_kind="sfx",
                                 duration_s=0.5)):
            result = provider.generate(req)
            self.assertTrue(os.path.getsize(result.output_path) > 1000)

### End-to-end visual (requires Pillow)
try:
    from PIL import Image, ImageDraw
    _HAS_PIL = True
except Exception:
    _HAS_PIL = False
def _make_test_image(path):
    """Draw a simple character (a circle 'body' with two eyes) and save it."""
    img = Image.new("RGB", (160, 160), (230, 220, 245))
    d = ImageDraw.Draw(img)
    d.ellipse([40, 40, 120, 140], fill=(240, 120, 170))   # body
    d.ellipse([60, 70, 75, 85], fill=(20, 20, 20))         # eye
    d.ellipse([90, 70, 105, 85], fill=(20, 20, 20))        # eye
    img.save(path)
    return path
@unittest.skipUnless(_HAS_PIL, "Pillow not installed")
class TestEndToEndOffline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.image = _make_test_image(os.path.join(self.tmp, "dragon.png"))
    def _provider(self, defect=None):
        return MockProvider(output_dir=os.path.join(self.tmp, "out"), defect=defect)
    def test_clean_clip_passes_and_writes_file(self):
        from apps.content_studio.imaging import load_animation_frames
        verifier = VisualVerifier(asker=lambda ref, frames, desc: clean_assessment(),
                                  sample_frames=4)
        req = AnimationRequest(image_path=self.image, prompt="the dragon breathes",
                               duration_s=1.0, fps=8)
        pr = generate_and_verify(self._provider(), req, verifier=verifier,
                                 max_attempts=2)
        self.assertTrue(pr.passed)
        self.assertEqual(len(pr.attempts), 1)
        self.assertTrue(os.path.exists(pr.output_path))
        frames = load_animation_frames(pr.output_path)
        self.assertGreater(len(frames), 1)   # it is actually animated
    def test_defect_clip_is_rejected_best_effort(self):
        # Verifier (here, a stand-in) flags the injected extra limb; the pipeline
        # should reject every round and return a best-effort result.
        flagged = clean_assessment(
            overall_score=35, extra_limbs_detected=True,
            scores=dict(anatomy=2, identity=7, temporal=6, artifacts=5, adherence=6),
            issues=[dict(category="anatomy", severity="critical",
                         description="duplicated limb", frame_index=0)],
            recommended_negative_prompt="extra limb, duplicated arm",
        )
        verifier = VisualVerifier(asker=lambda ref, frames, desc: flagged,
                                  sample_frames=4)
        req = AnimationRequest(image_path=self.image, prompt="the dragon waves",
                               duration_s=1.0, fps=8)
        pr = generate_and_verify(self._provider(defect="extra_limb"), req,
                                 verifier=verifier, max_attempts=2)
        self.assertFalse(pr.passed)
        self.assertEqual(len(pr.attempts), 2)
        self.assertTrue(pr.verdict.extra_limbs)
    def test_mock_t2v_video_generates_frames(self):
        provider = self._provider()
        req = VideoRequest(prompt="a golden orb drifts across a night sky",
                           duration_s=1.0, extra={"fps": 8})
        result = provider.generate(req)
        self.assertGreaterEqual(len(result.frames), 7)
        self.assertTrue(result.output_path.endswith(".gif"))
        verifier = VisualVerifier(asker=lambda ref, frames, desc: clean_assessment(),
                                  sample_frames=3)
        self.assertTrue(verifier.assess(result, req).passed)

### Policy coercion (malformed vision tool payloads)
class TestPolicyCoercion(unittest.TestCase):
    def test_scores_json_string_does_not_unpack_error(self):
        # Models sometimes emit nested objects as JSON strings; dict(str) raises
        # ValueError ("dictionary update sequence element #0 has length 1").
        raw = clean_assessment(
            overall_score=20,
            extra_limbs_detected=True,
            scores='{"anatomy": 1, "identity": 2, "temporal": 3, '
                   '"artifacts": 4, "adherence": 5}',
        )
        r = apply_policy(raw)
        self.assertFalse(r.passed)
        self.assertEqual(r.scores.get("anatomy"), 1)
        self.assertEqual(r.scores.get("identity"), 2)
    def test_issue_json_string_is_accepted(self):
        raw = clean_assessment(
            overall_score=90,
            issues=['{"category": "anatomy", "severity": "critical", '
                    '"description": "extra arm", "frame_index": 0}'],
        )
        r = apply_policy(raw)
        self.assertFalse(r.passed)
        self.assertEqual(len(r.issues), 1)
        self.assertEqual(r.issues[0].severity, "critical")
    def test_whole_issues_json_string_and_severity_case_are_accepted(self):
        raw = clean_assessment(
            issues='[{"category": "identity", "severity": "CRITICAL", '
                   '"description": "subject changed"}]',
        )
        r = apply_policy(raw)
        self.assertFalse(r.passed)
        self.assertEqual(r.issues[0].severity, "critical")
    def test_numeric_and_boolean_strings_are_coerced(self):
        raw = clean_assessment(
            overall_score="88.0",
            extra_limbs_detected="false",
            scores={
                "anatomy": "9", "identity": "9.0", "temporal": "8",
                "artifacts": "8", "adherence": "8",
            },
        )
        r = apply_policy(raw)
        self.assertTrue(r.passed)
        self.assertFalse(r.extra_limbs)
        self.assertEqual(r.score, 88)
    def test_unparseable_required_score_fails_closed(self):
        raw = clean_assessment(scores={
            "anatomy": "unknown", "identity": 9, "temporal": 8,
            "artifacts": 8, "adherence": 8,
        })
        self.assertFalse(apply_policy(raw).passed)
    def test_unparseable_issue_fails_closed(self):
        raw = clean_assessment(issues="not-json")
        r = apply_policy(raw)
        self.assertFalse(r.passed)
        self.assertEqual(r.critical_issues()[0].category, "verifier")

### Optional: live Claude verification (opt-in + real API key)
@unittest.skipUnless(
    _HAS_PIL
    and os.environ.get("CONTENT_STUDIO_LIVE_VISION") == "1"
    and (os.environ.get("ANTHROPIC_API_KEY")
         or os.environ.get("ANTHROPIC_API_KEY_LOCAL")),
    "set CONTENT_STUDIO_LIVE_VISION=1 with Pillow + Anthropic API key",
)
class TestLiveVision(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.image = _make_test_image(os.path.join(self.tmp, "dragon.png"))
    def test_real_verifier_flags_extra_limb(self):
        provider = MockProvider(output_dir=os.path.join(self.tmp, "out"),
                                defect="extra_limb")
        req = AnimationRequest(image_path=self.image, prompt="the character waves",
                               duration_s=1.0, fps=8)
        result = provider.generate(req)
        verdict = VisualVerifier(sample_frames=4).assess(result, req)
        # The real model should not wave a grossly duplicated-limb clip through.
        self.assertFalse(verdict.passed)


if __name__ == "__main__":
    unittest.main()

# ===== END OF FILE tests/test_content_studio.py =====
