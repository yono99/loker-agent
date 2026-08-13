from __future__ import annotations

import json
import re
from typing import List, Optional

from ..models import ApplicantProfile, Job, MatchResult, MatchScores
from .keywords import KEYWORDS


def _tokenize(text: str) -> str:
    return re.sub(r"[^a-z0-9+#.\s]", " ", (text or "").lower())


class KeywordMatcher:
    """Offline, deterministic scorer. No external API needed."""

    name = "keyword"

    def __init__(self, keywords: Optional[List[str]] = None):
        self.keywords = [k.strip().lower() for k in (keywords or KEYWORDS) if k.strip()]

    def match(self, job: Job, profile: ApplicantProfile) -> MatchResult:
        title = _tokenize(job.title)
        desc = _tokenize(job.description)
        cv_skills = {s.strip().lower() for s in profile.skills if s.strip()}
        if not cv_skills:
            result = MatchScores(overall=0.0)
            return MatchResult(job=job, scores=result, verdict="skip", reason="No skills in profile.")

        # 1) Fraction of CV skills found anywhere in the description.
        hits_desc = [k for k in cv_skills if k in desc]
        keyword_cv = (len(hits_desc) / len(cv_skills)) * 100

        # 2) Bonus: CV skills present in the job title.
        hits_title = [k for k in cv_skills if k in title]
        keyword_title = (len(hits_title) / len(cv_skills)) * 100

        # 3) Heuristic bonus when an explicit "required skills" section matches.
        required_skills = 0.0
        for m in re.finditer(r"required\s*skills?|persyaratan|kualifikasi", desc):
            window = desc[m.start() : m.start() + 400]
            has = sum(1 for s in cv_skills if s in window)
            required_skills = max(required_skills, has / len(cv_skills) * 100)

        # 4) Role-title bonus when a target role keyword appears in the title.
        role_bonus = 0.0
        for role in profile.job_titles:
            if role and _tokenize(role) in title:
                role_bonus = max(role_bonus, 20)

        overlap = sorted(set(hits_title) | set(hits_desc))
        score = (keyword_cv * 0.55) + (keyword_title * 0.10) + (required_skills * 0.15) + role_bonus
        score = min(100.0, score)

        result = MatchScores(
            overall=score,
            keyword_cv=keyword_cv,
            keyword_title=keyword_title,
            required_skills=required_skills,
            overlap=overlap,
        )
        return MatchResult(job=job, scores=result, verdict=_verdict(score), reason=_reason(result))


class LLMMatcher:
    """Optional LLM scoring via OpenAI-compatible chat completions API.

    Requires XAI_API_KEY (env) or `credentials.xai_api_key` in config.json.
    Base URL can be set via LLM_BASE_URL env or `credentials.llm_base_url` in config.
    """

    name = "llm"

    def __init__(self, api_key: str, model: str = "omniroute", base_url: str = "https://api.x.ai/v1"):
        from ..utils import Session

        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.session = Session()

    def match(self, job: Job, profile: ApplicantProfile) -> MatchResult:
        prompt = (
            "You match a candidate profile against an Indonesian job posting. "
            "Return ONLY JSON: "
            '{"score": 0-100(float), "overlap": [skills], "reason": "one short sentence"}.\n\n'
            f"JOB TITLE: {job.title}\nCOMPANY: {job.company}\n"
            f"SKILLS SET: {', '.join(profile.skills)}\n"
            f"JOB DESC: {job.description[:1800]}\n"
            f"LOCATION: {job.location}"
        )
        body = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": "You return strict JSON only."},
                {"role": "user", "content": prompt},
            ],
        }
        resp = self.session.post(
            f"{self.base_url}/chat/completions",
            json=body,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        parsed = {}
        try:
            data = resp.json()["choices"][0]["message"]["content"]
            m = re.search(r"\{.*\}", data, re.S)
            parsed = json.loads(m.group(0)) if m else {}
        except Exception:
            parsed = {}
        score = min(100.0, max(0.0, float(parsed.get("score", 0))))
        overlap = [str(x) for x in parsed.get("overlap", [])][:15]
        reason = str(parsed.get("reason", "") or "")
        result = MatchScores(overall=score, overlap=overlap)
        return MatchResult(job=job, scores=result, verdict=_verdict(score), reason=reason)


class MatcherFactory:
    @staticmethod
    def build(api_key: str = "", base_url: str = ""):
        if api_key:
            return LLMMatcher(api_key, base_url=base_url)
        return KeywordMatcher()


def _verdict(score: float) -> str:
    if score >= 70:
        return "apply"
    if score >= 50:
        return "consider"
    return "skip"


def _reason(s: MatchScores) -> str:
    if not s.overlap:
        return "No skill overlap found."
    return f"Overlap skills: {', '.join(s.overlap[:8])}"
