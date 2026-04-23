"""
Enrichment Pipeline Orchestrator
Runs all enrichment steps and produces hiring_signal_brief.json + competitor_gap_brief.json.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from agent.enrichment.crunchbase import CrunchbaseLoader, CrunchbaseCompany
from agent.enrichment.layoffs import LayoffsParser, LayoffSignal
from agent.enrichment.job_posts import JobPostScraper, JobVelocitySignal
from agent.enrichment.leadership import LeadershipDetector, LeadershipSignal
from agent.enrichment.ai_maturity import AIMaturityScorer, AIMaturityResult
from agent.enrichment.competitor_gap import CompetitorGapAnalyzer, CompetitorGapBrief
from agent.contradiction_detector import ContradictionDetector, Contradiction
from agent.icp_classifier import ICPClassifier, ICPClassification


class HiringSignalBrief(BaseModel):
    """Complete hiring signal brief for a prospect."""
    prospect_name: str
    prospect_domain: Optional[str] = None
    crunchbase_id: Optional[str] = None

    # Individual signals
    funding: dict = Field(default_factory=dict)
    job_velocity: dict = Field(default_factory=dict)
    layoffs: dict = Field(default_factory=dict)
    leadership: dict = Field(default_factory=dict)
    ai_maturity: dict = Field(default_factory=dict)

    # Classification
    icp_segment: dict = Field(default_factory=dict)

    # Bench match
    bench_match: dict = Field(default_factory=dict)

    # Contradictions
    contradictions: list[dict] = Field(default_factory=list)

    # Competitor gap reference
    competitor_gap_brief_ref: Optional[str] = None

    generated_at: str = ""


class EnrichmentPipeline:
    """
    Master orchestrator: runs all enrichment steps and merges results.
    Produces hiring_signal_brief.json and competitor_gap_brief.json.
    """

    def __init__(
        self,
        crunchbase_dir: str = "data/crunchbase",
        layoffs_dir: str = "data/layoffs",
        jobs_dir: str = "data/job_posts",
        output_dir: str = "outputs",
        bench_summary: Optional[dict] = None,
    ):
        self.crunchbase = CrunchbaseLoader(crunchbase_dir)
        self.layoffs = LayoffsParser(layoffs_dir)
        self.jobs = JobPostScraper(jobs_dir)
        self.leadership_detector = LeadershipDetector()
        self.ai_scorer = AIMaturityScorer()
        self.gap_analyzer = CompetitorGapAnalyzer()
        self.contradiction_detector = ContradictionDetector()
        self.icp_classifier = ICPClassifier()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Default bench summary
        self.bench_summary = bench_summary or {
            "available_stacks": ["python", "go", "data", "ml", "infra"],
            "total_available": 12,
            "by_stack": {
                "python": 4, "go": 2, "data": 3, "ml": 2, "infra": 1
            }
        }

        self._loaded = False

    def load_data(self):
        """Load all data sources. Call once before processing prospects."""
        if self._loaded:
            return

        self.crunchbase.load()
        self.layoffs.load()
        self.jobs.load_frozen_dataset()
        self._loaded = True

    def enrich_prospect(
        self,
        company_name: str,
        domain: Optional[str] = None,
    ) -> tuple[HiringSignalBrief, Optional[CompetitorGapBrief], list[Contradiction]]:
        """
        Run full enrichment for a single prospect.

        Returns:
            (hiring_signal_brief, competitor_gap_brief, contradictions)
        """
        if not self._loaded:
            self.load_data()

        # ─── 1. Crunchbase Lookup ────────────────────────────────────
        cb_company = None
        if domain:
            cb_company = self.crunchbase.get_by_domain(domain)
        if not cb_company:
            cb_company = self.crunchbase.get_by_name(company_name)

        funding_signal = self._extract_funding(cb_company)
        employee_count = self.crunchbase.get_employee_count_estimate(cb_company) if cb_company else None

        # ─── 2. Job Post Velocity ────────────────────────────────────
        velocity = self.jobs.get_velocity_signal(company_name)

        # ─── 3. Layoffs Check ────────────────────────────────────────
        layoff_signal = self.layoffs.check_company(company_name)

        # ─── 4. Leadership Changes ───────────────────────────────────
        leadership_signal = self.leadership_detector.check_from_crunchbase(
            company_name,
            cb_company.raw.get("people", []) if cb_company else []
        )

        # ─── 5. AI Maturity Score ────────────────────────────────────
        ai_result = self.ai_scorer.score(
            job_titles=velocity.job_titles,
            total_open_roles=velocity.total_open_roles,
            leadership_titles=[c.title for c in leadership_signal.changes] if leadership_signal.changes else [],
            tech_stack=[],  # Would come from BuiltWith/Wappalyzer
        )

        # ─── 6. ICP Classification ──────────────────────────────────
        days_since_funding = None
        if funding_signal.get("date"):
            try:
                fund_date = datetime.strptime(funding_signal["date"], "%Y-%m-%d")
                days_since_funding = (datetime.now() - fund_date).days
            except (ValueError, TypeError):
                pass

        icp = self.icp_classifier.classify(
            employee_count=employee_count,
            total_funding_usd=cb_company.total_funding_usd if cb_company else None,
            last_funding_date=cb_company.last_funding_date if cb_company else None,
            last_funding_type=cb_company.last_funding_type if cb_company else None,
            has_recent_layoff=layoff_signal.has_recent_layoff,
            layoff_headcount=layoff_signal.total_headcount_affected,
            has_leadership_change=leadership_signal.has_recent_change,
            ai_maturity=ai_result,
            days_since_funding=days_since_funding,
        )

        # ─── 7. Contradiction Detection ─────────────────────────────
        signal_dict = {
            "funding": funding_signal,
            "job_velocity": {
                "total_open_roles": velocity.total_open_roles,
                "sixty_day_change": velocity.sixty_day_change,
                "confidence": velocity.confidence,
            },
            "layoffs": {
                "has_recent_layoff": layoff_signal.has_recent_layoff,
                "event": layoff_signal.has_recent_layoff,
                "confidence": layoff_signal.confidence,
            },
            "leadership": {
                "new_cto": leadership_signal.new_cto,
                "has_recent_change": leadership_signal.has_recent_change,
                "confidence": leadership_signal.confidence,
            },
            "ai_maturity": {
                "score": ai_result.score,
                "confidence": ai_result.confidence,
                "has_ai_leadership": ai_result.has_ai_leadership,
            },
            "employee_count": employee_count or 0,
            "tech_stack": {},
        }
        contradictions = self.contradiction_detector.detect(signal_dict)

        # ─── 8. Competitor Gap Brief ─────────────────────────────────
        sector = cb_company.industry or "" if cb_company else ""
        sector_companies = []
        if sector:
            sector_peers = self.crunchbase.get_by_sector(sector)
            for peer in sector_peers[:15]:  # Cap for performance
                peer_velocity = self.jobs.get_velocity_signal(peer.name)
                sector_companies.append({
                    "name": peer.name,
                    "job_titles": peer_velocity.job_titles,
                    "total_open_roles": peer_velocity.total_open_roles,
                    "leadership_titles": [],
                    "tech_stack": [],
                    "employee_count": peer.employee_count,
                    "total_funding_usd": peer.total_funding_usd,
                })

        gap_brief = None
        if sector_companies:
            gap_brief = self.gap_analyzer.generate_brief(
                prospect_name=company_name,
                prospect_sector=sector,
                prospect_ai_maturity=ai_result,
                sector_companies=sector_companies,
            )

        # ─── Build Brief ─────────────────────────────────────────────
        brief = HiringSignalBrief(
            prospect_name=company_name,
            prospect_domain=domain,
            crunchbase_id=cb_company.cb_url if cb_company else None,
            funding=funding_signal,
            job_velocity={
                "open_roles": velocity.total_open_roles,
                "60d_change": velocity.sixty_day_change_str,
                "ai_roles_fraction": velocity.ai_roles_fraction,
                "confidence": velocity.confidence,
            },
            layoffs={
                "event": layoff_signal.has_recent_layoff,
                "headcount": layoff_signal.total_headcount_affected,
                "most_recent": layoff_signal.most_recent_date,
                "confidence": layoff_signal.confidence,
            },
            leadership={
                "new_cto": leadership_signal.new_cto,
                "new_vp_eng": leadership_signal.new_vp_eng,
                "has_recent_change": leadership_signal.has_recent_change,
                "confidence": leadership_signal.confidence,
            },
            ai_maturity={
                "score": ai_result.score,
                "confidence": ai_result.confidence,
                "uncertainty_reason": ai_result.uncertainty_reason,
                "language_constraint": ai_result.language_constraint,
                "has_ai_leadership": ai_result.has_ai_leadership,
            },
            icp_segment={
                "primary": icp.primary_segment,
                "secondary": icp.secondary_segment,
                "confidence": icp.confidence,
                "edge_case": icp.edge_case,
            },
            bench_match={
                "matched_stacks": [],  # Populated by policy engine
                "available": self.bench_summary.get("total_available", 0),
            },
            contradictions=[c.model_dump() for c in contradictions],
            competitor_gap_brief_ref="competitor_gap_brief.json" if gap_brief else None,
            generated_at=datetime.now().isoformat(),
        )

        # ─── Save Outputs ────────────────────────────────────────────
        self._save_brief(brief, company_name)
        if gap_brief:
            self._save_gap_brief(gap_brief, company_name)

        return brief, gap_brief, contradictions

    def _extract_funding(self, company: Optional[CrunchbaseCompany]) -> dict:
        """Extract funding signal from Crunchbase data."""
        if not company:
            return {"event": None, "confidence": "low", "source": "crunchbase"}

        event_str = None
        if company.last_funding_type and company.total_funding_usd:
            event_str = f"{company.last_funding_type}, ${company.total_funding_usd/1e6:.1f}M"
        elif company.last_funding_type:
            event_str = company.last_funding_type

        return {
            "event": event_str,
            "date": company.last_funding_date,
            "total_usd": company.total_funding_usd,
            "type": company.last_funding_type,
            "confidence": "high" if event_str else "low",
            "source": "crunchbase",
        }

    def _save_brief(self, brief: HiringSignalBrief, company: str):
        """Save hiring signal brief to outputs/."""
        safe_name = company.lower().replace(" ", "_")[:50]
        fpath = self.output_dir / f"hiring_signal_brief_{safe_name}.json"
        with open(fpath, "w") as f:
            json.dump(brief.model_dump(), f, indent=2, default=str)

    def _save_gap_brief(self, brief: CompetitorGapBrief, company: str):
        """Save competitor gap brief to outputs/."""
        safe_name = company.lower().replace(" ", "_")[:50]
        fpath = self.output_dir / f"competitor_gap_brief_{safe_name}.json"
        with open(fpath, "w") as f:
            json.dump(brief.model_dump(), f, indent=2, default=str)
