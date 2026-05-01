# Synthesis Memo: SimPO (Meng et al., NeurIPS 2024) and ORPO (Hong et al., EMNLP 2024)

## Key Takeaways
- **SimPO eliminates the reference model**: Unlike DPO, SimPO uses average log-probability of the sequence as the implicit reward, with a margin parameter γ that replaces β. No frozen reference model is needed, halving VRAM requirements.
- **ORPO combines SFT and preference in one loss**: Odds Ratio Preference Optimization adds a preference penalty to the standard SFT cross-entropy loss, training alignment and generation quality simultaneously in a single pass. This is the most parameter-efficient approach.
- **SimPO outperforms DPO on AlpacaEval 2 and Arena Hard**: Meng et al. report consistent 3–5 point improvements over DPO across multiple model sizes (1B–70B). The length-normalized reward signal in SimPO prevents the verbosity bias that plagues standard DPO.
- **ORPO is the cheapest training option**: Single-pass training with no reference model and no separate SFT stage. Hong et al. show competitive performance with DPO while using 30–50% less compute.

## Disagreement and Critique

Both SimPO and ORPO claim **general superiority over DPO** based on benchmarks that measure broad instruction following (AlpacaEval, MT-Bench, Arena Hard). Meng et al. frame SimPO's length normalization as universally beneficial because it prevents reward hacking through verbosity.

**For Tenacious-style B2B evaluation, length normalization is not universally beneficial — it can actively harm segment alignment detection.**

Our D06 failure mode involves emails where the semantic error is concentrated in 1–2 sentences within an otherwise correct 120-word email. A Seg2 prospect receives an email that is 90% correct restructuring language, but the closing CTA uses a Seg1 growth framing ("when you're ready to scale aggressively"). Under SimPO's average log-probability reward, this single misaligned sentence is diluted by the 90% correct content. The per-token averaging penalizes short, focused errors less than long, distributed errors — the opposite of what our failure taxonomy requires.

DPO's total-sequence reward does not have this dilution problem: the entire output is compared against the reference policy's assessment, and a single fatal sentence can dominate the gradient signal. For our specific failure mode, DPO's "blunt instrument" may actually be more appropriate than SimPO's "refined measurement."

**Our decision**: We select **ORPO** as our primary training algorithm, not SimPO, for three reasons:
1. **VRAM efficiency**: No reference model enables Qwen 3.5 4B on Colab T4, versus being limited to 0.8B with DPO.
2. **Combined SFT+preference**: The monolithic loss ensures the model maintains generation quality while learning preferences — important because our judge model must produce well-formatted VERDICT: PASS/FAIL outputs.
3. **We can compensate for length dilution**: By constructing preference pairs where the rejected output has the error in the opening sentence (not buried in the middle), we ensure the ORPO gradient signal concentrates on the diagnostic region. This is a data-construction choice, not an algorithm limitation.

SimPO remains a viable fallback if ORPO convergence is poor.

## Application to Tenacious-Bench

- **ORPO as primary, DPO as backup**: ORPO's parameter efficiency enables training on a larger backbone (4B vs 0.8B). If ORPO validation loss plateaus above DPO baseline after 1 epoch, we switch.
- **γ=1.0 (SimPO margin) vs λ=0.1 (ORPO odds ratio weight)**: Per Hong et al., λ=0.1 is the robust default; we adopt it and ablate at λ=0.05.
- **Error-front-loading in training data**: Rejected outputs are constructed with the D06 violation in the first 2 sentences to prevent the length-normalization dilution described above.
