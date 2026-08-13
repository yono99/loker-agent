from __future__ import annotations

import random
import re
import time
from typing import Optional

import requests


def normalize_text(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9+#.\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_english(text: str) -> bool:
    t = (text or "").strip()
    return bool(t) and (sum(1 for ch in t if ch.isascii()) / len(t)) > 0.9


def find_years(text: str) -> Optional[int]:
    """Best-effort extraction of years-of-experience from a job description."""
    patterns = [
        r"(\d+)\s*\+?\s*(?:tahun|years?)\s*(?:pengalaman|of experience)?",
        r"(?:pengalaman|experience)\s*(?:kerja\s*)?(?:min\.?\s*)?(\d+)\s*(?:tahun|years?)",
        r"(\d+)\s*[+\-]\s*(\d+)\s*(?:tahun|years?)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            nums = [int(x) for x in m.groups() if x]
            return max(nums) if nums else None
    return None


def sleep_random(lo: int, hi: int) -> None:
    time.sleep(random.uniform(lo, hi))


class Session:
    """requests.Session with retries + optional proxy tolerance."""

    def __init__(self, timeout: int = 25, retries: int = 3):
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                ),
                "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
            }
        )

    def get(self, url: str, **kwargs) -> requests.Response:
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        return self._request("POST", url, **kwargs)

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        last = None
        for attempt in range(self.retries + 1):
            try:
                resp = self.session.request(method, url, **kwargs)
                if resp.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError(f"HTTP {resp.status_code}")
                return resp
            except requests.RequestException as exc:
                last = exc
                time.sleep(2 ** attempt + random.random())
        raise last  # type: ignore[misc]
