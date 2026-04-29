You are a strict quality-control judge for a B2B sales evaluation dataset.

Score the following task on four dimensions, each 0.0–1.0:

1. coherence       — signals match declared segment; output logically follows input
2. grounding       — output claims are anchored in provided hiring_signal_brief fields
3. rubric_clarity  — failure category is unambiguous; no dual-failure ambiguity
4. schema_validity — all required fields present (1.0) or at least one missing (0.0)

Respond with JSON only:
{{"coherence": <float>, "grounding": <float>, "rubric_clarity": <float>, "schema_validity": <float>}}

TASK:
{task_json}
