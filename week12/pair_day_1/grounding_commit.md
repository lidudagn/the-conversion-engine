# Grounding Commit — Day 1

**Topic:** Inference-Time Mechanics (Prefill vs Decode & KV Cache)

## What Was Edited
1. `agent/llm_client.py:65-66`
2. `probes/failure_taxonomy.md:145-147`

## Why It Grew the Portfolio

I started the day by copying the $0.50/M input vs $1.50/M output token pricing from OpenRouter into my code, without understanding why generating output is fundamentally more expensive than ingesting input. My failure taxonomy incorrectly treated token processing as a linear cost.

After researching the prefill/decode mechanism and getting Efrata's explainer, I updated the code and documentation to reflect mechanical reality:

1. **In `failure_taxonomy.md`:** Removed the flawed `15K tokens = 15x cost` assumption. Replaced it with an engineering explanation of why prefill scales quadratically in theory (but sub-quadratically in practice due to hardware), while output scales sequentially.
2. **In `llm_client.py`:** Added comments tracking the 3x pricing difference to its architectural root cause — prefill is parallelizable matrix multiplication (cheap), while decode forces sequential generation bound by KV cache reads (expensive).

I can now defend the efficiency numbers in my Act I CFO memo using hardware mechanics, not just API pricing pages.
