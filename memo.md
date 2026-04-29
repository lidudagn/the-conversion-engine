# Decision Memo: The Conversion Engine

**To:** CEO & CFO, Tenacious Consulting and Outsourcing  **From:** Engineering  **Date:** April 25, 2026  
**Subject:** Automated Lead Generation System — Pilot Recommendation

---

## Page 1: The Decision

**Executive Summary**  
We built a signal-grounded outbound system enriching every prospect from Crunchbase firmographics, 60-day job-post velocity, layoffs.fyi, leadership-change detection, and AI maturity scoring — converting cold outreach into a verifiable research finding. Across 108 policy decisions, 52 (48%) qualified at a measured cost of **$0.013/qualified lead** (vs. ~$150–$400 for a manual SDR per qualified lead — a 99.97% cost reduction); the full pipeline ran at **p50: 1.5 s, p95: 1.9 s** with 100% tone-guard compliance in batch test (n=25). We recommend a bounded **30-day Segment 1 pilot: 200 prospects, $200 budget**, to establish live reply-rate data before scaling.

**τ²-Bench Baseline**

| Metric | Baseline (instructor) | PEV V1 (ours) |
|---|---|---|
| pass@1 | **0.7267** | 0.4615 |
| 95% CI | [0.6504, 0.7917] | [0.2308, 0.7692] |
| Delta A | — | **−0.2652** |
| Cost/task | $0.0199 | $0.0199 (est.) |
| p50 / p95 latency | 105.95 s / 551.65 s | 166.13 s / 279.05 s |
| n scored | 150 | 13/20 (7 API errors*) |

*7 errors = OpenRouter timeouts/credit exhaustion; excluded from scoring; no systematic bias (failures spread across random task indices). Model: `qwen/qwen3-next-80b-a3b-thinking`. Baseline: instructor, commit `d11a97072c`.

**Cost per Qualified Lead — Trace-Derived**  
Source: `outputs/policy_trace.jsonl` (108 records), `outputs/invoice_summary.json`.

| Component | Unit cost | Total |
|---|---|---|
| Enrichment (Crunchbase + job posts + layoffs.fyi) | $0.002/prospect | $0.22 (108×) |
| LLM composition | $0.008/email | $0.42 (52×) |
| Tone-guard check | $0.001/email | $0.05 (52×) |
| **Cost per qualified lead** | | **$0.013** |

ICP match: 52/108 = 48% (source: `output.abstain`, `policy_trace.jsonl`). Policy engine abstained on 56 — no email sent. Tenacious target: $5/lead. **Actual: $0.013.** Excludes reply-handling loops; estimated production cost: $0.05–$0.15/qualified lead — still well under target.

**Stalled-Thread Rate Delta**  
*Definition:* stalled-thread rate = fraction of inbound prospect replies that receive no follow-up action within 24 hours. Tenacious manual baseline: **30–40%** stall (executive interview; cause: human response lag of 1–3 days). System post-reply action rate: **100%** — every inbound webhook (`/webhook/email`, `/webhook/sms`) triggers qualifier processing at **p50 1.5 s** with zero dropped replies in batch test (n=25; source: `e2e_batch_results.json`). The eliminated stall component is human response latency (days → seconds). Prospect initial-reply rate and conversation-continuation rate are unmeasurable in synthetic evaluation — no live interactions were simulated; these are the primary pilot success criteria.

**Competitive-Gap Outbound Performance**  
Source: `outputs/policy_trace.jsonl` (52 qualified) + `outputs/reply_simulation_results.json` (LLM judge: `claude-3-5-haiku`, n=52, seed=42, synthetic).

| Variant | n | Tone-guard | Bench viol. | Sim. reply rate | Delta |
|---|---|---|---|---|---|
| Signal-grounded (assertive/suggestive) | 30 (58%) | 100% | 0 | **3.3% (1/30)** | — |
| Exploratory (neutral tone) | 22 (42%) | 100% | 0 | **0.0% (0/22)** | **+3.3 pp** |

Gap brief: 2/52 (4%) — thin sector coverage in test sample; expected 40–60% with full database. Delta direction consistent with industry data (Clay/Smartlead 2026: 7–12% vs. 1–3%). Absolute rates suppressed by cold outsourcing pitch; live pilot establishes calibrated baseline. Primary metric: A/B reply-rate delta tracked by `policy_trace.variant` in HubSpot over 30 days.

**Pilot Scope**  
Segment 1 (Series A/B, $5–30M, ≤ 6 months ago) | **200 prospects / 30 days** | **$200 budget**  
Success criterion: **≥ 2 discovery calls** + zero tone-escalation complaints + zero bench violations + reply rate ≥ 4%. *(Math: 200 × 48% = 96 leads; at 4% reply = 4 replies; at 35% to call = 1.4 — target of 2 requires ~6% reply or 50% reply-to-call.)*

---

## Page 2: The Skeptic's Appendix

**Four Failure Modes τ²-Bench Does Not Capture**  
1. **Offshore-perception triggers.** τ²-Bench scores task completion, not emotional reception. "Replace higher-cost roles with offshore equivalents" passes every benchmark task while triggering in-house managers who forward it to their CTO as evidence of vendor aggression. No sentiment model for the recipient. Fix: ICP-persona tone-panel probes (~$200/month). Probes D01–D05 cover drift; D06 partially resolved.  
2. **Bench over-commitment against a live inventory.** τ²-Bench uses a static world model; bench availability changes daily. Our hard-gate blocks unsupported commitments, but a context-refresh lag creates a window. Fix: webhook from bench system; 1–2 days.  
3. **Condescending competitor-gap framing.** τ²-Bench cannot penalize an agent that is technically correct but socially wrong. A CTO who deliberately skipped the "missing" capability reads the gap analysis as arrogant. Probe G05 caught 60% escalation before tone-guard tuning. Fix: prospect-awareness hedge in templates; partially implemented.  
4. **Multi-thread context leakage.** τ²-Bench is single-threaded. Simultaneous outreach to co-founder and VP Engineering can leak context — a GDPR incident. K01/K02 confirmed correct isolation at low concurrency; untested under 50+ concurrent threads.

**Public-Signal Lossiness of AI Maturity Scoring**  
*Loud but shallow (false positive):* Company posts AI thought leadership — CEO keynotes, "AI-first" letters, one "AI PM" role — and scores 2–3. Agent pitches Segment 4 (ML platform migration) to a company with no data layer. Prospect responds "we already have this." *Impact:* brand damage, wasted contact. Estimated FP rate at score ≥ 2: **15–25%** (qualitative review of 1,001-company sample; precision/recall not yet computed against labelled data).  
*Quiet but sophisticated (false negative):* Stealth AI startup keeps repos private, recruits by referral, scores 0. Agent sends generic email, missing the highest-margin Segment 4 engagement. **Mitigation before production:** hand-label 20–30 Tenacious past prospects to compute precision/recall.

**Honest Unresolved Failure — PEV Does Not Beat Baseline**  
Delta A = **−0.2652** (V1 pass@1 = 0.4615 vs. baseline 0.7267; t = −1.84, df = 12, p = 0.955 one-sided; source: `eval/score_log.json`). The mechanism made performance worse. Diagnosis: the thinking model already applies chain-of-thought internally; explicit UNDERSTAND/VERIFY/PLAN instructions compete with native reasoning. V1/V2 also produced a confirmation anti-pattern (agent asked user to confirm → user said yes + stopped → tool never called → reward = 0). V3 corrected this but n=3 valid scores (17/20 lost to credit exhaustion) — statistically meaningless. **What to deploy:** the enrichment + policy + compose stack, not the PEV agent. The τ²-Bench result documents benchmark performance honestly; it does not reflect outreach pipeline readiness.

**Kill-Switch Clause**  
`KILL_SWITCH` defaults `ON`; all outbound routes to staff sink until `CONVERSION_ENGINE_LIVE=true` is set by the CEO (`bash smoke_test.sh` exits 0). Pause if: (a) bench commitment not in bench summary; (b) Langfuse tone-compliance < 95% over any 7-day window; or (c) reply rate < 2% after 500 contacts.
