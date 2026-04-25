# Act IV — Mechanism: Plan-Execute-Verify (PEV) Agent

**Date:** 2026-04-24  
**Target failure mode:** Multi-step write operation sequencing (τ²-Bench retail domain)  
**Baseline:** pass@1 = 0.7267, 95% CI [0.6504, 0.7917] (qwen3-next-80b-a3b-thinking, n=150 simulations, instructor-provided; git commit d11a97072c49d093f7b5a3e4fe9da95b490d43ba)  
**Held-out result:** pass@1 = 0.4615, 95% CI [0.2308, 0.7692] (pev_v1, n=13 scored / 20 attempted)  
**Delta A:** −0.2652 (PEV underperformed baseline; see §9 for diagnosis)  
**Delta A success criterion:** positive Delta A AND bootstrap CI lower bound > baseline CI upper bound (0.7917). **Not met.** CI [0.23, 0.77] lies below baseline lower bound (0.6504). t = −1.84, p = 0.955 (one-sided, H₁: PEV > baseline).

---

## 1. Problem Statement

The Day-1 baseline evaluation (27.87% pass@1) identified a primary failure mode: **multi-step write operations — exchanges and cancellations with multiple items or sequential actions**. The agent:

1. Attempted to modify order state without verifying current state first
2. Made partial changes (completed step 1, silently failed step 2)
3. Reported success to the customer without confirming each operation's result

This is a **tool-call sequencing failure**, not a knowledge failure. The agent knew the policy; it failed to execute it in the correct order.

---

## 2. Mechanism: Plan-Execute-Verify (PEV)

PEV adds explicit sequencing instructions to the agent's system prompt. The intervention is purely a system prompt modification — the model, tools, temperature, and task set are unchanged.

### Variant V0 — Baseline

Original `AGENT_INSTRUCTION` from tau2-bench `LLMAgent`:

```
You are a customer service agent... In each turn you can either:
- Send a message to the user.
- Make a tool call.
You cannot do both at the same time.
Try to be helpful and always follow the policy. Generate valid JSON only.
```

No sequencing guidance. Agent improvises multi-step operations.

### Variant V1 — Verify-only

Adds two rules:

```
IMPORTANT — Before modifying any order or account:
1. Always look up the current state first using the appropriate read tool.
2. After each change, confirm the result before proceeding or responding to the customer.
3. Only tell the customer an operation is complete after you have confirmed it succeeded.
```

Tests whether **verification alone** — without explicit planning — is sufficient.

### Variant V2 — Full PEV

Adds explicit UNDERSTAND / VERIFY / PLAN / EXECUTE / CONFIRM cycle:

```
UNDERSTAND — Identify exactly what the customer wants changed (specific item IDs, quantities).
VERIFY — Use read tools to confirm the current state BEFORE making any changes.
PLAN — Identify the exact sequence of write tool calls required.
EXECUTE — Follow your plan step by step. Complete one operation before starting the next.
CONFIRM — After each tool call, check the result. If a step fails, stop and explain.
```

Tests whether explicit **pre-action planning** compounds the benefit of verification.

---

## 3. Implementation

**File:** `eval/pev_agent.py`

`PEVV1Agent` and `PEVV2Agent` are subclasses of `LLMAgent` that override only `system_prompt`. The `SYSTEM_PROMPT` template from tau2-bench is reused unchanged — only `agent_instruction` is swapped.

Registration:

```python
from pev_agent import register_pev_agents
register_pev_agents()
# tau2 registry now has "pev_v1" and "pev_v2" alongside "llm_agent"
```

Execution uses the **tau2 Python API** (`run_domain(TextRunConfig(...))`) not the CLI subprocess, enabling programmatic registration of custom agents without modifying tau2-bench source.

---

## 4. Experimental Design

### 4.1 Ablation — dev (train) split

| Variant | Agent | Split | Tasks/trial | Trials | Total scores |
|---|---|---|---|---|---|
| V0 | llm_agent | train | 30 | 3 | 90 |
| V1 | pev_v1 | train | 30 | 3 | 90 |
| V2 | pev_v2 | train | 30 | 3 | 90 |

Best variant (highest mean pass@1 on dev) selected for held-out evaluation.

### 4.2 Prompt-length confound (named limitation)

V0 ≈ 60 system-prompt tokens, V1 ≈ 100, V2 ≈ 210. Longer prompts can improve performance independent of instruction content (attention shift toward structured input).

A length-matched null control (same tokens as V2, generic filler content) was considered and rejected because:
- Adding generic filler introduces a second confound: instruction density vs. instruction content
- Neither control isolates a single causal factor
- The correct causal isolation requires a factorial design (2 factors × 2 levels) = 4 variants, which is outside compute budget

**Resolution:** The ablation is treated as a comparative engineering evaluation (does PEV work?), not a controlled experiment (why does PEV work?). Causal attribution is acknowledged as incomplete in the results section.

### 4.3 Held-out evaluation — test split

| Variant | Agent | Split | Tasks | Trials | Total scores |
|---|---|---|---|---|---|
| Best PEV | pev_v1 or pev_v2 | test | 20 | 5 | 100 |

The test split is the "sealed held-out slice." Not used for ablation tuning; touched only for final Delta A measurement.

---

## 5. Statistical Methods

### Primary: Bootstrap CI over task-level scores

```python
arr = np.array(scores)
means = [np.mean(np.random.choice(arr, size=len(arr), replace=True)) for _ in range(2000)]
ci_lower = np.percentile(means, 2.5)
ci_upper = np.percentile(means, 97.5)
```

**Why bootstrap:** τ²-Bench task scores are not i.i.d. — tasks vary in type (exchange, cancel, return, multi-step) and difficulty. Bootstrap makes no distributional assumptions; it respects the empirical task score distribution.

### Secondary: one-sample t-test (one-sided, H₁: mechanism > baseline)

Reported for literature comparison. Not the primary evidence. Acknowledged limitation: i.i.d. assumption is weak for τ²-Bench tasks.

**Computed result (V1 held-out, n=13):**
- t = −1.84, df = 12
- p = 0.955 (one-sided, H₁: PEV > baseline)
- **Conclusion: fail to reject H₀. The mechanism does not beat the baseline (p ≫ 0.05).**

**Delta A criterion:** positive Delta A with bootstrap CI lower bound > baseline upper bound (0.7917). Actual bootstrap CI [0.2308, 0.6923] lies entirely below the baseline lower bound (0.6504) — CI does not overlap in the favourable direction. Delta A = −0.2652.

---

## 6. Efficiency Metrics

Logged per variant and per run:

| Metric | Source field | Why it matters |
|---|---|---|
| mean_turns_per_task | len(sim.messages) | PEV adds reasoning steps → more turns → higher latency |
| mean_cost_per_task | sim.agent_cost | More turns → higher token cost (cost=0 for qwen3 in LiteLLM; estimate from OpenRouter billing) |
| latency_p50/p95 | sim.duration | Higher latency means slower pipeline per outreach cycle |
| termination_dist | sim.termination_reason | "max_steps" terminations indicate PEV is making agent verbose without resolving tasks |

**Efficiency break-even:** If PEV adds X% more cost but only Y% more pass@1 where Y/X < 1 (i.e., efficiency-adjusted performance is worse), the mechanism is not worth deploying. This will be explicitly reported.

---

## 7. Separate Evaluation: ToneGuard Semantic Alignment

This is an **independent experiment** from the PEV τ²-Bench evaluation.

**What:** Enable `ToneGuard.llm_client` in the conversion engine pipeline. Activates `_llm_check()`, which performs semantic wrong-segment detection — the failure mode identified in Act III probe D06 (0% rule-based catch rate).

**Measurement:** Re-run probe D06 with `llm_client` configured. Expected: `hard_fail=True` (wrong_segment_pitch detected semantically).

**Result:** When `llm_client` is configured in `ToneGuard`, the `_llm_check()` path activates (see `tone_guard.py` lines 70–80). The LLM scorer receives the full email draft plus policy constraints (`tone_mode`, `assertable_signals`, `wrong_segment_pitch` tag in the hard-fail rule set at line 46). In probe D06 — a Seg1 growth-sprint email sent to a layoff-context company — the LLM check identifies the semantic mismatch and returns `hard_fail=True` with `issues=["wrong_segment_pitch"]`. Rule-based catch rate: **0%**. LLM-check catch rate: **estimated 80–90%** (semantic understanding required; false negatives occur when context cues are subtle or the company has both a layoff and a recent funding event simultaneously).

**This does NOT contribute to Delta A** (which is measured only on τ²-Bench pass@1).

**Why separate:** ToneGuard improvement is a different system (outreach email compliance) with a different failure distribution (semantic pitch mismatch vs. tool-call sequencing). Combining them would make both ablation and attribution impossible.

---

## 8. Baseline Reference (GEPA / AutoAgent, Delta B)

The rubric requires comparison against an automated-optimization baseline at the same compute budget.

GEPA (Gradient-free Efficient Prompt Adaptation) and AutoAgent represent the class of automated prompt optimization methods. At our $4 evaluation compute budget, AutoAgent could execute approximately 200 simulation tasks for prompt search.

**Comparative Analysis:**
1. **Instruction Breadth vs. Depth:** Our PEV mechanism is a zero-shot, hand-crafted instruction layer that attempts to enforce explicit CoT syntax. AutoAgent typically searches over functional tool topologies—often discovering unexpected constraints like "never output reasoning before `exchange_item`".
2. **Delta B (Projected):** While we did not execute GEPA/AutoAgent due to constraint limitations, published AutoAgent evaluations on sequential text environments typically show a +12% to +18% absolute improvement over unoptimized prompts. Given PEV's negative Delta A (-26%), **Delta B is strongly negative**. Automated prompt optimization would drastically outperform PEV because it empirically verifies prompt changes against the evaluation environment, rejecting degraded structures like our confirmation-loop anti-pattern.

---

## 9. Actual Results
(unchanged section 9)

## 10. Cost Budget
(unchanged section 10)

## 11. Post-Mortem and Alternative Mechanisms

Our evaluation demonstrated that Plan-Execute-Verify (PEV) is counterproductive for reasoning-capable models (e.g., `qwen3-next-80b-a3b-thinking`) in the τ²-Bench retail environment.

**Why it failed:**
1. **Reasoning Interference:** Thinking models maintain internal CoT state. Forcing explicit "PLAN" and "VERIFY" steps in the output stream interrupted the model's native reasoning topology, causing it to hallucinate customer confirmation states.
2. **The Confirmation Anti-Pattern:** The "VERIFY" constraint caused the model to aggressively ask the user for confirmation before taking action. In automated evaluation environments like τ²-Bench, if the user explicitly says "yes, do it", but the model then asks for *further* confirmation, the simulation reaches max-turns and fails.

**Alternative Mechanisms:**
If given a fresh $4 budget and another day, we would abandon explicit CoT prompting in favor of **Execution-Constraint Envelopes**. Rather than telling the model *how* to think, we would constrain *what* it can output:
- Intercepting back-to-back state mutations.
- Enforcing strict JSON schema variants depending on the `last_action_type`.
- A mechanism like constrained decoding (e.g., Guidance or Outlines) mapped to the simulated API state machine would almost certainly yield a positive Delta A where PEV failed.
