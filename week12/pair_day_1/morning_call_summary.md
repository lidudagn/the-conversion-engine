# Morning Call Summary — Day 1

**Participants:** Efrata Wolde · Lidya Dagnew  
**Duration:** ~20 minutes  
**Topic:** Inference-time mechanics

---

## What We Each Brought In

**Efrata's draft question** was initially framed around why longer prompts cause latency to increase. The gap was real but the question was too broad — it could have been answered by saying "longer prompts take longer to process" without actually explaining the mechanism.

**Lidya Dagnew's draft question** was about why output tokens are priced 3× higher than input tokens despite the assumption that cost scales linearly with token count.

---

## How We Sharpened Each Other

On Efrata's question: Lidya Dagnew pushed back on "why does prompt length affect latency" as too vague. She asked: "What do you mean by latency — time to first token, or total response time?" That forced Efrata to be specific — the real gap was in not understanding what happens computationally during the input processing phase, and why that phase behaves differently from output generation. The question was reframed around the KV cache and prefill mechanics specifically.

On Lidya Dagnew's question: Efrata noted that the question was strong but could be made more grounded by tying it to a specific thing she had actually built — her CFO memo assumed linear cost scaling, so that became the anchor. Adding "and why does that mechanism make input tokens cheaper to process than output tokens?" sharpened the second half.

---

## Final Agreed Questions

**Efrata:** "My conversion-engine blog says the system prompt approach works 'until the prompt grows so long that latency suffers.' My pipeline currently sends a system prompt + a full enrichment brief on every LLM call. What is the KV cache, what actually happens computationally when the model processes a long input prompt, and why does prompt length affect latency in a way that output length does not affect it the same way?"

**Lidya Dagnew:** "My API charges 3× more for output tokens than for input tokens, and I assumed in my logs that longer prompts scale linearly in cost. What is the actual computational difference between prefill and decode in an LLM, and why does that mechanism make input tokens cheaper to process than output tokens?"
