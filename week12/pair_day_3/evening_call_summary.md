# Evening Call Summary — Day 3

**Date:** 2026-05-07  
**Topic:** Training and Post-Training Mechanics  
**Participants:** Lidya Dagnew & Martha Ketsela  
**Duration:** ~30 minutes  

---

## Feedback on Martha's Explainer (peer_explainer.md — DPO Beta)

**What landed immediately:**
- The decomposition of beta into two distinct roles — "overall step size" and "self-stopping signal" — was the moment the gap closed for me. I had been thinking of beta as a single knob, but Martha showed it appears in two separate places in the gradient: as a leading multiplier ($-\beta$) and inside the sigmoid ($\sigma(-\beta h)$). These do different things.
- The "Trap in the Training Logs" section was genuinely surprising. I didn't know that `rewards/margins` in TRL already has beta baked in, so dividing by beta to get actual policy drift ($h$) was a practical insight I can immediately apply to my next training run.
- The visualization of gradient scale across different beta values made the abstract math concrete. Seeing the β=0.01 line stay flat (no self-stopping) versus β=1.0 collapsing aggressively answered my original question about "what changes at the extremes."

**What I asked Martha to clarify:**
- I asked for more specificity about what happens with Qwen 0.5B specifically — a very small model. She added the point that small models are more sensitive to policy drift because they have fewer redundant parameters to absorb the shift. This means beta=0.1 is actually more critical for us than for someone fine-tuning a 7B model.
- I asked whether the "reward model overoptimisation" section at the end was necessary or if it diluted the focus. Martha defended it: "It's the same mechanism — KL constraint preventing distribution shift — just in a different setting. If you understand it here, you understand it everywhere." I agreed to keep it.

**Revision made:** Martha added one paragraph on the Qwen 0.5B sensitivity point. No other structural changes.

---

## Feedback on Lidya's Explainer (explainer.md — LoRA Rank)

**What landed for Martha:**
- The framing of rank as an "information bottleneck" clicked for her. She had been thinking of rank as "how many parameters," but the bottleneck framing — rank forces generalization by constraining the model to learn rules rather than memorize examples — changed her mental model.
- The ablation predictions (r=8 plateaus early, r=64 shark-fins on validation) gave her a concrete diagnostic she can run on her own training logs.

**What Martha asked me to clarify:**
- She pushed back on my claim that "rank-16 is over-provisioned for 200 pairs." She asked: "If it's over-provisioned, why doesn't it overfit?" I clarified that the DPO beta acts as a second regularizer — even with excess rank capacity, beta prevents the model from fully exploiting all those parameters. This is the interaction between rank and beta that neither of our explainers had explicitly named until this conversation.
- She asked me to add a note connecting the rank discussion to the DPO beta discussion, since they are complementary constraints. I added the "DPO Beta Connection" section to show that rank limits *how many* parameters change while beta limits *how much* they change.

**Revision made:** Added the "DPO Beta Connection" subsection and revised the conclusion to reference the rank-beta interaction.

---

## Gap Closure Judgments

**Lidya's gap (DPO Beta):** ✅ **Closed.** I can now explain the dual role of beta in the gradient, predict training behavior at different beta values, and diagnose policy drift from training logs by dividing out beta.

**Martha's gap (LoRA Rank):** ✅ **Closed.** Martha confirmed she now has a mental model for why r=16 works (intrinsic dimensionality + information bottleneck) and can predict ablation outcomes for her dataset size.

---

## Grounding Commits
- **Lidya:** Added a 5-line technical comment to `scripts/train_judge_lora.py` (line 187) documenting the "Trust Budget" role of beta=0.1 and the policy collapse risk.
- **Martha:** Will add a comment to her LoRA config explaining rank selection rationale based on task complexity and dataset size.
