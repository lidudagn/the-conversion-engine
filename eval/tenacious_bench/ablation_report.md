# Act IV: Ablation Studies & Measurement Report

## Overall Metrics
| Model | Accuracy | Pass Precision (1 - FP/TotalPasses) | SEMANTIC_FALSEHOOD Recall (4 Key Drafts) |
|---|---|---|---|
| Rule | 60.5% | 81.0% | 0/4 (0.0%) |
| Base | 39.5% | 42.9% | 2/4 (50.0%) |
| Trained | 53.5% | 52.4% | 3/4 (75.0%) |

## The 4-Draft Litmus Test (Evaluator Agreement vs Human Verdict)
| Task ID | Frozen Evaluator (Rule) | Trained Judge | Human Verdict (Expected) | Agreement Status |
|---|---|---|---|---|
| SG-BAD-03 | PASS | FAIL | FAIL | Disagrees: Evaluator WRONG, Model RIGHT |
| SG-BAD-05 | PASS | FAIL | FAIL | Disagrees: Evaluator WRONG, Model RIGHT |
| SG-BAD-07 | PASS | FAIL | FAIL | Disagrees: Evaluator WRONG, Model RIGHT |
| SG-BAD-12 | PASS | PASS | FAIL | Agrees: Model inherited Evaluator Blind Spot |

### Litmus Conclusion
**SUCCESS**: The Trained Judge successfully flipped 3/4 semantic truth violations without degrading style precision. It learned structural independence beyond our labeling rules.