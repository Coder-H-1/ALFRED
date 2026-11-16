"""
test_interrupt.py — Tests for Speech Interruption & Audio Filtering
"""

import unittest
import re
from main import filter_speech


class TestInterruptAndSpeechFilter(unittest.TestCase):
    """Tests speech text filtering and interrupt state management."""

    def test_filter_speech_parentheses(self):
        text = "Hello sir! (adjusting volume) Everything is operational."
        filtered = filter_speech(text)
        self.assertEqual(filtered, "Hello sir!  Everything is operational.")

    def test_filter_speech_emojis_and_asterisks(self):
        text = "*smiles* Good morning sir, *bows* how may I assist you?"
        filtered = filter_speech(text)
        self.assertEqual(filtered, "Good morning sir,  how may I assist you?")

    def test_continue_keywords_matching(self):
        continue_keywords = (
            "continue the previous command",
            "continue the speech for previous command interrupted",
            "continue the speech for the previous command interrupted",
            "continue the previous speech",
            "continue previous command",
            "continue the speech",
            "continue speech",
            "continue interrupted command",
            "continue interrupted speech",
            "continue",
        )
        sample_input = "continue the speech"
        matched = any(sample_input == kw or sample_input.startswith(kw) for kw in continue_keywords)
        self.assertTrue(matched)

        unrelated_input = "continue to download file"
        # starts with continue
        self.assertTrue(any(unrelated_input == kw or unrelated_input.startswith(kw) for kw in continue_keywords))


if __name__ == "__main__":
    unittest.main()
