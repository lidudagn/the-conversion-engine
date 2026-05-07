# Sources: Training and Post-Training Mechanics

## Canonical Papers

1. **Aghajanyan et al., 2020**: "Intrinsic Dimensionality Explains the Effectiveness of Language Model Fine-Tuning"
   - URL: https://arxiv.org/abs/2012.13255
   - **Why cited:** Provides the foundational theoretical proof that LLM fine-tuning occurs in a very low-dimensional subspace, justifying why low-rank methods like LoRA work.

2. **Hu et al., 2021**: "LoRA: Low-Rank Adaptation of Large Language Models"
   - URL: https://arxiv.org/abs/2106.09685
   - **Why cited:** The primary paper establishing the LoRA mechanism ($BA$ decomposition) and the hypothesis of low intrinsic rank for task-specific updates.

3. **Rafailov et al., 2023**: "Direct Preference Optimization: Your Language Model is Secretly a Reward Model"
   - URL: https://arxiv.org/abs/2305.18290
   - **Why cited:** Foundational for the DPO mechanics mentioned in Lidya's question, specifically the role of the KL-divergence constraint (Beta).

## Documentation & Blogs

- **Sebastian Raschka**: "Practical Tips for Fine-tuning LLMs with LoRA"
  - URL: https://sebastianraschka.com/blog/2023/lora-finetuning.html
  - **Why cited:** Provides the engineering rules of thumb (e.g., $\alpha = 2 \times r$, target all linear layers) used in production fine-tuning.
