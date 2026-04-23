# Act III — Failure Taxonomy

**Derived from:** 45-probe adversarial run on 2026-04-23  
**Bugs found:** 3  
**Failure classes:** 5

This taxonomy organizes the failure modes discovered by the probe library into classes by root cause, impact, and recoverability. It drives the target failure mode selection in `target_failure_mode.md`.

---

## Class 1 — Unsafe Input Handling (Safety)

**Root cause:** Input from untrusted sources (company names, job post titles, enrichment field values) reaches downstream components without sanitization.

**Impact:** Path traversal / `FileNotFoundError` from HTML characters in filenames; silent data corruption if input reaches LLM context without escaping.

**Probes that triggered this class:** E01, E02, E04 (bug-fixed)

**Before fix (E04):** Company name `<script>alert('xss')</script> Corp` caused a crash because `_save_brief()` used the raw name as a file path component. The resulting path `outputs/hiring_signal_brief_<script>alert('xss')</script>_corp.json` is invalid on all OSes.

**After fix:** `_safe_filename()` strips all non-alphanumeric characters before file path construction.

**Residual risk:** If enrichment data is later passed to an LLM prompt (e.g., in `EmailComposer`), prompt injection via job post titles or funding descriptions is possible unless the LLM is instruction-tuned to ignore embedded directives. The deterministic enrichment layer is safe; the LLM composition layer is the risk surface.

**Severity:** High — crash + potential security issue  
**Recoverability:** Fixed in this run  
**Likelihood in production:** Medium (Crunchbase data is structured; free-text fields like job post descriptions are higher risk)

---

## Class 2 — Defensive Coding Gaps (Robustness)

**Root cause:** Internal code assumes well-formed dicts from other modules but doesn't guard missing keys.

**Impact:** `KeyError` crashes when contradiction dicts from `ContradictionDetector` don't include a `'name'` key (e.g., future edge cases, manually constructed test data, or version drift between modules).

**Probes that triggered this class:** C06 (bug-fixed)

**Before fix:** `policy_engine.py:184` did `c['name'].upper()` without `.get()` — any dict without a `'name'` key raised `KeyError` and crashed the entire pipeline run.

**After fix:** `c.get("name", "unknown").upper()` — the contradiction is logged as "unknown" type and the pipeline continues.

**Severity:** High — silent crash with no fallback  
**Recoverability:** Fixed in this run  
**Likelihood in production:** Low-medium (only triggered by dicts from new contradiction rules or test harness that don't include the 'name' field)

---

## Class 3 — Tone Guard Coverage Gap (Compliance)

**Root cause:** The rule-based fallback in `ToneGuard._rule_based_check()` had no patterns for the five hard-fail categories: guarantee language, fabricated superlatives, bench overcommitment by count, explicit pricing, and competitor attacks.

**Impact:** When `ToneGuard` is initialized without an `llm_client` (the common case in tests and batch runs without LLM keys), every email — including emails with "We guarantee 3x revenue", "$15,000/month per engineer", and "#1 ranked firm" — would be marked `passed=True` and dispatched.

**Probes that triggered this class:** D01, D02, D03, D04, D07 (all pre-fix failures; post-fix all pass with hard-fails triggered)

**Before fix:**
- `passed=True` for: guarantee language, bench overcommitment (500+ engineers), explicit pricing, competitor attacks, fabricated rankings.

**After fix:** Five new keyword pattern groups added:
1. **Guarantee language** — "we guarantee", "guaranteed", "100% success", "without exception", "every time"
2. **Superlatives** — "#1 ranked", "number one", "best in africa", inflated NPS claims
3. **Bench overcommitment** — regex `\b([1-9]\d{2,})\s+engineers?\b` → count ≥ 100 → hard fail
4. **Explicit pricing** — regex `\$[\d,]+(?:\.\d+)?(?:\s*/\s*(?:month|year|engineer))` → hard fail
5. **Competitor attacks** — known competitor name + attack qualifier → hard fail

**Severity:** Critical — compliance and brand risk  
**Recoverability:** Fixed in this run  
**Likelihood in production:** High — LLM sometimes generates guarantee/superlative language even when not asked; rule-based guard is the last line of defense

---

## Class 4 — Semantic Alignment Gap (Quality, Not Fixed)

**Root cause:** The rule-based tone guard cannot detect *semantic* misalignment between email content and the active policy — e.g., a Segment 1 pitch (recently-funded startup language) sent under a Segment 2 policy (restructuring/cost-discipline language).

**Impact:** Segment pitch mismatch lands wrong with the prospect. A CTO navigating a painful restructuring receives enthusiastic "congrats on your Series A" language — brand damage and low conversion.

**Probes that triggered this class:** D06 (probe passes because system doesn't crash, but misalignment isn't caught)

**Root cause detail:** Keyword matching can't detect semantic incompatibility. Knowing that "recently closed a round" is Seg1 language and "cost discipline" is Seg2 language requires understanding both; no phrase pattern bridges them.

**Severity:** Medium-High — affects conversion rate, not safety  
**Recoverability:** Requires LLM-based tone check (already implemented in `ToneGuard._llm_check()`, active when llm_client provided)  
**Likelihood in production:** Low-medium (policy engine selects segment from ICP classifier; mismatch requires classifier error upstream)

**This is the target failure mode for Act IV.** See `target_failure_mode.md`.

---

## Class 5 — Boundary / Edge Case Behavior (Correctness)

**Root cause:** Classifiers and scorers at exact thresholds (0.5, 0.85), with zero/null inputs, or with contradictory multi-signal inputs produce stable but sometimes unexpected outputs.

**Impact:** Mostly correct — the ICP classifier, policy engine, and AI maturity scorer all handle boundary inputs without crashing. Some behaviors are worth documenting:
- ICP confidence = 0.499 → abstain (correct; 0.5 is the threshold)
- Segment 4 with AI maturity = 0 → tone_mode=exploratory (correct; Seg4 requires maturity ≥ 2)
- Negative funding → no Segment 1 (correct; amount-range gate not met)
- All four segments simultaneously → primary_segment=1 (correct; highest score wins)

**Probes that triggered this class:** A05, A06, A07, A08, B01, B02, B03, B04

**Severity:** Low — boundary behaviors are correct after review  
**Recoverability:** No fix needed  
**Likelihood in production:** Low (real Crunchbase data rarely has negative funding or future dates)

---

## Summary

| Class | Description | Severity | Fixed? | Probes |
|---|---|---|---|---|
| 1 | Unsafe input handling (HTML in filenames) | High | ✅ Yes | E04 |
| 2 | Defensive coding gap (KeyError in policy engine) | High | ✅ Yes | C06 |
| 3 | Tone guard coverage gap (5 hard-fail patterns missed) | Critical | ✅ Yes | D01–D04, D07 |
| 4 | Semantic alignment gap (wrong-segment pitch undetected) | Medium-High | ❌ No (LLM-only) | D06 |
| 5 | Boundary / edge case behavior | Low | N/A (correct) | A05–A08, B01–B04 |

**Confirmed pre-fix failure rate:** 9 / 45 probes (20%)  
**Post-fix failure rate:** 0 / 45 probes (0%)  
**Remaining risk surface:** Class 4 (semantic alignment) is only fully mitigated when `llm_client` is provided to `ToneGuard`.
