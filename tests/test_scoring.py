"""Tests for score normalization and fallback behavior.

These tests exercise the pure-Python scoring logic without external API calls.
"""

import unittest

from detector.services.scoring import _clamp, calculate_final_score


class ScoreNormalizationTests(unittest.TestCase):
    def test_fraction_is_interpreted_as_percentage(self):
        self.assertEqual(_clamp(0.25), 25)

    def test_scores_stay_in_percentage_range(self):
        self.assertEqual(_clamp(-7), 0)
        self.assertEqual(_clamp(140), 100)
        self.assertEqual(_clamp(None), 0)
        self.assertEqual(_clamp("invalid"), 0)


class FinalScoreTests(unittest.TestCase):
    def test_missing_api_key_produces_uncertain_verdict_without_local_evidence(self):
        result = calculate_final_score(
            {"metadata_score": 0, "ela_score": 0, "artifact_score": 0},
            {"error": "missing_api_key", "reasons": [], "visual_signs": []},
        )
        self.assertEqual(result["verdict"], "uncertain")

    def test_strong_local_signal_is_suspicious_even_if_api_fails(self):
        result = calculate_final_score(
            {"metadata_score": 80, "ela_score": 20, "artifact_score": 15},
            {"error": "openrouter_failure", "reasons": [], "visual_signs": []},
        )
        self.assertEqual(result["verdict"], "suspicious")
        self.assertGreaterEqual(result["final_score"], 80)

    def test_ai_generated_verdict_is_normalized(self):
        result = calculate_final_score(
            {"metadata_score": 0, "ela_score": 0, "artifact_score": 0},
            {
                "verdict": "ai_generated",
                "confidence": 90,
                "ai_generation_probability": 85,
                "manipulation_probability": 0,
                "reasons": [],
                "visual_signs": [],
            },
        )
        self.assertEqual(result["verdict"], "likely_ai_generated")

    def test_duplicate_reasons_are_removed(self):
        result = calculate_final_score(
            {
                "metadata_score": 0,
                "ela_score": 0,
                "artifact_score": 0,
                "reasons": ["shared", "local"],
            },
            {
                "verdict": "uncertain",
                "confidence": 0,
                "ai_generation_probability": 0,
                "manipulation_probability": 0,
                "reasons": ["shared", "model"],
                "visual_signs": [],
            },
        )
        self.assertEqual(result["reasons"], ["shared", "local", "model"])


if __name__ == "__main__":
    unittest.main()
