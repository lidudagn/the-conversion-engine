# Tenacious Style Guide v2

> Tone markers, formatting rules, and 24 labeled outreach drafts.
> Source: Mentor-provided reference document.

## Purpose

This guide codifies the Tenacious voice and provides 12 labeled "good" and 12 labeled "bad" outreach drafts. The labeled drafts are training data for the agent's tone-preservation check and reference material for any team member writing email or LinkedIn outreach in the Tenacious voice.

The drafts are anchored to real Tenacious context: the four ICP segments (recently-funded Series A/B startups, mid-market platforms restructuring cost, engineering-leadership transitions, specialized capability gaps), the four hiring signals (funding event, job-post velocity, layoffs, leadership change), the AI maturity score (0–3), the four-stack bench composition (Python, Go, data, ML, infra), and the public pricing bands.

---

## The Five Tone Markers

Every outreach, every reply, every discovery-call context brief must preserve these markers. A draft that scores below 4/5 on any marker is regenerated. A draft that fails two or more markers is a brand violation.

### 1. Direct
Clear, brief, actionable. No filler. Subject lines state intent — "Request," "Follow-up," "Context," "Question" — never "Quick," "Just," or "Hey." Body of cold outreach: 120 words maximum. One clear ask per message.

### 2. Grounded
Every claim is supported by the hiring signal brief or the competitor gap brief. When a signal is weak (fewer than five open roles, single low-confidence input), the agent asks rather than asserts.

### 3. Honest
Refuses claims that cannot be grounded in data. Never claims "aggressive hiring" if the job-post signal is weak. Never over-commits bench capacity that bench_summary.json does not show. Never fabricates peer-company practices.

### 4. Professional
Language appropriate for founders, CTOs, and VPs of Engineering. Avoids internal jargon — "bench" reads as offshore-vendor language. No offshore clichés ("top talent," "world-class," "A-players," "rockstar," "ninja").

### 5. Non-condescending
Frames competitor gaps as research findings or questions worth asking, never as failures of the prospect's leadership.

---

## Formatting Constraints

| Rule | Limit |
|---|---|
| Cold outreach body | Max 120 words |
| Warm reply body | Max 200 words |
| Re-engagement body | Max 100 words |
| Subject line | Under 60 characters |
| Asks per message | 1 |
| Emojis in cold | None |
| Attachments in cold | None |

---

## Signature Template

```
[First name]
[Title — "Research Partner," "Delivery Lead," "Engagement Manager"]
Tenacious Intelligence Corporation
gettenacious.com
```

---

## Pre-flight Checklist

| Check | Pass condition | Fail behavior |
|---|---|---|
| Hiring signal grounding | At least one named signal referenced | Regenerate |
| Confidence-aware phrasing | Low/Med → interrogative; High → assertive | Regenerate |
| Bench-vs-engineering-team | No "bench" externally | Regenerate |
| Bench-to-brief match | Capacity supported by bench_summary.json | Route to human |
| Pricing scope | Public bands only; no multi-phase TCV | Route to discovery |
| Word count | Within limits per type | Trim or regenerate |
| One ask | Single CTA | Pick highest-value, regenerate |
| Banned phrase scan | None present | Regenerate |
| LinkedIn-roast test | Would not be screenshotted and posted | Regenerate |

---

## Banned Phrases

| Phrase | Reason |
|---|---|
| world-class | Marketing filler |
| top talent | Offshore-vendor cliché |
| A-players | Same |
| rockstar / ninja / wizard | Outdated vendor jargon |
| skyrocket / supercharge / 10x | Unsubstantiated growth promises |
| I hope this email finds you well | Generic template signal |
| just following up / circling back | Re-engagement filler |
| Quick question / Quick chat | Implies time is owed |
| synergize / synergy / leverage / ecosystem | Consultant jargon |
| game-changer / disruptor / paradigm shift | Hype |
| our proprietary [X] / our AI-powered [X] | Black-box claims |
| You'll regret / Don't miss out | Fake urgency |
| Per my last email | Passive-aggressive |
| our 500 employees / our 20 years | Self-centered |
| I'll keep this brief — but [long] | Performative concision |
| I noticed you're a [job title] | Generic, not signal |

---

## Twelve Good Drafts

### GOOD #1 — Series A funding + role velocity, high confidence
**Segment:** 1 (recently-funded). **Signal:** Funding event + hiring velocity. **Confidence:** High.
- Subject: "Request: 15 minutes on your Q3 Python hiring"
- Names exact funding ($14M Series A, February) and role trend (2→7 in 60 days)
- 89 words. One ask. No banned phrases.

### GOOD #2 — Post-layoff cost-pressure, mid-market restructuring
**Segment:** 2 (restructuring). **Signal:** layoffs.fyi, 45 days, 12% cut. **Confidence:** High.
- Subject: "Context: lower-cost engineering capacity post-restructure"
- Uses "contraction" not "layoff failure." Conditional: "If you are scoping…"
- 100 words. Public pricing bands only.

### GOOD #3 — New CTO 90-day window
**Segment:** 3 (leadership transition). **Signal:** CTO announcement, 18 days ago. **Confidence:** High.
- Subject: "Context: a brief on offshore engineering models"
- Self-aware of inbox noise. Explicit "no follow-up" opt-out.
- 96 words. Value-add (one-page brief with honest trade-offs).

### GOOD #4 — Capability gap, AI maturity 2
**Segment:** 4 (capability gaps). **Signal:** 3 peers with MLOps postings, prospect has none. **Confidence:** High.
- Subject: "Question: your MLOps function in 2026"
- Frames gap as "two readings" not a deficiency. Asks prospect's reasoning.
- 117 words. Public starter project floor.

### GOOD #5 — Weak signal, asks rather than asserts
**Segment:** 1 or 2. **Signal:** 2 open roles, ambiguous. **Confidence:** Low.
- Subject: "Question: are your data engineering hires keeping up?"
- "I cannot tell from the outside." Explicit out: "ignore this."
- 105 words. Interrogative phrasing for weak signal.

### GOOD #6 — Resource value-add, no-pitch first touch
**Segment:** 1 (early-stage). **Signal:** Seed extension, public hires. **Confidence:** Med-High.
- Subject: "Resource: Series A engineering scale-up checklist"
- Pure value-add. Lists items arguing against Tenacious's own service.
- 116 words. Lowest-friction ask ("Want me to send the PDF?").

### GOOD #7 — Warm reply with bench routing
**Segment:** 1 (warm). **Signal:** Bench match supported.
- Subject: "Re: scope of the three-engineer engagement"
- Public bands only. Routes specific quote to human delivery lead.
- 130 words (warm limit 200).

### GOOD #8 — Re-engagement with new content
**Segment:** 2. **Signal:** Fresh layoffs.fyi sub-sector data.
- Subject: "New: layoffs.fyi data on your sub-sector this quarter"
- Two new verifiable data points. No "following up."
- 113 words. Explicit "no follow-up needed."

### GOOD #9 — Bench-gated honest decline
**Segment:** 1 (hot). **Signal:** 15-engineer ask not supported by bench.
- Subject: "Re: scaling to 15 engineers in 30 days"
- Refuses to over-commit. Offers partial + peer-firm referral.
- 116 words. Most important tone-check draft.

### GOOD #10 — AI maturity 0–1, gentle Segment 1 reframe
**Segment:** 1 with AI maturity 0–1. **Signal:** Funding + no AI roles.
- Subject: "Question: standing up your first AI function"
- "A normal place to be at your stage, not a gap."
- 130 words. Conditional throughout.

### GOOD #11 — Mutual connection (real)
**Segment:** 4 (data platform). **Signal:** Warm intro + matching tech stack.
- Subject: "Context: Arjun's recommendation"
- Names specific project context and architectural learnings.
- 110 words. Two low-friction options.

### GOOD #12 — Two-line micro-touch, post-engagement
**Segment:** 4 (warm post-call). **Signal:** Competitor stack data.
- Subject: "Quick thought after our call"
- 47 words. "No reply needed." References agreed next-step date.

---

## Twelve Bad Drafts

### BAD #1 — Wall of self-promotion
**Failures:** Grounded, Professional, Direct. 3 banned phrases. 152 words. No signal.
- "World-class," "top talent," "gold standard." 80% about Tenacious.

### BAD #2 — Asserts on weak signal
**Failures:** Honest, Grounded. "Scaling aggressively" on 2 open roles.
- "Top talent," "skyrocket," "Quick chat" — 3 banned phrases.

### BAD #3 — Bench overcommitment
**Failures:** Honest, Professional. Commits 12 Go engineers not in bench.
- Uses "bench" externally. Skips scope/pricing/handoff.

### BAD #4 — Condescending competitor gap
**Failures:** Non-condescending, Honest, Professional. Subject: "behind the curve."
- "You are falling behind," "catch up" — frames prospect as failing.

### BAD #5 — Aggressive third follow-up
**Failures:** Non-condescending, Honest. "Per my last three emails."
- Passive-aggressive guilt trip. Fake deadline.

### BAD #6 — Generic template
**Failures:** ALL markers. Unfilled [First Name] tokens.
- 5 banned phrases. Zero signal grounding.

### BAD #7 — Fake urgency / discount
**Failures:** Honest, Professional. Fabricated scarcity + 30% discount.
- "URGENT" subject, "Don't miss out." Pricing not in sheet.

### BAD #8 — Wrong segment pitch (D06)
**Failures:** Grounded, Honest. Pitches Seg4 to AI maturity 0–1.
- Assumes agentic-systems roadmap. Should be GOOD #10 framing.

### BAD #9 — PDF attachment cold
**Failures:** Direct, Grounded. 38-page cold PDF. No signal.

### BAD #10 — Multiple stacked asks
**Failures:** Direct. 4 asks + 60-minute call + 3 follow-up emails.

### BAD #11 — Pricing fabrication
**Failures:** Honest. Invented $1.2M TCV. Cold contract.

### BAD #12 — Signal fabrication
**Failures:** Honest, Grounded. Wrong funding round/amount. Highest-cost failure.

---

## Tone-Preservation Scoring Spec

| Marker | Score 5 (passes) | Score ≤ 2 (fails) |
|---|---|---|
| Direct | Subject states intent, body ≤ limits, one ask, no filler | "Quick/Just/Hey" subject; multi-paragraph intro; ≥2 asks |
| Grounded | Named signal from brief; confidence-aware phrasing | No signal named; asserts on weak signal |
| Honest | Names what brief doesn't show; interrogative for low-confidence | Unsupported claims; bench overcommit; pricing fabrication |
| Professional | No banned phrases; no "bench" externally | Banned phrase present; consultant jargon |
| Non-condescending | Gaps framed as research findings/questions | "Falling behind," "you need to," assumes reasoning |

---

## Outreach Decision Flow

| Step | Question | Action |
|---|---|---|
| 1 | ICP segment + confidence? | Low confidence across all → value-add resource touch |
| 2 | AI maturity score? | 0–1: Seg1 framing. 2+high+peers: Seg4 |
| 3 | Capacity commitment? | Cross-check bench_summary.json. Not supported → route human |
| 4 | Price mentioned? | Public bands only. Multi-phase TCV → route human |
| 5 | Previously contacted? | Stalled → re-engage with new content only |
| 6 | Final scan | Banned phrases, word count, signature, LinkedIn-roast test |
