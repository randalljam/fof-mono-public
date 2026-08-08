import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.diar_formats import (
    deepgram_words_to_turns,
    parse_timestamp_to_seconds,
    read_rttm,
    segments_to_rttm_turns,
    segments_to_seglst,
    stem_to_session_id,
    wer_normalize,
    write_rttm,
)
from core.diar_metrics import compute_cpwer, compute_diarization_metrics, compute_tcpwer

def _seg(timestamp, speaker, dialogue, start_secs):
    return {
        "timestamp": timestamp,
        "speaker_full": speaker,
        "speaker_name": speaker,
        "dialogue": dialogue,
        "start_secs": start_secs,
    }

class TestTimestampAndNormalize(unittest.TestCase):
    def test_parse_timestamp_forms(self):
        self.assertEqual(parse_timestamp_to_seconds("0:41"), 41.0)
        self.assertEqual(parse_timestamp_to_seconds("1:02:03"), 3723.0)
        self.assertIsNone(parse_timestamp_to_seconds("n/a"))
        self.assertIsNone(parse_timestamp_to_seconds(None))
    def test_wer_normalize(self):
        self.assertEqual(wer_normalize("Hello, World! It's me."), "hello world it's me")
        self.assertEqual(wer_normalize(""), "")

class TestRttmRoundTrip(unittest.TestCase):
    def test_write_read_rttm(self):
        turns = [
            {"uri": "s1", "speaker": "A", "start": 0.0, "duration": 2.5},
            {"uri": "s1", "speaker": "B", "start": 2.5, "duration": 1.0},
        ]
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "s1.rttm")
            write_rttm(turns, path)
            back = read_rttm(path)
        self.assertEqual(len(back), 2)
        self.assertEqual(back[0]["speaker"], "A")
        self.assertAlmostEqual(back[1]["start"], 2.5)
        self.assertAlmostEqual(back[1]["duration"], 1.0)
    def test_multiword_speaker_round_trip(self):
        """Spaces in labels must not collapse distinct speakers on read."""
        from core.diar_formats import rttm_speaker_id

        turns = [
            {"uri": "s1", "speaker": "Speaker 0", "start": 0.0, "duration": 1.0},
            {"uri": "s1", "speaker": "Speaker 1", "start": 1.0, "duration": 1.0},
            {"uri": "s1", "speaker": "Dale Pfau (EPC Chair)", "start": 2.0, "duration": 1.0},
        ]
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "multi.rttm")
            write_rttm(turns, path)
            back = read_rttm(path)
        self.assertEqual([t["speaker"] for t in back], [rttm_speaker_id(t["speaker"]) for t in turns])
        self.assertEqual(len({t["speaker"] for t in back}), 3)
    def test_read_legacy_spaced_speaker_labels(self):
        """Older RTTMs that wrote 'Speaker 0' with a space still parse distinctly."""
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "legacy.rttm")
            with open(path, "w") as f:
                f.write(
                    "SPEAKER s1 1 0.000 1.000 <NA> <NA> Speaker 0 <NA> <NA>\n"
                    "SPEAKER s1 1 1.000 1.000 <NA> <NA> Speaker 1 <NA> <NA>\n"
                )
            back = read_rttm(path)
        self.assertEqual([t["speaker"] for t in back], ["Speaker 0", "Speaker 1"])

class TestMdConverters(unittest.TestCase):
    def setUp(self):
        self.segments = [
            _seg("0:00", "Alice", "Hello there, everyone.", 0.0),
            _seg("0:10", "Bob", "Hi Alice.", 10.0),
            _seg("0:15", "Alice", "Let's begin.", 15.0),
        ]
    def test_segments_to_seglst(self):
        records = segments_to_seglst(self.segments, "ep1")
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0]["speaker"], "Alice")
        self.assertEqual(records[0]["words"], "hello there everyone")
        self.assertEqual(records[0]["start_time"], 0.0)
        self.assertEqual(records[0]["end_time"], 10.0)
    def test_segments_to_rttm_turns_durations(self):
        turns = segments_to_rttm_turns(self.segments, "ep1", tail_duration=4.0)
        self.assertEqual(len(turns), 3)
        self.assertAlmostEqual(turns[0]["duration"], 10.0)
        self.assertAlmostEqual(turns[2]["duration"], 4.0)

class TestDeepgramConverters(unittest.TestCase):
    def test_words_group_into_turns(self):
        words = [
            {"word": "hi", "punctuated_word": "Hi", "start": 0.0, "end": 0.4, "speaker": 0},
            {"word": "there", "punctuated_word": "there.", "start": 0.4, "end": 0.8, "speaker": 0},
            {"word": "hello", "punctuated_word": "Hello", "start": 1.0, "end": 1.5, "speaker": 1},
        ]
        turns = deepgram_words_to_turns(words, "s1")
        self.assertEqual(len(turns), 2)
        self.assertEqual(turns[0]["speaker"], "spk0")
        self.assertEqual(turns[0]["words"], "Hi there.")
        self.assertAlmostEqual(turns[0]["duration"], 0.8)
        self.assertEqual(turns[1]["speaker"], "spk1")

class TestSessionId(unittest.TestCase):
    def test_stem_sanitized(self):
        self.assertEqual(
            stem_to_session_id("2023-01-05_PV EPC Meeting"), "2023-01-05_PV-EPC-Meeting"
        )

class TestDiarizationMetrics(unittest.TestCase):
    def test_perfect_match_zero_der(self):
        ref = [
            {"speaker": "A", "start": 0.0, "duration": 5.0},
            {"speaker": "B", "start": 5.0, "duration": 5.0},
        ]
        hyp = [
            {"speaker": "x", "start": 0.0, "duration": 5.0},
            {"speaker": "y", "start": 5.0, "duration": 5.0},
        ]
        m = compute_diarization_metrics(ref, hyp, "s1")
        self.assertAlmostEqual(m["der_strict"], 0.0)
        self.assertAlmostEqual(m["jer"], 0.0)
        self.assertEqual(m["speaker_count_error"], 0)
    def test_boundary_shift_counts_confusion(self):
        ref = [
            {"speaker": "A", "start": 0.0, "duration": 5.0},
            {"speaker": "B", "start": 5.0, "duration": 5.0},
        ]
        hyp = [
            {"speaker": "x", "start": 0.0, "duration": 6.0},
            {"speaker": "y", "start": 6.0, "duration": 4.0},
        ]
        m = compute_diarization_metrics(ref, hyp, "s1")
        self.assertAlmostEqual(m["der_strict"], 0.1, places=5)
        self.assertLess(m["der_lenient"], m["der_strict"])

class TestCpwer(unittest.TestCase):
    def setUp(self):
        self.ref = [
            {"session_id": "s1", "speaker": "A", "words": "hello world how are you", "start_time": 0.0, "end_time": 2.0},
            {"session_id": "s1", "speaker": "B", "words": "i am fine thanks", "start_time": 2.0, "end_time": 4.0},
        ]
    def test_perfect_cpwer_zero(self):
        hyp = [dict(r, speaker=f"spk{i}") for i, r in enumerate(self.ref)]
        out = compute_cpwer(self.ref, hyp)
        self.assertAlmostEqual(out["combined"]["error_rate"], 0.0)
    def test_substitution_counted(self):
        hyp = [dict(self.ref[0], speaker="spk0"), dict(self.ref[1], speaker="spk1", words="i am fine thank you")]
        out = compute_cpwer(self.ref, hyp)
        self.assertEqual(out["combined"]["errors"], 2)
        self.assertAlmostEqual(out["combined"]["error_rate"], 2 / 9)
        tc = compute_tcpwer(self.ref, hyp, collar=5)
        self.assertEqual(tc["combined"]["errors"], 2)

if __name__ == "__main__":
    unittest.main()
