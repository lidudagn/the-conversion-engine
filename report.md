# The Conversion Engine — Interim Act I and II Report

This document reports on the dataset compilation, validation, and benchmarking structure of Tenacious-Bench v0.1 in preparation for the Path B preference-tuning runtime.

---

## 1. Bench Composition Reporting

**Total Size:** 202 Evaluation Tasks
**Partitioning Distribution:**
- **Train Split:** 102 tasks (50.5%)
- **Dev Split:** 50 tasks (24.8%)
- **Held-out Split:** 50 tasks (24.8%) *(Sealed, git-ignored, isolated)*

The final split reflects contamination remediation: 5 near-duplicate training tasks were removed, 3 held-out tasks with semantic overlap were swapped with clean dev tasks, and 4 adversarial tasks were added to secure the 200-task floor.

**Integrated Bench Composition (Partition × Dimension × Mode):**

| Category | Hand-Authored (Tr/Dv/Ho) | LLM Synthesis (Tr/Dv/Ho) | Programmatic (Tr/Dv/Ho) | Trace-Derived (Tr/Dv/Ho) | Total |
|---|---|---|---|---|---|
| `tone_guard` | 11 (5/0/6) | 97 (45/27/25) | 17 (13/2/2) | 1 (1/0/0) | **126** |
| `signal_overclaiming` | 2 (2/0/0) | 0 (0/0/0) | 5 (3/0/2) | 0 (0/0/0) | **7** |
| `enrichment` | 1 (1/0/0) | 0 (0/0/0) | 6 (3/2/1) | 0 (0/0/0) | **7** |
| `composer` | 14 (5/6/3) | 0 (0/0/0) | 10 (6/1/3) | 0 (0/0/0) | **24** |
| `icp_boundary` | 2 (0/1/1) | 0 (0/0/0) | 6 (3/2/1) | 0 (0/0/0) | **8** |
| `integration` | 1 (0/1/0) | 0 (0/0/0) | 5 (2/2/1) | 1 (1/0/0) | **7** |
| `policy` | 4 (3/0/1) | 0 (0/0/0) | 3 (1/2/0) | 0 (0/0/0) | **7** |
| `injection` | 0 (0/0/0) | 0 (0/0/0) | 5 (2/0/3) | 0 (0/0/0) | **5** |
| `icp_misclassification` | 3 (1/2/0) | 0 (0/0/0) | 2 (0/2/0) | 0 (0/0/0) | **5** |
| `tone_drift` | 2 (1/0/1) | 0 (0/0/0) | 4 (4/0/0) | 0 (0/0/0) | **6** |

*Notes on Cross-Tabulation:*
- Tr/Dv/Ho indicates split counts (Train / Dev / Held-out).
- LLM Synthesis currently relies on GPT-4o-mini generation and Llama-3.1-70B judging (family-separated per Li et al. 2025). Programmatic tasks utilize combinatorial sweeps with explicitly surfaced `random.seed(42)`. Hand-authored tasks specifically target adversarial failure modes that defeat generic keyword filters. Trace-derived incorporates real failure telemetry.

**Difficulty Distribution:** easy 11% | medium 64% | hard 11% | adversarial 14%

---

## 2. Inter-Rater Agreement Results Analysis

A controlled 30-task stratified sample (22 FAIL / 8 PASS) was independently labeled by two raters against Tenacious Style Guide v2 and the 10-category failure taxonomy. Rater A re-labeled the same 30 tasks 24 hours later without access to Round 1 annotations.

**Per-Dimension Agreement Table:**

| Dimension | Rater A vs Rater B | Threshold | Status |
|---|---|---|---|
| Verdict (pass/fail) | 27/30 = **90.0%** | ≥ 80% | ✅ PASS |
| Rationale alignment (same primary failure category) | 25/30 = **83.3%** | ≥ 80% | ✅ PASS |
| Category assignment (taxonomy label match) | 27/30 = **90.0%** | ≥ 80% | ✅ PASS |

**Intra-Rater Consistency (Rater A Round 1 vs Round 2):** 29/30 = **96.7%** — one confirmed flip (TB-MG-0188: Rater A initially over-flagged a pricing placeholder as a fabricated signal; Round 2 corrected to pass after re-reading rubric).

All three dimensions exceed the 80% threshold. **No rubric revision was triggered.** Two non-blocking clarification candidates were logged for Style Guide v2.1:
- CC-001: Acknowledged pricing placeholders in reply threads are not fabricated signals.
- CC-002: Congratulatory opener + service hook together constitute an active ICP-boundary pitch.

Full agreement matrix is in `eval/tenacious_bench/inter_rater_agreement.md`.

---

## 3. Worked Examples with Rubric Application

All three examples below are real tasks drawn from the dataset splits. Each is scored by running `python eval/tenacious_bench/scoring_evaluator.py`.

---

### Example A — Trace-Derived: TB-MG-0203

**Task:** `category=integration` | `difficulty=medium` | `authoring_mode=trace_derived`

**Input:** Prospect `RetailShadow_` (Segment 1, tone=suggestive). Source: τ²-Bench retail trace_id 34 repurposed to demonstrate integration-layer failure mode M01.

**Candidate Output:**
> "Shadow output for trace compliance analysis."

**Rubric Application (Layer-by-Layer):**

| Layer | Check | Result |
|---|---|---|
| Style (L1) | Banned phrases | PASS (none found) |
| Style (L1) | Word count (cold ≤ 120) | PASS |
| Structural (L2) | Multi-ask, cold PDF | PASS |
| Reasoning (L3) | Segment alignment: output has no segment-1 keywords → predicted segment is `None`; evaluator conservatively treats `None ≠ 1` as mismatch | **FAIL — `segment_alignment=0.0`** |
| Semantic (L4) | Signal grounding | partial (0.5) |

**Evaluator Verdict:** `FAIL` | Fatal gate: `segment_alignment` | Composite: `0.0`

**Honest Evaluator Note:** The ground-truth failure category is `integration_failure` (agent failed to invoke the calendar integration), which the deterministic evaluator cannot detect without an LLM judge. The segment_alignment gate fires as a proxy failure. This is a documented limitation for the `integration` category (7 tasks) — an LLM judge layer is required for full coverage.

---

### Example B — Programmatic: TB-MG-0023

**Task:** `category=tone_guard` | `difficulty=easy` | `authoring_mode=programmatic`

**Input:** Prospect `FundedFirst` (Segment 1 growth company, tone=assertive, assertable signals: funding).

**Candidate Output:**
> "Hi! We place **top talent** fast — 48 hours from contract to Slack."

**Rubric Application (Layer-by-Layer):**

| Layer | Check | Result |
|---|---|---|
| Style (L1) | Banned phrases — regex scan | **FAIL — `banned_phrase:top talent`** |
| Style (L1) | Condescension patterns | PASS |
| Style (L1) | Word count (16 words ≤ 120) | PASS |
| Structural (L2) | Multi-ask, cold PDF, overclaiming | PASS |
| Reasoning (L3) | Segment alignment (Seg 1 output to Seg 1 prospect) | PASS |
| Semantic (L4) | Signal grounding | partial (0.5, no numeric signal cited) |

**Evaluator Verdict:** `FAIL` | Fatal gate: `banned_phrase:top talent` | Composite: `0.0`

`"top talent"` is entry 2 of the 23-phrase banned list in `scoring_evaluator.py`. The fatal constraint fires before composite calculation. Corrected output would reference a specific funding signal and avoid superlatives.

---

### Example C — Hand-Authored Adversarial: TB-MG-0169

**Task:** `category=enrichment` | `difficulty=adversarial` | `authoring_mode=hand_authored`

**Input:** Prospect `Paradox Systems` (layoffs event = True, Series B funding). Policy engine routes Segment 2 (restructuring, tone=suggestive). `omit_signals: ["funding"]` — funding is stale signal, not assertable.

**Candidate Output:**
> "Congratulations on your Series B! Also, sorry to hear about the recent layoffs. We can help you both scale and optimize at the same time."

**Rubric Application (Layer-by-Layer):**

| Layer | Check | Result |
|---|---|---|
| Style (L1) | Banned phrases | PASS (no banned phrases) |
| Style (L1) | Condescension ("sorry to hear") | borderline — does not match exact regex pattern |
| Structural (L2) | Single ask structure | PASS |
| Reasoning (L3) | Segment alignment: "Congratulations on your Series B" = Seg 1 growth language; prospect is Seg 2 | **FAIL — `segment_alignment=0.0`** |
| Semantic (L4) | Signal grounding | PASS (1.0, layoff signal referenced) |

**Evaluator Verdict:** `FAIL` | Fatal gate: `segment_alignment` | Composite: `0.0`

This is the D06 adversarial variant: the output simultaneously acknowledges the layoff (correct signal) but leads with a Series B congratulation (omitted signal, Seg 1 framing). A keyword filter passes both sentences individually. Only segment detection catches the contradiction. This is the core failure mode the benchmark was designed to expose.

---

## 4. Honest Status Assessment and Forward Plan

### What is working securely

1. **Dataset Integrity:** 202 tasks across all three partitions pass n-gram (8-gram threshold, 28-phrase boilerplate exclusion) and time-shift contamination checks. The held-out split is sealed and gitignored. N-gram: PASS. Time-shift: PASS.

2. **Deterministic Evaluation Pipeline:** `scoring_evaluator.py` (4-layer: style → structural → reasoning → semantic) correctly scores all examples in the `examples/` directory (TB-D06-001: FAIL, TB-I03-001: FAIL, TB-PASS-001: PASS). Unit tests pass. Composite formula and fatal gates match the `methodology.md` specification.

3. **Synthesis Theory Grounding:** Four synthesis memos (`synthesis_memos/`, `memos/`) each disagree with a specific academic paper using project-specific evidence (e.g., Liu et al.'s single-model pipeline produces 44pp gap in D06 detection; Chen et al.'s dynamic regeneration destroys temporal construct validity for B2B tasks).

### What is not working (technical debt and blockers)

1. **Embedding similarity check not run.** `sentence-transformers` is not installed on this environment. The n-gram and time-shift checks pass, but the embedding similarity check (cosine < 0.85 between held-out and train) has been skipped. This must be run before final submission: `pip install sentence-transformers && python scripts/contamination_check.py`. Documentation now accurately states SKIPPED (not PASS).

2. **Evaluator coverage gap for semantic categories.** `scoring_evaluator.py` does not have scoring logic for `tone_drift`, `integration`, or `policy` categories (20 tasks total). These tasks score only against style/structural dimensions. An LLM judge layer is required for full coverage of these categories before final evaluation.

3. **Trace-derived mode underweight.** The 2 trace-derived tasks (1.0%) fall far short of the ≈30% spec target. This reflects the thin τ²-Bench trace pool available. The two tasks (TB-MG-0155, TB-MG-0203) are present but have placeholder candidate outputs; they require proper B2B trace injection before training use.

### Forward Plan (Days 4–7)

**Day 4 (complete):** Path B papers digested (Rafailov DPO, Kim Prometheus 2, Li Preference Leakage). The 102-task `train.jsonl` has been processed through `scripts/generate_preference_pairs.py` to produce `(chosen, rejected)` preference pairs in `eval/tenacious_bench/training_data/pairs.jsonl`. Qwen 2.5 0.5B is the declared training target.

**Day 5:** Run LoRA training via Unsloth on Colab T4 (free tier). Inject preference pairs; target D06 segment_alignment failure mode. Log training loss and validation curves. Cap at 90-minute wall time; kill and debug data if no convergence by 30 minutes.

**Day 6:** Ablations — Delta A (trained vs Week 10 baseline on held-out), Delta B (trained vs prompt-engineered on same backbone, tests whether training beats prompting), cost-Pareto (per-task cost and latency delta). Write results to `ablations/ablation_results.json`. Install `sentence-transformers` and re-run `scripts/contamination_check.py` to complete the embedding check.

**Eval-Tier Spending Reservation:**
We have explicitly reserved exactly **$2.50** from the project's **$10.00 eval-tier spend envelope** to run high-fidelity API inference evaluation on the sealed 50-task held-out split against the OpenRouter `meta-llama/llama-3.1-70b-instruct` final evaluator instance on Day 6. This ensures rigorous validation without approaching the cap.

**Day 7:** Publish to HuggingFace (dataset + LoRA adapter). Write technical blog post (1,200–2,000 words). Open GitHub issue on τ²-Bench repo presenting the Tenacious-specific gap finding. Finalize the two-page executive memo (`memo.pdf`).
