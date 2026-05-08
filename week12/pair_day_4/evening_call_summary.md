# Evening Call Summary — Day 4

**Date:** 2026-05-08  
**Topic:** Evaluation and Statistics  
**Participants:** Lidya Dagnew & Melaku Yilma  
**Duration:** ~35 minutes  

---

## Feedback on Melaku's Explainer (peer_explainer.md — Bootstrap P-Value Mechanics)

**What landed immediately:**
- Melaku's explanation of what the paired bootstrap physically computes — "it simulates 10,000 alternate worlds where the two models are equally good, and counts how often those worlds produce a delta as extreme as what you observed" — was the clearest framing I've encountered. I had been thinking of p-values as a quality score; now I understand they are a **noise filter**.
- His distinction between **internal validity** (does the result hold on this sample?) and **external validity** (does it hold in production?) was the core insight. My `run_real_ablation.py` handles internal validity perfectly; nothing in my pipeline addresses external validity.
- The concrete example of how a 50-task held-out set with only 3 confidence-boundary cases gives bootstrap a structurally biased input was actionable — I can now audit my held-out set's composition.

**What I asked Melaku to clarify:**
- I asked whether there's a minimum sample size below which bootstrap CIs become unreliable. He pointed to the rule of thumb that bootstrap is questionable below n=20, and my held-out partition (n=50) is borderline — adequate for aggregate metrics but insufficient for stratified subgroup analysis (where individual strata might have n=5).
- I asked about the practical difference between "paired" and "unpaired" bootstrap. He clarified that paired bootstrap preserves the task-level correlation (both models see the same task), which is critical because task difficulty is a confounder. My implementation correctly uses paired resampling.
- I pushed on whether there's a way to test external validity without more data. He encouraged me to look into **Behavioral Testing (CheckList)**, which he added to his sources.

**Revision made:** Melaku added a section on the mismatch between bootstrap variance and distribution shift to emphasize that significance measures stability of measurement, not completeness of behavior.

---

## Feedback on Lidya's Explainer (explainer.md — Statistical Significance vs. Deployment Reliability)

**What landed for Melaku:**
- The Simpson's Paradox table was the "click" moment — seeing aggregate +8% coexist with subgroup −20% on hard cases made the abstract concept concrete.
- The framing of bootstrap as having a "structural limitation" (it can only resample from data you give it) reframed his understanding of his own results. He realized his p=0.018 is valid *conditional on* his benchmark distribution, but says nothing about a deployment distribution that over-represents hard cases.

**What Melaku asked me to clarify:**
- He asked whether my claim about "hidden stratification" applies to his specific case or is a general risk. I clarified that it's both — Oakden-Rayner et al. (2020) showed this kills deployed medical imaging models, and his pattern (adapter improves on easy cases, regresses on hard) is the same mechanism in a different domain.
- He asked me to add a concrete code snippet showing how to compute per-stratum accuracy from existing ablation results. I added a Python example that partitions results by difficulty tier and computes accuracy per partition.
- He pushed back on my recommendation to "add a sentence to every p-value claim." We agreed that the better grounding edit is to add a **stratified results table** or a **statistical caveat** citing the specific distribution limitations.

**Revision made:** Added a caveat to the grounding edit to emphasize that aggregate significance does not guarantee per-subgroup reliability.

---

## Gap Closure Judgments

**Lidya's gap (Bootstrap P-Value Mechanics):** ✅ **Closed.** I can now explain what paired bootstrap physically computes (noise simulation under the null), why it handles internal but not external validity, and how to audit my held-out set's composition as a diagnostic for Simpson's Paradox.

**Melaku's gap (Statistical Significance vs. Deployment Reliability):** ✅ **Closed.** Melaku confirmed he now understands why his p=0.018 is real but incomplete, and will add stratified reporting to his ablation pipeline.

---

## Grounding Commits
- **Lidya:** Added a statistical caveat to the `memo_week11.md` p-value claim acknowledging the Simpson's Paradox risk for under-sampled subgroups.
- **Melaku:** Will add a stratified evaluation breakdown by failure type to his evaluation script.
