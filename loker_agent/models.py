from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class Job:
    """Normalized job listing independent of source platform."""

    platform: str  # 'glints' | 'kalibrr' | 'jobstreet' | 'kitalulus'
    job_id: str
    title: str
    company: str
    location: str = ""
    salary: str = ""
    url: str = ""
    description: str = ""
    employment_type: str = ""
    published: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)
    scraped_at: int = field(default_factory=_now_ms)

    def fingerprint(self) -> str:
        return f"{self.platform}|{self.job_id}".lower()


@dataclass
class ApplicantProfile:
    name: str = ""
    email: str = ""
    phone: str = ""
    location: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    job_titles: List[str] = field(default_factory=list)
    years_experience: int = 0
    education: str = ""
    summary: str = ""
    resume_path: Optional[str] = None
    answers: Dict[str, str] = field(default_factory=dict)

    @property
    def all_skill_text(self) -> str:
        return " ".join(self.skills).lower()


@dataclass
class MatchScores:
    overall: float = 0.0  # 0..100
    keyword_cv: float = 0.0
    keyword_title: float = 0.0
    required_skills: float = 0.0
    overlap: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "overall": round(self.overall, 1),
            "keyword_cv": round(self.keyword_cv, 1),
            "keyword_title": round(self.keyword_title, 1),
            "required_skills": round(self.required_skills, 1),
            "overlap": self.overlap,
        }


@dataclass
class MatchResult:
    job: Job
    scores: MatchScores
    verdict: str = ""  # apply | consider | skip
    reason: str = ""


@dataclass
class ApplicationRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    platform: str = ""
    external_job_id: str = ""
    job_title: str = ""
    company: str = ""
    status: str = "applied"  # applied | skipped | failed
    score: float = 0.0
    applied_at: int = field(default_factory=_now_ms)
    detail: str = ""
    created_at: int = field(default_factory=_now_ms)
