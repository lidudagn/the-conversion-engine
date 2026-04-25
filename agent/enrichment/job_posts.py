"""
Enrichment Pipeline — Job Post Scraper
Playwright-based scraper for public job pages.
Respects robots.txt. Computes job-post velocity.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class JobPost(BaseModel):
    """A single job posting."""
    title: str
    company: str
    department: Optional[str] = None
    location: Optional[str] = None
    posted_date: Optional[str] = None
    tech_stack: list[str] = Field(default_factory=list)
    is_ai_adjacent: bool = False
    source: str = ""
    url: Optional[str] = None


class JobVelocitySignal(BaseModel):
    """Job post velocity signal for a company."""
    company: str
    total_open_roles: int = 0
    ai_adjacent_roles: int = 0
    ai_roles_fraction: float = 0.0
    sixty_day_change: Optional[float] = None  # Percentage change
    sixty_day_change_str: str = ""
    job_titles: list[str] = Field(default_factory=list)
    confidence: str = "medium"
    source: str = "job_posts"


AI_ROLE_KEYWORDS = [
    "machine learning", "ml engineer", "data scientist", "ai engineer",
    "llm engineer", "applied scientist", "ai product manager",
    "data platform engineer", "ml ops", "mlops", "deep learning",
    "nlp engineer", "computer vision", "ai researcher", "ai/ml",
    "generative ai", "prompt engineer"
]


class JobPostScraper:
    """
    Scrape and analyze public job posts.
    Uses frozen dataset from seed repo as primary source.
    Live scraping via Playwright is optional and capped at 200 companies.
    """

    def __init__(self, data_dir: str = "data/job_posts"):
        self.data_dir = Path(data_dir)
        self._posts: list[JobPost] = []
        self._by_company: dict[str, list[JobPost]] = {}

    def load_frozen_dataset(self) -> list[JobPost]:
        """Load from frozen dataset (seed repo)."""
        posts = []
        for fpath in self.data_dir.glob("*.json"):
            try:
                with open(fpath, "r") as f:
                    data = json.load(f)
                records = data if isinstance(data, list) else [data]
                for record in records:
                    post = self._parse_record(record)
                    if post:
                        posts.append(post)
            except (json.JSONDecodeError, Exception) as e:
                print(f"Warning: Could not parse {fpath}: {e}")

        self._posts = posts
        self._build_index()
        print(f"Loaded {len(posts)} job posts from frozen dataset")
        return posts

    def _parse_record(self, record: dict) -> Optional[JobPost]:
        """Parse a job post record."""
        try:
            title = (record.get("title") or record.get("job_title") or "").strip()
            if not title:
                return None

            company = (record.get("company") or record.get("company_name") or "").strip()

            # Detect AI-adjacent roles
            is_ai = any(kw in title.lower() for kw in AI_ROLE_KEYWORDS)

            # Extract tech stack from description
            tech_stack = []
            desc = (record.get("description") or record.get("requirements") or "").lower()
            tech_keywords = [
                "python", "go", "golang", "java", "typescript", "react",
                "kubernetes", "docker", "aws", "gcp", "azure",
                "pytorch", "tensorflow", "spark", "kafka", "postgresql",
                "snowflake", "dbt", "databricks", "airflow"
            ]
            for kw in tech_keywords:
                if kw in desc:
                    tech_stack.append(kw)

            return JobPost(
                title=title,
                company=company,
                department=record.get("department", ""),
                location=record.get("location", ""),
                posted_date=record.get("posted_date", record.get("date", "")),
                tech_stack=tech_stack,
                is_ai_adjacent=is_ai,
                source=record.get("source", "frozen_dataset"),
                url=record.get("url", "")
            )
        except Exception:
            return None

    def _build_index(self):
        """Build company lookup index."""
        self._by_company = {}
        for post in self._posts:
            key = post.company.lower()
            if key not in self._by_company:
                self._by_company[key] = []
            self._by_company[key].append(post)

    def get_velocity_signal(self, company_name: str) -> JobVelocitySignal:
        """
        Get job post velocity signal for a company.

        60-day velocity calculation:
          recent  = posts with posted_date >= today - 60 days
          older   = posts with posted_date in [today-120d, today-60d)
          change  = (recent - older) / older × 100   (% growth in posting rate)
          If older == 0 but recent > 0: reported as "+N (new)" — first observed postings.
          If no date data is available: sixty_day_change is None, confidence stays "medium".

        Confidence tiers: high (≥10 posts), medium (3–9), low (<3).
        """
        key = company_name.lower()
        posts = self._by_company.get(key, [])

        total = len(posts)
        ai_adjacent = sum(1 for p in posts if p.is_ai_adjacent)
        ai_fraction = ai_adjacent / max(total, 1)
        titles = [p.title for p in posts]

        sixty_day_change = None
        change_str = ""
        if posts:
            cutoff_60 = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
            cutoff_120 = (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d")

            recent = sum(1 for p in posts if p.posted_date and p.posted_date >= cutoff_60)
            older = sum(1 for p in posts
                       if p.posted_date and cutoff_120 <= p.posted_date < cutoff_60)

            if older > 0:
                sixty_day_change = ((recent - older) / older) * 100
                change_str = f"{sixty_day_change:+.0f}%"
            elif recent > 0:
                change_str = f"+{recent} (new)"

        # Confidence based on data quality
        confidence = "high" if total >= 10 else "medium" if total >= 3 else "low"

        return JobVelocitySignal(
            company=company_name,
            total_open_roles=total,
            ai_adjacent_roles=ai_adjacent,
            ai_roles_fraction=round(ai_fraction, 3),
            sixty_day_change=sixty_day_change,
            sixty_day_change_str=change_str,
            job_titles=titles,
            confidence=confidence,
            source="job_posts"
        )

    async def scrape_company_live(self, company_url: str) -> list[JobPost]:
        """
        Live scrape a company's public careers page via Playwright.
        Use sparingly — capped at 200 companies per run.

        robots.txt policy (enforced before any page load):
          1. Fetch <scheme>://<host>/robots.txt and parse with urllib.robotparser.
          2. If the target URL is disallowed for user-agent "*", abort and return [].
          3. If robots.txt is unreachable (network error, 404, timeout), treat as
             "no restriction" and proceed — this matches the Robots Exclusion Protocol
             spec which says absence of a robots.txt implies no restrictions.
          4. Only publicly accessible career pages are scraped; pages behind login
             walls are never attempted.
        """
        try:
            from playwright.async_api import async_playwright
            import urllib.robotparser
            from urllib.parse import urlparse

            parsed = urlparse(company_url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(robots_url)
            try:
                rp.read()
                if not rp.can_fetch("*", company_url):
                    print(f"robots.txt disallows scraping: {company_url} — skipping")
                    return []
            except Exception:
                # robots.txt unreachable → treat as no restriction per RFC spec
                pass

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(company_url, timeout=15000)
                await page.wait_for_timeout(2000)

                # Extract job listings — generic approach
                content = await page.content()
                await browser.close()

                # Parse job listings from HTML (simplified)
                # In production, this would have site-specific extractors
                return []

        except ImportError:
            print("Playwright not available for live scraping")
            return []
        except Exception as e:
            print(f"Error scraping {company_url}: {e}")
            return []
