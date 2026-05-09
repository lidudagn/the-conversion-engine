# Portfolio Update — Week 12

**Author:** Lidya Dagnew  
**Audience:** FDE Hiring Manager  
**Date:** May 9, 2026  

---

## Summary

Week 12 transformed my Weeks 10–11 portfolio from "a system that works" into "a system I can defend." Four paired research days produced four concrete edits to existing artifacts, each grounded in a knowledge gap I identified, researched with a partner, and closed with a public explainer. A fifth standalone post addressed structured output reliability.

---

## The Four Grounding Commits

**1. Cost Model Defense** (`agent/llm_client.py`)  
*Gap:* I priced prompt tokens at $0.50/M and completion tokens at $1.50/M without understanding the 3x cost asymmetry.  
*Edit:* Added inline documentation explaining the prefill (parallel, compute-bound) vs. decode (sequential, memory-bound) distinction that drives the pricing difference. I can now defend my cost projections to a CFO by explaining the GPU utilization difference.

**2. Tool-Use Architecture Documentation** (`agent/composer.py`)  
*Gap:* I used prompt-stuffing ("Return valid JSON") instead of native function-calling without understanding the structural difference.  
*Edit:* Added documentation explaining why native `tools` parameter constrains generation at decode time while prompt-stuffing only biases the softmax distribution. This informs the v2 migration path from prompt-stuffing to structured tool-use.

**3. DPO Beta Hyperparameter Defense** (`scripts/train_judge_lora.py`)  
*Gap:* I set `beta=0.1` because it was the default, without understanding its role as a KL constraint.  
*Edit:* Added a 5-line technical comment documenting beta's dual role as step-size multiplier and self-stopping signal. I can now explain why 0.1 is the right value for a 0.5B model trained on 200 preference pairs — it prevents policy collapse while remaining responsive to alignment preferences.

**4. Statistical Significance Caveat** (`memo_week11.md`)  
*Gap:* I reported p=0.0127 as closing evidence for deployment readiness.  
*Edit:* Added a statistical caveat citing the ASA Statement on p-Values, acknowledging that aggregate significance does not guarantee per-subgroup reliability. This changes the memo's decision logic from "significant → deploy" to "significant → stratify → deploy."

---

## What Changed

Before Week 12, my portfolio demonstrated that I could **build** an AI system — a conversion engine, a custom benchmark, a preference-tuned judge. After Week 12, my portfolio demonstrates that I can **defend** every engineering choice in that system: why the cost model works, why the hyperparameters are set where they are, why the statistics say what I claim they say, and where the system's guarantees end.

The four grounding edits collectively address the most common failure mode in FDE interviews: "You built it, but can you explain why you built it this way?" I can now answer that question for every load-bearing component in my portfolio.
