from __future__ import annotations

import os
import re
from typing import List, Optional

from .models import ApplicantProfile
from .matchers.keywords import KEYWORDS

# Expand with role-specific buzzwords
EXTRA_SKILL_WORDS = [
    "docker", "kubernetes", "terraform", "airflow", "spark", "kafka", "git",
    "pandas", "numpy", "pyspark", "sql", "python", "javascript", "typescript",
    "react", "node.js", "golang", "java", "excel", "power bi", "tableau",
    "machine learning", "deep learning", "llm", "nlp", "rag", "langchain",
    "playwright", "selenium", "pytest", "ci/cd", "linux", "bash", "aws", "gcp",
    "azure", "microservices", "rest api", "graphql", "postgresql", "mysql",
    "mongodb", "redis", "elasticsearch", "etl", "dbt", "looker", "metabase",
    # IT support / help desk / networking
    "windows", "windows server", "active directory", "group policy", "microsoft 365",
    "office 365", "helpdesk", "help desk", "it support", "troubleshooting",
    "hardware", "incident management", "ticketing", "remote support", "rdp",
    "teamviewer", "anydesk", "cisco", "ccna", "mikrotik", "routeros", "router",
    "switch", "lan/wan", "tcp/ip", "dns", "dhcp", "vpn", "firewall", "network",
    "networking", "server monitoring", "server administration", "printer",
]

# Short skills that are fine to match as substrings; everything else under 3 chars is noise.
SHORT_OK = {"sql", "git", "aws", "nlp", "rag", "dbt", "etl", "qa", "ai"}


class CVProfileParser:
    """Extract a matching profile from a plain-text CV or a YAML/JSON profile file."""

    def __init__(self, keywords: Optional[List[str]] = None):
        self.keywords = [k.lower() for k in (keywords or (KEYWORDS + EXTRA_SKILL_WORDS))]
        self.keywords = sorted(set(self.keywords), key=len, reverse=True)

    def parse_file(self, path: str) -> ApplicantProfile:
        ext = os.path.splitext(path)[1].lower()
        if ext in (".pdf",):
            return self._parse_pdf(path)
        if ext in (".txt", ".md", ".yaml", ".yml", ".json"):
            return self._parse_text(path)
        if ext in (".docx", ".doc"):
            return self._parse_docx(path)
        raise ValueError(f"Unsupported CV file type: {ext}")

    def _parse_pdf(self, path: str) -> ApplicantProfile:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("Install pypdf for PDF CV parsing: pip install pypdf") from exc
        reader = PdfReader(path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return self.parse_text(text, source=path)

    def _parse_docx(self, path: str) -> ApplicantProfile:
        try:
            import docx  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Install python-docx for .docx CV parsing") from exc
        doc = docx.Document(path)
        text = "\n".join(p.text for p in doc.paragraphs)
        return self.parse_text(text, source=path)

    def _parse_text(self, path: str) -> ApplicantProfile:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return self.parse_text(fh.read(), source=path)

    def parse_text(self, text: str, source: Optional[str] = None) -> ApplicantProfile:
        lower = text.lower()
        found = []
        for kw in self.keywords:
            if len(kw) < 3 and kw not in SHORT_OK:
                continue  # skip high-noise short tokens like "go"
            pattern = re.escape(kw).replace(r"\ ", r"\s*")
            if re.search(pattern, lower):
                found.append(kw)
        found = sorted(set(found))

        email = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
        phone = re.search(r"(?:\+62|62|0)[\s-]?8[\d\s-]{8,13}", text)

        # years of experience heuristic
        years = None
        m = re.search(r"(\d+)\s*\+?\s*(?:tahun|years?)\s*(?:pengalaman|of experience)", lower)
        if m:
            years = int(m.group(1))

        summary = ""
        for line in text.splitlines():
            if re.search(r"ringkasan|summary|profil singkat", line, re.I):
                summary = line.strip()
                break

        return ApplicantProfile(
            name=_extract_name(text),
            email=email.group(0) if email else "",
            phone=phone.group(0).strip() if phone else "",
            skills=found,
            job_titles=_extract_job_titles(text),
            years_experience=years or 0,
            summary=summary,
            resume_path=source,
        )

    def from_structured(self, data: dict) -> ApplicantProfile:
        skills = list(data.get("skills", []))
        if data.get("extra_skills"):
            skills = list(set(skills) | set(data["extra_skills"]))
        return ApplicantProfile(
            name=data.get("name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            skills=skills,
            job_titles=data.get("job_titles", []),
            years_experience=int(data.get("years_experience", 0) or 0),
            education=data.get("education", ""),
            summary=data.get("summary", ""),
            answers=data.get("answers", {}),
        )


def _extract_name(text: str) -> str:
    for line in text.splitlines()[:20]:
        line = line.strip()
        if line and len(line) < 60 and not any(ch.isdigit() for ch in line):
            return line
    return ""


_ROLE_MARKERS = (
    "support", "engineer", "developer", "analyst", "admin", "specialist",
    "consultant", "technician", "helpdesk", "help desk", "network", "manager",
)


def _extract_job_titles(text: str, max_titles: int = 6) -> List[str]:
    """Best-effort role titles from the CV header (pipe-separated or line-based)."""
    titles: List[str] = []
    for line in text.splitlines()[:12]:
        line = line.strip()
        if re.search(r"summary|ringkasan|pengalaman|experience|pendidikan|education", line, re.I):
            break
        for part in line.split("|"):
            part = part.strip()
            if not part or len(part) > 60:
                continue
            if re.search(r"[@+\d]|\.(com|id|my|net|io)\b", part, re.I):
                continue  # contact/link, not a role
            if any(mk in part.lower() for mk in _ROLE_MARKERS):
                titles.append(part)
            if len(titles) >= max_titles:
                return titles
    return titles
