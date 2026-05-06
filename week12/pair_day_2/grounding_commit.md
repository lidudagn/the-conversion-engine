# Grounding Commit — Day 2

**Topic:** Agent and Tool-Use Internals (Token Mechanics)

## What Was Edited
1. `agent/composer.py:247-254`

## Why It Grew the Portfolio

When I built the pipeline, I chose to use raw prompt-stuffing across the entire system. I had my `EmailComposer` generate drafts and decisions based entirely on system prompt rules. I did this because it "worked," not because I understood the engineering trade-off. 

After pairing with Rahel, I learned the mechanical difference: proper function-calling enforces **grammar-based decoding** (logit masking), which zeroes out the probability of any token that violates the tool's schema. I was sacrificing hardware-level reliability checks. 

However, since `EmailComposer` only needs to run a single generation turn and already has a robust fallback to `_template_compose` if the generation fails, I realized my original architecture was actually the correct choice for this specific bottleneck—just for reasons I couldn't previously articulate. 

I updated `composer.py` with an architectural comment defending the decision to forego logit-masking in favor of single-turn latency. I now own this architectural design instead of just defending it as "the way I initially wrote it."
