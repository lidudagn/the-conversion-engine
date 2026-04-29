import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
import json
from eval.tenacious_bench.scoring_evaluator import ScoringEvaluator

class TestScoringEvaluator(unittest.TestCase):
    def setUp(self):
        self.evaluator = ScoringEvaluator()

    def test_pass_task_from_example(self):
        with open("eval/tenacious_bench/examples/tb_pass_001.json") as f:
            task = json.load(f)
        result = self.evaluator.evaluate_task(task)
        self.assertEqual(result.verdict, "PASS")
        self.assertGreaterEqual(result.composite, 0.70)
        print(f"tb_pass_001.json passed with composite: {result.composite}")

    def test_segment_mismatch_failure(self):
        # Target failure mode: D06 — growth pitch sent to restructuring company
        with open("eval/tenacious_bench/examples/tb_d06_001.json") as f:
            task = json.load(f)
        result = self.evaluator.evaluate_task(task)
        self.assertEqual(result.verdict, "FAIL")
        self.assertEqual(result.dimensions["segment_alignment"], 0.0)
        self.assertIn("segment_alignment", result.fatal_reasons)
        print("tb_d06_001.json caught correctly (segment mismatch).")

    def test_forbidden_signal_failure(self):
        with open("eval/tenacious_bench/examples/tb_i03_001.json") as f:
            task = json.load(f)
        result = self.evaluator.evaluate_task(task)
        self.assertEqual(result.verdict, "FAIL")
        self.assertEqual(result.dimensions["honesty_constraint"], 0.0)
        self.assertIn("honesty_violation", result.fatal_reasons)
        print("tb_i03_001.json caught correctly (honesty violation).")

if __name__ == '__main__':
    unittest.main()
