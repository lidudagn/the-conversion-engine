# τ²-Bench Baseline Report

## Reproduction

**Domain:** retail
**Model:** qwen/qwen3-235b-a22b (via OpenRouter)
**Tasks Evaluated:** 61
**Date:** 2026-04-22

## Results

| Metric | Value |
|---|---|
| Mean pass@1 | 0.2787 |
| Tasks passed | 17 / 61 |
| Published leaderboard reference | ~42% |

**Reward distribution:** 17 tasks scored 1.0, 44 tasks scored 0.0

## Methodology

We reproduced the τ²-Bench retail domain baseline using the dev-tier model (qwen/qwen3-235b-a22b) via OpenRouter. Evaluation ran through the standard τ²-Bench CLI (`tau2 run`) with max concurrency 10. The user simulator used both `gpt-4.1-2025-04-14` (11 runs) and `qwen/qwen3-235b-a22b` (9 runs with reward data).

Rewards were extracted from the τ²-Bench simulation result JSONs stored in `eval/tau2-bench/data/simulations/`. Each simulation records per-task `reward_info.reward` as either 0.0 or 1.0.

## Observations

Our baseline of 27.87% pass@1 is below the published τ²-Bench retail leaderboard reference of ~42%. This gap establishes the improvement target for mechanism design in Act IV. Tasks where the agent failed typically involved multi-step write operations (exchanges, cancellations) requiring correct sequencing of tool calls.

## Cost

Total evaluation cost estimated at < $2.00 across 20 simulation runs. Within the $4 budget target for Days 1–4.
