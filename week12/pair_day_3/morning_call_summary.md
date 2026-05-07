# Morning Call Summary — Day 3

**Date:** 2026-05-07
**Topic:** Training and Post-Training Mechanics
**Participants:** Lidya Dagnew & Martha Ketsela

## Ambiguity & Sharpening

### Lidya's Question:
- **Initial:** What does `beta=0.1` do in my LoRA training script?
- **Sharpening:** We focused on the **KL-divergence penalty**. We realized the question isn't just about what number to pick, but the mathematical role of beta as a "trust budget" for how much the model is allowed to move away from the reference policy to satisfy the preference pairs. We sharpened the question to ask about gradient behavior at the extremes.

### Martha's Question:
- **Initial:** Why is `r=16` enough for my judge model training?
- **Sharpening:** We focused on **Intrinsic Dimensionality**. We sharpened Martha's question to ask why a rank-16 subspace is sufficient for binary constraint judging on a 200-pair dataset, and what the mechanical differences in training dynamics (loss curves, overfitting) would be if the rank were doubled or halved.

## Final Questions Finalized
Both partners confirmed that the questions are unambiguous and hit the "resolvable in one explainer" criteria.
