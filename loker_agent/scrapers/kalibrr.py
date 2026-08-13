from __future__ import annotations

from typing import List

from ..config import Config
from ..models import Job
from ..utils import Session
from .base import BaseScraper


class KalibrrScraper(BaseScraper):
    """Search Kalibrr jobs via the jobseeker HTTP API (cookie + KB-CSRF optional for search)."""

    platform = "kalibrr"
    BASE = "https://jobseeker.kalibrr.com/kjs/job_board/search"

    def __init__(self, config: Config):
        super().__init__(config.max_per_platform)
        self.config = config
        self.session = Session()

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Host": "jobseeker.kalibrr.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/118.0",
            "KB-CSRF": self.config.kalibrr_csrf,
            "Cookie": self.config.kalibrr_cookie,
        }

    def search(self, keyword: str, location: str) -> List[Job]:
        params = {
            "limit": self.max_results,
            "offset": 0,
            "text": keyword,
            "location": location,
            "responds_fast": "false",
        }
        resp = self.session.get(self.BASE, params=params, headers=self._headers())
        if resp.status_code != 200:
            raise RuntimeError(f"Kalibrr search failed: HTTP {resp.status_code} {resp.text[:300]}")

        data = resp.json()
        jobs = data.get("jobs", []) if isinstance(data, dict) else []
        out: List[Job] = []
        for item in jobs:
            jid = str(item.get("id") or "")
            if not jid:
                continue
            company = item.get("company") or {}
            location = _fmt_location(item.get("google_location") or item.get("location") or {})
            salary = item.get("salary_shown") or item.get("base_salary") or ""
            url = (
                item.get("apply_redirect_url")
                or item.get("url")
                or (f"https://www.kalibrr.com/jobs/{item.get('slug')}" if item.get("slug") else "")
            )
            out.append(
                Job(
                    platform=self.platform,
                    job_id=jid,
                    title=item.get("name") or item.get("title") or "",
                    company=company.get("name") or "" if isinstance(company, dict) else str(company),
                    location=str(location or ""),
                    salary=str(salary or ""),
                    url=url or "",
                    description=str(item.get("description") or "")[:4000],
                    employment_type=str(item.get("tenure") or item.get("work_experience") or ""),
                    published=str(item.get("created_at") or item.get("activation_date") or ""),
                    raw=item,
                )
            )
        return out


def _fmt_location(loc) -> str:
    """Kalibrr returns google_location as {address_components: {city, region, country}}."""
    if isinstance(loc, str):
        return loc
    if isinstance(loc, dict):
        comp = loc.get("address_components") or {}
        if isinstance(comp, dict):
            parts = [comp.get("city"), comp.get("region"), comp.get("country")]
            return ", ".join(str(x) for x in parts if x)
        return str(comp)
    return str(loc or "")
