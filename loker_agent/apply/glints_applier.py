from __future__ import annotations

from typing import Dict, List, Optional

from ..config import Config
from ..models import Job
from ..utils import Session


class GlintsApplier:
    """Auto-apply on Glints using the same GraphQL API the mobile app uses.

    Reference: ReverserID/Glints-Bot-Apply (reverse-engineered from Android app v1.106.2).
    """

    name = "glints"

    BASE = "https://api.glints.com"
    CLIENT_ID = "5e5c566a-5ac6-44e3-b286-3246fbc97bfb"
    DEVICE_ID = "loker-agent-0001"
    APP_VERSION = "1.106.2"
    APP_PLATFORM = "ANDROID"
    OS_VERSION = "9"
    COUNTRY_CODE = "ID"
    LANGUAGE = "id"
    USER_AGENT = "Dart/3.9 (dart:io)"

    def __init__(self, config: Config):
        self.config = config
        self.session = Session()
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

    def _headers(self, json_body: bool = False) -> Dict[str, str]:
        h = {
            "user-agent": self.USER_AGENT,
            "accept-encoding": "gzip",
            "accept-language": self.LANGUAGE,
            "x-app-platform": self.APP_PLATFORM,
            "x-app-version": self.APP_VERSION,
            "x-os-version": self.OS_VERSION,
            "x-glints-country-code": self.COUNTRY_CODE,
            "x-device-id": self.DEVICE_ID,
        }
        if json_body:
            h["content-type"] = "application/json"
        if self.access_token:
            h["authorization"] = f"Bearer {self.access_token}"
        return h

    def login(self) -> None:
        username = self.config.glints_username
        password = self.config.glints_password
        if not username or not password:
            raise RuntimeError("Glints username/password not configured")
        resp = self.session.post(
            f"{self.BASE}/oauth2/token",
            json={
                "username": username,
                "password": password,
                "grant_type": "password",
                "client_id": self.CLIENT_ID,
                "sessionId": self.DEVICE_ID,
            },
            headers=self._headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token")

    def apply(self, job: Job) -> str:
        if not self.access_token:
            self.login()
        # one-tap apply requires a resume id from the profile; if not present,
        # we report a clear error instead of silently skipping.
        resume_id = self.config._data.get("glints_resume_id", "")
        if not resume_id:
            raise RuntimeError(
                "glints_resume_id missing. Set it in config.json (visible in Glints "
                "app when you view your resume) to enable one-tap apply."
            )
        body = {"data": {"resume": resume_id, "answers": []}, "source": "FOR_YOU"}
        resp = self.session.post(
            f"{self.BASE}/v2/api/v2/jobs/{job.job_id}/applications",
            json=body,
            headers=self._headers(json_body=True),
        )
        if resp.status_code != 201:
            raise RuntimeError(f"Glints apply failed: HTTP {resp.status_code} {resp.text[:300]}")
        return f"Glints application sent (resume {resume_id})"
