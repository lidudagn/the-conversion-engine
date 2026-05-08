# Grounding Commit — Day 4

**Topic:** Evaluation and Statistics (Bootstrap P-Value Mechanics)

## What Was Edited
1. `memo_week11.md:25-26` — Added a statistical caveat after the Delta A p-value claim.

## Why It Grew the Portfolio

My Week 11 CFO memo reported "p=0.0127, paired bootstrap n=10,000" as the closing argument for deploying the trained judge. After pairing with Melaku and researching what bootstrap p-values actually establish, I now understand that this p-value guarantees **internal validity** (the lift is not sampling noise) but not **external validity** (the lift holds on the deployment distribution).

The specific risk: my held-out set contains <10% confidence-boundary cases, but production traffic may contain 25%+ of these hard cases. An aggregate p-value masks per-subgroup performance via Simpson's Paradox. The grounding edit adds a technical caveat citing the ASA Statement on p-Values (Wasserstein & Lazar, 2016), transforming a "we're significant, ship it" claim into a properly qualified deployment recommendation.

This is not a cosmetic edit — it changes the **decision logic** of the memo. Before: "p<0.05 → deploy." After: "p<0.05 validates the lift is real; stratified evaluation validates the lift is reliable."
