# Synthesis Memo: Direct Preference Optimization (Rafailov et al., NeurIPS 2023)

## Key Takeaways
- **DPO eliminates the reward model**: Unlike RLHF, DPO reparameterizes the reward function directly into the policy, using a simple binary cross-entropy loss over preference pairs (chosen vs. rejected). This removes the RL training loop entirely.
- **The β hyperparameter controls conservatism**: Higher β keeps the trained model closer to the reference policy; lower β allows more deviation. Rafailov et al. show β=0.1 is a robust default for most tasks.
- **Reference model is load-bearing**: DPO requires a frozen reference model to compute the KL-divergence penalty in the loss. This doubles VRAM requirements compared to SFT — a critical constraint for Colab T4 (16GB).
- **Data quality dominates data quantity**: The paper demonstrates that 1,000–5,000 high-quality preference pairs are sufficient to produce measurable alignment shifts, consistent with the LIMA principle.

## Disagreement and Critique

Rafailov et al. present DPO as universally applicable to any preference dataset, treating the preference signal as a clean binary: chosen is better than rejected, full stop. Their theoretical framework assumes **preferences are consistent and transitive** across the dataset.

**This assumption breaks down for Tenacious-style B2B semantic alignment, and our training data construction proves it.**

In our preference pairs for D06 (Wrong-Segment Pitching), the "rejected" outputs are not simply worse — they are **contextually wrong in ways that share surface features with the chosen outputs**. A Segment 2 (restructuring/efficiency) email that uses the word "scale" in the context of "scaling down" is semantically correct for Seg2 but lexically identical to a Seg1 growth pitch's use of "scale." Standard DPO treats this as a clean preference signal, but the model may learn the wrong feature: "avoid the word scale" rather than "detect contextual usage of scale."

Our Week 10 trace evidence confirms this risk. In `outputs/e2e_batch_results.json` (the AMS-PAR trace), the agent correctly used Seg4 keywords ("AI infrastructure," "maturity") but applied them to the wrong company — the hiring signal was for Data Platform Engineers, not ML Engineers. A naive DPO training on this pair would teach the model "avoid AI keywords" rather than "verify the hiring signal supports AI maturity inference." The distinction is between **surface-level keyword avoidance** (which DPO naturally learns) and **grounding verification** (which requires the model to cross-reference input fields).

**Our mitigation**: We construct "hard negative" preference pairs (pair_type: "hard") where the rejected output deliberately uses correct keywords in the wrong framing context. This forces DPO to learn the semantic distinction rather than the keyword distinction. Without this, DPO on our domain would produce a model that is syntactically conservative but semantically unimproved — passing fewer D06 probes by writing bland emails rather than by correctly routing segments.

## Application to Tenacious-Bench

- **β=0.1 as starting point**: We adopt Rafailov et al.'s recommended β and plan a single ablation at β=0.05 to test whether more policy deviation helps on our adversarial slice.
- **Three-tier rejection strategy**: Each training task produces three rejected variants (blatant, subtle, hard negative) to ensure DPO learns grounding-level distinctions, not just surface rejection.
- **VRAM constraint drives SimPO consideration**: The reference model requirement doubles memory. On Colab T4 with 16GB, this limits us to Qwen 3.5 0.8B with DPO, or allows Qwen 3.5 4B with SimPO/ORPO (reference-free). This is the primary motivation for evaluating reference-free alternatives.
