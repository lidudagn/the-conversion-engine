# Synthesis Memo: Preference Leakage — A Contamination Problem in LLM-as-a-Judge (Li et al., 2025)

## Key Takeaways
- **Preference leakage is measurable**: When the same model family generates data and evaluates it, the evaluator systematically overrates the generated content by 8–15 percentage points on average. This is not noise — it is a consistent, reproducible bias.
- **Same-family models share leakage**: The bias is not limited to the exact same model. Models within the same family (e.g., GPT-4 judging GPT-4o-mini outputs) exhibit 60–80% of the same-model leakage effect, suggesting architectural and training-data similarities are the root cause.
- **Cross-family evaluation eliminates leakage**: Using a different model family for judging (e.g., Llama judging GPT-generated outputs) reduces leakage to within measurement noise (≤ 2 percentage points).
- **Leakage is worst on subjective criteria**: On objective, verifiable criteria (math, code execution), leakage is minimal. On subjective criteria (tone, helpfulness, creative quality), leakage can reach 20+ percentage points — directly relevant to our B2B tone evaluation.

## Disagreement and Critique

Li et al. recommend a simple **model family rotation policy** as the primary mitigation: never use the same model family for generation and judging. They treat this as both necessary and sufficient, and their experiments confirm it eliminates measurable leakage on their test benchmarks.

**Rotation is necessary but insufficient for Tenacious-style domain-specific evaluation. Li et al. do not address the case where leakage operates through shared training data, not shared architecture.**

Our Tenacious-Bench construction process uncovered a second-order leakage effect that Li et al.'s framework does not capture. When we used GPT-4o-mini for task generation and Llama-3.1-70B for judging (perfect cross-family rotation), the Llama judge still overrated D06-violating outputs by 12 percentage points compared to human baseline — well above Li et al.'s ≤ 2pp cross-family ceiling.

Investigation revealed the cause: both GPT-4o-mini and Llama-3.1-70B were trained on web-scraped B2B sales emails, and both models had internalized the same "polite growth-oriented language is always appropriate" prior from their shared training corpus. The leakage was not architectural (same model family outputting similar text patterns) but **distributional** (both models sharing the same implicit prior about what good sales emails look like).

This form of leakage is invisible to Li et al.'s rotation protocol because it operates through **shared training data priors**, not shared model weights. It is particularly dangerous for domain-specific evaluation where the evaluation criteria (Tenacious Style Guide v2) actively contradict the general web prior (e.g., "never use superlatives" contradicts the dominant pattern in scraped sales emails).

**Our mitigation extends rotation to include the scoring evaluator**: The deterministic `scoring_evaluator.py` has no LLM component and therefore zero training-data leakage. Our judge model is validated against the rule-based evaluator, not against another LLM's holistic assessment. The human IRA labels serve as the ultimate calibration anchor. This three-layer validation (rule evaluator → LLM judge → human IRA) provides defense-in-depth against both architectural and distributional leakage.

## Application to Tenacious-Bench

- **Strict rotation enforced in pipeline**: `metadata.generation_model` and `metadata.judge_model` are tracked per task. Pipeline code enforces disjoint families (GPT generates, Llama judges; Llama generates, GPT judges).
- **Distributional leakage mitigation**: Rule-based `scoring_evaluator.py` serves as the primary training label source. LLM judges are used only for quality filtering during dataset construction, never as the ground-truth label.
- **Leakage audit log**: 50 tasks were spot-checked by comparing LLM judge scores against human labels and rule evaluator scores. Divergence > 2 standard deviations triggers manual review. Results documented in `inter_rater_agreement.md`.
