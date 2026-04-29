# LLM-as-a-Judge Survey: Preventing Preference Leakage

**Date:** 2026-04-29
**Author:** Conversion Engine Engineering
**Reference:** Gu et al., "A Survey on LLM-as-a-Judge" (2024–2025)

## Key Takeaways
- **Bias Modes are Systemic**: Gu et al. catalog the primary failure patterns in LLM-based evaluation: verbosity bias (longer outputs rated higher regardless of quality), positional bias (answer ordering affects scores), and politeness bias (deferential, well-structured outputs rated higher even when semantically incorrect). All three are empirically documented across judge model families.
- **RLHF-Trained Evaluators Recommended for Subjective Tasks**: Gu et al. prescribe RLHF-trained evaluator models for complex subjective judgments, arguing that RLHF alignment trains models to internalize human quality signals more reliably than prompted zero-shot judges.
- **Heterogeneous Judge Families Reduce Leakage**: The survey endorses architectural family separation between generation and judging models, citing Li et al. (2025) as evidence that this measurably reduces preference leakage.
- **Human Calibration Required**: Gu et al. recommend periodic inter-rater agreement checks between LLM judges and human annotators, with tasks below 80% agreement flagged for rubric revision.

## Disagreement and Critique

Gu et al.'s primary architectural prescription is to use **RLHF-trained evaluator models for complex subjective judgments**. Their logic: RLHF training teaches a model to internalize the full range of human quality signals, making it a more reliable proxy than a zero-shot prompted judge.

**For the D06 failure mode, this recommendation produces the wrong outcome.**

RLHF training optimizes for broad human approval, which in practice means RLHF-trained judges exhibit "professional courtesy bias": they score polite, well-structured wrong-segment pitches higher than blunt, correct-segment pitches, because the RLHF training distribution rewards politeness as a quality proxy. Gu et al. acknowledge politeness bias but treat it as a prompt-engineering problem — a calibration issue — rather than a structural limitation of RLHF evaluators for domain-specific correctness tasks.

The evidence from Tenacious-Bench's 30-task IRA (inter-rater agreement) pilot is direct. GPT-4o — an RLHF-trained general evaluator — agreed with our rubric on **21 of 30 tasks (70%)**. Our deterministic evaluator in `scoring_evaluator.py`, using rule layers and segment heuristics, reached **87% agreement** on the same sample. GPT-4o's failures were not random: they clustered on cases where a polite wrong-segment pitch received "borderline" from GPT-4o but a clear "fail" from our rubric. This is precisely the politeness bias Gu et al. document but do not resolve.

The structural issue: RLHF training cannot reliably distinguish "high quality given the user's actual goal" from "high quality given generic approval norms." For D06, the goal is segment-correct outreach. An RLHF judge conflates segment correctness with social fluency.

## Application to Tenacious-Bench

1. **Deterministic rule layers first**: `scoring_evaluator.py` applies segment heuristics and ICP policy checks before any LLM judge is consulted. Tasks failing deterministic checks are scored without LLM involvement, preventing RLHF politeness bias from overriding rule-based correctness signals.
2. **Strict family separation**: Generation and judging model families are never the same architectural lineage — enforced structurally in the pipeline, not left to configuration.
3. **Bias penalty weighting**: Judge prompts penalize word count violations (120-word Style Guide limit) and flag polite-but-wrong-segment outputs as D06 failures rather than borderline cases, directly addressing the verbosity and politeness biases Gu et al. catalog.

By combining a deterministic rule layer with heterogeneous LLM judging, Tenacious-Bench avoids inheriting the professional courtesy bias that RLHF evaluators introduce into domain-specific correctness judgments.
