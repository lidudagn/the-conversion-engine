# Sources: Inference-Time Mechanics

## Canonical Papers

1. **Vaswani et al., 2017**: "Attention Is All You Need"
   - URL: https://arxiv.org/abs/1706.03762
   - **Why cited:** Establishes the core $O(n^2)$ computational complexity of the self-attention mechanism during the prefill phase, explaining why prompt length scaling is mathematically superlinear.

2. **Kwon et al., 2023**: "Efficient Memory Management for Large Language Model Serving with PagedAttention"
   - URL: https://arxiv.org/abs/2309.06180
   - **Why cited:** Introduces PagedAttention and maps out the memory bottleneck caused by the KV cache. Explains how the KV cache grows dynamically, why it causes fragmentation, and introduces the vLLM architecture, which serves as the foundation for prefix caching.

## Tools / Patterns

- **Streaming OpenRouter Benchmark Script** (`demo_latency.py`)
  - A custom Python async script using the OpenAI client SDK to run `stream=True` requests. 
  - Measures Time-To-First-Token (TTFT) to isolate prefill latency from decode token generation speed. 
  - Result log saved in `demo_results.json` showing A/B scaling comparisons.
