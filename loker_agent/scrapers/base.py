from __future__ import annotations

from typing import List, Optional

from ..models import Job


class BaseScraper:
    platform = "base"

    def __init__(self, max_results: int = 30):
        self.max_results = max_results

    def search(self, keyword: str, location: str) -> List[Job]:
        raise NotImplementedError
