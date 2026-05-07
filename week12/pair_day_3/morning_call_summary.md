# Morning Call Summary — Day 3

**Date:** 2026-05-07  
**Topic:** Training and Post-Training Mechanics  
**Participants:** Lidya Dagnew & Martha Ketsela  
**Duration:** ~25 minutes  

---

## Lidya's Draft Question (Before Sharpening)

**Original draft:** "What does `beta=0.1` do in my DPO training script?"

**Martha's interrogation:**
- Martha immediately pushed back: "That's a settings question, not a gap question. You could answer that by reading the TRL docs. What is it that you *can't* explain even after reading the docs?"
- I clarified that I understand beta "controls how far the model moves from the reference," but I cannot explain *how* — what happens at the gradient level, what the loss surface looks like, and what would mechanically break if I changed it.
- Martha asked: "If I set beta to 1.0 right now, what would you predict happens to your training loss curve?" I admitted I had no prediction — that's the gap.
- She then asked: "Is your question about the math, or about the practical consequence?" We agreed it's about the math *because* the math is what lets you predict the practical consequence.

**Sharpened version:** "In the DPO loss function, how does beta mathematically control the tradeoff between increasing preference likelihood and staying close to the base model's original policy, and what changes in gradient behavior would I expect if beta were much larger or smaller?"

**Why this version is better:** It names the specific mechanism (gradient behavior), asks for predictions at extremes (larger/smaller), and connects to a concrete artifact (`train_judge_lora.py` line 187). It cannot be answered by reading a one-line docstring.

---

## Martha's Draft Question (Before Sharpening)

**Original draft:** "Why did I use r=16 for LoRA? Is it the right rank?"

**Lidya's interrogation:**
- I pushed back similarly: "Right for what? You need to name what would be *wrong* about a different rank." Martha said she doesn't know what would happen if she used r=8 or r=64.
- I asked: "Do you understand why low-rank works at all — why a 1024×16 matrix can capture what a 1024×1024 update would?" She said no — she knows the decomposition ($\Delta W = BA$) but not why the rank-16 subspace is sufficient for her specific task.
- We discussed whether the question is about the math (intrinsic dimensionality) or the engineering (training dynamics). Martha wanted both — she wants to know *why* it works theoretically and *what she'd see* in ablations.
- I suggested she narrow to one: "Pick the ablation angle — what would you see at r=8 vs r=64 on your 200-pair dataset?" She agreed that's the version that would actually change how she works.

**Sharpened version:** "What does the intrinsic dimensionality of fine-tuning tell us about the relationship between task complexity and required rank? Specifically: if I had run ablations at r=8 and r=64 on my 200-pair dataset, what differences in training dynamics — loss curve shape, validation loss trajectory, signs of overfitting — would I expect to see, and why?"

**Why this version is better:** It grounds the theoretical concept (intrinsic dimensionality) in a concrete prediction (ablation outcomes), tied to her specific dataset size (200 pairs) and task type (binary constraint judging).

---

## Sign-off
Both partners confirmed the questions are unambiguous, diagnostic, grounded in specific artifacts, and resolvable in a single explainer. Questions finalized for the day.
