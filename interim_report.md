# The Conversion Engine — Interim Report
## Tenacious Consulting and Outsourcing | April 22, 2026

---

## Architecture Diagram

```mermaid
flowchart TD
    subgraph Data Layer
        CB[Crunchbase]
        JP[Job Posts]
        LF[Layoffs.fyi]
        LS[Leadership]
        AM[AI Maturity]
        GB[Gap Brief]
        CD[Contradiction]
    end

    subgraph Decision Engine
        PE{Policy Engine\npre-LLM}
        PE -- Tone mode --> LLM
        PE -- Gap gate --> LLM
        PE -- Classify --> LLM
    end

    subgraph Core Agent
        LLM[LLM Composer]
        Qual[Qualifier]
        Sched[Scheduler]
    end

    subgraph Compliance
        TG{Tone Guard\npost-LLM}
    end

    subgraph Outreach Channels
        EM[Email 1°]
        SM[SMS 2°]
        VM[Voice 3°]
    end

    subgraph External Systems
        CRM[HubSpot CRM]
        CAL[Cal.com Booking]
        OBS[Langfuse Tracing]
    end

    Data Layer --> PE
    PE --> Core Agent
    Core Agent --> TG
    TG --> Outreach Channels
    Outreach Channels -.-> External Systems

    style PE fill:#f9f,stroke:#333,stroke-width:2px
    style TG fill:#f9f,stroke:#333,stroke-width:2px
```

## System Architecture Diagram and Design Rationale

The Conversion Engine is a signal-grounded, decision-intelligence-driven lead generation system built for Tenacious Consulting and Outsourcing. The architecture decouples research from outreach through three layers:

**Layer 1 — Deterministic Research (Enrichment Pipeline)**
Six signal modules extract facts from public data: Crunchbase ODM (1,000 companies), layoffs.fyi, job-post velocity, leadership changes, AI maturity scoring (0–3), and competitor gap analysis. No LLM is used for data extraction.

**Layer 2 — Policy Engine (Pre-LLM Control)**
A deterministic decision layer computes what the LLM can and cannot say before any text is generated. Rules cover: tone mode (assertive/suggestive/exploratory), competitor-gap gating by confidence, signal classification (assertable/question/omit), bench-capacity hard constraints, and abstention for low-confidence prospects. Every decision is logged to `policy_trace.jsonl`.

**Layer 3 — Outreach + Compliance**
The LLM Composer drafts emails constrained by a Signal Usage Contract. A post-LLM Tone Guard scores drafts against the Tenacious style guide and hard-fails on over-claiming. A Contradiction Detector identifies cross-signal tensions (e.g., funded + laid off) and frames them as research findings.

**Kill-switch:** ON by default. All outbound routes to staff sink.

---

### Design Rationale

| Decision | Rationale |
|---|---|
| Pre-LLM policy engine | Prevents hallucination by constraining the LLM before it generates |
| Signal usage contract | Composer can only reference signals the policy engine classifies |
| Tone guard hard-fail | Over-claiming blocks send entirely — brand protection |
| Contradiction framing | Cross-signal tensions become research findings, not pitches |
| Failure propagation / Fallbacks | Unhandled integration exceptions fall back to staff escalation; timeouts emit an abstention variant. |
| Rate-limit handling | Async exponential backoffs handle API throttling limits across data layer fetching. |

---

## Production Stack Status Coverage

All required infrastructural components have been implemented and documented within the codebase.

| Component | Tool Chosen | Capability Verified | Configuration Details & Design Decisions | Verification Evidence |
|---|---|---|---|---|
| Email Delivery | Resend | Outbound sending drafted. | Implements a centralized kill-switch (`CONVERSION_ENGINE_LIVE`) routing outbound mail to a safe staff sink. | **Unverified.** Code structure relies on API keys but lacks exported trace IDs or webhooks. |
| SMS Routing | Africa's Talking | Sandbox drafted. | Dedicated for warm leads. Handles programmatic formatting but restricted to sandbox. | **Unverified.** Interacts via sandbox but lacks inbound/outbound confirmation traces. |
| CRM | HubSpot | Schema mapping drafted. | Designed to map rich enrichment signals into custom properties and logs touches. | **Unverified.** No contact JSON payload, exported object, or live API response logged yet. |
| Calendar | Cal.com | Stub integration only. | Attempted to pass contextual prospect briefs into booking metadata. | **Mocked / Failed.** API interaction is not functional; system heavily patches failures with mocked `mock_cal_98765` objects. |
| Observability | Langfuse | Wrappers implemented. | Wraps policy engine to track output costs relying on token metrics instead of binary logs. | **Unverified.** Wrappers deployed but no physical trace logs flushed and documented. |
| LLM Engine | OpenRouter | Local queries functional. | Leverages dev-tier Qwen3 model constrained by policy engine. | Simulated local tests triggered generation but await production tracing. |

---

## Enrichment Pipeline Documentation

| Signal | Source | Status | Output |
|---|---|---|---|
| Firmographics | Crunchbase ODM CSV | ✅ 1,000 companies loaded | Funding, employees, sector |
| Job velocity | Frozen dataset | ✅ Ready | 60-day change, AI-role fraction |
| Layoffs | layoffs.fyi CSV | ✅ 20 events loaded | 120-day window, headcount |
| Leadership | Crunchbase + press | ✅ Built | 90-day CTO/VP detection |
| AI maturity | Multi-signal (0–3) | ✅ Built (Logic only) | Per-signal justification, confidence |
| Competitor gap | Top-quartile analysis | ✅ Built (Logic only) | `competitor_gap_brief.json` |

### Validation Methodology & Implementation Details

**Validation Status:** 
Currently, the pipeline operates as an unvalidated structural prototype. No accuracy checks exist against human-labeled ground truth. We lack false positive rate estimates for entity resolution, and Crunchbase ingestion lacks deduplication logic.

**Implementation Details:**
- **AI Maturity Computation:** A programmatic 0-3 scoring heuristic. High-weight factors (Named AI/ML leadership, specific AI-adjacent titles) provide +1. Medium-weight (executive AI commentary, strategic GitHub repos) provide +0.5. Values map directly to a static `confidence` label sent to the policy engine.
- **Competitor Selection Logic:** Analyzes prospects by pulling intra-sector peers clustered using coarse 10x-banding of total funding size and employee count, labeling the top 25% by maturity score as the definitive "top quartile" benchmark.

---

## 5. τ²-Bench Baseline

**Status:** ✅ Complete (Provided by Instructor)

| Metric | Value |
|---|---|
| Mean pass@1 | **72.67%** |
| Tasks passed | 22 / 30 |
| Published leaderboard reference | ~42% |
| Model | openrouter/qwen/qwen3-next-80b-a3b-thinking |
| 95% CI | [0.6504, 0.7917] |

Per instructor guidance, this baseline was provided centrally due to resource constraints to ensure everyone works from the same starting point. It achieves 72.67% pass@1 on 30 tasks with 5 trials. The actual mechanism design evaluation in Act IV will only require 1 trial per task.

---

## 6. Synthetic Component Test Results

The following table represents **synthetic, strictly local loopback tests** against a static mock data payload (Consolety). None of these represent true End-to-End verified integrations over external API borders.

| Step | Result | Latency Method |
|---|---|---|
| Data loading (CB + layoffs + jobs) | Local CSV parse | — |
| Enrichment pipeline | Local brief output | `time.time()` (local cpu bound) |
| Policy engine | Triggered rules (in-memory) | `time.time()` (local cpu bound) |
| Email composition | Abstention variant | Static text generation |
| Tone guard | Passed (in-memory) | Local token match |
| Email send (kill-switch) | Blocked intentionally | — |
| SMS send (sandbox) | Unverified | — |
| HubSpot contact | **Unverified representation** | — |
| Cal.com booking | **Mock fallback invoked** | — |
| Qualification handler | Synthetic test passed | — |

**Note on Latency:** Previous claims of 137ms p50 over 20+ operations were derived entirely from local execution loopbacks using mocked object bypasses, unsupported by any real Langfuse traces or span exports. They do not represent live production network conditions.

---

## 7. Current Implementation State

- Full enrichment pipeline structure constructed for public intelligence scraping.
- Policy Engine rules engine and post-LLM Tone Guard deployed structurally.
- Kill-switch logic blocks physical sends safely.
- Qualification classification logic created to handle inbound parsing.

## Honest Status Report and Forward Plan

**Honest Status Report:**
This is a structurally complete but physically unverified interim submission. While the architecture cleanly separates the data layer from policy constraints, the production stack is currently heavily mocked or lacks exported trace evidence. Specifically, Cal.com is non-functional and relies on a hardcoded mock, HubSpot lacks JSON payload validation logs, and Langfuse tracing is implemented in code but requires API injection and real network execution to prove latency claims. The system strongly frames LLM behavior, but cannot claim "verified end-to-end operation" until physical evidence is captured.

**Forward Plan**

To successfully bridge logic completions into the remaining project deliverables, the following roadmap will be executed:

*   **Act III (Tomorrow): Adversarial Probing & Failure Taxonomy**
    We will develop 30+ structured adversarial probes inside `probes/` targeting the pre-LLM Policy Engine and post-LLM Tone Guard. This will test resilience against PII extraction, competitor hallucination, tone manipulation, and prompt injection, leading directly to our Failure Taxonomy documentation.
*   **Act IV (Days +2): Mechanism Design & Held-Out Evaluation**
    Building on the instructor-provided 72.67% baseline, we will design and implement targeted pipeline mechanisms (e.g., explicit tool-call sequencing rules, enriched state tracking) to structurally defend against the failure modes exposed in Act III, optimizing pass@1 on the sealed evaluation slice.
*   **Act V (Days +3): Executive Demo & Final Memo**
    We will complete the final 2-page decision memo for the Tenacious executive team outlining ROI, failure analysis bounds, and architectural defensibility. A comprehensive Loom video will demonstrate the end-to-end flow from Crunchbase firmographics scaling to a live HubSpot/Cal.com booking.
