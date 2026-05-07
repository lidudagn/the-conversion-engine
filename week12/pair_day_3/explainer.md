# Why Rank-16 is Enough: Intrinsic Dimensionality and LoRA Rank

*Written by Lidya Dagnaw for Martha Ketsela, whose fine-tune uses r=16 for a 200-pair binary judge task.*

When you set `r=16` in Unsloth, you are making a bet about the **intrinsic dimensionality** of your task. Martha's question is: *Why does a 1024x16 matrix (1.75% of parameters) work for a complex judging task?*

The answer lies in the difference between the model's **nominal dimensionality** (total parameters) and its **intrinsic dimensionality** (the actual degrees of freedom needed to solve a specific task).

## The Theory: Pre-training as Compression

As established by **Aghajanyan et al. (2020)**, pre-trained models already contain the "concepts" needed for most tasks. Fine-tuning isn't teaching the model new knowledge; it's learning how to **recombine** existing knowledge to fit a specific format or constraint.

For a binary pass/fail judge:
1. The model already knows what "professional" or "polite" looks like.
2. It already understands "sales outreach."
3. Your 200 preference pairs are simply teaching it the specific **decision boundary** between Seg1 and Seg2.

Because the model already has the high-level features, the "direction" it needs to move in parameter space is very small. Aghajanyan found that for many NLP tasks, the intrinsic dimension is often just a few hundred parameters. At `r=16`, your LoRA adapter for a 0.5B model has millions of parameters—physically, it is actually **over-provisioned** for 200 pairs.

## Ablation Dynamics: r=8 vs. r=16 vs. r=64

If Martha ran ablations on her 200-pair dataset, here is what the mechanics would look like:

### 1. The Rank-8 Ablation (Underfitting / Bottleneck)
- **Dynamics:** The training loss would likely plateau at a higher level. 
- **Why:** The subspace is so small (a very narrow "pipe") that the model cannot capture the nuances of your segment definitions. It might learn "politeness" but fail to distinguish the subtle "growth" vs. "efficiency" framing because it lacks the mathematical degrees of freedom to represent both simultaneously.
- **Signs:** High training loss, high validation loss, and poor score on hard-negative pairs.

### 2. The Rank-64 Ablation (Overfitting / Memorization)
- **Dynamics:** The training loss will plummet to near-zero very quickly, but validation loss will "shark-fin" (spike upward).
- **Why:** With `r=64`, you are giving a 0.5B model enough "memory" to literally memorize the 200 specific email examples in your training set rather than learning the general rule. The rank is no longer an information bottleneck; it's a wide-open storage bank.
- **Signs:** Perfectly low training loss, but catastrophic performance on your held-out evaluation set.

## Ranking the Trade-offs

| Rank ($r$) | Parameters | Risk | Best For |
|---|---|---|---|
| **r=4/8** | 0.4% | Underfitting | Stylistic tweaks, basic tone shifts |
| **r=16/32** | 1.5-3% | Balanced | **The "Sweet Spot"** for instruction following/judging |
| **r=64+** | 6%+ | Overfitting | Extensive new domain knowledge / Long-context tasks |

## The DPO Beta Connection (Lidya's Gap)

In `train_judge_lora.py`, the `beta=0.1` acts as a second guardrail. While `rank` limits **how many** parameters can change, `beta` limits **how much** the values of those parameters can move away from the base model. 

High rank + low beta = The model changes many weights, but only very slightly.
Low rank + high beta = The model changes very few weights, but moves them aggressively.

## Conclusion for the Portfolio

For a 200-pair binary judging task, **Rank-16 is a conservative, safe choice.** It provides enough capacity to learn the segment boundaries without being so large that the model simply memorizes your synthetic pairs. If Martha sees her model "forgetting" how to speak English or becoming overly biased, the solution is usually to lower the rank or increase the Beta penalty, forcing the model to rely more on its pre-trained "common sense."
