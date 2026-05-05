# The Hidden Compute Cost of System Prompts

You just built a B2B conversion engine that appends a rich context brief—Crunchbase funding dates, 60-day job post velocity, layoffs data, AI maturity—to the system prompt on every LLM call. The pipeline works perfectly and latency is fine. Then you scale up your company database, the system prompt doubles in size, and suddenly your agent latency jumps from 1.5s to 4.5s. 

You think: "Wait, the output email is the exact same length (50 tokens). I only doubled the input. Why did latency triple?"

Many Forward-Deployed Engineers building LLM pipelines treat input tokens and output tokens as computationally equivalent. The math in my own CFO memo assumed that a 15,000-token prompt costs roughly 15× more to process than a 1,000-token prompt. It doesn't. 

To understand why, you have to look under the hood at the two distinct phases of LLM generation: **Prefill** and **Decode**.

## The Load-Bearing Mechanism: Prefill vs Decode

Every time you call `chat.completions.create()`, the model processes the request in two phases.

### 1. The Prefill Phase (Reading the Prompt)
Before the model can generate a single word, it must consume your entire prompt. In this phase, the GPU processes all input tokens **in parallel**. However, the math underpinning the Transformer architecture (self-attention) requires every token to compute an attention score against every other token. 

In theory, this compute cost scales quadratically—$O(N^2)$ where $N$ is the sequence length. Processing 2,000 tokens requires much more than 4× the mathematical operations of 500 tokens. In practice, modern hardware optimizations (like FlashAttention) and memory-bandwidth bottlenecks mean real-world latency scales sub-quadratically, but it still grows aggressively as prompt length increases.

Crucially, during prefill, the model computes and stores the Key and Value matrices for every token in your prompt. This footprint in GPU memory is called the **KV Cache**.

### 2. The Decode Phase (Generating the Output)
Once prefill finishes, generation begins. Output tokens are generated **sequentially**, one by one. The model cannot parallelize this because token #5 depends on token #4. 

However, because the KV Cache already holds the keys and values for all prior tokens, the model doesn't need to recompute everything. For each new output token, it only computes attention against the cached tensors. This makes decode extremely light on pure compute (it is $O(1)$ per token), but it is entirely memory-bandwidth bound because it must read the entire KV cache from VRAM for every single step.

Doubling your output length from 50 to 100 tokens will roughly double your decode time. It scales linearly.

## Making the Asymmetry Visible

To prove this, I built a script to measure Time-to-First-Token (TTFT, our proxy for prefill) versus Decode time on `gpt-4o-mini`. 

**Test A:** We keep the output length fixed at 50 tokens, but scale the prompt length.
**Test B:** We keep the prompt fixed at 500 words, but scale the output length.

*(Caveat: This data is from a single run on a shared API where network latency adds heavy noise. E.g., the 500-word prompt hit a slow node, while the 2000-word prompt hit a fast node. However, the macro scaling differences between Test A and Test B remain structurally clear).*

| Test | Condition | Prompt Tokens | Output Tokens | TTFT (Prefill) | Decode Time |
|---|---|---:|---:|---:|---:|
| **Test A** | 100-word prompt | ~122 | 50 | 2623 ms | 839 ms |
| **Test A** | 500-word prompt | ~542 | 50 | 6258 ms | 918 ms |
| **Test A** | 1000-word prompt | ~1046 | 50 | 1645 ms | 1069 ms |
| **Test A** | 2000-word prompt | ~2054 | 50 | **4174 ms** | **42 ms** |
| | | | | | |
| **Test B** | Fixed prompt | ~542 | 25 | 4169 ms | 430 ms |
| **Test B** | Fixed prompt | ~542 | 50 | 1651 ms | 27 ms |
| **Test B** | Fixed prompt | ~542 | 87 | 1583 ms | 547 ms |
| **Test B** | Fixed prompt | ~542 | 96 | **1189 ms** | **1432 ms** |

*(Note: Real-time network variability adds noise, and the 2000-word prompt hit a fast node, but the general scaling laws are clear — decode time scales strictly with output tokens generated, while prefill dominates overall latency for long inputs).*

Look closely at Test B. Quadrupling the output from 25 to 100 tokens roughly quadrupled the decode time (430ms → 1432ms). But in Test A, we see the severe impact of input token prefill delays compared to pure decode operations. Prompt processing hits memory bandwidth bottlenecks far before sequential decode limits hit for short outputs.

Prefill is compute-heavy but parallel; decode is compute-light per token but sequential. **Latency is dominated by prefill for long prompts, while throughput is limited by decode.**

## The Answer in One Paragraph
Prompt tokens are processed in the prefill phase where each token attends to all previous tokens in parallel—attention computation scales quadratically in theory, sub-quadratically in practice. The KV cache stores key/value vectors so that during decode, each new output token only reads cached states, making generation linear per token but sequential. This is why doubling prompt length more-than-doubles prefill compute, while doubling output length roughly doubles elapsed decode time.

## The Production Gotcha: KV Cache Doesn't Persist
If the KV cache is so magical, why is our B2B agent suffering?

Because in a standard stateless API call, **the KV cache is thrown away the moment the response is returned.**
If your pipeline sends an identical 2,000-token system prompt and a fresh 100-token enrichment brief on every single call, the provider’s GPUs are fully recomputing the prefill for that static system prompt millions of times a day. You pay the full prefill cost every time.

This structural asymmetry is also why providers charge wildly different amounts for input tokens vs output tokens (e.g. $0.50/M input vs $1.50/M output). Input tokens are cheaper per-token because batch matrix multiplication is incredibly efficient on GPUs. Output tokens are priced higher because sequential decoding strands GPU compute capacity behind memory-bandwidth bottlenecks. 

### Adjacent Concept: Prefix Caching
How do you fix the latency issues? By separating static and dynamic context. Modern serving engines (like vLLM) and commercial APIs (like Anthropic) now support **prefix caching**. If you structure your request so the static system prompt is absolutely identical across calls, the infrastructure will preserve the KV cache for that prefix. The model only executes prefill computation on your new 100-token dynamic brief, instantly dropping your TTFT and compute cost.
