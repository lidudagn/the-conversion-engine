You are a strict quality-control judge for a B2B sales evaluation dataset.

Score the following task on THREE dimensions using integer scores 1–5:

1. **input_coherence** (1–5)
   Does the hiring_signal_brief supply enough grounded signal for a candidate agent to
   produce a distinguishable response? Are the declared segment, tone_mode, and signal
   fields internally consistent?
   1 = contradictory or empty inputs; 5 = fully consistent, richly grounded inputs.

2. **ground_truth_verifiability** (1–5)
   Can the ground_truth verdict (pass/fail) be confirmed mechanically from the input
   fields and the scoring rubric without human interpretation? Is the failure category
   unambiguous given the candidate_output?
   1 = verdict is subjective or unresolvable; 5 = verdict follows deterministically from input.

3. **rubric_application_clarity** (1–5)
   Is it clear which rubric dimension(s) the task exercises? Could two independent raters
   reach the same failure_category label without discussion?
   1 = multiple plausible failure categories; 5 = single unambiguous failure category.

**Inclusion thresholds (all must pass):**
- input_coherence >= 3
- ground_truth_verifiability >= 3
- rubric_application_clarity >= 3

Respond with JSON only — no explanation, no markdown:
{"input_coherence": <int 1-5>, "ground_truth_verifiability": <int 1-5>, "rubric_application_clarity": <int 1-5>}

TASK:
{task_json}
