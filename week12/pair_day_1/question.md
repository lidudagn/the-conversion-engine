# Day 1 Question — Inference-Time Mechanics

## Question

In my Conversion Engine's `llm_client.py` (line 66), I charge prompt tokens at $0.50/M and completion tokens at $1.50/M without understanding the underlying cost difference. **What is the actual computational difference between prefill and decode in a single LLM inference call, and how does this asymmetry lead to different pricing for input vs output tokens?**

This would let me correct my linear cost assumptions in `failure_taxonomy.md` and defend cost-per-lead in my CFO memo.

## Artifact Connections

- [`llm_client.py:66`](../agent/llm_client.py) — Cost formula with unexplained 3× pricing difference
- [`failure_taxonomy.md:146`](../probes/failure_taxonomy.md) — Incorrect claim that 15K-token prompt "inflates cost 15×" (assumes linear scaling)
- [`memo.md`](../memo.md) — CFO cost table with per-component cost breakdown I cannot mechanically defend

## Why This Matters

Every outreach call in my pipeline invokes `chat_completion()` which bills at these rates. I copied the pricing from OpenRouter without understanding the computational reason behind the asymmetry. My failure taxonomy assumes prompt cost scales linearly — if it scales superlinearly, my cost pathology risk assessment is wrong. Closing this gap lets me defend the $0.013/qualified-lead claim in my CFO memo with mechanical understanding, not copied numbers.
