# Week 12 Synthesis — Knowledge Gap Formulation for Compounding

**Author:** Lidya Dagnew  
**Date:** May 9, 2026  
**Program:** Forward-Deployed Engineer, Cohort 2026  

---

## The Gaps Closed

This week I closed eight knowledge gaps across four paired research days — four I named, four I researched for partners. Each gap connected to a specific artifact in my Weeks 10–11 portfolio (the Conversion Engine, Tenacious-Bench, and the DPO-trained judge). Each closure produced a grounding edit to that artifact. A fifth standalone post on structured output and constrained decoding rounded out the public artifact set.

### Four Gaps I Named (Questions I Asked)

**1. Prefill vs. Decode Cost Asymmetry (Day 1, partner: Efrata Wolde)**
I charged prompt tokens at $0.50/M and completion tokens at $1.50/M in `llm_client.py` without understanding why they cost differently. Efrata showed me that prefill is parallelizable matrix multiplication while decode is sequential, memory-bound autoregression. The cost difference comes from GPU utilization: prefill saturates compute; decode wastes it waiting on memory bandwidth.

**2. Token-Level Mechanics of Function-Calling (Day 2, partner: Rahel Samson)**
My `composer.py` uses prompt-stuffing ("Return valid JSON") instead of native function-calling. Rahel explained that the `tools` parameter injects structured tokens into the model's context and constrains generation to valid function-call syntax at decode time. I now understand why native tool-use is structurally more reliable than prompt-stuffing.

**3. DPO Beta as a "Trust Budget" (Day 3, partner: Martha Ketsela)**
I set `beta=0.1` in my DPO trainer because it was the default. Martha showed that beta plays two roles in the gradient: a direct step-size multiplier and a self-stopping signal via the sigmoid. I now understand that beta=0.1 is a deliberate stability measure for Qwen 0.5B that prevents policy collapse while allowing preference learning.

**4. Bootstrap P-Value Mechanics (Day 4, partner: Melaku Yilma)**
I reported p=0.0127 in my CFO memo as if it closed the case for deploying the trained judge. Melaku showed that bootstrap p-values measure internal validity (sampling stability) but not external validity (deployment reliability). A significant aggregate result can mask subgroup failures via Simpson's Paradox.

### Four Gaps I Researched (Questions I Answered)

**1. System Prompt Cost Scaling (Day 1, for Efrata Wolde)**
Efrata couldn't explain why her agent's latency tripled when the system prompt doubled. I researched prefill compute scaling (quadratic attention) and KV cache mechanics to show that long system prompts are a hidden cost multiplier.

**2. Tool-Use Token Mechanics (Day 2, for Rahel Samson)**
Rahel couldn't explain what happens at the token level when a model "chooses" a tool. I traced the generation process from `tools` parameter injection through constrained sampling to function-call token emission.

**3. LoRA Rank as Information Bottleneck (Day 3, for Martha Ketsela)**
Martha couldn't explain why rank-16 is sufficient for her 200-pair binary judge task. I connected Aghajanyan et al. (2020) on intrinsic dimensionality to practical ablation predictions, showing that rank acts as a forced-generalization bottleneck.

**4. Statistical Significance vs. Deployment Reliability (Day 4, for Melaku Yilma)**
Melaku's adapter improved ΔB=+0.1046 (p=0.018) but still failed on confidence-boundary cases. I researched Simpson's Paradox and hidden stratification to show why aggregate metrics mask subgroup regressions.

### Standalone Post (Day 5)
**Structured Output vs. Constrained Decoding** — Researched the token-level mechanics of grammar-constrained sampling (Willard & Louf, 2023) to explain why "Return valid JSON" prompting is a probabilistic bias while constrained decoding is a structural guarantee. Published as a standalone post to round out the five-post public artifact requirement.

---

## The Most Surprising Thing I Learned

The most surprising insight was from Day 4: **my own p-value was lying to me.** I had been treating p=0.0127 as proof that my trained judge was ready for deployment. Melaku's explainer showed that the bootstrap can only resample from the data I gave it — and if my held-out set underrepresents the failure modes that matter in production, the p-value confirms stability on a biased sample. The grounding edit to `memo_week11.md` changed the decision logic of my CFO memo from "p<0.05 → deploy" to "p<0.05 validates the lift is real; stratified evaluation validates the lift is reliable." That single sentence changes the engineering standard for how I evaluate every future model.

---

## Trajectory Reflection

The sharpness of my questions improved measurably across the week. Day 1's question ("What is the computational difference between prefill and decode?") was diagnostic but broadly scoped. By Day 4 ("What is the paired bootstrap p-value physically computing when it resamples my 50-task held-out set 10,000 times, and why is a significant p-value insufficient to guarantee deployment reliability?") the question named the exact function, the exact dataset size, the exact claim in my memo, and asked for both the mechanism and its limitation. The constraint of one question per day forced genuine triage.

The grounding edits compound. Each day's edit made a different part of my portfolio technically defensible: Day 1 fixed cost accounting in `llm_client.py`, Day 2 added tool-use documentation to `composer.py`, Day 3 defended the `beta=0.1` hyperparameter in `train_judge_lora.py`, and Day 4 qualified the p-value claim in `memo_week11.md`. Together, they transform my portfolio from "a system that works" to "a system I can defend."
