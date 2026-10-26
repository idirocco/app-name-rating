import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from evaluator import deterministic_criteria, eligibility, length_score, overall_score, syllable_score, unicode_letter_count
from history import append_evaluations, history_by_normalized_name, load_history


class EvaluatorTests(unittest.TestCase):
    def test_length_counts_unicode_letters(self):
        self.assertEqual(unicode_letter_count("Áurea 2!"), 5)
        self.assertEqual(length_score(5), 10)

    def test_syllable_scoring(self):
        self.assertEqual(syllable_score(2), 10)
        self.assertEqual(syllable_score(3), 7)
        self.assertEqual(syllable_score(5), 1)

    def test_deterministic_metadata(self):
        d1 = deterministic_criteria("Nuvio")["D1"]
        self.assertIn("estimated_syllables", d1)
        self.assertIn("uncertain", d1)

    def test_mandatory_failure_overrides_score(self):
        mandatory = {"M1": {"status": "PASS"}, "M2": {"status": "FAIL"}}
        self.assertEqual(eligibility(mandatory), "FAIL")

    def test_weighted_score_is_calculated_locally(self):
        mandatory = {key: {"score": 10} for key in ("M1", "M2", "M3", "M4", "M5")}
        desirable = {key: {"score": 10} for key in ("D3", "D4", "D6")}
        self.assertEqual(overall_score(mandatory, desirable), 10)

    def test_history_is_saved_as_json(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            saved = append_evaluations([{"name": "Nuvio", "overall_score": 8.5}], path)
            self.assertEqual(saved[0]["name"], "Nuvio")
            self.assertIn("evaluated_at", saved[0])
            self.assertEqual(load_history(path)[0]["overall_score"], 8.5)

    def test_history_lookup_uses_normalized_case_insensitive_name(self):
        history = [{"name": "Nuvio", "overall_score": 8.5}]
        saved = history_by_normalized_name(history)
        self.assertEqual(saved["nuvio"]["overall_score"], 8.5)


if __name__ == "__main__":
    unittest.main()
