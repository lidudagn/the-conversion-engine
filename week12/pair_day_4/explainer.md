# When p < 0.05 Lies: Why Statistical Significance Can't Save Your LLM Evaluation

*Written by Lidya Dagnew for Melaku Yilma, whose LoRA adapter improved ΔB=+0.1046 (p=0.018) but still fails on confidence-boundary cases.*

---

You trained a LoRA adapter. Your benchmark score went up by +0.1046. Your paired bootstrap returned p=0.018. Every textbook says that's significant at the 0.05 level. You ship the model.

Then it fails — not randomly, but *systematically* — on the exact cases that matter most: emails that use the right segment keywords but frame the intent wrong. The benchmark rarely sampled these cases. The p-value never told you about them.

This post explains why.

## What Statistical Significance Actually Establishes

A p-value answers exactly one question: **"If the true performance difference were zero, how likely would I be to observe a sample difference this large or larger?"**

That's it. It measures the probability of your observed data *under the null hypothesis*. When your `paired_bootstrap_p` function resamples 10,000 times from your 50-task held-out set, it is simulating what the accuracy difference would look like if the two models were actually equivalent and you just happened to get lucky or unlucky in your sample.

p=0.018 means: "In only 1.8% of the 10,000 resampled worlds, the accuracy difference was as large as what I actually observed." So we reject the null hypothesis — the models are probably not equivalent.

**What this guarantees:**
- The observed accuracy difference is unlikely to be pure sampling noise.

**What this does NOT guarantee:**
- That the improvement is *large enough to matter* (practical significance ≠ statistical significance).
- That the improvement holds *across all subgroups* of your evaluation distribution.
- That the improvement holds *on a different distribution* than your held-out set.

## The Hidden Stratification Problem

This is where Melaku's failure pattern becomes diagnostic. Your benchmark samples tasks from a distribution. If that distribution over-represents "easy" cases (blatant misalignment, obvious wrong-segment) and under-represents "hard" cases (confidence-boundary, correct keywords but wrong intent), then your aggregate metric is dominated by performance on the easy cases.

This is a form of **Simpson's Paradox**: the aggregate trend (improvement) masks a subgroup trend (regression or stagnation on hard cases).

Concretely, consider a benchmark with 50 tasks:
- 40 are "easy" (blatant misalignment, obvious pass/fail)
- 10 are "hard" (confidence-boundary, subtle intent errors)

| Subgroup | Baseline Accuracy | Adapter Accuracy | Δ |
|---|---|---|---|
| Easy (n=40) | 70% (28/40) | 85% (34/40) | +15% |
| Hard (n=10) | 50% (5/10) | 30% (3/10) | **−20%** |
| **Aggregate (n=50)** | **66% (33/50)** | **74% (37/50)** | **+8%** ✅ |

The aggregate improvement is +8% and likely "statistically significant" at n=50. But the adapter is *worse* on the hard cases that actually determine deployment reliability. The p-value cannot detect this because it operates on the aggregate, not the partition.

## Why Bootstrap Cannot Save You

The bootstrap is a powerful tool — it makes no distributional assumptions, it handles correlated scores well, and it gives honest confidence intervals. But it has a structural limitation: **it can only resample from the data you give it.**

If your held-out set of 50 tasks contains only 3 confidence-boundary cases, the bootstrap will dutifully resample from those 3 cases. The resulting CI reflects the uncertainty in *your sample*, not the uncertainty in *the deployment distribution*. A narrow CI from a biased sample is worse than a wide CI from a representative one — it gives you false confidence.

This is the difference between **internal validity** (does the result hold for this sample?) and **external validity** (does the result hold for the real world?). Your bootstrap handles internal validity. Nothing in your statistical pipeline handles external validity.

## What to Do Instead

Statistical significance is necessary but not sufficient. To bridge the gap between "benchmark lift" and "deployment reliability," you need three additional layers:

**1. Stratified Evaluation.** Break your held-out set into subgroups by difficulty tier (blatant, subtle, hard-negative). Report accuracy per stratum. If any stratum regresses, the aggregate p-value is misleading.

**2. Minimum Detectable Effect (MDE).** Before running the evaluation, define the smallest improvement that would actually matter for your deployment. If your MDE is +5% and your observed Δ is +10.46%, you have practical significance. If your MDE is +15%, you don't — regardless of the p-value.

**3. Coverage Testing.** Explicitly check whether your benchmark distribution matches your deployment distribution. If your benchmark has 6% confidence-boundary cases but your production traffic is 25% confidence-boundary, your evaluation is structurally uninformative about the cases that matter most.

## The Takeaway for Melaku's Portfolio

The p=0.018 in your ablation report is real evidence — it means the adapter genuinely improved aggregate accuracy. But it cannot tell you whether the adapter is safe to deploy, because safety is a per-subgroup property and your benchmark is an aggregate instrument.

The grounding edit is this: wherever you report a p-value as evidence of improvement, add a sentence acknowledging what it does not establish. "Statistically significant at p<0.05; however, this result reflects aggregate accuracy and does not guarantee performance on under-sampled subgroups (e.g., confidence-boundary cases, which comprise <10% of the held-out set)."

---

## Sources

- Efron & Tibshirani (1993). *An Introduction to the Bootstrap.*
- Wasserstein & Lazar (2016). "The ASA Statement on p-Values." *The American Statistician*, 70(2).
- Oakden-Rayner et al. (2020). "Hidden Stratification Causes Clinically Meaningful Failures in Machine Learning." *CHIL 2020.*
