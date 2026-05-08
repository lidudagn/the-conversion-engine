# Sources: Evaluation and Statistics

## Canonical Papers

1. **Efron & Tibshirani, 1993**: *An Introduction to the Bootstrap*
   - URL: https://doi.org/10.1007/978-1-4899-4541-9
   - **Why cited:** The foundational reference for bootstrap confidence intervals and p-value computation via resampling. Establishes the theoretical basis for the `paired_bootstrap_p` function in `run_real_ablation.py`.

2. **Wasserstein & Lazar, 2016**: "The ASA Statement on p-Values: Context, Process, and Purpose"
   - URL: https://doi.org/10.1080/00031305.2016.1154108
   - **Why cited:** The American Statistical Association's official guidance on what p-values do and do not establish — directly relevant to why p=0.018 does not guarantee deployment reliability.

3. **Oakden-Rayner et al., 2020**: "Hidden Stratification Causes Clinically Meaningful Failures in Machine Learning for Medical Imaging"
   - URL: https://arxiv.org/abs/1909.12475
   - **Why cited:** Demonstrates how aggregate metrics mask subgroup failures in deployed ML systems — the exact mechanism behind Melaku's "confidence-boundary" failure pattern.

## Documentation & Blogs

- **Anthropic Evals Documentation**: "Statistical Significance in LLM Evaluation"
  - **Why cited:** Industry guidance on when bootstrap CIs are and are not sufficient for deployment decisions.

- **Simpson's Paradox** (Wikipedia / Stanford Encyclopedia of Philosophy)
  - URL: https://plato.stanford.edu/entries/paradox-simpson/
  - **Why cited:** The formal name for the phenomenon where aggregate improvements conceal subgroup regressions.
