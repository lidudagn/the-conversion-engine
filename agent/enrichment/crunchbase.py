"""
Enrichment Pipeline — Crunchbase ODM Loader
Loads 1,001 company records from Crunchbase CSV dataset.
"""

import csv
import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field


class FundingRound(BaseModel):
    round_type: str = ""
    amount_usd: Optional[float] = None
    announced_on: Optional[str] = None
    investor_names: list[str] = Field(default_factory=list)


class CrunchbaseCompany(BaseModel):
    name: str
    domain: Optional[str] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None
    industry: Optional[str] = None
    industry_groups: list[str] = Field(default_factory=list)
    headquarters_location: Optional[str] = None
    country: Optional[str] = None
    employee_count: Optional[str] = None
    founded_on: Optional[str] = None
    total_funding_usd: Optional[float] = None
    last_funding_type: Optional[str] = None
    last_funding_date: Optional[str] = None
    num_funding_rounds: int = 0
    funding_rounds: list[FundingRound] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    status: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    cb_url: Optional[str] = None
    founders: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    raw: dict = Field(default_factory=dict)


class CrunchbaseLoader:
    def __init__(self, data_dir: str = "data/crunchbase"):
        self.data_dir = Path(data_dir)
        self._companies: list[CrunchbaseCompany] = []
        self._by_name: dict[str, CrunchbaseCompany] = {}
        self._by_domain: dict[str, CrunchbaseCompany] = {}

    def load(self) -> list[CrunchbaseCompany]:
        companies = []
        # Load CSV files
        for fpath in self.data_dir.glob("*.csv"):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        company = self._parse_csv_row(row)
                        if company:
                            companies.append(company)
            except Exception as e:
                print(f"Warning: Could not parse {fpath}: {e}")
        # Also try JSON files if any
        for fpath in self.data_dir.glob("*.json"):
            try:
                with open(fpath, "r") as f:
                    data = json.load(f)
                records = data if isinstance(data, list) else [data]
                for record in records:
                    company = self._parse_json_record(record)
                    if company:
                        companies.append(company)
            except Exception as e:
                print(f"Warning: Could not parse {fpath}: {e}")

        self._companies = companies
        self._build_indices()
        print(f"Loaded {len(companies)} companies from Crunchbase ODM")
        return companies

    def _parse_csv_row(self, row: dict) -> Optional[CrunchbaseCompany]:
        try:
            name = (row.get("name") or "").strip()
            if not name:
                return None

            # Parse industries from JSON-like string
            categories = []
            industries_raw = row.get("industries", "")
            if industries_raw:
                try:
                    items = json.loads(industries_raw.replace("\"\"", "\""))
                    for item in items:
                        if isinstance(item, dict):
                            categories.append(item.get("value", item.get("id", "")))
                        elif isinstance(item, str):
                            categories.append(item)
                except (json.JSONDecodeError, TypeError):
                    categories = [s.strip() for s in industries_raw.split(",") if s.strip()]

            # Parse social media for linkedin
            linkedin_url = ""
            social_raw = row.get("social_media_links", "")
            if "linkedin" in social_raw.lower():
                try:
                    links = json.loads(social_raw.replace("\"\"", "\""))
                    for link in links:
                        if isinstance(link, str) and "linkedin" in link.lower():
                            linkedin_url = link
                except (json.JSONDecodeError, TypeError):
                    pass

            # Parse tech stack from builtwith
            tech_stack = []
            builtwith_raw = row.get("builtwith_tech", "")
            if builtwith_raw:
                try:
                    tech_items = json.loads(builtwith_raw.replace("\"\"", "\""))
                    for item in tech_items:
                        if isinstance(item, dict):
                            tech_stack.append(item.get("value", item.get("name", "")))
                        elif isinstance(item, str):
                            tech_stack.append(item)
                except (json.JSONDecodeError, TypeError):
                    tech_stack = [s.strip() for s in builtwith_raw.split(",") if s.strip()]

            # Parse funding
            total_funding = None
            funding_raw = row.get("total_funding_amount", row.get("total_funding", ""))
            if funding_raw:
                try:
                    total_funding = float(str(funding_raw).replace(",", "").replace("$", ""))
                except (ValueError, TypeError):
                    pass

            last_funding_type = row.get("last_funding_type", row.get("funding_type", ""))
            last_funding_date = row.get("last_funding_date", row.get("last_equity_funding_date", ""))

            num_rounds = 0
            nr_raw = row.get("num_funding_rounds", "0")
            try:
                num_rounds = int(nr_raw) if nr_raw else 0
            except (ValueError, TypeError):
                pass

            # Extract domain from website
            website = row.get("website", "")
            domain = ""
            if website:
                domain = website.replace("https://", "").replace("http://", "").replace("www.", "").strip("/")

            return CrunchbaseCompany(
                name=name,
                domain=domain,
                short_description=row.get("about", ""),
                long_description=row.get("full_description", ""),
                industry=categories[0] if categories else "",
                industry_groups=categories,
                headquarters_location=row.get("region", ""),
                country=row.get("country_code", ""),
                employee_count=row.get("num_employees", ""),
                founded_on=row.get("founded_date", ""),
                total_funding_usd=total_funding,
                last_funding_type=last_funding_type,
                last_funding_date=last_funding_date,
                num_funding_rounds=num_rounds,
                categories=categories,
                status=row.get("operating_status", ""),
                linkedin_url=linkedin_url,
                cb_url=row.get("url", ""),
                tech_stack=tech_stack,
                raw=dict(row),
            )
        except Exception as e:
            return None

    def _parse_json_record(self, record: dict) -> Optional[CrunchbaseCompany]:
        try:
            name = record.get("name", record.get("company_name", "")).strip()
            if not name:
                return None

            categories = []
            for c in record.get("categories", []):
                if isinstance(c, str):
                    categories.append(c)
                elif isinstance(c, dict):
                    categories.append(c.get("name", c.get("value", "")))

            return CrunchbaseCompany(
                name=name,
                domain=record.get("domain", record.get("homepage_url", "")),
                short_description=record.get("short_description", ""),
                long_description=record.get("description", ""),
                industry=categories[0] if categories else "",
                industry_groups=categories,
                country=record.get("country_code", ""),
                employee_count=str(record.get("num_employees_enum", "")),
                founded_on=record.get("founded_on", ""),
                total_funding_usd=record.get("total_funding_usd"),
                last_funding_type=record.get("last_funding_type", ""),
                last_funding_date=record.get("last_funding_at", ""),
                num_funding_rounds=record.get("num_funding_rounds", 0),
                categories=categories,
                status=record.get("status", ""),
                cb_url=record.get("cb_url", ""),
                raw=record,
            )
        except Exception:
            return None

    def _build_indices(self):
        self._by_name = {}
        self._by_domain = {}
        for c in self._companies:
            if c.name:
                self._by_name[c.name.lower()] = c
            if c.domain:
                self._by_domain[c.domain.lower()] = c

    def get_by_name(self, name: str) -> Optional[CrunchbaseCompany]:
        return self._by_name.get(name.lower())

    def get_by_domain(self, domain: str) -> Optional[CrunchbaseCompany]:
        return self._by_domain.get(domain.lower())

    @property
    def companies(self) -> list[CrunchbaseCompany]:
        return self._companies

    def get_recently_funded(self, days: int = 180) -> list[CrunchbaseCompany]:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return [c for c in self._companies
                if c.last_funding_date and c.last_funding_date >= cutoff]

    def get_by_sector(self, sector: str) -> list[CrunchbaseCompany]:
        sector_lower = sector.lower()
        return [
            c for c in self._companies
            if (c.industry and sector_lower in c.industry.lower())
            or any(sector_lower in cat.lower() for cat in c.categories)
        ]

    def get_employee_count_estimate(self, company: CrunchbaseCompany) -> Optional[int]:
        range_map = {
            "1-10": 5, "11-50": 30, "51-100": 75, "101-250": 175,
            "251-500": 375, "501-1000": 750, "1001-5000": 3000,
            "5001-10000": 7500, "10001+": 15000
        }
        if company.employee_count:
            for key, val in range_map.items():
                if key in company.employee_count:
                    return val
        return None
