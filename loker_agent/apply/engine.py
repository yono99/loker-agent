from __future__ import annotations

import random
import time
from typing import List, Optional

from ..config import Config
from ..database import Database
from ..models import ApplicationRecord, Job, MatchResult


class ApplicationEngine:
    """Sequential auto-apply runner with per-platform appliers."""

    def __init__(self, config: Config, db: Database, appliers: List[object], dry_run: bool = True):
        self.config = config
        self.db = db
        self.appliers = {a.name: a for a in appliers}
        self.dry_run = dry_run
        self.applied: List[ApplicationRecord] = []
        self.failed: List[ApplicationRecord] = []

    def apply(self, results: List[MatchResult]) -> List[ApplicationRecord]:
        targets = [r for r in results if r.verdict == "apply"]
        if not targets:
            return []

        for r in targets:
            applier = self.appliers.get(r.job.platform)
            if not applier:
                continue
            if self.config.confirm_before_apply:
                ok = self._confirm(r)
                if not ok:
                    self._record(r, "skipped", "user skipped")
                    continue

            lo, hi = self.config.delay_seconds
            time.sleep(random.uniform(lo, hi))
            try:
                if self.dry_run:
                    detail = "DRY RUN - no real application sent"
                    rec = self._record(r, "applied", detail)
                else:
                    detail = applier.apply(r.job)
                    rec = self._record(r, "applied", detail)
                self.applied.append(rec)
            except Exception as exc:  # noqa: BLE001
                rec = self._record(r, "failed", f"{type(exc).__name__}: {exc}")
                self.failed.append(rec)

        return self.applied

    def _record(self, result: MatchResult, status: str, detail: str) -> ApplicationRecord:
        rec = ApplicationRecord(
            platform=result.job.platform,
            external_job_id=result.job.job_id,
            job_title=result.job.title,
            company=result.job.company,
            status=status,
            score=result.scores.overall,
            detail=detail,
        )
        self.db.insert_application(rec)
        return rec

    def _confirm(self, result: MatchResult) -> bool:
        try:
            ans = input(
                f"\nApply to [{result.job.platform}] {result.job.title} @ {result.job.company} "
                f"(score {result.scores.overall:.0f})? [y/N] "
            ).strip().lower()
            return ans in ("y", "yes")
        except EOFError:
            return False
