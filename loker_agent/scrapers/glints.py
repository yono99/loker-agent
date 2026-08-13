from __future__ import annotations

import urllib.parse
from typing import Dict, List, Optional

from ..config import Config
from ..models import Job
from ..utils import Session
from .base import BaseScraper


class GlintsScraper(BaseScraper):
    """Search Glints jobs via the mobile GraphQL-ish REST endpoints.

    Requires a logged-in Glints session. Reference: ReverserID/Glints-Bot-Apply.
    """

    platform = "glints"
    BASE = "https://api.glints.com"
    CLIENT_ID = "5e5c566a-5ac6-44e3-b286-3246fbc97bfb"
    DEVICE_ID = "loker-agent-0001"
    APP_VERSION = "1.106.2"
    APP_PLATFORM = "ANDROID"
    COUNTRY_CODE = "ID"
    LANGUAGE = "id"
    USER_AGENT = "Dart/3.9 (dart:io)"

    def __init__(self, config: Config):
        super().__init__(config.max_per_platform)
        self.config = config
        self.session = Session()
        self.access_token: Optional[str] = None

    def _headers(self, json_body: bool = False) -> Dict[str, str]:
        h = {
            "user-agent": self.USER_AGENT,
            "accept-encoding": "gzip",
            "accept-language": self.LANGUAGE,
            "x-app-platform": self.APP_PLATFORM,
            "x-app-version": self.APP_VERSION,
            "x-glints-country-code": self.COUNTRY_CODE,
            "x-device-id": self.DEVICE_ID,
            "x-os-version": "9",
        }
        if json_body:
            h["content-type"] = "application/json"
        if self.access_token:
            h["authorization"] = f"Bearer {self.access_token}"
        return h

    def login(self) -> None:
        resp = self.session.post(
            f"{self.BASE}/oauth2/token",
            json={
                "username": self.config.glints_username,
                "password": self.config.glints_password,
                "grant_type": "password",
                "client_id": self.CLIENT_ID,
                "sessionId": self.DEVICE_ID,
            },
            headers=self._headers(),
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Glints login failed: HTTP {resp.status_code} {resp.text[:300]}")
        self.access_token = resp.json().get("access_token")

    def _ensure_auth(self) -> None:
        if not self.access_token:
            self.login()

    def search(self, keyword: str, location: str) -> List[Job]:
        self._ensure_auth()
        query = {
            "page": 1,
            "pageSize": self.max_results,
            "countryId": "ID",
            "keyword": keyword,
            "location": location,
            "sort": "recent",
        }
        url = f"{self.BASE}/v2/api/v3/jobs?{urllib.parse.urlencode(query)}"
        resp = self.session.get(url, headers=self._headers())
        if resp.status_code != 200:
            raise RuntimeError(f"Glints search failed: HTTP {resp.status_code} {resp.text[:300]}")

        data = resp.json()
        jobs = data.get("data", []) if isinstance(data, dict) else data
        out: List[Job] = []
        for item in jobs:
            jid = str(item.get("id") or item.get("slug") or "")
            if not jid:
                continue
            out.append(
                Job(
                    platform=self.platform,
                    job_id=jid,
                    title=item.get("title") or item.get("name") or "",
                    company=(item.get("company") or {}).get("name", "")
                    if isinstance(item.get("company"), dict)
                    else str(item.get("company") or ""),
                    location=_fmt_location(item),
                    salary=item.get("salary") or "",
                    url=item.get("url") or "",
                    description=(item.get("description") or "")[:4000],
                    employment_type=item.get("employmentType") or "",
                    published=str(item.get("publishedAt") or ""),
                    raw=item,
                )
            )
        return out[: self.max_results]


def _fmt_location(item: dict) -> str:
    loc = item.get("location") or {}
    if isinstance(loc, dict):
        parts = [loc.get("city"), loc.get("region"), loc.get("country")]
        return ", ".join(str(x) for x in parts if x)
    return str(loc)
