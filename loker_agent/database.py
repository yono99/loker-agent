from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional

from .models import ApplicationRecord, Job, MatchScores


class Database:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        cur = self.conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                fingerprint TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                job_id TEXT NOT NULL,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                salary TEXT,
                url TEXT,
                description TEXT,
                employment_type TEXT,
                published TEXT,
                raw TEXT,
                scraped_at INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_jobs_platform ON jobs(platform);

            CREATE TABLE IF NOT EXISTS matches (
                fingerprint TEXT PRIMARY KEY,
                overall REAL,
                keyword_cv REAL,
                keyword_title REAL,
                required_skills REAL,
                overlap TEXT,
                verdict TEXT,
                reason TEXT,
                matched_at INTEGER
            );

            CREATE TABLE IF NOT EXISTS applications (
                id TEXT PRIMARY KEY,
                platform TEXT,
                external_job_id TEXT,
                job_title TEXT,
                company TEXT,
                status TEXT,
                score REAL,
                applied_at INTEGER,
                detail TEXT,
                created_at INTEGER
            );
            """
        )
        self.conn.commit()

    # ---- jobs ----
    def upsert_job(self, job: Job) -> None:
        self.conn.execute(
            """
            INSERT INTO jobs (fingerprint, platform, job_id, title, company,
                              location, salary, url, description,
                              employment_type, published, raw, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(fingerprint) DO UPDATE SET
                title=excluded.title, company=excluded.company,
                location=excluded.location, salary=excluded.salary,
                url=excluded.url, description=excluded.description,
                employment_type=excluded.employment_type,
                published=excluded.published, raw=excluded.raw
            """,
            (
                job.fingerprint(),
                job.platform,
                job.job_id,
                job.title,
                job.company,
                job.location,
                job.salary,
                job.url,
                job.description,
                job.employment_type,
                job.published,
                json.dumps(job.raw, ensure_ascii=False),
                job.scraped_at,
            ),
        )
        self.conn.commit()

    def upsert_jobs(self, jobs: List[Job]) -> None:
        for job in jobs:
            self.upsert_job(job)

    def get_jobs(
        self, platform: Optional[str] = None, limit: int = 500
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM jobs"
        params: list = []
        if platform:
            sql += " WHERE platform = ?"
            params.append(platform)
        sql += " ORDER BY scraped_at DESC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    # ---- matches ----
    def save_match(self, fp: str, scores: MatchScores, verdict: str, reason: str) -> None:
        self.conn.execute(
            """
            INSERT INTO matches (fingerprint, overall, keyword_cv, keyword_title,
                                 required_skills, overlap, verdict, reason, matched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(fingerprint) DO UPDATE SET
                overall=excluded.overall, keyword_cv=excluded.keyword_cv,
                keyword_title=excluded.keyword_title,
                required_skills=excluded.required_skills,
                overlap=excluded.overlap, verdict=excluded.verdict,
                reason=excluded.reason, matched_at=excluded.matched_at
            """,
            (
                fp,
                scores.overall,
                scores.keyword_cv,
                scores.keyword_title,
                scores.required_skills,
                json.dumps(scores.overlap, ensure_ascii=False),
                verdict,
                reason,
                int(time.time() * 1000),
            ),
        )
        self.conn.commit()

    # ---- applications ----
    def insert_application(self, rec: ApplicationRecord) -> None:
        self.conn.execute(
            """
            INSERT INTO applications (id, platform, external_job_id, job_title,
                                      company, status, score, applied_at, detail, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rec.id,
                rec.platform,
                rec.external_job_id,
                rec.job_title,
                rec.company,
                rec.status,
                rec.score,
                rec.applied_at,
                rec.detail,
                rec.created_at,
            ),
        )
        self.conn.commit()

    def get_applications(self, limit: int = 200) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM applications ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self.conn.close()
