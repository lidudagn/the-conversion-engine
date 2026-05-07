# Day 3 Question — Training and Post-Training Mechanics

## Question

In my `train_judge_lora.py` (line 187), I set `beta=0.1` in the DPO (Direct Preference Optimization) trainer, but I cannot explain what this hyperparameter is mechanically doing during optimization. **In the DPO loss function, how does beta mathematically control the tradeoff between increasing preference likelihood and staying close to the base model’s original policy, and what changes in gradient behavior would I expect if beta were much larger or much smaller?**

## Artifact Connections

- [`scripts/train_judge_lora.py:165-188`](../scripts/train_judge_lora.py) — DPO trainer configuration with `beta=0.1`.
- [`memos/llm_judge_survey.md`](../memos/llm_judge_survey.md) — Previous survey on LLM evaluation bias that led to the need for a preference-tuned judge.

## Why It Matters

My current preference-tuning process is a "black box" where I am trusting the default `beta=0.1` without understanding the underlying KL-divergence constraint. If my judge model starts "collapsing" or ignoring the instructions it learned during SFT (supervised fine-tuning), I wouldn't know if the beta is too low (allowing too much deviation) or too high (preventing the model from learning the new preferences). Knowing this mechanical role will allow me to properly "tune the tuner" rather than just running scripts.
