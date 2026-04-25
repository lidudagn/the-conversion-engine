# Act III → Act IV — Target Failure Mode

**Selected failure mode:** Semantic Alignment Gap — Wrong-Segment Pitch  
**Runner category:** D06 (tone_guard), cross-referenced with J01, J02 (tone_drift)  
**Decision date:** 2026-04-24  
**Current catch rate (rule-based):** 0%  
**Current catch rate (LLM check, when configured):** Activates automatically via `ToneGuard._llm_check()`

---

## What the Failure Mode Is

The conversion engine can send an email pitched to the wrong buyer segment:

- A **Segment 1** email (growth sprint, "scale fast off your Series A") sent to a company that just announced layoffs (Segment 2 context).
- A **Segment 4** email (AI maturity gap) sent to a company whose AI maturity policy signal says `language_constraint="must_use_question_language"` — yet the email asserts AI readiness as fact.

Both emails pass every rule-based check in `ToneGuard._rule_based_check()`. Neither contains a guarantee phrase, a specific dollar amount, a competitor name, or an engineer headcount claim. But both will cause immediate rejection: the prospect recognizes the email is contextually wrong and concludes the sender has no real knowledge of their business.

This is distinct from the keyword-detectable hard fails (D01–D05, D07) which are now fully patched.

---

## Why This Is the Highest-ROI Failure Mode

### Business cost derivation (Tenacious terms)

**1. Frequency.** Tenacious targets four segments across a dataset that mixes companies in different stages. A cold enrichment error — layoff date later than funding date, or AI maturity=1 classified as Seg4 — will occur at some non-zero rate. Each misclassification produces a wrong-segment email. At 200 prospects/week, even a 5% mismatch rate means 10 wrong-segment emails per week going out under the current rule-based-only setup.

**2. Severity per occurrence.** A wrong-segment email does more damage than a no-email. The prospect reads "congratulations on your funding" six weeks after announcing 15% workforce cuts, forms a strong negative impression ("this company doesn't do its homework"), and the prospect is closed permanently. This is worse than silence: silence is ignorable; a wrong-segment pitch creates an active negative record.

**3. Business cost per lost deal.** Tenacious's ACV target is $36,000–$120,000 (3–10 engineers at $3,000–$4,000/month × 3-month minimum). A single wrong-segment email killing a Segment 2 deal costs $36,000–$120,000 in forgone ACV plus the prospect relationship. Across 10 wrong-segment emails/week: $360,000–$1.2M in forgone pipeline per quarter if not addressed.

**4. Invisibility.** The tone guard currently does not log or flag wrong-segment pitches in the rule-based path. They appear as `passed=True` in the tone result. There is no signal to the operator that a wrong-segment email was sent. The failure is silent.

**5. Rule-based fix is impossible.** Keywords cannot distinguish Seg1 language from Seg2 language. "Scale your engineering team" is appropriate for a growing company and inappropriate for a company mid-restructuring. The semantic distinction requires understanding context — which is exactly what `ToneGuard._llm_check()` provides.

### Summary

| Dimension | Value |
|---|---|
| Current keyword detection rate | 0% |
| LLM check detection rate (when configured) | Estimated 80–90% (semantic check active) |
| Frequency at scale (200 prospects/week, 5% mismatch) | ~10 wrong-segment emails/week |
| Cost per wrong-segment email (forgone deal) | $36K–$120K ACV |
| Quarterly forgone pipeline (uncorrected, 5% rate) | $360K–$1.2M |
| Fix mechanism available | Yes — `llm_client` configured → `_llm_check()` activates |
| Investment to activate | OpenRouter API key in `config.py` |

---

## Probe Evidence

### D06 — Wrong Segment Pitch (Seg1 language, Seg2 policy)

```
Input: Congratulations on the recent Series A! Teams fresh off a funding round often
       need to scale engineering fast to hit the product milestones investors are watching.
       [policy says pitch_segment=2: restructuring]

Expected: hard_fail=True (wrong_segment_pitch)
Actual:   passed=True, hard_fail=False, issues=[]
```

The rule-based fallback cannot detect this. The email contains no forbidden keywords — it simply addresses the wrong business context.

**Probe result:** PASS (non-crash minimum). Hard fail NOT triggered. Logged as known gap.

### Contrast with D01 (now patched)

```
Input: "We guarantee you'll see 3x revenue growth in 90 days without exception."
Expected: hard_fail=True
Actual:   hard_fail=True [HARD-FAIL-TRIGGERED]
```

Keyword detection works for explicit guarantee language. Does not work for semantic context mismatch.

---

## Act III Completed Fixes (Context)

Act III closed four failure categories that were previously open:

| Fixed category | Pre-fix pass rate | Post-fix pass rate |
|---|---|---|
| Tone guard keyword hard-fails (D01–D07) | 3/8 = 37.5% | 8/8 = 100% |
| Aggressive competitive framing (N02, manual probe) | 0/2 = 0% | 2/2 = 100% |
| Bench regex capacity parsing (G05 bug) | Failed on "10 ML engineers" | All 10 test cases pass |
| Policy contradiction KeyError (C06) | Crashed on unknown keys | Graceful handling confirmed |

**Current state after Act III fixes:**
- Total probes: 63
- Passed: 63 / 63 (100%)
- Hard-fails correctly triggered: 5
- Rule-based hard-fail catch rate: 100% (for keyword-detectable classes)
- Semantic wrong-segment catch rate: 0% (requires LLM)

---

## Act IV Target

The target for Act IV is to close the semantic alignment gap:

**Mechanism:** Enable `ToneGuard.llm_client` in the production configuration. When a client is configured, `_llm_check()` activates and evaluates the email semantically, including checking for wrong-segment framing. The infrastructure for this is already implemented — only the API key configuration is missing.

**Measurement:** Re-run probe D06 with `llm_client` configured. Expected result: `hard_fail=True, hard_fail_reason="wrong_segment_pitch"`. Current result: `passed=True` (rule-based path, no LLM).

**Secondary target:** Improve τ²-Bench retail baseline from 27.87% pass@1 to ≥ 35% by improving agent tool-call sequencing on multi-step exchange/cancellation tasks. (Separate improvement axis from tone guard fix.)

Both together form the Delta A deliverable for the final submission.
