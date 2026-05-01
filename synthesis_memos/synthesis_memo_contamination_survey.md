# Synthesis Memo: Recent Advances in LLM Benchmarks against Data Contamination (Chen et al., EMNLP 2025)

## Key Takeaways

- **Static benchmarks degrade fast**: Chen et al. document systematic contamination of popular benchmarks (MMLU, HumanEval, GSM8K) within months of public release. The core mechanism is memorization-at-pretraining: frontier models absorb test sets before evaluators can rotate them.

- **Three contamination vectors**: (1) n-gram overlap between test and training corpora, (2) semantic/embedding proximity even when surface text is rephrased, (3) temporal leakage from time-shifted re-use of "public signal" data. The paper recommends checking all three independently — passing one check does not imply passing the others.

- **Dynamic evaluation as the mitigation**: The paper's proposed solution is test sets that change faster than models can be retrained on them — via template randomization, parameter sweeps, or sealed evaluation windows. For static datasets, the minimum bar is: n-gram dedup (8-gram overlap < threshold), embedding-cosine dedup (< 0.85), and time-shift verification.

## Disagreement with a Specific Design Choice

Chen et al. recommend embedding-similarity dedup as the primary contamination signal, with n-gram overlap as a secondary check. For Tenacious-Bench, I inverted this priority: **n-gram overlap is the binding constraint; embedding similarity is the secondary check**. The reason is domain specificity: Tenacious-style outreach emails share high embedding similarity legitimately — two correctly-aligned Segment 2 (restructuring) emails are semantically close because they *should* reference cost-cutting and layoffs. Using embedding cosine < 0.85 as the primary filter would remove valid near-duplicate tasks that differ only in company name or headcount. N-gram overlap at the 8-gram level is more discriminating because it catches verbatim structural reuse (templated sentences) without penalizing legitimate semantic overlap.

Evidence: contamination_check.json shows 0 n-gram violations and 0 embedding violations at cosine < 0.85 — both checks pass, but the n-gram check is the one that would fire first if a training task leaked verbatim into the held-out set.

## Application to Tenacious-Bench

All three Chen et al. contamination vectors were checked before sealing the held-out partition:
1. N-gram (8-gram): 0 violations across held_out × train pairs (scripts/contamination_check.py)
2. Embedding cosine: all held_out–train pairs below 0.85 (all-MiniLM-L6-v2)
3. Time-shift: all tasks reference the frozen April 2026 hiring signal window (data/job_posts/frozen_april2026.json)

The 5 near-duplicate train tasks identified were removed and replaced with clean dev tasks before the held-out partition was sealed.
