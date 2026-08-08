import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.diar_backends import assign_words_to_speakers

class TestAssignWordsToSpeakers(unittest.TestCase):
    def test_midpoint_containment(self):
        words = [{"word": "hello", "start": 1.0, "end": 1.4}]
        turns = [{"speaker": "SPEAKER_00", "start": 0.0, "duration": 2.0}]
        assigned = assign_words_to_speakers(words, turns)
        self.assertEqual(assigned[0]["speaker"], "SPEAKER_00")
    def test_nearest_within_two_seconds_fallback(self):
        words = [{"word": "hello", "start": 2.6, "end": 2.8}]
        turns = [{"speaker": "SPEAKER_00", "start": 0.0, "duration": 1.0}]
        assigned = assign_words_to_speakers(words, turns)
        self.assertEqual(assigned[0]["speaker"], "SPEAKER_00")
    def test_unknown_beyond_two_seconds(self):
        words = [{"word": "hello", "start": 4.1, "end": 4.3}]
        turns = [{"speaker": "SPEAKER_00", "start": 0.0, "duration": 1.0}]
        assigned = assign_words_to_speakers(words, turns)
        self.assertEqual(assigned[0]["speaker"], "unknown")
    def test_empty_turns(self):
        words = [{"word": "hello", "start": 0.0, "end": 0.5}]
        assigned = assign_words_to_speakers(words, [])
        self.assertEqual(assigned[0]["speaker"], "unknown")

if __name__ == "__main__":
    unittest.main()
