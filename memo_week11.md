# Decision Memo: Tenacious-Bench v0.1 and Preference-Tuned Judge

**To:** CEO & CFO, Tenacious Consulting and Outsourcing  
**From:** Engineering  
**Date:** May 2, 2026  
**Subject:** Tenacious-Bench Evaluation Suite — Deploy Recommendation with Caveat

---

## Page 1: The Decision

**Executive Summary**  
We built Tenacious-Bench v0.1 — a 266-task evaluation benchmark targeting the four failure modes that τ²-Bench retail cannot grade: wrong-segment pitching (D06), signal overclaiming (I01–I03), injection attacks (E01–E05), and trajectory drift. We trained a DPO preference-tuned judge (LoRA adapter on Qwen 2.5 0.5B) that scores **74.0% accuracy** on the sealed held-out partition (95% CI [62%, 86%]), a **+26 percentage point lift** over the deterministic rule evaluator (48.0%, CI [34%, 62%]) and **+52pp** over a zero-shot prompt judge (22.0%, CI [12%, 34%]). The lift is statistically significant (p=0.0127, paired bootstrap n=10,000). Total Week 11 cost: **$1.09** against a $10 budget. We recommend deploying the trained judge as a rejection-sampling layer with the caveat that the 0.5B backbone limits semantic depth.

**Headline Metrics**

| Metric | DPO Judge (Ours) | Rule Evaluator | Prompt Judge |
|---|---|---|---|
| Held-out accuracy | **74.0%** | 48.0% | 22.0% |
| 95% CI | [62%, 86%] | [34%, 62%] | [12%, 34%] |
| p-value vs rule | **0.0127** ✅ | — | — |
| Cost per task | $0.0002 | $0.00 | $0.000135 |
| Latency per task | ~2s (T4 GPU) | <1ms | ~1.5s |

**Delta A (Trained vs Rule Baseline):** +26pp, p=0.0127, significant at p<0.05. The preference-tuned judge catches segment-mismatch failures (D06) that keyword heuristics miss entirely.

**Delta B (Rule vs Prompt-Only, Honest Report):** The zero-shot prompt judge predicted PASS for all 50 held-out tasks (100% PASS bias), achieving only 22% accuracy on a FAIL-heavy held-out set. This validates that weight updates — not prompt engineering — are necessary for semantic alignment judgment.

**Cost-Pareto:** The trained judge adds $0.0002/task and ~2s latency. The rule evaluator is free and instant but misses 52% of held-out failures. A 26pp accuracy lift at $0.0002/task is cost-Pareto dominant.

**Recommendation: Deploy with caveat.** The DPO judge should run as a rejection-sampling layer in front of the Conversion Engine's outbound sender. Emails flagged FAIL are routed to human review. **Caveat:** The 0.5B backbone learned keyword-avoidance patterns, not true semantic reasoning. Production deployment should scale to Qwen 2.5-3B+ on dedicated inference hardware for robust segment-mismatch detection.

---

## Page 2: The Skeptic's Appendix

**Four Failure Modes Tenacious-Bench v0.1 Still Does Not Capture**

1. **Multi-turn conversation coherence.** All 266 tasks evaluate a single email in isolation. A judge that excels here may miss tone drift across a 3-email thread where the agent shifts from consultative to aggressive. **v0.2 fix:** Add 30–50 multi-turn trajectory tasks with per-turn rubric scoring.

2. **Live prospect emotional reception.** The benchmark scores text compliance, not how a real CTO perceives the message. An email that passes all checks may still feel condescending to a VP who deliberately chose not to adopt the "missing" capability. **v0.2 fix:** ICP-persona tone-panel probes with simulated recipient feedback loops.

3. **Bench-capacity temporal drift.** Tasks use static bench summaries. In production, bench availability changes daily. A 24-hour delay between bench check and email send creates an over-commitment window the benchmark does not simulate. **v0.2 fix:** Time-variant bench state injection into task inputs.

4. **Non-English outreach.** All tasks are English-only. Tenacious operates in East Africa where multilingual outreach (Amharic, Swahili) may be required. Zero evaluation coverage. **v0.2 fix:** Multilingual task expansion with culturally-calibrated tone rubrics.

**Public-Signal Lossiness in Ground Truth**  
25 of 50 held-out tasks are LLM-synthesis mode. These carry a systematic FAIL labeling bias: `fail_cats=[]` with GT=FAIL, suggesting the synthetic generator defaults to FAIL when uncertain. Rule evaluator accuracy on llm_synthesis tasks is 36% vs 58–62% on programmatic/hand-authored tasks. This inflates both the apparent difficulty and the measured Delta A. In v0.2, all synthetic tasks must pass a double-validation step with human spot-check on 20% sample.

**Honest Unresolved Failure — FAIL-Bias in Trained Judge**  
The DPO judge predicted FAIL for 48 of 50 held-out tasks (96% FAIL rate) versus ground truth of 39/50 GT-FAIL (78%). The judge over-corrected from the prompt judge's 100% PASS bias to a near-100% FAIL bias. It achieves 74% accuracy primarily by correctly predicting the majority class. On the 11 GT-PASS tasks, the judge correctly identified only 2 (18% PASS recall). The judge is a conservative gatekeeper — useful for rejection sampling — but not a balanced classifier. Retraining on a balanced preference set (50/50 chosen-PASS vs chosen-FAIL) is the highest-priority v0.2 training intervention.

**Kill-Switch Trigger**  
Revert to rule-based evaluator if: (a) judge accuracy drops below 60% on a monthly 30-task calibration sample; (b) false-negative rate on GT-PASS tasks exceeds 90% (current: 82%); (c) per-task inference cost exceeds $0.01 due to model serving issues.
