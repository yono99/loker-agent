from loker_agent.config import Config
from loker_agent.matchers.engine import MatcherFactory
from loker_agent.models import ApplicantProfile, Job

cfg = Config.load("config.json")

# Profile dummy
profile = ApplicantProfile(
    name="Cahyo",
    skills=["python", "sql", "docker", "kubernetes", "linux"],
    job_titles=["data engineer", "backend developer"],
    years_experience=3,
    education="S1 Teknik Informatika",
    summary="Data engineer with ETL experience.",
    answers={}
)

# Job dummy dengan field yang benar
job = Job(
    platform="test",
    title="Data Engineer",
    company="PT Tech",
    location="Jakarta",
    description="Looking for a data engineer with Python, SQL, Docker, and Airflow experience.",
    url="https://example.com",
    posted_at="2026-08-12"
)

# Test LLM matcher
matcher = MatcherFactory.build(cfg.xai_api_key, cfg.llm_base_url)
result = matcher.match(job, profile)

print(f"Matcher: {matcher.name}")
print(f"Score: {result.scores.overall:.1f}")
print(f"Verdict: {result.verdict}")
print(f"Reason: {result.reason}")
print(f"Overlap: {result.scores.overlap}")
