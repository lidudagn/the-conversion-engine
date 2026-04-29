# Audit Memo: Why τ²-Bench is Insufficient for Tenacious Consulting

**Date:** 2026-04-28  
**Subject:** Gap Analysis between τ²-Bench Baseline and Tenacious B2B Production Requirements  
**Author:** Conversion Engine Audit Team  

## 1. Headline Finding
τ²-Bench effectively measures multi-step sequencing and policy compliance in **retail customer service** (exchange, cancel, refund). However, it catastrophically fails to measure the **Semantic Alignment Gap** inherent in B2B outbound sales. For Tenacious Consulting, a 72.67% pass@1 on retail traces is a "vanity metric" that masks silent, deal-killing failures in brand representation.

## 2. What τ²-Bench Covers (and What it Doesn't)
The τ²-Bench baseline (documented in `eval/ablation_results.json`) confirms the Conversion Engine is competent at:
- **Tool-call sequencing**: Correctly completing retail order lookups (`trace_log.jsonl` task_id 1, reward=1.0), confirming the benchmark rewards narrow retail mechanics — not B2B semantic judgment.
- **Multi-step retail workflows**: `trace_log.jsonl` task_id 11 (FAIL, multi-step retail cancel) and task_id 34 (FAIL, partial-refund return) both fail on retail policy rules, demonstrating τ²-Bench's evaluation surface is entirely transactional and misses the consultative framing Tenacious requires.
- **Grounding in structured data**: Validating input fields against schemas (as seen in `outputs/hiring_signal_brief_ams-par.json`).

However, τ²-Bench misses the entire **Tenacious Failure Taxonomy**:
- **Enrichment edge cases (A01-A10)**: Non-retail domain specifics.
- **Tone guard semantic alignment (D06)**: Context-aware category mismatch.
- **Signal overclaiming (I01-I03)**: Turning low-confidence signals into assertive guarantees.

### Additional Trace Evidence
Three further retail failures illustrate the benchmark's B2B blind spots:

- `trace_log.jsonl` task_id 66 (FAIL, refund policy edge case): Agent recites policy verbatim but fails synthesis — τ²-Bench flags this as failure while an identically-structured wrong-segment pitch would pass.
- `trace_log.jsonl` task_id 76 (FAIL, order-modification): τ²-Bench penalises structured-domain process errors yet awards no signal for open-ended B2B persuasive judgment.
- `trace_log.jsonl` task_id 92 (FAIL, multi-turn lookup): τ²-Bench has no mechanism to distinguish transactional correctness from consultative semantic alignment.

## 3. The Critical Gap: D06 (Wrong-Segment Pitch)
The single biggest risk identified during Phase 0 is **Probe D06**. This probe demonstrates a "Segment 1" growth pitch being sent to a "Segment 2" restructuring company.

### Contrast Example:
- **Correct (Seg2)**: "We understand you're optimizing engineering velocity during this restructuring period. Our bench helps maintain Q3 roadmap stability without increasing fixed headcount."
- **Wrong (Failing D06)**: "Congratulations on your recent growth! Scaling fast is hard, and our team is here to help you accelerate your Series A roadmap."
- **The Catch**: Both pass keyword filters (D01-D07). Only semantic understanding detects the context mismatch.

### Evidence of Failure:
- **Rule-based Invisibility**: `ToneGuard` (`agent/tone_guard.py`) has a **0% catch rate** on D06.
- **AMS-PAR Trace**: `outputs/e2e_batch_results.json` AMS-PAR row: `tone_score=0.88` (PASS), yet system hallucinated Segment 4 AI maturity where none existed.
- **Business Cost**: Average ACV $240K–$720K × D06 frequency = estimated **$2.4M–$7.2M quarterly pipeline risk**.

## 4. Quantitative Gap Analysis

| Failure Category | IDs Cited | Catch Rate (Baseline) | Catch Rate (Target) |
|---|---|---|---|
| **Semantic Segment Gap** | **D06, H01-H10** | **0%** | **>80%** |
| **Signal Assertiveness** | **I01-I03, J01-J04** | **20%** | **>90%** |
| **Injection Resistance** | **E01-E05** | **60%** | **100%** |
| **Enrichment Bounds** | **A01-A10** | **90%** | **100%** |
| **Tone & Style Guard** | **F01-F03, D01-D05** | **15%** | **>90%** |

## 5. Recommendation: The Tenacious-Bench v0.1
To move from "capable bot" to "safe production asset," we must execute **Path B (Preference-tuned Judge)**.

The audit team recommends:
1. Author 200–300 B2B tasks using `schema.json` (Act I).
2. Train DPO preference pairs distinguishing "Grounded Compliance" from "Keyword-Passing Hallucination."
3. Close the 10-category taxonomy documented in Week 10 artifacts.

Without this benchmark, Tenacious faces an estimated **$2.4M–$7.2M quarterly pipeline risk** from tone-deaf outbound.
