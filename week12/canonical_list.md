# Canonical Reading List — Week 12

**Author:** Lidya Dagnew  
**Cohort Contribution:** Forward-Deployed Engineer, 2026  

---

## Papers

### Inference & Architecture
1. **Pope et al. (2022).** *Efficiently Scaling Transformer Inference.* Google Research.
   - **Why it matters:** Establishes the prefill/decode asymmetry that determines LLM inference cost. Essential for any FDE doing cost modeling.
   
2. **Willard & Louf (2023).** *Efficient Guided Generation for Large Language Models.* (Outlines)
   - **Why it matters:** The foundational paper on grammar-constrained decoding. Explains how to guarantee structured output without sacrificing model quality.

### Training & Post-Training
3. **Rafailov et al. (2023).** *Direct Preference Optimization: Your Language Model is Secretly a Reward Model.* NeurIPS 2023.
   - **Why it matters:** The DPO loss derivation and beta's role as a KL constraint. Required reading for anyone fine-tuning with preference data.

4. **Aghajanyan et al. (2020).** *Intrinsic Dimensionality Explains the Effectiveness of Language Model Fine-Tuning.* ACL 2021.
   - **Why it matters:** Proves that fine-tuning happens in a tiny subspace, which is why LoRA works at all. Connects task complexity to required rank.

5. **Hu et al. (2021).** *LoRA: Low-Rank Adaptation of Large Language Models.* ICLR 2022.
   - **Why it matters:** The LoRA paper itself. Every FDE using adapters should understand why BA decomposition preserves the base model's knowledge.

### Evaluation & Statistics
6. **Efron & Tibshirani (1993).** *An Introduction to the Bootstrap.* Chapman & Hall.
   - **Why it matters:** The canonical reference for bootstrap CIs and p-values. Essential for understanding what your ablation statistics actually measure.

7. **Wasserstein & Lazar (2016).** "The ASA Statement on p-Values." *The American Statistician.*
   - **Why it matters:** The official guidance on what p-values do and do not establish. Should be cited every time you report significance.

8. **Oakden-Rayner et al. (2020).** "Hidden Stratification Causes Clinically Meaningful Failures in Machine Learning." *CHIL 2020.*
   - **Why it matters:** Demonstrates Simpson's Paradox in deployed ML — aggregate metrics masking subgroup failures. Directly applicable to LLM benchmark evaluation.

9. **Dror et al. (2018).** "The Hitchhiker's Guide to Testing Statistical Significance in NLP."
   - **Why it matters:** Practical guidance on when paired bootstrap matters vs. parametric tests for NLP model comparison.

### Agent & Tool-Use
10. **Schick et al. (2023).** *Toolformer: Language Models Can Teach Themselves to Use Tools.*
    - **Why it matters:** Establishes how tool-use is learned as a token-generation pattern, not a separate capability.

---

## Tools & Patterns

1. **Unsloth** — Efficient LoRA fine-tuning with 2x speedup and 60% memory reduction. Used for training the Tenacious-Bench judge.

2. **TRL (Transformer Reinforcement Learning)** — Hugging Face library for DPO/ORPO/SimPO training. The `DPOTrainer` and `DPOConfig` are the entry points for preference tuning.

3. **Outlines / Guidance** — Grammar-constrained decoding libraries. Use when "Return valid JSON" is insufficient for production reliability.

4. **OpenAI Structured Outputs** — `response_format: { type: "json_schema" }`. The production-grade API for schema-constrained decoding without external libraries.

5. **Paired Bootstrap Testing** — Pattern for comparing two models on the same task set. Preserves task-level correlation, isolates model difference. Implementation in `scripts/run_real_ablation.py`.
