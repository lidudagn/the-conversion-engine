# Grounding Commit — Day 3

**Topic:** Training Mechanics (DPO Beta Parameter)

## What Was Edited
1. `scripts/train_judge_lora.py:186-193`

## Why It Grew the Portfolio

When I set up the judge model training, I used the default `beta=0.1` without understanding that it acts as the **mathematical anchor** (Lagrange multiplier) for the KL-divergence constraint. 

After pairing with Martha and analyzing the gradient behavior $\beta \cdot \sigma(-\beta h)$, I now understand that Beta is my **"Trust Budget."** It controls how aggressively the model deviates from the base Qwen policy to satisfy my "segment alignment" preferences. 

This grounding edit adds technical documentation to my training script, proving that my hyperparameter choice is a deliberate stability measure for a small model (0.5B) where "policy collapse" is a major risk at lower Beta settings. I am no longer just running default scripts; I am engineering the optimization tradeoff.
