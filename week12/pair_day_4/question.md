# Day 4 Question — Evaluation and Statistics

## Question

In my `run_real_ablation.py`, I compute bootstrap confidence intervals and paired bootstrap p-values to compare three judges (rule-based, prompt-only, LoRA-trained). The p-value tells me whether the accuracy difference is statistically significant, but I cannot explain what that p-value actually *measures* at the mechanical level. **What is the paired bootstrap p-value physically computing when it resamples my 50-task held-out set 10,000 times, and why is a significant p-value (p=0.0127) insufficient to guarantee that my trained judge will not catastrophically fail on a deployment distribution that differs from my held-out sample?**

## Artifact Connections

- [`scripts/run_real_ablation.py:185-205`](../scripts/run_real_ablation.py) — The `paired_bootstrap_p` function that computes the p-value I report.
- [`eval/method.md:122-144`](../eval/method.md) — The statistical methods section where I describe bootstrap CI and acknowledge the i.i.d. limitation.
- [`memo_week11.md:13`](../memo_week11.md) — Where I claim "p=0.0127, paired bootstrap n=10,000" as evidence of a significant lift.

## Why It Matters

I report p=0.0127 in my Week 11 CFO memo as if it closes the case. But my held-out set is only 50 tasks, and my benchmark rarely samples "confidence-boundary" cases (emails that are *almost* correct but subtly misaligned). If p-values only tell me about sampling noise on my *existing* distribution, they say nothing about whether the judge will fail on the distribution I actually care about in production. This gap means I am potentially making a deployment recommendation on insufficient evidence.
