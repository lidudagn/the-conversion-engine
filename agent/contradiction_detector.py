"""
★ Contradiction Detector — Cross-Signal Intelligence
Detects contradictions between signals that make outreach feel
like a research finding, not a pitch.

Each contradiction carries a confidence score.
If confidence < 0.6 → omit from email.
"""

from typing import Optional
from pydantic import BaseModel, Field


class Contradiction(BaseModel):
    """A detected cross-signal contradiction."""
    name: str
    description: str
    signals_used: list[str]
    confidence: float              # 0-1; < 0.6 = don't use in email
    framing: str                   # Human-crafted language for the email
    segment_override: Optional[int] = None  # If contradiction changes segment


class ContradictionDetector:
    """
    Rule-based detector for cross-signal contradictions.
    Contradictions demonstrate the agent has actually thought about
    the prospect's situation.
    """

    def detect(self, signals: dict) -> list[Contradiction]:
        """
        Detect contradictions from enrichment signals.

        Args:
            signals: Dict with keys like 'funding', 'layoffs', 'job_velocity',
                    'leadership', 'ai_maturity', 'employee_count', 'tech_stack'
        """
        contradictions = []

        for rule in self.RULES:
            try:
                result = rule(signals)
                if result:
                    contradictions.append(result)
            except (KeyError, TypeError, AttributeError):
                continue

        return contradictions

    @property
    def RULES(self):
        return [
            self._growth_vs_layoff,
            self._hiring_velocity_vs_small_team,
            self._ai_ambition_vs_no_ai_team,
            self._new_leader_old_stack,
            self._funded_but_not_hiring,
            self._hiring_but_no_funding,
        ]

    def _growth_vs_layoff(self, signals: dict) -> Optional[Contradiction]:
        """Funded recently AND had layoffs → contradictory signal."""
        funding = signals.get("funding", {})
        layoffs = signals.get("layoffs", {})

        has_funding = bool(funding.get("event"))
        has_layoffs = bool(layoffs.get("has_recent_layoff") or layoffs.get("event"))

        if has_funding and has_layoffs:
            # Confidence depends on signal quality
            fund_conf = {"high": 0.9, "medium": 0.7, "low": 0.4}.get(
                funding.get("confidence", "medium"), 0.6)
            lay_conf = {"high": 0.9, "medium": 0.7, "low": 0.4}.get(
                layoffs.get("confidence", "high"), 0.8)
            confidence = min(fund_conf, lay_conf)

            return Contradiction(
                name="growth_vs_layoff",
                description="Company raised funding recently but also had layoffs",
                signals_used=["funding", "layoffs"],
                confidence=confidence,
                framing=(
                    "You've raised recently but also went through layoffs — "
                    "I've seen teams in that position balancing growth with "
                    "cost discipline. That tension usually means the next "
                    "hires matter more than average."
                ),
                segment_override=None  # Could be Segment 1 OR 2
            )
        return None

    def _hiring_velocity_vs_small_team(self, signals: dict) -> Optional[Contradiction]:
        """Hiring fast but still a small team → pressure point."""
        velocity = signals.get("job_velocity", {})
        employee_count = signals.get("employee_count", 0)

        change = velocity.get("sixty_day_change")
        if isinstance(employee_count, str):
            # Parse range
            try:
                employee_count = int(employee_count.split("-")[0])
            except (ValueError, IndexError):
                employee_count = 0

        if change and change > 100 and employee_count > 0 and employee_count < 30:
            confidence = 0.7 if velocity.get("confidence") == "high" else 0.5
            return Contradiction(
                name="hiring_velocity_vs_small_team",
                description="Small team with rapidly growing open roles",
                signals_used=["job_velocity", "employee_count"],
                confidence=confidence,
                framing=(
                    "Your team is still small but your open roles suggest "
                    "you're trying to grow fast — that's usually the moment "
                    "where the build-vs-outsource question gets real."
                ),
            )
        return None

    def _ai_ambition_vs_no_ai_team(self, signals: dict) -> Optional[Contradiction]:
        """AI maturity ≥2 but no AI leadership → gap opportunity."""
        ai = signals.get("ai_maturity", {})

        score = ai.get("score", 0)
        has_leader = ai.get("has_ai_leadership", False)

        if score >= 2 and not has_leader:
            confidence = 0.6 if ai.get("confidence") != "low" else 0.4
            return Contradiction(
                name="ai_ambition_vs_no_ai_team",
                description="Company investing in AI but lacks dedicated leadership",
                signals_used=["ai_maturity"],
                confidence=confidence,
                framing=(
                    "You seem to be investing in AI but without a dedicated AI "
                    "leader yet — that's a pattern where outside expertise can "
                    "accelerate the first 6 months significantly."
                ),
            )
        return None

    def _new_leader_old_stack(self, signals: dict) -> Optional[Contradiction]:
        """New engineering leader + legacy tech → reassessment window."""
        leadership = signals.get("leadership", {})
        tech_stack = signals.get("tech_stack", {})

        has_new_leader = bool(leadership.get("new_cto") or leadership.get("has_recent_change"))

        # Heuristic: if tech stack age is high or legacy technologies detected
        stack_age_score = tech_stack.get("age_score", 0)

        if has_new_leader and stack_age_score > 2:
            confidence = 0.6 if leadership.get("confidence") != "low" else 0.4
            return Contradiction(
                name="new_leader_old_stack",
                description="New engineering leadership with legacy tech stack",
                signals_used=["leadership", "tech_stack"],
                confidence=confidence,
                framing=(
                    "New engineering leadership often reassesses the stack — "
                    "if that's on your radar, we've helped teams in similar "
                    "transitions."
                ),
            )
        return None

    def _funded_but_not_hiring(self, signals: dict) -> Optional[Contradiction]:
        """Recently funded but few open roles → unusual silence."""
        funding = signals.get("funding", {})
        velocity = signals.get("job_velocity", {})

        has_funding = bool(funding.get("event"))
        total_roles = velocity.get("total_open_roles", 0)

        if has_funding and total_roles < 3:
            return Contradiction(
                name="funded_but_not_hiring",
                description="Recently funded but very few open roles",
                signals_used=["funding", "job_velocity"],
                confidence=0.5,
                framing=(
                    "You closed a round recently but don't seem to have "
                    "many open roles yet — sometimes that means the team "
                    "is still figuring out what to build first. We've "
                    "helped in exactly that situation."
                ),
            )
        return None

    def _hiring_but_no_funding(self, signals: dict) -> Optional[Contradiction]:
        """Lots of open roles but no recent funding → bootstrapped growth or burn concern."""
        funding = signals.get("funding", {})
        velocity = signals.get("job_velocity", {})

        has_funding = bool(funding.get("event"))
        total_roles = velocity.get("total_open_roles", 0)

        if not has_funding and total_roles > 10:
            return Contradiction(
                name="hiring_but_no_funding",
                description="Aggressive hiring without recent funding",
                signals_used=["funding", "job_velocity"],
                confidence=0.5,
                framing=(
                    "You're hiring aggressively without a recent round — "
                    "that usually means either strong revenue or a tight "
                    "cost window. Either way, time-to-productivity on new "
                    "hires matters more than usual."
                ),
            )
        return None
