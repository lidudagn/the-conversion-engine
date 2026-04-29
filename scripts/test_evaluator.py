import unittest
import json
from eval.tenacious_bench.scoring_evaluator import ScoringEvaluator

class TestScoringEvaluator(unittest.TestCase):
    def setUp(self):
        self.evaluator = ScoringEvaluator()

    def test_pass_task(self):
        # TB-MG-001 equivalent
        task = {
            "input": {
                "hiring_signal_brief": {"prospect_name": "TestCorp"},
                "policy_decision": {"pitch_segment": 1, "tone_mode": "suggestive"}
            },
            "candidate_output": "I saw TestCorp is scaling. We'd love to help.",
            "ground_truth": {
                "verdict": "pass",
                "inferred_segment": 1,
                "failure_categories": []
            }
        }
        result = self.evaluator.evaluate_task(task)
        self.assertEqual(result.verdict, "PASS")
        self.assertGreater(result.composite_score, 0.7)

    def test_segment_mismatch_failure(self):
        # Target failure mode: D06
        task = {
            "input": {
                "hiring_signal_brief": {"prospect_name": "TestCorp", "layoffs": {"event": True}},
                "policy_decision": {"pitch_segment": 2, "tone_mode": "suggestive"}
            },
            "candidate_output": "Congratulations on your rapid growth! Scaling fast is our specialty.",
            "ground_truth": {
                "verdict": "fail",
                "inferred_segment": 2,
                "failure_categories": ["wrong_segment_pitch"]
            }
        }
        result = self.evaluator.evaluate_task(task)
        self.assertEqual(result.verdict, "FAIL", "Should fail due to Seg1 pitch sent to Seg2 company")
        self.assertEqual(result.dimensions["segment_alignment"], 0.0)

    def test_forbidden_signal_failure(self):
        task = {
            "input": {
                "hiring_signal_brief": {"prospect_name": "TestCorp"},
                "policy_decision": {"pitch_segment": 1, "tone_mode": "suggestive"}
            },
            "candidate_output": "I am a world-class AI agent.",
            "ground_truth": {
                "verdict": "fail",
                "inferred_segment": 1,
                "failure_categories": ["banned_phrase"]
            }
        }
        result = self.evaluator.evaluate_task(task)
        self.assertEqual(result.verdict, "FAIL")

if __name__ == "__main__":
    unittest.main()

    def test_overclaim_failure(self):
        task = {
            "input": {
                "hiring_signal_brief": {"prospect_name": "GrowFast"},
                "policy_decision": {"pitch_segment": 1, "tone_mode": "assertive"}
            },
            "candidate_output": "We guarantee results. Our engineers are #1 ranked and will transform your team.",
            "ground_truth": {
                "verdict": "fail",
                "inferred_segment": 1,
                "failure_categories": ["signal_overclaiming"],
                "forbidden_signals": ["guarantee"],
                "required_signals": []
            }
        }
        result = self.evaluator.evaluate_task(task)
        self.assertEqual(result.verdict, "FAIL")
        self.assertIn("overclaiming", result.fatal_reasons)

    def test_examples_directory(self):
        examples_dir = os.path.join(os.path.dirname(__file__), "..", "eval", "tenacious_bench", "examples")
        json_files = list(__import__("pathlib").Path(examples_dir).glob("*.json"))
        self.assertGreater(len(json_files), 0, "No example tasks found")
        for path in json_files:
            with open(path) as f:
                task = json.load(f)
            result = self.evaluator.evaluate_task(task)
            self.assertIn(result.verdict, ("PASS", "FAIL", "BORDERLINE"))

if __name__ == "__main__":
    unittest.main(verbosity=2)
