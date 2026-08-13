from __future__ import annotations

from ..config import Config
from ..models import Job
from ..utils import Session


class KalibrrApplier:
    """Apply to a Kalibrr job using the jobseeker API (cookie + KB-CSRF required)."""

    name = "kalibrr"
    BASE = "https://jobseeker.kalibrr.com"

    def __init__(self, config: Config):
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

    def apply(self, job: Job) -> str:
        url = f"{self.BASE}/api/candidate/job_applications/{job.job_id}"
        resp = self.session.post(
            url,
            headers=self._headers(),
            json={
                "referrer": None,
                "session_referrer": "www.kalibrr.com_organic_null_path",
                "app_source": "job-full-page",
            },
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Kalibrr apply failed: HTTP {resp.status_code} {resp.text[:300]}")
        return f"Kalibrr application sent for {job.job_id}"
