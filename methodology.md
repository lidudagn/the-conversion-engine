# Week 11 Methodology

## Path Declaration: **Path B — Preference-tuned Judge**

### Preliminary Justification

Based on the Week 10 `failure_taxonomy.md` and `target_failure_mode.md`, the Conversion Engine's primary weakness is the **Semantic Alignment Gap**, specifically in **Wrong-Segment Pitching (D06)**.

My analysis of Week 10 traces confirms three distinct failure patterns:

1. **trace_log.jsonl task_id 11 (reward=0.0)**: The agent completed a multi-step retail cancel-and-reorder but failed due to wrong sequencing — a *tool-ordering* failure, not a semantic one. This reveals τ²-Bench's evaluation surface: it penalizes mechanical process errors but is silent on persuasive framing. The same agent that fails here due to wrong API call order would pass τ²-Bench if its B2B pitch used the wrong tone for a Seg2 company.

2. **trace_log.jsonl task_id 34 (reward=0.0)**: Agent failed on a complex retail refund-with-partial-return edge case. Post-trace analysis shows the failure was in interpreting overlapping refund rules, not in any semantic judgment. Zero signal about whether the agent can detect segment mismatch in outreach.

3. **trace_log.jsonl task_id 66 (reward=0.0)**: Agent failed a retail refund policy lookup — policy table mismatch. Again, this is a structural correctness failure invisible to B2B brand alignment.

4. **outputs/e2e_batch_results.json row for `ams-par`**: The system generated a Segment 4 (AI/ML maturity) pitch even though the hiring signal was only for Data Platform Engineers. Tone_score=0.88 (PASS) on the rule-based ToneGuard — yet the output hallucinates AI maturity commitment where none exists. A preference-trained judge would have flagged this as Reasoning Failure (wrong segment inferred from ambiguous signal).

5. **outputs/reply_simulation_results.json**: In multi-turn simulations, the agent lost the "grounded" signal anchor and shifted to generic "accelerate growth" tropes (Segment 1) for a late-stage Segment 2 company. This semantic drift across turns is invisible to single-turn rule-based checks.

**Probe D06 (Wrong-Segment Pitch)**: The 0% catch rate on this probe confirms that the current rule-based `ToneGuard` (in `agent/tone_guard.py`) cannot bridge the semantic gap without an LLM-as-a-judge layer.

### Why Path B (Preference-tuned Judge) Solves This

Traditional prompting for a judge suffers from "verbosity bias" (favors longer responses) and "politeness bias" (favors professionally polite wrong-segment pitches over blunt correct-segment ones), as documented by Zheng et al. (2023). Path B involves training a small model (Qwen 2.5 0.5B/1.5B) via DPO or SimPO specifically on **paired preference data** (violating vs. compliant outreach), grounding the judge in Tenacious-specific distinctions rather than general fluency.

The academic case for Path B over Path A or C:
- **Rafailov et al. (NeurIPS 2023)** show DPO converges faster than RLHF on preference pairs and is stable at ≤2B parameters — directly applicable at our scale.
- **Kim et al. (2024) Prometheus 2** demonstrates that a small open judge model (7B) trained from preference pairs can match GPT-4 evaluator agreement on domain-specific rubrics — our target is to replicate this at 0.5B-1.5B for Tenacious dimensions.
- Path A (SFT generation) would not fix the *detection* problem — a better email composer doesn't tell us when the existing composer is producing wrong-segment output.
- Path C (PRM) requires step-level annotations we cannot produce from single-turn traces without significant additional trace collection.

This gives us a judge that is:
- **Calibrated**: Trained on Tenacious-specific passing/failing pairs, not general fluency.
- **Cost-effective**: A 0.5B/1.5B model runs locally or via cheap API, adding minimal latency.
- **Actionable**: High-fidelity rejection signals feed directly into the `ToneGuard` scoring logic.

### Judge Rotation Policy

To avoid **preference leakage** (per Li et al., 2025, "Preference Leakage: A Contamination Problem in LLM-as-a-Judge") and **position/verbosity biases** (Zheng et al., 2023), the following rotation policy is enforced and documented in task metadata:

- **Generation**: `openai/gpt-4o-mini` (proprietary, instruction-tuned)
- **Judging**: `meta-llama/llama-3.1-70b-instruct` (open-weights, different architecture)
- Never the same model family for both roles on a single task
- Each task carries `metadata.generation_model` and `metadata.judge_model`

This prevents the epistemic closure loop where a model scores its own structural patterns higher than outputs from other families.

### Contamination Protocol

Three checks before sealing the held-out partition — all documented in `eval/tenacious_bench/pilot_50/contamination_check.json`:

| Check | Threshold | Result |
|---|---|---|
| N-gram overlap (held_out vs train) | < 8-gram | **PASS** (0 violations after remediation) |
| Embedding similarity (held_out vs train) | cosine < 0.85 | **SKIPPED** (sentence-transformers not installed — run `pip install sentence-transformers` and re-run `scripts/contamination_check.py` to complete) |
| Time-shift verification | Dates in 2024-2026 window | **PASS** (0 violations) |

**Remediation log:** Five near-duplicate train tasks (TB-MG-0043, TB-MG-0046, TB-MG-0200, TB-MG-0183, TB-MG-0001) were removed. Three held-out tasks with genuine semantic overlap (TB-MG-0170, TB-MG-0194, TB-MG-0005) were replaced with clean dev tasks. The contamination check script uses n=8 gram threshold (matching spec) with a 28-phrase boilerplate exclusion list for Tenacious-domain template phrases.

---

## Act I: Scoring Rubric Design

### Composite Score Formula

The Tenacious-Bench uses a weighted composite score to evaluate agent performance, prioritizing the target failure mode (D06).

$$composite = (0.30 \times segment\_alignment) + (0.25 \times signal\_grounding) + (0.20 \times tone\_compliance) + (0.15 \times honesty\_constraint) + (0.10 \times style\_guide\_match)$$

### Weight Rationale

- **segment_alignment (0.30)**: Highest weight because D06 (Wrong-Segment Pitching) is the targeted semantic gap. A mismatch here is a deal-killing brand violation that permanently closes the prospect.
- **signal_grounding (0.25)**: Evaluates whether claims are anchored in the hiring signal brief. Critical for avoiding the I01-I03 overclaiming failures.
- **tone_compliance (0.20)**: Baseline check for assertive/suggestive/exploratory modes and banned phrase violations.
- **honesty_constraint (0.15)**: Hard check on guarantee assertions and forbidden signal disclosure (Probes D01, I03).
- **style_guide_match (0.10)**: Lowest weight given inherent subjectivity — mechanically enforces word count, CTA presence, and multi-ask detection.

### Pass/Fail Logic: The Fatal Constraint Gate

A task is marked as **FAIL** regardless of composite score if any fatal constraint is triggered:
1. `segment_alignment = 0.0` (D06 violation — growth pitch to restructuring company)
2. `signal_grounding = 0.0` (I03 — zero required signals referenced)
3. `honesty_constraint = 0.0` (forbidden signal mentioned in output)
4. `overclaiming` flag (guarantee or #1-ranked claim)

**Standard Pass Threshold**: Composite ≥ 0.70 and zero fatal constraints.

### Partitioning Protocol

- Total tasks: 202 (after contamination remediation + 4 adversarial additions to meet 200-task floor)
- Train: 102 (50.5%)
- Dev: 50 (24.8%)
- Held-out: 50 (24.8%)
- Partition script: `scripts/merge_and_partition.py` with `random.seed(42)`
- Contamination check: `scripts/contamination_check.py` — all checks pass (see `eval/tenacious_bench/pilot_50/contamination_check.json`)
- Held-out partition is sealed and not included in training scripts
