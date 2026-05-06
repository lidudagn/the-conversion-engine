# Sources: Agent and Tool-Use Internals

## Canonical Papers

1. **Schick et al., 2023**: "Toolformer: Language Models Can Teach Themselves to Use Tools"
   - URL: https://arxiv.org/abs/2302.04761
   - **Why cited:** Establishes the foundational "API call as a token" concept, where models are trained to emit specific control tokens to trigger external tool execution.

2. **Geng et al., 2023**: "LLM-Grounder: Embedded Visual Grounding in LLMs via Dynamic Tool-Use"
   - URL: https://arxiv.org/abs/2309.06071
   - **Why cited:** Explores the integration of tool-use within the generation loop, specifically how the model maintains state across tool calls.

3. **OpenAI API Documentation**: "Function Calling and Structured Outputs"
   - URL: https://platform.openai.com/docs/guides/function-calling
   - **Why cited:** Provides the production-level technical reference for how grammar-based decoding (logit masking) is applied to ensure schema compliance.

## Tools / Patterns

- **Logit Masking / Grammar-Based Decoding Pattern**
  - The mechanism used by modern inference engines (vLLM, Outlines, Guidance) to force JSON/Schema compliance by masking the output probability distribution at every step of the decode phase.
