1/ Why does appending a 2,000-token context brief to your agent's system prompt tank its latency, but generating 200 words of output instead of 50 feels relatively "normal"? The answer lies under the hood of LLM inference: the Prefill vs Decode asymmetry.

2/ When you make an API call, generation happens in two phases. Phase 1 is **Prefill**. The model must consume your whole prompt. It calculates attention for every token against every other token in parallel. In theory this is O(n²) math; in practice, hardware optimizations make latency sub-quadratic but still superlinear.

3/ During prefill, the model calculates and stores Key/Value matrices for every token in GPU memory. This is the **KV Cache**. Phase 2 is **Decode**. Because the keys/values are cached, generating the next token is O(1) pure compute. Output tokens are generated sequentially, running linearly.

4/ Here's the production gotcha killing your agent: if you use a stateless API, **the KV cache is thrown away after every call.** If you send the same 2,000-token system prompt + a new 50-token brief for 1,000 prospects, you pay the massive prefill compute cost 1,000 separate times.

5/ This is also why input tokens are priced ~3x cheaper than output tokens. Prefill is highly parallelizable (efficient on GPUs). Decode is sequential and memory-bandwidth bound (slow on GPUs). Prefill compute-heavy but parallel; decode is compute-light per token but sequential.

6/ The architectural fix for long prompts? Prefix Caching. By ensuring your static instructions are perfectly identical across calls, modern serving infrastructures will hold the KV cache in VRAM, letting your agent skip the prefill penalty entirely. Full explainer with latency benchmarks: [Link to Blog]
