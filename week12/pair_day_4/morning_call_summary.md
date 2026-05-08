# Morning Call Summary — Day 4

**Date:** 2026-05-08  
**Topic:** Evaluation and Statistics  
**Participants:** Lidya Dagnew & Melaku Yilma  
**Duration:** ~25 minutes  

---

## Lidya's Draft Question (Before Sharpening)

**Original draft:** "What does the p-value in my ablation actually mean?"

**Melaku's interrogation:**
- Melaku pushed immediately: "You could Wikipedia that. What's the gap that's actually stopping you from making a better decision?" I said I don't know whether my p=0.0127 tells me the judge is safe to deploy or just that it's better than random on my specific 50 tasks.
- He asked: "If I gave you a new held-out set with 50 *different* tasks tomorrow, would you expect the same p-value?" I admitted I had no intuition for this — I don't understand whether the p-value generalizes or is bound to my specific sample.
- We discussed whether the question is about the math of bootstrap resampling or about the limits of statistical significance for deployment decisions. I wanted both: the mechanics of what `paired_bootstrap_p` is physically computing, and why a significant result doesn't guarantee deployment reliability.

**Sharpened version:** "What is the paired bootstrap p-value physically computing when it resamples my 50-task held-out set 10,000 times, and why is a significant p-value (p=0.0127) insufficient to guarantee that my trained judge will not catastrophically fail on a deployment distribution that differs from my held-out sample?"

**Why this version is better:** It names the exact function (`paired_bootstrap_p`), the exact dataset size (50 tasks), and the exact claim in the memo (p=0.0127). It asks for both the mechanism and the limitation.

---

## Melaku's Draft Question (Before Sharpening)

**Original draft:** "My adapter improved the score but sometimes still fails. Why?"

**Lidya's interrogation:**
- I pushed back: "Fails how? On which tasks? You need to name the failure pattern." Melaku said his adapter improved ΔB by +0.1046 (p=0.018) but still failed systematically on "confidence-boundary" cases — emails that use the right keywords but frame the intent incorrectly.
- I asked: "Is your question about why the adapter fails, or about why the benchmark didn't catch it?" He realized the deeper gap is the second one: the benchmark rarely samples these hard cases, so a statistically significant aggregate improvement masks systematic failures on the distribution tail.
- We sharpened the question to ask explicitly about the gap between statistical significance (aggregate metric) and deployment reliability (per-subgroup performance).

**Sharpened version:** "In Week 11, a LoRA adapter improved benchmark performance by ΔB=+0.1046 (p=0.018), yet still failed systematically on confidence-boundary cases the benchmark rarely sampled. What does statistical significance actually establish in LLM evaluation, and why can statistically significant aggregate gains still fail to demonstrate deployment reliability?"

**Why this version is better:** It names the exact delta (+0.1046), the exact significance level (p=0.018), and the specific failure pattern (confidence-boundary cases). It asks a question that connects to Simpson's Paradox — aggregate metrics masking subgroup failures.

---

## Sign-off
Both partners confirmed the questions are unambiguous, diagnostic, grounded in specific artifacts, and resolvable in a single explainer. Questions finalized for the day.
