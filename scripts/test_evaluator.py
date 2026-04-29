import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
import json
from eval.tenacious_bench.scoring_evaluator import ScoringEvaluator

class TestScoringEvaluator(unittest.TestCase):
    def setUp(self):
        self.evaluator = ScoringEvaluator()

    def test_pass_task(self):
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
        self.assertGreater(result.composite, 0.7)

    def test_segment_mismatch_failure(self):
        # Target failure mode: D06 — growth pitch sent to restructuring company
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
        self.assertEqual(result.verdict, "FAIL", "Should fail: Seg1 pitch sent to Seg2 company")
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
