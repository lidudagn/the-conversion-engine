"""
Enrichment Pipeline — Competitor Gap Brief Generator
Identifies top-quartile competitors and extracts specific practices the prospect is missing.
Output: competitor_gap_brief.json
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from agent.enrichment.ai_maturity import AIMaturityScorer, AIMaturityResult


class CompetitorProfile(BaseModel):
    """A competitor's AI maturity profile."""
    name: str
    sector: str = ""
    ai_maturity_score: int = 0
    ai_maturity_confidence: str = "low"
    key_practices: list[str] = Field(default_factory=list)
    employee_count: Optional[str] = None
    total_funding_usd: Optional[float] = None


class GapFinding(BaseModel):
    """A specific practice gap between prospect and top quartile."""
    practice: str
    top_quartile_prevalence: str   # e.g. "70%"
    prospect_status: str           # e.g. "No public signal"
    confidence: str                # "high", "medium", "low"
    relevance_to_tenacious: str    # How Tenacious can help


class CompetitorGapBrief(BaseModel):
    """Full competitor gap brief for a prospect."""
    prospect_name: str
    prospect_ai_maturity: int = 0
    prospect_sector: str = ""
    sector_distribution: dict = Field(default_factory=dict)  # mean, p75, p90
    top_quartile_companies: list[CompetitorProfile] = Field(default_factory=list)
    gaps: list[GapFinding] = Field(default_factory=list)
    confidence_avg: float = 0.0    # Average confidence across gaps
    generated_at: str = ""


class CompetitorGapAnalyzer:
    """Generate competitor gap briefs by comparing prospect to sector top quartile."""

    def __init__(self):
        self.scorer = AIMaturityScorer()

    def generate_brief(
        self,
        prospect_name: str,
        prospect_sector: str,
        prospect_ai_maturity: AIMaturityResult,
        sector_companies: list[dict],
    ) -> CompetitorGapBrief:
        """
        Generate a competitor gap brief.

        Args:
            prospect_name: Target company name
            prospect_sector: Industry/sector
            prospect_ai_maturity: Prospect's AI maturity result
            sector_companies: List of companies in same sector, each with:
                name, job_titles, leadership_titles, tech_stack, total_open_roles
        """
        # Score all sector companies
        scored_companies: list[CompetitorProfile] = []
        scores: list[int] = []

        for company in sector_companies:
            if company.get("name", "").lower() == prospect_name.lower():
                continue  # Don't compare prospect to itself

            result = self.scorer.score(
                job_titles=company.get("job_titles", []),
                total_open_roles=company.get("total_open_roles", 0),
                leadership_titles=company.get("leadership_titles", []),
                github_ai_repos=company.get("github_ai_repos", 0),
                exec_ai_mentions=company.get("exec_ai_mentions", []),
                tech_stack=company.get("tech_stack", []),
                strategic_comms=company.get("strategic_comms", [])
            )

            scored_companies.append(CompetitorProfile(
                name=company.get("name", ""),
                sector=prospect_sector,
                ai_maturity_score=result.score,
                ai_maturity_confidence=result.confidence,
                key_practices=self._extract_practices(result),
                employee_count=company.get("employee_count"),
                total_funding_usd=company.get("total_funding_usd")
            ))
            scores.append(result.score)

        # Include prospect score in distribution
        all_scores = scores + [prospect_ai_maturity.score]

        # Compute sector distribution
        if all_scores:
            sorted_scores = sorted(all_scores)
            mean_score = sum(all_scores) / len(all_scores)
            p75_idx = int(len(sorted_scores) * 0.75)
            p90_idx = int(len(sorted_scores) * 0.90)
            distribution = {
                "mean": round(mean_score, 2),
                "p75": sorted_scores[min(p75_idx, len(sorted_scores) - 1)],
                "p90": sorted_scores[min(p90_idx, len(sorted_scores) - 1)],
                "count": len(all_scores)
            }
        else:
            distribution = {"mean": 0, "p75": 0, "p90": 0, "count": 0}

        # Identify top quartile
        p75_threshold = distribution.get("p75", 2)
        top_quartile = [c for c in scored_companies if c.ai_maturity_score >= p75_threshold]
        top_quartile.sort(key=lambda x: x.ai_maturity_score, reverse=True)
        top_quartile = top_quartile[:10]  # Cap at 10

        # Extract gaps
        gaps = self._identify_gaps(prospect_ai_maturity, top_quartile)

        # Average confidence
        confidence_map = {"high": 0.9, "medium": 0.6, "low": 0.3}
        if gaps:
            conf_avg = sum(confidence_map.get(g.confidence, 0.5) for g in gaps) / len(gaps)
        else:
            conf_avg = 0.0

        return CompetitorGapBrief(
            prospect_name=prospect_name,
            prospect_ai_maturity=prospect_ai_maturity.score,
            prospect_sector=prospect_sector,
            sector_distribution=distribution,
            top_quartile_companies=top_quartile,
            gaps=gaps,
            confidence_avg=round(conf_avg, 2),
            generated_at=datetime.now().isoformat()
        )

    def _extract_practices(self, result: AIMaturityResult) -> list[str]:
        """Extract key practices from an AI maturity result."""
        practices = []
        for ev in result.evidence:
            if ev.weight in ("high", "medium") and ev.value:
                if ev.signal == "ai_roles" and isinstance(ev.value, int) and ev.value > 0:
                    practices.append(f"Active AI hiring ({ev.value} roles)")
                elif ev.signal == "ai_leadership" and ev.value:
                    practices.append("Dedicated AI/ML leadership")
                elif ev.signal == "github_activity" and isinstance(ev.value, int) and ev.value > 0:
                    practices.append("Public AI/ML repositories")
                elif ev.signal == "exec_commentary" and isinstance(ev.value, int) and ev.value > 0:
                    practices.append("Executive AI commitment")
                elif ev.signal == "ml_stack" and isinstance(ev.value, int) and ev.value > 0:
                    practices.append("Modern ML/AI tooling stack")
        return practices

    def _identify_gaps(
        self,
        prospect: AIMaturityResult,
        top_quartile: list[CompetitorProfile]
    ) -> list[GapFinding]:
        """Identify specific gaps between prospect and top quartile."""
        gaps = []
        if not top_quartile:
            return gaps

        # Count practice prevalence in top quartile
        practice_counts: dict[str, int] = {}
        for company in top_quartile:
            for practice in company.key_practices:
                practice_counts[practice] = practice_counts.get(practice, 0) + 1

        total_tq = len(top_quartile)

        # Check each practice against prospect
        prospect_practices = set()
        for ev in prospect.evidence:
            if ev.value and ev.weight in ("high", "medium"):
                prospect_practices.add(ev.signal)

        gap_mappings = {
            "Active AI hiring": ("ai_roles", "AI/ML talent outsourcing engagement"),
            "Dedicated AI/ML leadership": ("ai_leadership", "Fractional AI leadership consulting"),
            "Public AI/ML repositories": ("github_activity", "AI platform development"),
            "Executive AI commitment": ("exec_commentary", "AI strategy consulting"),
            "Modern ML/AI tooling stack": ("ml_stack", "ML platform migration consulting"),
        }

        for practice, count in sorted(practice_counts.items(), key=lambda x: -x[1]):
            prevalence = count / total_tq
            if prevalence < 0.3:
                continue  # Not prevalent enough to be meaningful

            signal_name, relevance = gap_mappings.get(practice, (None, "Consulting engagement"))
            prospect_has = signal_name in prospect_practices if signal_name else False

            if not prospect_has:
                confidence = "high" if prevalence >= 0.6 else "medium" if prevalence >= 0.4 else "low"
                gaps.append(GapFinding(
                    practice=practice,
                    top_quartile_prevalence=f"{prevalence:.0%}",
                    prospect_status="No public signal",
                    confidence=confidence,
                    relevance_to_tenacious=relevance
                ))

        return gaps[:3]  # Cap at 3 most relevant gaps
