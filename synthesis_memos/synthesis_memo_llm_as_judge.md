# Synthesis Memo: A Survey on LLM-as-a-Judge (Gu et al., 2024–2025)

## Key Takeaways

- **Three evaluation paradigms**: Gu et al. categorize LLM-as-a-judge into (1) pointwise scoring (judge evaluates a single output on a rubric), (2) pairwise comparison (judge picks the better of two outputs), and (3) listwise ranking. Pointwise is the most scalable for dataset authoring; pairwise is highest-signal for preference pair selection. The survey recommends using both: pointwise to filter task quality, pairwise to select chosen/rejected pairs for DPO.

- **Calibration failures are systematic**: Position bias, verbosity bias, and self-preference are all documented at >10% error rates in zero-shot judge settings. The paper's primary mitigation is rubric anchoring — providing the judge with explicit scoring rubrics and worked examples rather than asking for holistic judgment. Judges without rubrics show >30% variance on equivalent inputs.

- **Small judges match frontier judges when rubric-grounded**: The key finding relevant to Path B is that a 7B judge trained on rubric-grounded preferences (Prometheus 2, Kim et al. 2024) achieves correlation with GPT-4-class judges on in-domain tasks. This validates training a 0.5B judge for Tenacious-specific tasks where the rubric is machine-verifiable.

## Disagreement with a Specific Design Choice

Gu et al. recommend pairwise comparison as the gold standard for preference data construction — always compare two outputs side-by-side rather than scoring each independently. For Tenacious-Bench training data generation, I used **pointwise judge filtering followed by heuristic pairing**, not pairwise comparison. The reason: pairwise comparison at 279 pairs × 3 rejection tiers = 837 judge calls, each requiring two full email completions in context. At dev-tier pricing this was within budget, but the quality signal was lower than expected because the judge frequently preferred the "blatant" wrong-segment email over the "subtle" wrong-segment email for the wrong reasons (fluency, not alignment). Pointwise scoring with explicit dimension rubrics (segment_alignment, signal_grounding, tone_compliance) was more reliable for filtering than holistic pairwise preference.

This matches the finding in §4.3 of Gu et al. that rubric-anchored pointwise scoring has lower variance than free-form pairwise comparison when the rubric dimensions are well-defined — which they are in Tenacious-Bench.

## Application to Tenacious-Bench

The judge pipeline in this project follows Gu et al.'s calibration recommendations:
1. **Rubric anchoring**: every judge call includes the five Tenacious scoring dimensions with explicit pass/fail thresholds (eval/prompts/judge_filter_prompt.md)
2. **Cross-family rotation**: generation model ≠ judge model (Li et al. 2025 preference leakage prevention)
3. **Spot-check calibration**: 50 sampled tasks scored by eval-tier model (Claude Sonnet 4.6) to calibrate the cheap-model judge
4. **Pointwise for dataset filtering, pairwise implicit via DPO**: the DPO preference pairs encode the pairwise signal without requiring explicit pairwise judge calls
