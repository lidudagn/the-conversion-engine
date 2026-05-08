# When Statistical Significance Lies: What Bootstrap p-Values Actually Measure in LLM Evaluation

## Overview

A statistically significant benchmark improvement does not necessarily imply deployment reliability.

In Week 11, `run_real_ablation.py` compared three judges:

- rule-based,
- prompt-only,
- and LoRA-trained,

using paired bootstrap confidence intervals and paired bootstrap p-values across a 50-task held-out benchmark.

The trained judge achieved a statistically significant improvement:

- p = 0.0127

Yet this raised a deeper question:

What is the paired bootstrap p-value actually computing mechanically, and why can statistically significant benchmark gains still fail catastrophically after deployment?

This explainer argues that the paired bootstrap p-value measures sampling stability under the benchmark distribution — not universal model correctness — and therefore cannot guarantee reliability under deployment distribution shift.

---

# 1. What a p-Value Is Actually Measuring

A p-value is not:

- the probability the model is correct,
- the probability the improvement is “real,”
- nor the probability deployment will succeed.

Instead, the paired bootstrap p-value measures:

> how often the observed performance difference could plausibly appear from sampling variation alone under the benchmark distribution.

The key phrase is:

> under the benchmark distribution.

That limitation is load-bearing.

---

# 2. What the Paired Bootstrap Is Physically Doing

The evaluation pipeline contains:

- 50 held-out benchmark tasks,
- three judges,
- and repeated resampling.

The paired bootstrap repeatedly creates new pseudo-datasets by:

1. sampling 50 tasks *with replacement*,
2. preserving task alignment across judges,
3. recomputing accuracy differences,
4. and repeating this process 10,000 times.

Mechanically, each bootstrap sample asks:

> “If these 50 tasks were another plausible sample from the same benchmark distribution, how much would the observed judge difference vary?”

This creates an empirical distribution of score differences.

The p-value is then computed as the proportion of bootstrap worlds where:

- the observed improvement disappears,
- reverses,
- or becomes statistically negligible.

---

# 3. Why Pairing Matters

The bootstrap is *paired* because all judges are evaluated on the same tasks.

This removes unnecessary variance.

Without pairing:

- task difficulty differences would dominate variance estimates.

With pairing:

- each bootstrap sample compares judges under identical task conditions.

This isolates the actual model difference more cleanly.

The paired bootstrap therefore estimates:

[ \Delta_{judge} = Accuracy_A - Accuracy_B ]

under repeated resampling of tasks.

---

# 4. What Statistical Significance Actually Establishes

A significant p-value establishes only this:

> Under repeated resampling of this benchmark distribution, the observed improvement is unlikely to be caused purely by random sampling noise.

That is all.

It does NOT establish:

- universal capability,
- robustness,
- calibration,
- deployment safety,
- or distributional generalization.

This distinction is critical.

---

# 5. Why Deployment Reliability Is a Different Problem

The bootstrap assumes:

[ Train Distribution ≈ Held-Out Distribution ≈ Deployment Distribution ]

But real deployment rarely satisfies this assumption.

Deployment inputs may differ in:

- phrasing,
- ambiguity,
- adversarial structure,
- edge-case frequency,
- confidence-boundary density,
- or tool-use complexity.

The paired bootstrap never evaluates those unseen regions.

It only estimates uncertainty *inside the sampled benchmark world.*

---

# 6. The Hidden Assumption Behind p=0.0127

The p-value depends entirely on the benchmark sample.

If the 50-task held-out set underrepresents:

- boundary cases,
- adversarial prompts,
- ambiguous tool calls,
- or rare failure modes,

then the bootstrap repeatedly resamples a benchmark that already hides those weaknesses.

This creates a dangerous illusion:

[ Statistical Stability ≠ Behavioral Completeness ]

A model can appear statistically reliable because the benchmark itself fails to expose deployment-critical regions.

---

# 7. Why Catastrophic Failures Can Coexist With Strong p-Values

This happens because benchmarks measure averages.

Suppose:

- 47 tasks are easy,
- 3 tasks are deployment-critical edge cases.

A judge may improve substantially on the 47 common tasks while still catastrophically failing on the 3 critical ones.

The aggregate metric improves.

The bootstrap repeatedly confirms that improvement.

The p-value becomes significant.

Yet the deployment-critical behavior remains broken.

The statistical machinery is functioning correctly.

The benchmark coverage is what failed.

---

# 8. Bootstrap Variance vs Distribution Shift

Bootstrap resampling estimates:

[ uncertainty conditioned on the observed dataset ]

It does NOT estimate:

[ uncertainty under unseen distributions ]

This is one of the most misunderstood ideas in evaluation.

The bootstrap can quantify:

- sampling noise,
- metric stability,
- confidence intervals,
- and estimate variance.

But it cannot detect:

- hidden subpopulations,
- future deployment drift,
- adversarial regions,
- or unsupported behavioral modes.

Those require:

- stress testing,
- stratified evaluation,
- adversarial sampling,
- and distribution-shift analysis.

---

# 9. Why This Matters for LLM Evaluation

Modern LLM benchmarks often report:

- confidence intervals,
- bootstrap p-values,
- and statistically significant gains.

But significance testing only answers:

> “Is the measured improvement stable under this benchmark sampling process?”

It does not answer:

> “Will the system behave reliably in the real world?”

Those are fundamentally different questions.

---

# Conclusion

The paired bootstrap p-value in `run_real_ablation.py` physically computes how stable the observed judge improvement remains under repeated resampling of the held-out benchmark tasks.

It estimates uncertainty caused by finite sampling inside the benchmark distribution.

A statistically significant result like:

- p = 0.0127

therefore establishes:

- benchmark-level statistical stability,

but not:

- deployment reliability,
- robustness,
- or behavioral completeness.

The critical lesson is:

> Statistical significance measures stability of measurement — not completeness of behavior.

A benchmark can be statistically rigorous while still systematically blind to deployment-critical failures.

Understanding that distinction is essential for evaluating LLM systems honestly.

---

# Sources

- Efron & Tibshirani (1993) — *An Introduction to the Bootstrap*
- Kohavi (1995) — *A Study of Cross-Validation and Bootstrap for Accuracy Estimation*
- Dror et al. (2018) — *The Hitchhiker’s Guide to Testing Statistical Significance in NLP*
- Bowman & Dahl (2021) — *What Will it Take to Fix Benchmarking in NLP?*
- Sculley et al. (2015) — *Hidden Technical Debt in Machine Learning Systems*
- Ribeiro et al. (2020) — *Beyond Accuracy: Behavioral Testing of NLP Models with CheckList*

---

# Tool Used

Tool:
- Claude Code with artifact inspection

Artifacts Reviewed:
- `run_real_ablation.py`
- bootstrap evaluation outputs
- held-out judge comparison metrics

Purpose:
The artifact inspection was used to understand:
- how paired bootstrap resampling was implemented,
- what the p-value was mechanically estimating,
- and why statistical significance could coexist with deployment failure under distribution shift.