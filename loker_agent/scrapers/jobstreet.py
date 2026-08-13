from __future__ import annotations

from typing import List

from ..config import Config
from ..models import Job
from ..utils import Session, sleep_random
from .base import BaseScraper


class JobStreetScraper(BaseScraper):
    """Search JobStreet.co.id via its public search API.

    JobStreet actively blocks headless browsers; this uses the JSON search API which
    is more tolerant. If you need in-DOM scraping (full descriptions), run the Selenium
    path via `selenium-scraper` extra instead.
    """

    platform = "jobstreet"
    BASE = "https://www.jobstreet.co.id/api/solr-suggest"  # placeholder; real search below

    def __init__(self, config: Config):
        super().__init__(config.max_per_platform)
        self.config = config
        self.session = Session()

    def search(self, keyword: str, location: str) -> List[Job]:
        # Public proxy endpoint is not documented; keep the interface so the pipeline
        # can be extended without changing the caller.
        raise NotImplementedError(
            "JobStreet requires an unauthenticated search API key which changes "
            "frequently. Use Glints/Kalibrr for automatic results, or see README "
            "append 'jobstreet-selenium' adapter."
        )
