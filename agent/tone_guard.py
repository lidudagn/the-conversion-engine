"""
★ Tone Guard — Post-LLM Compliance Checker
Second LLM call to score draft against Tenacious style guide.
~$0.002 per check. Prevents tone drift and over-claiming.

Hard-fail rules:
  - overclaiming → force regenerate
  - violates_signal_constraint → block send entirely
  - wrong_segment_pitch → block send
"""

import json
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from agent.policy_engine import PolicyDecision


class ToneResult(BaseModel):
    """Result of a tone guard check."""
    overall_score: float = 0.0          # 0-1
    dimensions: dict = Field(default_factory=dict)
    issues: list[str] = Field(default_factory=list)
    hard_fail: bool = False             # True = block send
    hard_fail_reason: Optional[str] = None
    rewrite_suggestion: Optional[str] = None
    passed: bool = True


class ToneGuard:
    """
    Post-LLM compliance check. Scores drafted email against
    Tenacious style guide and policy constraints.

    Cost: ~$0.002 per check (acceptable for brand protection).
    """

    REGEN_THRESHOLD = 0.75    # Below this → regenerate
    MAX_REGENS = 2            # Cap to prevent runaway cost

    HARD_FAIL_ISSUES = [
        "overclaiming",
        "violates_signal_constraint",
        "wrong_segment_pitch",
        "bench_overcommitment",
        "unauthorized_pricing",
    ]

    def __init__(self, style_guide: str = "", llm_client=None):
        self.style_guide = style_guide
        self.llm_client = llm_client

    async def check(
        self,
        draft: str,
        policy: PolicyDecision,
    ) -> ToneResult:
        """
        Score a draft email against style guide and policy constraints.

        Returns ToneResult with pass/fail and detailed scoring.
        """
        # Build the scoring prompt
        prompt = self._build_check_prompt(draft, policy)

        if self.llm_client:
            # Use LLM for sophisticated tone checking
            result = await self._llm_check(prompt)
        else:
            # Rule-based fallback
            result = self._rule_based_check(draft, policy)

        # Apply hard-fail rules
        result = self._apply_hard_fails(result)

        return result

    def _build_check_prompt(self, draft: str, policy: PolicyDecision) -> str:
        """Build the tone checking prompt."""
        return f"""Score this draft email against the style guide and policy constraints.

STYLE GUIDE:
{self.style_guide}

POLICY CONSTRAINTS:
- Tone mode: {policy.tone_mode}
- Assertable signals (can state as fact): {policy.assertable_signals}
- Must-question signals (phrase as questions): {policy.question_signals}
- Must-omit signals (do not mention): {policy.omit_signals}
- Gap delivery mode: {policy.gap_delivery_mode}
- Bench match: {policy.bench_match}

DRAFT EMAIL:
{draft}

Score 0-1 on each dimension. Flag specific issues.
Return JSON:
{{
  "overall_score": 0.0-1.0,
  "dimensions": {{
    "style_compliance": 0.0-1.0,
    "overclaiming": 0.0-1.0,
    "tone_match": 0.0-1.0,
    "signal_compliance": 0.0-1.0,
    "gap_delivery": 0.0-1.0
  }},
  "issues": ["issue description"],
  "rewrite_suggestion": "rewritten email if score < {self.REGEN_THRESHOLD}"
}}"""

    def _rule_based_check(self, draft: str, policy: PolicyDecision) -> ToneResult:
        """Rule-based tone check fallback (no LLM needed)."""
        issues = []
        scores = {
            "style_compliance": 0.8,  # Default reasonable
            "overclaiming": 1.0,
            "tone_match": 0.8,
            "signal_compliance": 1.0,
            "gap_delivery": 0.8,
        }

        draft_lower = draft.lower()

        # Check for overclaiming with omitted signals
        for signal in policy.omit_signals:
            signal_keywords = self._get_signal_keywords(signal)
            for kw in signal_keywords:
                if kw in draft_lower:
                    issues.append(f"Uses omitted signal '{signal}' (keyword: '{kw}')")
                    scores["signal_compliance"] = 0.3
                    scores["overclaiming"] = 0.3

        # Check for assertion language on question-only signals
        assertion_phrases = [
            "you are", "you're", "your company is", "clearly",
            "obviously", "it's clear", "we can see", "we know",
            "you need", "you must"
        ]
        if policy.tone_mode in ("exploratory", "suggestive"):
            for phrase in assertion_phrases:
                if phrase in draft_lower:
                    issues.append(f"Assertive language '{phrase}' in {policy.tone_mode} mode")
                    scores["tone_match"] -= 0.1

        # Check for unsupported signal claims
        for signal in policy.question_signals:
            signal_kws = self._get_signal_keywords(signal)
            for kw in signal_kws:
                if kw in draft_lower:
                    # Check if it's phrased as a question
                    # Find the sentence containing the keyword
                    sentences = draft.split(".")
                    for sentence in sentences:
                        if kw in sentence.lower() and "?" not in sentence:
                            issues.append(
                                f"Signal '{signal}' asserted but should be phrased as question"
                            )
                            scores["signal_compliance"] -= 0.2

        # Hard-fail: guarantee/absolute claim language → overclaiming
        guarantee_phrases = [
            "we guarantee", "guaranteed", "100% success", "without exception",
            "every time", "always deliver", "zero risk", "risk-free",
            "we promise", "definitively will",
        ]
        for phrase in guarantee_phrases:
            if phrase in draft_lower:
                issues.append(f"overclaiming: guarantee language ('{phrase}')")
                scores["overclaiming"] = 0.0

        # Hard-fail: fabricated superlatives → overclaiming
        superlative_phrases = [
            "#1 ranked", "#1 firm", "number one", "best in africa",
            "best in the world", "top-ranked", "industry-leading nps",
            "nps of 9", "nps of 10",
        ]
        for phrase in superlative_phrases:
            if phrase in draft_lower:
                issues.append(f"overclaiming: unsubstantiated superlative ('{phrase}')")
                scores["overclaiming"] = 0.0

        # Hard-fail: bench overcommitment (large specific engineer counts)
        import re
        large_eng_match = re.search(r"\b([1-9]\d{2,})\s+(?:dedicated\s+)?engineers?\b", draft_lower)
        if large_eng_match:
            count = int(large_eng_match.group(1))
            capacity = policy.available_capacity or {}
            total_available = sum(capacity.values()) if capacity else (
                sum(v for v in capacity.values()) if capacity else 0
            )
            # 500+ engineers when bench is small → bench overcommitment
            if count >= 100:
                issues.append(f"bench_overcommitment: claims {count} engineers (bench not verified)")
                scores["overclaiming"] = 0.0

        # Hard-fail: explicit pricing disclosure
        pricing_match = re.search(r"\$[\d,]+(?:\.\d+)?(?:\s*(?:per|/)\s*(?:month|year|engineer|person))", draft_lower)
        if pricing_match:
            issues.append(f"unauthorized_pricing: specific rate disclosed ('{pricing_match.group()}')")
            scores["overclaiming"] = 0.0

        # Hard-fail: aggressive competitor attacks by name
        known_competitors = ["accenture", "mckinsey", "deloitte", "bcg", "thoughtworks", "andela"]
        attack_qualifiers = ["unlike", "better than", "inferior", "overpriced", "underperform", "bloated"]
        for comp in known_competitors:
            if comp in draft_lower:
                for qualifier in attack_qualifiers:
                    if qualifier in draft_lower:
                        issues.append(f"overclaiming: competitor attack ('{comp}' + '{qualifier}')")
                        scores["overclaiming"] = 0.1
                        break

        # Check for bench overcommitment (bench_match=False path)
        commitment_phrases = [
            "we can provide", "we have", "our team of",
            "dedicated team", "assign", "staff"
        ]
        if not policy.bench_match:
            for phrase in commitment_phrases:
                if phrase in draft_lower:
                    issues.append("Bench commitment language without match")
                    scores["overclaiming"] = 0.2

        # Check for pricing language beyond public tiers
        deep_pricing_phrases = [
            "custom pricing", "discount", "negotiate",
            "special rate", "we can offer"
        ]
        for phrase in deep_pricing_phrases:
            if phrase in draft_lower:
                issues.append("Pricing language that should route to human")
                scores["overclaiming"] -= 0.2

        # Compute overall
        overall = sum(scores.values()) / len(scores)
        scores["tone_match"] = max(0, scores["tone_match"])
        scores["signal_compliance"] = max(0, scores["signal_compliance"])
        scores["overclaiming"] = max(0, scores["overclaiming"])

        return ToneResult(
            overall_score=round(overall, 2),
            dimensions=scores,
            issues=issues,
            passed=overall >= self.REGEN_THRESHOLD and not any(
                self._is_hard_fail_issue(i) for i in issues
            ),
        )

    async def _llm_check(self, prompt: str) -> ToneResult:
        """LLM-based tone check (when client available)."""
        try:
            response = await self.llm_client.chat.completions.create(
                model="qwen/qwen3-235b-a22b",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            data = json.loads(response.choices[0].message.content)

            return ToneResult(
                overall_score=data.get("overall_score", 0.5),
                dimensions=data.get("dimensions", {}),
                issues=data.get("issues", []),
                rewrite_suggestion=data.get("rewrite_suggestion"),
                passed=data.get("overall_score", 0) >= self.REGEN_THRESHOLD,
            )
        except Exception as e:
            # Fallback to rule-based
            return ToneResult(
                overall_score=0.5,
                issues=[f"LLM check failed: {str(e)}"],
                passed=False,
            )

    def _apply_hard_fails(self, result: ToneResult) -> ToneResult:
        """Apply hard-fail rules that override pass/fail."""
        for issue in result.issues:
            if self._is_hard_fail_issue(issue):
                result.hard_fail = True
                result.hard_fail_reason = issue
                result.passed = False
                break
        return result

    def _is_hard_fail_issue(self, issue: str) -> bool:
        """Check if an issue triggers a hard fail."""
        issue_lower = issue.lower()
        return any(hf in issue_lower for hf in [
            "overclaim", "omitted signal", "bench commitment",
            "violates_signal", "wrong_segment", "bench overcommit",
            "unauthorized_pricing"
        ])

    def _get_signal_keywords(self, signal: str) -> list[str]:
        """Map signal names to content keywords to check."""
        keyword_map = {
            "funding": ["raised", "funding", "series", "round", "investors"],
            "job_velocity": ["hiring", "open roles", "recruiting", "growing team"],
            "layoffs": ["layoff", "restructur", "downsiz", "cut"],
            "leadership": ["new cto", "new vp", "appointed", "leadership change"],
            "ai_maturity": ["ai team", "machine learning", "ai strategy", "ai maturity"],
        }
        return keyword_map.get(signal, [signal])
