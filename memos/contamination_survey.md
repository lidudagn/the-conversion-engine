# Contamination Survey: Securing the Tenacious-Bench

**Date:** 2026-04-29
**Author:** Conversion Engine Engineering
**Reference:** Chen et al., "Recent Advances in LLM Benchmarks against Data Contamination" (EMNLP 2025)

## Key Takeaways
- **Contamination is a Silent Validity Threat**: Chen et al. document that static benchmarks are systematically vulnerable to training-set overlap, with contaminated models showing inflated scores that do not generalize. For Tenacious-Bench, this threat is acute: a preference-tuned judge trained on contaminated tasks would produce artificially high D06 pass rates — the exact vanity metric the benchmark was designed to expose.
- **Three Distinct Contamination Vectors**: The survey identifies n-gram overlap (verbatim copying), semantic paraphrase overlap (same meaning, different phrasing), and temporal leakage as separate threat classes requiring separate mitigations.
- **Dynamic Evaluation as the Central Proposal**: Chen et al.'s Section 4.2 recommends that benchmark maintainers periodically regenerate test examples from updated source distributions to prevent static contamination from accumulating.
- **Partition Hygiene as Prerequisite**: Strict partition segregation — no prompt-response pair appearing in both train and held-out — is treated as table stakes before any decontamination strategy is applied.

## Disagreement and Critique

Chen et al.'s Section 4.2 advocates for **dynamic benchmark generation**: periodically regenerating test examples with fresh surface forms to outpace model memorization. For general-domain benchmarks like MMLU, this is sound — paraphrasing a knowledge-retrieval question does not change what is being tested.

**For B2B sales evaluation, dynamic regeneration destroys construct validity.**

Tenacious-Bench tasks are temporally anchored to real-world events. A representative task: "Company X closed a Series A in February 2026; current date is May 2026 — craft the outreach." The correct answer is a direct function of the temporal gap between funding event and outreach date. If dynamic regeneration shifts the funding date to "July 2026" to break surface-form contamination, the task tests a different temporal reasoning instance with a different correct answer. The benchmark's validity is destroyed in the act of preserving surface novelty.

Chen et al.'s proposal implicitly assumes paraphrasing preserves task semantics. For B2B sales, the semantic content of a task *is* the real-world state of a company at a specific date — paraphrasing the date changes the task, not just its clothing.

**Our alternative**: temporal-anchor preservation via time-shift controls. Rather than regenerating tasks, we inject a programmatic time-shift into the evaluation harness, advancing the "current date" variable forward. A contaminated model that memorized the correct pitch for "May 2026" will assert a stale funding signal when the harness says "August 2026," producing a detectable `stale_signal` failure. This tests contamination robustness without altering the temporal construct under evaluation.

## Mitigation Strategy

**N-Gram Overlap**: We compute n-gram overlap between `held_out` and `train` sets. Threshold: no 8-gram intersection. Tasks sharing an 8+ word sequence with training data are rejected or moved to `dev`. All checks currently pass.

**Semantic Embedding Similarity**: Using `all-MiniLM-L6-v2`, we compare task pairs on the concatenation of `hiring_signal_brief` and `policy_decision`. Threshold: cosine similarity below 0.85. Colliding tasks are deduplicated before the held-out partition is sealed.

**Time-Shift Controls**: The evaluation harness injects a shifted "current date," rendering memorized pitches detectable as `stale_signal` failures. This is our primary defense against contamination that passes both n-gram and embedding checks.

## Current Status
The `merge_and_partition.py` script enforces content-hash deduplication across the 202-task pool. No exact prompt-response pair leaks across the 102 `train`, 61 `dev`, and 39 `held_out` splits. All contamination checks pass.
