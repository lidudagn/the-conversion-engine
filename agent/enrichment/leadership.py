"""
Enrichment Pipeline — Leadership Change Detector
Detects new CTO/VP Engineering appointments in the last 90 days.
Key signal for Segment 3 (leadership transition).
"""

from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field


class LeadershipChange(BaseModel):
    """A detected leadership change."""
    name: str
    title: str
    company: str
    date: Optional[str] = None
    source: str = ""
    confidence: str = "medium"


class LeadershipSignal(BaseModel):
    """Signal output for leadership changes."""
    company: str
    has_recent_change: bool = False
    changes: list[LeadershipChange] = Field(default_factory=list)
    new_cto: Optional[str] = None
    new_vp_eng: Optional[str] = None
    confidence: str = "medium"
    source: str = "crunchbase+press"


ENGINEERING_LEADER_TITLES = [
    "chief technology officer", "cto",
    "vp of engineering", "vp engineering", "vice president of engineering",
    "vp of technology", "vice president of technology",
    "head of engineering", "director of engineering",
    "chief information officer", "cio",
    "chief architect",
]


class LeadershipDetector:
    """Detect engineering leadership changes from Crunchbase + press signals."""

    def check_from_crunchbase(
        self,
        company_name: str,
        people: list[dict],
        days: int = 90
    ) -> LeadershipSignal:
        """
        Check for recent leadership changes from Crunchbase people data.

        Args:
            company_name: Company name
            people: List of person dicts with 'name', 'title', 'started_on' fields
            days: Lookback window (default 90 days for Segment 3)
        """
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        changes = []

        for person in people:
            title = (person.get("title") or "").lower()
            started_on = person.get("started_on") or person.get("start_date") or ""
            name = person.get("name") or person.get("first_name", "") + " " + person.get("last_name", "")

            if not self._is_engineering_leader(title):
                continue

            if started_on and started_on >= cutoff:
                changes.append(LeadershipChange(
                    name=name.strip(),
                    title=person.get("title", ""),
                    company=company_name,
                    date=started_on,
                    source="crunchbase",
                    confidence="medium"  # Crunchbase dates can lag
                ))

        new_cto = None
        new_vp_eng = None
        for c in changes:
            t = c.title.lower()
            if "cto" in t or "chief technology" in t:
                new_cto = c.name
            if "vp" in t and "eng" in t:
                new_vp_eng = c.name

        return LeadershipSignal(
            company=company_name,
            has_recent_change=len(changes) > 0,
            changes=changes,
            new_cto=new_cto,
            new_vp_eng=new_vp_eng,
            confidence="medium" if changes else "low",
            source="crunchbase"
        )

    def check_from_press(
        self,
        company_name: str,
        press_mentions: list[dict],
        days: int = 90
    ) -> LeadershipSignal:
        """
        Check for leadership changes from press releases / news.

        Args:
            company_name: Company name
            press_mentions: List of dicts with 'title', 'date', 'content' fields
            days: Lookback window
        """
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        changes = []

        appointment_keywords = [
            "appointed", "named", "promoted", "joins as", "hired as",
            "announces", "welcomes", "new cto", "new vp"
        ]

        for mention in press_mentions:
            title = (mention.get("title") or "").lower()
            content = (mention.get("content") or "").lower()
            date = mention.get("date") or ""

            if date and date < cutoff:
                continue

            combined = title + " " + content
            has_appointment = any(kw in combined for kw in appointment_keywords)
            has_eng_title = self._is_engineering_leader(combined)

            if has_appointment and has_eng_title:
                # Extract the person name — best effort
                changes.append(LeadershipChange(
                    name="(detected from press)",
                    title=self._extract_title(combined),
                    company=company_name,
                    date=date,
                    source="press_release",
                    confidence="medium"
                ))

        return LeadershipSignal(
            company=company_name,
            has_recent_change=len(changes) > 0,
            changes=changes,
            confidence="medium" if changes else "low",
            source="press"
        )

    def _is_engineering_leader(self, text: str) -> bool:
        """Check if text contains an engineering leadership title."""
        text_lower = text.lower()
        return any(title in text_lower for title in ENGINEERING_LEADER_TITLES)

    def _extract_title(self, text: str) -> str:
        """Best-effort title extraction from press text."""
        for title in ENGINEERING_LEADER_TITLES:
            if title in text.lower():
                return title.title()
        return "Engineering Leader"
