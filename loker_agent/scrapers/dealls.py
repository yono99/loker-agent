from __future__ import annotations

from typing import Dict, List

from ..config import Config
from ..models import Job
from ..utils import Session
from .base import BaseScraper


class DeallsScraper(BaseScraper):
    """Search Dealls jobs via the public sejutacita REST API.

    Dealls (dealls.com) is an Indonesian career platform. Its web app talks to
    api.sejutacita.id, which exposes a public job-search endpoint that requires
    no authentication or cookies. The search response does not include a full
    description; job detail (responsibilities/requirements, used by the CV
    matcher) is available via get_job_details().
    """

    platform = "dealls"
    BASE = "https://api.sejutacita.id"
    SEARCH_ENDPOINT = "/v1/explore-job/job"
    DETAIL_ENDPOINT = "/v1/job-portal/job/slug/{slug}"
    APP_NAME = "Deall-Talent-Web"
    APP_VERSION = "2.49.65"

    _EMP_TYPES = {
        "fullTime": "Full-time",
        "partTime": "Part-time",
        "contract": "Contract",
        "internship": "Internship",
        "freelance": "Freelance",
    }

    def __init__(self, config: Config):
        super().__init__(config.max_per_platform)
        self.config = config
        self.session = Session()

    def _headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://dealls.com",
            "Referer": "https://dealls.com/",
            "X-Client-App-Name": self.APP_NAME,
            "X-Client-App-Version": self.APP_VERSION,
        }

    def _search_params(self, keyword: str, location: str) -> Dict[str, str]:
        params: Dict[str, str] = {
            "page": "1",
            "sortParam": "mostRelevant",
            "sortBy": "asc",
            "boostTheBoostedJob": "true",
            "published": "true",
            "limit": str(self.max_results),
            "status": "active",
            "search": keyword,
        }
        if location:
            params["city"] = location
        return params

    def search(self, keyword: str, location: str) -> List[Job]:
        resp = self.session.get(
            f"{self.BASE}{self.SEARCH_ENDPOINT}",
            params=self._search_params(keyword, location),
            headers=self._headers(),
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Dealls search failed: HTTP {resp.status_code} {resp.text[:300]}")

        data = resp.json()
        docs = (data.get("data") or {}).get("docs") or []
        out: List[Job] = []
        for item in docs:
            jid = str(item.get("id") or "")
            if not jid:
                continue
            job = self._to_job(item, location)
            if job is not None:
                out.append(job)
        return out[: self.max_results]

    def get_job_details(self, slug: str) -> dict:
        """Fetch full job detail by slug (responsibilities, requirements, skills).

        Note: this endpoint is rate-limited; call it selectively, not per job.
        """
        resp = self.session.get(
            f"{self.BASE}{self.DETAIL_ENDPOINT.format(slug=slug)}",
            headers=self._headers(),
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Dealls detail failed: HTTP {resp.status_code} {resp.text[:300]}")
        return resp.json().get("data") or {}

    def get_job_url(self, item: dict) -> str:
        slug = item.get("slug") or ""
        company_slug = (item.get("company") or {}).get("slug") if isinstance(item.get("company"), dict) else ""
        if company_slug:
            return f"https://dealls.com/loker/{slug}~{company_slug}"
        return f"https://dealls.com/loker/{slug}"

    def _to_job(self, item: dict, location: str) -> Job | None:
        jid = str(item.get("id") or "")
        if not jid:
            return None

        salary = _fmt_salary(item)
        employment_type = _fmt_employment(item.get("employmentTypes") or [])
        desc = (
            " ".join(
                str(s.get("name"))
                for s in (item.get("skills") or [])
                if isinstance(s, dict) and s.get("name")
            )
        )
        desc = " ".join([str(item.get("role") or ""), str(item.get("jobRoleCategorySlug") or ""), desc]).strip()

        company = item.get("company") or {}
        company_name = company.get("name") if isinstance(company, dict) else str(company or "")

        return Job(
            platform=self.platform,
            job_id=jid,
            title=item.get("role") or item.get("title") or "",
            company=company_name,
            location=_fmt_location(item, location),
            salary=salary,
            url=self.get_job_url(item),
            description=desc[:4000],
            employment_type=employment_type,
            published=str(item.get("publishedAt") or ""),
            raw=item,
        )


def _fmt_location(item: dict, fallback: str) -> str:
    city = item.get("city") or {}
    country = item.get("country") or {}
    parts = []
    if isinstance(city, dict):
        parts.append(str(city.get("name") or ""))
    elif city:
        parts.append(str(city))
    if isinstance(country, dict):
        parts.append(str(country.get("name") or ""))
    elif country:
        parts.append(str(country))
    joined = ", ".join(p for p in parts if p)
    return joined or fallback


def _fmt_salary(item: dict) -> str:
    rng = item.get("salaryRange")
    if isinstance(rng, dict) and rng:
        parts = []
        for key in ("min", "max"):
            if rng.get(key):
                parts.append(_format_rupiah(rng.get(key)))
        if parts:
            return " - ".join(parts)
    if item.get("salaryType") == "unpaid":
        return "Unpaid"
    return ""


def _format_rupiah(value) -> str:
    try:
        n = int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return str(value)
    return f"Rp{n:,.0f}".replace(",", ".")


def _fmt_employment(types: list) -> str:
    mapped = [DeallsScraper._EMP_TYPES.get(t, t) for t in types]
    return ", ".join(mapped)