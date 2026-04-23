"""
ICP Classifier — Segment classification with confidence scoring.
Handles edge cases like post-layoff + recent funding.
Abstention with strong UX when confidence is low.
"""

from typing import Optional
from pydantic import BaseModel, Field

from agent.enrichment.ai_maturity import AIMaturityResult


class ICPClassification(BaseModel):
    """ICP segment classification result."""
    primary_segment: Optional[int] = None     # 1-4 or None
    secondary_segment: Optional[int] = None   # Possible alternative
    confidence: float = 0.0                   # 0-1
    reasoning: str = ""
    edge_case: Optional[str] = None           # Named edge case if detected


# Strong abstention template — NOT generic "just reaching out"
ABSTENTION_TEMPLATE = """I might be off here, but from what I could see publicly, it looks like {company} is at a point where {hedged_observation}.

If that's even partially right, it might be worth comparing notes — we work with teams at a similar stage on {relevant_capability}.

Either way, no pressure — just thought the timing was interesting."""


class ICPClassifier:
    """
    Classify prospects into ICP segments with confidence scoring.

    Segments:
    1. Recently-funded Series A/B startups (15-80 people, $5-30M, last 6 months)
    2. Mid-market platforms restructuring cost (200-2000 people, post-layoff)
    3. Engineering-leadership transitions (new CTO/VP Eng, last 90 days)
    4. Specialized capability gaps (AI/ML build needs, maturity ≥ 2)
    """

    def classify(
        self,
        employee_count: Optional[int],
        total_funding_usd: Optional[float],
        last_funding_date: Optional[str],
        last_funding_type: Optional[str],
        has_recent_layoff: bool = False,
        layoff_headcount: int = 0,
        has_leadership_change: bool = False,
        ai_maturity: Optional[AIMaturityResult] = None,
        days_since_funding: Optional[int] = None,
    ) -> ICPClassification:
        """Classify a prospect into an ICP segment."""

        scores = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        reasoning_parts = []

        # ─── Segment 1: Recently-funded startups ─────────────────────
        if days_since_funding is not None and days_since_funding <= 180:
            scores[1] += 0.4
            reasoning_parts.append(f"Funded {days_since_funding}d ago")

            if last_funding_type and any(t in last_funding_type.lower()
                                         for t in ["series_a", "series a", "series_b", "series b"]):
                scores[1] += 0.2
                reasoning_parts.append(f"Round type: {last_funding_type}")

            if total_funding_usd and 5_000_000 <= total_funding_usd <= 30_000_000:
                scores[1] += 0.2
                reasoning_parts.append(f"Funding: ${total_funding_usd/1e6:.1f}M (sweet spot)")

            if employee_count and 15 <= employee_count <= 80:
                scores[1] += 0.2
                reasoning_parts.append(f"Team size: {employee_count} (scale-up phase)")

        # ─── Segment 2: Mid-market restructuring ─────────────────────
        if has_recent_layoff:
            scores[2] += 0.4
            reasoning_parts.append("Recent layoff event")

            if employee_count and 200 <= employee_count <= 2000:
                scores[2] += 0.3
                reasoning_parts.append(f"Mid-market size: {employee_count}")

            if layoff_headcount > 50:
                scores[2] += 0.1
                reasoning_parts.append(f"Significant headcount reduction: {layoff_headcount}")

        # ─── Segment 3: Leadership transitions ───────────────────────
        if has_leadership_change:
            scores[3] += 0.6
            reasoning_parts.append("New CTO/VP Engineering detected")
            # Narrow but high-conversion window

        # ─── Segment 4: Specialized capability gaps ──────────────────
        if ai_maturity and ai_maturity.score >= 2:
            scores[4] += 0.3
            reasoning_parts.append(f"AI maturity score: {ai_maturity.score}")

            if ai_maturity.confidence in ("high", "medium"):
                scores[4] += 0.2
                reasoning_parts.append("AI signal confidence sufficient for Seg 4 pitch")
        elif ai_maturity and ai_maturity.score < 2:
            # Hard gate: don't pitch Segment 4
            scores[4] = 0.0

        # ─── Edge Case Detection ─────────────────────────────────────
        edge_case = None

        # Post-layoff + recent funding = ambiguous
        if has_recent_layoff and days_since_funding and days_since_funding <= 180:
            edge_case = "layoff_plus_funding"
            reasoning_parts.append("EDGE CASE: post-layoff + recent funding")
            # Don't force a segment — let policy engine handle via contradiction

        # ─── Pick Primary + Secondary ────────────────────────────────
        sorted_segments = sorted(scores.items(), key=lambda x: -x[1])
        primary = sorted_segments[0]
        secondary = sorted_segments[1]

        # Confidence is the gap between top two
        if primary[1] > 0:
            confidence = min(primary[1], 1.0)
            if secondary[1] > 0:
                # Reduce confidence if secondary is close
                gap = primary[1] - secondary[1]
                if gap < 0.2:
                    confidence *= 0.7  # Ambiguous
        else:
            confidence = 0.0

        return ICPClassification(
            primary_segment=primary[0] if primary[1] > 0.2 else None,
            secondary_segment=secondary[0] if secondary[1] > 0.2 else None,
            confidence=round(confidence, 2),
            reasoning="; ".join(reasoning_parts),
            edge_case=edge_case,
        )

    def get_abstention_email(
        self,
        company_name: str,
        hedged_observation: str,
        relevant_capability: str
    ) -> str:
        """Generate a strong abstention email (not generic)."""
        return ABSTENTION_TEMPLATE.format(
            company=company_name,
            hedged_observation=hedged_observation,
            relevant_capability=relevant_capability,
        )
