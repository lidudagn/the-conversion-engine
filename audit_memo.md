# Audit Memo: Why τ²-Bench is Insufficient for Tenacious Consulting

**Date:** 2026-04-28  
**Subject:** Gap Analysis between τ²-Bench Baseline and Tenacious B2B Production Requirements  

## 1. Headline Finding
τ²-Bench effectively measures retail customer service tasks (exchange, cancel, refund), but catastrophically fails measuring B2B outbound sales capabilities. While Conversion Engine scores a 72.67% pass@1 on retail traces, this vanity metric masks silent, deal-killing failures in brand representation, grounding, and semantic alignment crucial for Tenacious Consulting.

## 2. Retail Success Masks B2B Blind Spots
τ²-Bench baseline validation confirms the Engine excels at retail multi-step workflows. For example, the agent correctly completes retail order lookups (Trace ID 1) and fails cleanly on retail policy bounds like multi-step retail cancels (Trace ID 11) and partial-refund returns (Trace ID 34). 

However, τ²-Bench evaluates pure transactional correctness. It penalizes structured-domain process errors (Trace ID 76, order-modification) and multi-turn lookup flaws (Trace ID 92), but possesses no mechanism to evaluate B2B consultative judgment or signal qualification. When an agent recites policy verbatim but fails consultative synthesis (Trace ID 66), τ²-Bench correctly flags it as a failure in retail but entirely ignores the identical underlying pathology in B2B context sensing.

## 3. The Tenacious Failure Taxonomy: Identified Gaps

To measure actual business risk, we must assess four mutually distinct gaps ignored by τ²-Bench.

### Gap A: Semantic Alignment Gap (The D06 Failure)
The most critical defect is Probe **D06**. It demonstrates a "Segment 1" growth pitch sent to a "Segment 2" restructuring company. Both pass keyword filters, but the context mismatch is a semantic failure. `ToneGuard` caught 0% of these. Probe **H01** reinforces this: a post-layoff firm without VC funding erroneously receives a Seg1 growth pitch about hypergrowth. This gap presents an estimated $2.4M–$7.2M quarterly pipeline risk.

### Gap B: Signal Overclaiming & Qualification
τ²-Bench ignores evidence grounding. Probe **I01** exposes that a single job post is hallucinated into "your company is aggressively hiring". Probe **I03** shows a question-only funding signal stated as a factual assertion. Furthermore, Probe **C03** exposes bench over-commitment: sending "we can staff your team" without verifying the engineer pool. These failures unilaterally destroy prospect trust.

### Gap C: Deeper Trajectory & Grounding Failures
Beyond basic mismatches, the agent frequently struggles with complex trajectory constraints. Probe **B01** reveals the agent pushing assertive pitches despite borderline ICP confidence (0.499), violating the structural abstention policy. Probe **N02** highlights aggressive gap framing ungrounded in evidence ("falling behind rapidly"), while the AMS-PAR trace from Week 10 shows the agent completely hallucinating a Segment 4 AI maturity score ungrounded from the input brief.

### Gap D: Systemic Coordination & Reliability
Transactional tests miss multi-component pipeline edges. Probe **E04** demonstrates an HTML-injected company name causing an operational pipeline crash. Probe **M01** emphasizes that if a kill switch fails to intercept a scheduling attempt, it triggers an unauthorized real-world calendar invite. These flaws directly expose Tenacious to operational or legal risk.

## 4. Recommendation: The Tenacious-Bench v0.1
To bridge these gaps, Tenacious faces unacceptable risk without a custom evaluation suite. We must execute **Path B (Preference-tuned Judge)**:
1. Develop a schema-compliant dataset of B2B tasks.
2. Train a DPO model distinguishing "Grounded Compliance" from "Keyword-Passing Hallucination."
3. Completely evaluate the Conversion Engine against Tenacious-Bench prior to deployment.
