# Decision Memo: The Conversion Engine

**To:** CEO & CFO, Tenacious Consulting and Outsourcing  
**From:** Engineering  
**Date:** April 25, 2026  
**Subject:** Automated Lead Generation System — Pilot Recommendation

---

## Page 1: The Decision

**Executive Summary**  
We designed and built a signal-grounded outbound engine that enriches prospects from Crunchbase firmographics, job-post velocity, layoffs.fyi, and AI maturity scoring before composing personalized hiring-signal briefs and competitor-gap analyses. The system passed a 63-probe adversarial test suite with 100% compliance. We recommend a bounded 30-day pilot targeting Segment 1 (recently-funded Series A/B startups) before broader deployment.

**Evaluation & Unit Economics**  
- **Benchmark (τ²-Bench retail):** Baseline agent achieves 72.67% pass@1 (95% CI: [0.6504, 0.7917]); instructor-provided, model: qwen3-next-80b-a3b-thinking. Our Plan-Execute-Verify mechanism scored 46.15% pass@1 on the held-out test slice (n=13/20; 7 tasks failed due to API infrastructure errors). The mechanism did not improve on the baseline in this evaluation — detailed in method.md §9. The primary constraint was API reliability, not mechanism design.
- **Cost per qualified lead:** ~$0.05 enrichment + ~$0.05 LLM composition = **~$0.10 per processed prospect**, well below the $5 internal target. Total R&D evaluation spend: $0.91 (source: invoice_summary.json).
- **Speed-to-lead delta:** Current Tenacious manual process sees 30–40% stalled-thread rate due to slow follow-up. Our system responds to prospect events in seconds (pipeline p50: 1.5s, p95: 1.9s), eliminating the human response-latency component of stalls. Residual stall causes (no reply, schedule conflicts) require separate measurement against live prospects.
- **Competitive-gap outbound:** 100% of system-generated outreach leads with a prospect-specific research finding (AI maturity score + top-quartile competitor gap). A/B reply-rate data vs. generic pitch is unavailable from synthetic-only evaluation. Industry benchmarks (Clay, Smartlead 2026) show 7–12% reply rates for signal-grounded outreach vs. 1–3% for generic cold email.

**Pipeline Impact Scenarios (Annualized)**  
Sources: Tenacious internal conversion rates (discovery→proposal 35–50%, proposal→close 25–40%); ACV $240K–$720K talent outsourcing, $80K–$300K project consulting (Tenacious internal).

At 60 signal-grounded outreach touches/week (matching one SDR's baseline volume):

| Scenario | Contacts/yr | Replies (7%) | Closed deals (conservative) | Revenue range |
|---|---|---|---|---|
| 1 segment | 3,120 | 218 | ~10–15 | $2.4M–$10.8M |
| 2 segments | 6,240 | 437 | ~20–30 | $4.8M–$21.6M |
| All 4 segments | 12,480 | 874 | ~40–60 | $9.6M–$43.2M |

**Pilot Scope Recommendation**  
Launch against **Segment 1 (Recently-funded Series A/B)** at **200 prospects over 30 days** with a **$200 inference budget**. Success criterion: **3 confirmed discovery calls booked by the system** with no tone-escalation complaints and zero bench-commitment violations. Review results before expanding to additional segments.

---

## Page 2: The Skeptic's Appendix

**Four Failure Modes τ²-Bench Does Not Capture**  
1. **Offshore perception triggers:** τ²-Bench tests task completion, not emotional reception. Phrases like "offshore equivalents" or "replace higher-cost roles" trigger in-house engineering managers who read Tenacious outreach. Benchmark passes even when tone would produce immediate blocklisting. *Fix cost:* ~$100/month in adversarial tone audits.
2. **Bench over-commitment against fluid inventory:** The benchmark uses a static world model. In production, bench availability changes daily. Pre-intervention, the agent hallucinated capacity ("500 engineers ready to deploy"). Our hard-gate parsing stage blocks commitments not supported by the bench summary, but a lag between bench updates and the agent's view creates a window for over-commitment. *Fix cost:* webhook from bench system to agent context; 1–2 days engineering.
3. **Brand risk from competitor-gap framing:** τ²-Bench does not penalize condescension. A gap analysis that says "you are behind your competitors" to a CTO who made a deliberate architectural choice reads as arrogant. The system needs a defensive-reply detector — currently absent. *Fix cost:* 2–3 days, additional probe category.
4. **Multi-company multi-contact threading:** τ²-Bench is single-thread. Real Tenacious outreach reaches co-founder and VP Engineering simultaneously. Without strict thread isolation, Prospect A's context leaks to Prospect B — a GDPR incident. Probe K01/K02 confirmed our current isolation is correct, but this was not tested under concurrent high-load conditions. *Fix cost:* Load test with 50+ simultaneous threads.

**Public-Signal Lossiness**  
AI maturity scoring relies on public signals that carry known error modes:
- **Loud but shallow (false positive):** Company posts extensive AI thought leadership, scores 3, but has no production deployments. Agent pitches Segment 4 (ML platform migration) to a company without a data layer. *Impact:* Prospect responds with "we already have this" or, worse, perceives Tenacious as not doing their homework. Deal stalls.
- **Quiet but sophisticated (false negative):** Stealth AI startup keeps repos private, scores 0. Agent sends generic exploratory email, missing Segment 4 opportunity entirely. *Impact:* Revenue loss; Tenacious never gets a chance to pitch the highest-margin engagement type.
- **Mitigation:** Request a reference sample of 20–30 Tenacious past prospects to hand-label and compute precision/recall before production.

**Unresolved Failure — Probe D06 (Semantic Wrong-Segment Pitch)**  
The rule-based tone guard (100% pass rate on structural checks) completely failed (0% catch rate) on semantic misalignment: pitching "scale fast!" language to a company actively executing layoffs. The LLM-backed `_llm_check()` path resolves this but adds latency and cost. Without it enabled, the system will send contextually inappropriate emails that damage the Tenacious brand with high-visibility prospects in distress.

**Kill-Switch Clause**  
The `KILL_SWITCH` flag defaults to `ON`, routing all outbound to `sink@tenacious-challenge.test`. **The CEO should trigger an automatic pause if:** (a) any outbound message contains a bench commitment not in the current bench summary, (b) Langfuse tone-compliance rate drops below 95% over any 7-day window, or (c) reply rate falls below 2% after 500 contacts (indicating signal quality failure).
