"""
Enrichment Pipeline — AI Maturity Scorer
Scores companies 0-3 on AI readiness with explicit uncertainty modeling.
language_constraint enforced by policy engine.

Known error modes (not yet calibrated against labelled data):
  False positive: company posts AI thought leadership but has no production deployments.
    Scores 2-3 from exec_commentary/strategic_comms; agent pitches Seg4 to a company
    without a data layer. Mitigation: language_constraint="should_hedge" on medium confidence.
  False negative: stealth AI startup keeps repos private; scores 0 despite active AI work.
    Agent sends exploratory email, misses Seg4 pitch opportunity.
  Recommended: hand-label 20-30 Tenacious past prospects to compute precision/recall before
    production deployment.
"""

from typing import Optional
from pydantic import BaseModel, Field


class AISignalEvidence(BaseModel):
    """A single piece of evidence for AI maturity."""
    signal: str           # e.g. "ai_roles", "ai_leadership"
    weight: str           # "high", "medium", "low"
    value: Optional[int | str | bool] = None
    source: Optional[str] = None
    note: Optional[str] = None


class AIMaturityResult(BaseModel):
    """AI maturity score with explicit uncertainty."""
    score: int                  # 0-3
    confidence: str             # "high", "medium", "low"
    uncertainty_reason: str     # Why this confidence level
    evidence: list[AISignalEvidence] = Field(default_factory=list)
    language_constraint: str    # "can_assert" | "should_hedge" | "must_use_question_language"
    has_ai_leadership: bool = False
    ai_roles_count: int = 0
    total_roles_count: int = 0


class AIMaturityScorer:
    """
    Score AI maturity 0-3 from public signals.

    High weight:   AI-adjacent open roles, Named AI/ML leadership
    Medium weight: Public GitHub org activity, Executive commentary
    Low weight:    Modern data/ML stack, Strategic communications

    Score 0: No public signal
    Score 1: 1-2 low/medium signals
    Score 2: 1 high-weight signal OR 3+ medium-weight
    Score 3: Multiple high-weight + supporting medium
    """

    AI_ROLE_KEYWORDS = [
        "machine learning", "ml engineer", "data scientist", "ai engineer",
        "llm engineer", "applied scientist", "ai product manager",
        "data platform engineer", "ml ops", "mlops", "deep learning",
        "nlp engineer", "computer vision", "ai researcher", "ai/ml",
        "generative ai", "prompt engineer"
    ]

    AI_LEADER_TITLES = [
        "head of ai", "vp data", "vp of data", "chief scientist",
        "chief data officer", "head of machine learning", "director of ai",
        "vp artificial intelligence", "head of data science",
        "chief ai officer", "director of machine learning"
    ]

    ML_STACK_TOOLS = [
        "dbt", "snowflake", "databricks", "weights and biases", "wandb",
        "ray", "vllm", "mlflow", "kubeflow", "sagemaker", "vertex ai",
        "hugging face", "langchain", "llamaindex", "pinecone"
    ]

    def score(
        self,
        job_titles: list[str] | None = None,
        total_open_roles: int = 0,
        leadership_titles: list[str] | None = None,
        github_ai_repos: int = 0,
        exec_ai_mentions: list[str] | None = None,
        tech_stack: list[str] | None = None,
        strategic_comms: list[str] | None = None
    ) -> AIMaturityResult:
        """Score AI maturity from available signals."""

        job_titles = job_titles or []
        leadership_titles = leadership_titles or []
        exec_ai_mentions = exec_ai_mentions or []
        tech_stack = tech_stack or []
        strategic_comms = strategic_comms or []

        evidence = []
        high_signals = 0
        medium_signals = 0
        low_signals = 0

        # --- HIGH WEIGHT: AI-adjacent open roles ---
        ai_roles = self._count_ai_roles(job_titles)
        ai_fraction = ai_roles / max(total_open_roles, 1)
        evidence.append(AISignalEvidence(
            signal="ai_roles",
            weight="high",
            value=ai_roles,
            source="job_posts",
            note=f"{ai_roles}/{total_open_roles} roles are AI-adjacent ({ai_fraction:.0%})"
        ))
        if ai_roles >= 3:
            high_signals += 1
        elif ai_roles >= 1:
            medium_signals += 1

        # --- HIGH WEIGHT: Named AI/ML leadership ---
        has_ai_leader = self._has_ai_leadership(leadership_titles)
        evidence.append(AISignalEvidence(
            signal="ai_leadership",
            weight="high",
            value=has_ai_leader,
            source="team_page",
            note="AI/ML leadership detected" if has_ai_leader else "No AI leadership found"
        ))
        if has_ai_leader:
            high_signals += 1

        # --- MEDIUM WEIGHT: GitHub activity ---
        evidence.append(AISignalEvidence(
            signal="github_activity",
            weight="medium",
            value=github_ai_repos,
            source="github",
            note=f"{github_ai_repos} AI-related repos" if github_ai_repos else "No public org or AI repos"
        ))
        if github_ai_repos >= 2:
            medium_signals += 1

        # --- MEDIUM WEIGHT: Executive commentary ---
        evidence.append(AISignalEvidence(
            signal="exec_commentary",
            weight="medium",
            value=len(exec_ai_mentions),
            source="press",
            note=f"{len(exec_ai_mentions)} recent AI mentions by executives" if exec_ai_mentions else "No executive AI commentary found"
        ))
        if len(exec_ai_mentions) >= 1:
            medium_signals += 1

        # --- LOW WEIGHT: ML stack ---
        ml_tools = self._detect_ml_stack(tech_stack)
        evidence.append(AISignalEvidence(
            signal="ml_stack",
            weight="low",
            value=len(ml_tools),
            source="builtwith",
            note=f"ML tools: {', '.join(ml_tools)}" if ml_tools else "No ML stack detected"
        ))
        if len(ml_tools) >= 2:
            low_signals += 1

        # --- LOW WEIGHT: Strategic communications ---
        evidence.append(AISignalEvidence(
            signal="strategic_comms",
            weight="low",
            value=len(strategic_comms),
            source="annual_reports",
            note=f"{len(strategic_comms)} strategic AI references" if strategic_comms else "No strategic AI communications"
        ))
        if len(strategic_comms) >= 1:
            low_signals += 1

        # --- SCORING ---
        score = self._compute_score(high_signals, medium_signals, low_signals)
        confidence = self._compute_confidence(score, high_signals, medium_signals, low_signals)
        uncertainty_reason = self._build_uncertainty_reason(
            score, confidence, high_signals, medium_signals, low_signals, evidence
        )
        language_constraint = self._get_language_constraint(confidence)

        return AIMaturityResult(
            score=score,
            confidence=confidence,
            uncertainty_reason=uncertainty_reason,
            evidence=evidence,
            language_constraint=language_constraint,
            has_ai_leadership=has_ai_leader,
            ai_roles_count=ai_roles,
            total_roles_count=total_open_roles
        )

    def _count_ai_roles(self, titles: list[str]) -> int:
        """Count AI-adjacent roles from job titles."""
        count = 0
        for title in titles:
            title_lower = title.lower()
            if any(kw in title_lower for kw in self.AI_ROLE_KEYWORDS):
                count += 1
        return count

    def _has_ai_leadership(self, titles: list[str]) -> bool:
        """Check for named AI/ML leadership."""
        for title in titles:
            title_lower = title.lower()
            if any(lt in title_lower for lt in self.AI_LEADER_TITLES):
                return True
        return False

    def _detect_ml_stack(self, stack: list[str]) -> list[str]:
        """Detect ML stack tools."""
        found = []
        for tool in stack:
            tool_lower = tool.lower()
            if any(ml in tool_lower for ml in self.ML_STACK_TOOLS):
                found.append(tool)
        return found

    def _compute_score(self, high: int, medium: int, low: int) -> int:
        """Compute 0-3 score from signal counts."""
        if high >= 2 and medium >= 1:
            return 3
        if high >= 1 or medium >= 3:
            return 2
        if medium >= 1 or low >= 2:
            return 1
        return 0

    def _compute_confidence(self, score: int, high: int, medium: int, low: int) -> str:
        """Compute confidence in the score."""
        if score == 0:
            return "medium"  # Absence ≠ proof of absence
        if score == 3 and high >= 2:
            return "high"
        if score == 2 and high >= 1 and medium >= 1:
            return "high"
        if score == 2 and high >= 1:
            return "medium"
        if score == 2 and medium >= 3:
            return "medium"
        if score == 1 and medium >= 1:
            return "medium"
        return "low"

    def _build_uncertainty_reason(
        self, score: int, confidence: str,
        high: int, medium: int, low: int,
        evidence: list[AISignalEvidence]
    ) -> str:
        """Build human-readable uncertainty explanation."""

        if confidence == "high":
            return (f"Score {score} supported by {high} high-weight and {medium} "
                    f"medium-weight signals. Multiple confirming sources.")

        if confidence == "medium":
            if score == 0:
                return ("Score 0 but absence of public signal does not prove absence "
                        "of AI capability. Company may keep AI work private.")
            return (f"Score {score} from {'high' if high else 'medium'}-weight signals "
                    f"but lacking confirmation from additional sources. "
                    f"Some uncertainty remains.")

        # Low confidence
        reasons = []
        if high == 0:
            reasons.append("No high-weight signals observed")
        if score >= 2:
            reasons.append(f"Score {score} from limited evidence")
        reasons.append("Absence may reflect private work, not actual absence")
        return ". ".join(reasons) + "."

    def _get_language_constraint(self, confidence: str) -> str:
        """Map confidence to language constraint for the policy engine."""
        return {
            "high": "can_assert",
            "medium": "should_hedge",
            "low": "must_use_question_language"
        }[confidence]
