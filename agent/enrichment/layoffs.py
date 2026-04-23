"""
Enrichment Pipeline — Layoffs.fyi Parser
Parses layoff data from CSV format (layoffs.fyi structure).
"""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class LayoffEvent(BaseModel):
    company: str
    date: str
    total_laid_off: Optional[int] = None
    percentage: Optional[float] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    funds_raised: Optional[float] = None
    stage: Optional[str] = None
    source: Optional[str] = None


class LayoffSignal(BaseModel):
    company_name: str
    has_recent_layoff: bool = False
    events: list[LayoffEvent] = Field(default_factory=list)
    total_headcount_affected: int = 0
    most_recent_date: Optional[str] = None
    confidence: str = "low"


class LayoffsParser:
    """Parse layoffs.fyi data from CSV."""

    def __init__(self, data_dir: str = "data/layoffs", lookback_days: int = 120):
        self.data_dir = Path(data_dir)
        self.lookback_days = lookback_days
        self._events: list[LayoffEvent] = []
        self._by_company: dict[str, list[LayoffEvent]] = {}

    def load(self) -> list[LayoffEvent]:
        """Load layoff data from CSV files."""
        events = []

        for fpath in self.data_dir.glob("*.csv"):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        event = self._parse_csv_row(row)
                        if event:
                            events.append(event)
            except Exception as e:
                print(f"Warning: Could not parse {fpath}: {e}")

        # Also try JSON files
        for fpath in self.data_dir.glob("*.json"):
            try:
                with open(fpath, "r") as f:
                    data = json.load(f)
                records = data if isinstance(data, list) else [data]
                for rec in records:
                    event = self._parse_json_record(rec)
                    if event:
                        events.append(event)
            except Exception as e:
                print(f"Warning: Could not parse {fpath}: {e}")

        self._events = events
        self._build_index()
        print(f"Loaded {len(events)} layoff events")
        return events

    def _parse_csv_row(self, row: dict) -> Optional[LayoffEvent]:
        """Parse a CSV row into a LayoffEvent."""
        try:
            company = (row.get("company") or "").strip()
            if not company:
                return None

            total = None
            total_raw = row.get("total_laid_off", row.get("laid_off_count", ""))
            if total_raw:
                try:
                    total = int(str(total_raw).replace(",", ""))
                except (ValueError, TypeError):
                    pass

            pct = None
            pct_raw = row.get("percentage_laid_off", row.get("percentage", ""))
            if pct_raw:
                try:
                    pct = float(str(pct_raw).replace("%", ""))
                except (ValueError, TypeError):
                    pass

            funds = None
            funds_raw = row.get("funds_raised", row.get("funds_raised_millions", ""))
            if funds_raw:
                try:
                    funds = float(str(funds_raw).replace(",", "").replace("$", ""))
                except (ValueError, TypeError):
                    pass

            return LayoffEvent(
                company=company,
                date=row.get("date", row.get("Date_layoffs", "")),
                total_laid_off=total,
                percentage=pct,
                industry=row.get("industry", row.get("Industry", "")),
                location=row.get("location_hq", row.get("location", "")),
                country=row.get("country", row.get("Country", "")),
                funds_raised=funds,
                stage=row.get("stage", row.get("Stage", "")),
                source=row.get("source", row.get("Source", "")),
            )
        except Exception:
            return None

    def _parse_json_record(self, rec: dict) -> Optional[LayoffEvent]:
        """Parse a JSON record into a LayoffEvent."""
        try:
            company = (rec.get("company") or rec.get("Company") or "").strip()
            if not company:
                return None
            return LayoffEvent(
                company=company,
                date=rec.get("date", rec.get("Date", "")),
                total_laid_off=rec.get("total_laid_off", rec.get("Laid_Off_Count")),
                percentage=rec.get("percentage_laid_off", rec.get("Percentage")),
                industry=rec.get("industry", rec.get("Industry")),
                location=rec.get("location_hq", rec.get("Location_HQ")),
                country=rec.get("country", rec.get("Country")),
                funds_raised=rec.get("funds_raised"),
                stage=rec.get("stage", rec.get("Stage")),
                source=rec.get("source"),
            )
        except Exception:
            return None

    def _build_index(self):
        """Build company name → events index."""
        self._by_company = {}
        for event in self._events:
            key = event.company.lower()
            if key not in self._by_company:
                self._by_company[key] = []
            self._by_company[key].append(event)

    def check_company(self, company_name: str) -> LayoffSignal:
        """Check if a company has recent layoffs."""
        events = self._by_company.get(company_name.lower(), [])

        if not events:
            return LayoffSignal(
                company_name=company_name,
                has_recent_layoff=False,
                confidence="high",  # High confidence it's NOT in dataset
            )

        cutoff = (datetime.now() - timedelta(days=self.lookback_days)).strftime("%Y-%m-%d")
        recent_events = []

        for event in events:
            if event.date and event.date >= cutoff:
                recent_events.append(event)

        total_affected = sum(
            e.total_laid_off for e in recent_events if e.total_laid_off
        )
        most_recent = max(
            (e.date for e in recent_events if e.date), default=None
        )

        return LayoffSignal(
            company_name=company_name,
            has_recent_layoff=bool(recent_events),
            events=recent_events,
            total_headcount_affected=total_affected,
            most_recent_date=most_recent,
            confidence="high" if recent_events else "medium",
        )

    @property
    def all_events(self) -> list[LayoffEvent]:
        return self._events

    @property
    def companies_with_layoffs(self) -> list[str]:
        return list(self._by_company.keys())
