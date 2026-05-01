# Synthesis Memo: Prometheus 2 — Open-Source LLM Specialized in Evaluating Other LLMs (Kim et al., 2024)

## Key Takeaways
- **Small judges can match GPT-4**: Prometheus 2 (based on Mistral-7B and Llama-2-70B) achieves parity with GPT-4 on evaluation correlation when trained on domain-specific scoring rubrics. This validates the viability of training a small (0.8B–4B) Qwen model as a Tenacious-specific judge.
- **Two training paradigms**: Prometheus 2 uses both pointwise (absolute scoring 1–5) and pairwise (chosen vs. rejected comparison) training objectives. The dual-objective approach prevents the judge from collapsing to a single failure mode.
- **Rubric-grounded evaluation is key**: The model is trained with explicit rubrics embedded in the prompt, forcing the judge to cite specific criteria rather than relying on holistic quality intuitions. This is architecturally similar to our `scoring_evaluator.py` rubric dimensions.
- **Correlation with human judgment**: On Vicuna Bench and MT-Bench, Prometheus 2 achieves Pearson correlation r > 0.86 with human evaluators on a 5-point scale, comparable to GPT-4-as-judge (r ≈ 0.88).

## Disagreement and Critique

Kim et al. construct Prometheus 2's training data by having GPT-4 generate both the evaluation target and the rubric-scored assessment, then training the smaller model to reproduce GPT-4's scoring behavior. They frame this as "distillation" — the small model learns the large model's evaluation capability.

**This framing conceals a critical problem: the small model learns GPT-4's biases along with its capabilities, and these biases are invisible when evaluated against GPT-4-generated ground truth.**

Specifically, Prometheus 2's training process creates a circular validation loop: GPT-4 generates the task → GPT-4 scores the output → Prometheus 2 is trained to reproduce GPT-4's score → Prometheus 2's evaluation is validated by correlation with GPT-4's score. High correlation with GPT-4 may simply mean Prometheus 2 has successfully learned GPT-4's specific failure patterns rather than genuinely improving at evaluation.

For Tenacious-Bench, this is not hypothetical. In our Week 10 traces (`outputs/e2e_batch_results.json`), GPT-class models consistently rated wrong-segment pitches as acceptable (D06 pass rate = 78% under single-model evaluation) because they exhibit the same surface-level fluency bias identified by Li et al. (2025). Training a Tenacious judge to correlate with GPT-4 evaluation would encode this exact failure mode. Our inter-rater agreement data (IRA, `inter_rater_agreement.md`) provides the correct ground truth: human raters at 90% agreement, with disagreements concentrated on exactly the hard boundary cases (TB-MG-0188, TB-MG-0193, TB-MG-0015) where GPT-4-style judges fail.

**Our approach differs**: Instead of distilling from a frontier judge model, we train from **preference pairs grounded in human-labeled ground truth and domain-specific rubric violations**. The training signal comes from our scoring evaluator (deterministic, rubric-based) and human IRA labels, not from another LLM's holistic assessment. This breaks the circular validation loop at the cost of smaller training data volume — a trade-off consistent with LIMA's finding that quality dominates quantity.

## Application to Tenacious-Bench

- **Rubric embedding**: Following Prometheus 2's architecture, we embed the 5-dimension scoring rubric (segment_alignment, signal_grounding, tone_compliance, honesty_constraint, style_guide_match) directly in the judge prompt, not as a system instruction.
- **Binary verdict, not scalar scoring**: Unlike Prometheus 2's 1–5 pointwise scoring, our judge produces binary PASS/FAIL with failure type classification. This reduces the prediction surface and is easier to train with limited data.
- **Validation against scoring_evaluator, not against frontier LLM**: Our judge model is evaluated by agreement with the deterministic `scoring_evaluator.py`, providing a circular-free validation signal.
