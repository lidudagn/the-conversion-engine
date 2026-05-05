# Why Output Tokens Cost 3× More Than Input Tokens: Prefill vs Decode Explained

*Week 12 · Day 1 · Written by Efrata Wolde for Lidya Dagnew*

---

## The Assumption Worth Questioning

When you see an API pricing page that charges $X per million input tokens and $3X per million output tokens, the natural assumption is that output tokens are just arbitrarily more expensive — a pricing decision, not a technical one.

But the 3× ratio is not arbitrary. It reflects a real asymmetry in how the GPU does work during inference. Input tokens and output tokens go through fundamentally different computational phases, and once you understand those phases, the pricing makes complete sense.

---

## Phase 1: Prefill — The Parallel Pass

When you send a prompt to an LLM, the first thing the model does is process all of your input tokens at once in a single forward pass. This is called the **prefill phase**.

Here's what happens in that single pass: every input token gets transformed through every layer of the network simultaneously. The GPU processes a matrix that is (number of tokens) × (model dimension) wide, and because modern GPUs are built for exactly this kind of large parallel matrix multiplication, they are extremely efficient at it. Throwing 500 tokens at the prefill phase costs only slightly more GPU time than throwing 50 tokens — the work scales, but the GPU stays fully utilised throughout.

During this pass, the model computes and stores something called the **KV cache** — a set of key and value matrices for every layer, for every input token. Think of it as the model's "memory" of your prompt. It is saved in GPU memory so it never has to be recomputed.

The prefill phase is **compute-bound**: the bottleneck is arithmetic throughput, which is what GPUs are good at.

---

## Phase 2: Decode — The Sequential Loop

Once prefill is done, the model starts generating your output. This is the **decode phase**, and it works completely differently.

The model generates **one token at a time**. To produce the first output token, it runs a forward pass. To produce the second output token, it runs another forward pass — this time reading the full KV cache from memory plus the new token it just generated. To produce the third token: another pass, reading a slightly larger KV cache. And so on, for every single token in your output.

Each output token is its own sequential forward pass. They cannot be parallelised — each token depends on the one before it.

This is the key difference. The decode phase is **memory-bandwidth-bound**: the bottleneck is not arithmetic but how fast the GPU can *read* the KV cache from memory on each pass. The GPU arithmetic units end up mostly idle, waiting for data to arrive from memory. It is a much less efficient use of the hardware.

---

## Why This Makes Output Tokens More Expensive

Put the two phases side by side:

| | Prefill | Decode |
|---|---|---|
| How tokens are processed | All at once, in parallel | One at a time, sequentially |
| Number of forward passes | 1 | 1 per output token |
| Bottleneck | Arithmetic (GPU loves this) | Memory bandwidth (GPU mostly waits) |
| GPU utilisation | High | Low |

If you generate 1,000 output tokens, you run approximately 1,000 forward passes, each one reading the growing KV cache from memory. If your prompt had 1,000 input tokens, you ran 1 forward pass.

API providers are selling you GPU time. The same 1,000 tokens consume dramatically different amounts of GPU time depending on whether they are in your input or your output. The 3× pricing is the provider passing that real cost difference on to you honestly.

---

## What This Means for Your Cost Assumption

Your original assumption — that longer prompts scale linearly in cost — was partially right but missed something important.

Prefill cost *does* scale with input length, but sub-linearly because of parallelism. The GPU handles a 2,000-token prompt in not much more time than a 1,000-token prompt.

But output length scales *linearly and more expensively*, because each additional output token is a full sequential pass at low GPU utilisation.

The practical implication: if you want to reduce your API costs, **cutting output length has higher ROI than cutting input length**. A shorter system prompt saves some prefill cost, but a shorter generation target (via concise prompting or max_tokens limits) saves more per token removed.

---

## A Concrete Analogy

Think of prefill like a photocopier running 100 pages — it processes everything in one uninterrupted run. Fast, efficient, parallel.

Decode is like a person writing out those 100 pages by hand, one at a time, re-reading everything written so far before writing the next line. Each page takes the same effort as the last, and none of them can be written until the previous one is done.

Same volume of text. Completely different cost structure.

---

## Grounding in Your Work

This mechanism is directly relevant to any LLM pipeline where you are calling the API repeatedly. Each call has a prefill phase (your system prompt + context) and a decode phase (the model's response). If your system prompts are growing longer over time — to add more instructions, more examples, more context — you are adding prefill cost, which is cheap. But if your model responses are also getting longer, you are adding decode cost at a higher rate.

Understanding this split is the first step toward knowing where to look when your costs start climbing.

---

*Sources: Attention Is All You Need (Vaswani et al., 2017) · Efficient Memory Management for Large Language Model Serving with PagedAttention (Kwon et al., 2023)*
