# The Conversion Engine — Interim Report
## Tenacious Consulting and Outsourcing | April 23, 2026

---

## 1. Architecture Overview

The Conversion Engine is a signal-grounded, decision-intelligence-driven lead generation system built for Tenacious Consulting and Outsourcing. The architecture decouples research from outreach through three layers:

**Layer 1 — Deterministic Research (Enrichment Pipeline)**
Six signal modules extract facts from public data: Crunchbase ODM (1,000 companies), layoffs.fyi (20 events), job-post velocity (181 frozen posts, 28 companies), leadership changes, AI maturity scoring (0–3 with per-signal justification), and competitor gap analysis. No LLM is used for data extraction — all enrichment is deterministic.

**Layer 2 — Policy Engine (Pre-LLM Control)**
A deterministic decision layer computes what the LLM can and cannot say before any text is generated. Rules cover: tone mode (assertive/suggestive/exploratory), competitor-gap gating by confidence, signal classification (assertable/question/omit), bench-capacity hard constraints, and abstention for low-confidence prospects. Every decision is logged to `outputs/policy_trace.jsonl`.

**Layer 3 — Outreach + Compliance**
The LLM Composer drafts emails constrained by a Signal Usage Contract. A post-LLM Tone Guard scores drafts against the Tenacious style guide and hard-fails on overclaiming, bench overcommitment, unauthorized pricing, competitor attacks, and fabricated superlatives. A Contradiction Detector identifies cross-signal tensions and frames them as research findings.

**Kill-switch:** ON by default. All outbound routes to staff sink (`SINK_EMAIL=lidyadagnew7@gmail.com`, `SINK_SMS=+251923561220`).

---

## 2. Key Design Decisions

| Decision | Rationale |
|---|---|
| Pre-LLM policy engine | Prevents hallucination by constraining the LLM before it generates |
| Signal usage contract | Composer references only signals the policy engine classifies as assertable or question |
| Tone guard with 5 hard-fail categories | Overclaiming, bench overcommitment, pricing, superlatives, competitor attacks — all block send |
| Contradiction framing | Cross-signal tensions become research findings, not pitches |
| Bench gate enforcement | Agent never commits capacity the bench summary does not show |
| Strong abstention | Low-confidence prospects get hedged, signal-grounded exploratory emails |

---

## 3. Production Stack — All Integrations Verified

| Integration | Status | Verified Evidence |
|---|---|---|
| Email — Resend (primary) | ✅ SENT | Resend ID `7c7f3a47-7a5c-47ab-98df-e9e620ebecf4`; kill-switch → lidyadagnew7@gmail.com |
| SMS — Africa's Talking (secondary) | ✅ SENT | Kill-switch → +251923561220 (sandbox); AT API response received |
| HubSpot CRM | ✅ UPDATED | Contact ID `763552830697`; all custom properties synced (icp_segment, ai_maturity_score, enrichment_timestamp) |
| Cal.com Booking | ✅ BOOKED | Booking ID `18707337`; real booking created via Cal.com v2 API |
| Langfuse Observability | ✅ LOGGING | Per-trace cost attribution; Langfuse v4 API (`start_observation`); traces visible in cloud |
| OpenRouter LLM | ✅ LIVE | `qwen/qwen3-235b-a22b`; τ²-Bench baseline and email composition |

---

## 4. Enrichment Pipeline — All Signal Sources Active

| Signal | Source | Status | Sample Output (WISEiTECH) |
|---|---|---|---|
| Firmographics | Crunchbase ODM 1,000-company sample | ✅ 1,000 companies loaded | employees, funding, sector, domain |
| Job velocity | `data/job_posts/frozen_april2026.json` (181 posts, 28 companies) | ✅ Loaded | ai_roles=9, total_roles=18, velocity: rising |
| Layoffs | `data/layoffs/layoffs.csv` (20 events) | ✅ Loaded | No layoff detected for WISEiTECH |
| Leadership | Crunchbase + press signal | ✅ Built | 90-day CTO/VP detection window |
| AI maturity | Multi-signal scorer (0–3) | ✅ Score: 2 | ai_roles_count=9/18; confidence=medium |
| Competitor gap | Top-quartile sector analysis | ✅ Generated | `competitor_gap_brief_wiseitech.json` |
| ICP classification | 4-segment classifier with confidence | ✅ Segment 4 | primary=4 (AI capability gap), confidence=0.5 |

**Briefs generated:** `outputs/hiring_signal_brief_wiseitech.json` + `outputs/competitor_gap_brief_wiseitech.json`  
**Batch output:** 25 prospects; `hiring_signal_brief_*.json` and `competitor_gap_brief_*.json` for all 25

---

## 5. τ²-Bench Baseline

| Metric | Value |
|---|---|
| **Mean pass@1** | **27.87%** (17 / 61 tasks) |
| 95% CI | [0.1629, 0.3945] |
| Published reference | ~42% (τ²-Bench leaderboard, Feb 2026) |
| Model | `qwen/qwen3-235b-a22b` via OpenRouter |
| p50 task latency | 92.45s |
| p95 task latency | 214.46s |
| Estimated cost | ~$0.30 |

Scores extracted from per-task `reward_info.reward` in simulation result JSON files (`eval/tau2-bench/data/simulations/`). Binary rewards (0.0 or 1.0) per task. 95% CI uses t-distribution on n=61 task scores. Full methodology in `eval/baseline.md`.

---

## 6. End-to-End Test — 12-Step Pipeline (WISEiTECH)

Test prospect: **WISEiTECH** (wise.co.kr) — ICP Segment 4, AI maturity=2, confidence=0.5

| Step | Result | Key Output |
|---|---|---|
| Data loading | ✅ 1,201 records | 1,000 CB companies, 20 layoffs, 181 job posts |
| Enrichment pipeline | ✅ Brief generated | ICP=4, AI maturity=2, 119ms |
| Policy engine | ✅ 9 rules triggered | tone_mode=exploratory, abstain=False |
| Email composition | ✅ signal_grounded variant | Subject: "Quick thought on scaling at WISEiTECH" |
| Tone guard | ✅ Score 0.88, passed | hard_fail=False |
| Email send (Resend) | ✅ SENT | Resend ID: 7c7f3a47; kill-switch → lidyadagnew7@gmail.com |
| SMS send (Africa's Talking) | ✅ SENT | kill-switch → +251923561220 |
| HubSpot contact | ✅ UPDATED | Contact ID: 763552830697; all fields populated |
| Cal.com booking | ✅ BOOKED | Booking ID: 18707337 (real API booking) |
| Qualification handler | ✅ Buying signal detected | "Sounds interesting, tell me more about your Python team" |
| Channel orchestrator | ✅ Correct routing | next_action=send_email |
| **All 12 steps** | ✅ **PASSED** | — |

**p50 latency: 60.7ms** | **p95 latency: 1,520ms** (across 5 recorded step timings)

---

## 7. Batch Throughput — 25 Synthetic Prospects

| Metric | Value |
|---|---|
| Prospects processed | 25 / 25 |
| p50 full-pipeline latency | 1,535ms |
| p95 full-pipeline latency | 1,913ms |
| `hiring_signal_brief_*.json` files | 25 |
| `competitor_gap_brief_*.json` files | 25 |

---

## 8. What Is Working

- Full enrichment pipeline producing `hiring_signal_brief.json` and `competitor_gap_brief.json` from real public data
- Policy engine correctly gating Segment 4 pitches by AI maturity, downgrading tone below confidence threshold
- Tone guard enforcing 5 hard-fail categories with rule-based pattern detection (no LLM key required)
- Email sent via Resend with verified delivery (Resend ID confirmed)
- SMS routed via Africa's Talking sandbox to registered sink number (+251923561220)
- HubSpot contact created/updated with enrichment metadata, ICP segment, and AI maturity score
- Cal.com discovery call booked with real API (booking ID confirmed)
- Langfuse traces writing to cloud with per-trace attribution
- Kill-switch ON by default; all outbound routes to staff sink

## 9. Plan for Remaining Days

| Day | Focus |
|---|---|
| Apr 23 (today) | Act III adversarial probes ✅ DONE — 45 probes, 3 bugs fixed |
| Apr 24 | Act IV mechanism design — improve τ²-Bench pass@1 |
| Apr 25 | Act V — 2-page memo + demo video; final submission |
