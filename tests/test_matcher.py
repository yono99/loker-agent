from loker_agent.models import ApplicantProfile, Job
from loker_agent.matchers.engine import KeywordMatcher


def test_skill_overlap_yields_apply():
    profile = ApplicantProfile(
        skills=["python", "sql", "airflow", "docker"],
        job_titles=["data engineer"],
    )
    job = Job(
        platform="kalibrr",
        job_id="1",
        title="Data Engineer",
        company="PT ABC",
        description="Need python, sql, airflow and docker experience to build data pipelines.",
    )
    res = KeywordMatcher().match(job, profile)
    assert res.verdict == "apply"
    assert res.scores.overall >= 70


def test_no_overlap_skips():
    profile = ApplicantProfile(skills=["java"])
    job = Job(platform="kalibrr", job_id="2", title="UI Designer", company="PT B",
              description="Design beautiful interfaces with figma.")
    res = KeywordMatcher().match(job, profile)
    assert res.verdict == "skip"
