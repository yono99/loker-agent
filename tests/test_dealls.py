from loker_agent.config import Config
from loker_agent.scrapers.dealls import DeallsScraper

SAMPLE_JOB = {
    "id": "6a7d41c9830af30012fe457f",
    "slug": "backend-developer-golang-4",
    "role": "Backend Developer - Golang",
    "employmentTypes": ["contract"],
    "workplaceType": "onSite",
    "publishedAt": "2026-08-13T04:02:17.836Z",
    "status": "active",
    "salaryType": "paid",
    "salaryRange": {"min": 5000000, "max": 9000000},
    "country": {"name": "Indonesia", "id": 102},
    "city": {"name": "Jakarta Pusat", "id": 157},
    "company": {"name": "TOG Indonesia", "slug": "tog-indonesia"},
    "skills": [{"name": "Golang"}, {"name": "Docker"}],
    "jobRoleCategorySlug": "it-and-software-engineering",
}

SAMPLE_RESPONSE = {
    "data": {
        "docs": [SAMPLE_JOB],
        "totalDocs": 1,
        "totalPages": 1,
        "page": 1,
    }
}

DETAIL_RESPONSE = {
    "data": {
        "result": {
            "role": "Backend Developer - Golang",
            "responsibilities": "<ul><li>Build Go services</li></ul>",
            "requirements": "<p>Golang, Docker experience</p>",
            "candidatePreference": {"skills": [{"name": "Golang"}]},
        }
    }
}


class FakeResponse:
    def __init__(self, status_code, data, text=None):
        self.status_code = status_code
        self._data = data
        self.text = text if text is not None else ""

    def json(self):
        return self._data


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        if "/v1/job-portal/job/slug/" in url:
            return self.responses["detail"]
        return self.responses["search"]


def _config(tmp_path):
    cfg = Config.default(str(tmp_path))
    return cfg


def test_search_parses_job_and_builds_url(tmp_path):
    cfg = _config(tmp_path)
    scraper = DeallsScraper(cfg)
    scraper.session = FakeSession({"search": FakeResponse(200, SAMPLE_RESPONSE)})

    jobs = scraper.search("backend developer", "Jakarta")

    assert len(jobs) == 1
    job = jobs[0]
    assert job.platform == "dealls"
    assert job.job_id == SAMPLE_JOB["id"]
    assert job.title == "Backend Developer - Golang"
    assert job.company == "TOG Indonesia"
    assert job.location == "Jakarta Pusat, Indonesia"
    assert job.salary == "Rp5.000.000 - Rp9.000.000"
    assert job.employment_type == "Contract"
    assert job.url == "https://dealls.com/loker/backend-developer-golang-4~tog-indonesia"
    assert "Golang" in job.description
    assert "Docker" in job.description


def test_search_passes_city_param(tmp_path):
    cfg = _config(tmp_path)
    scraper = DeallsScraper(cfg)
    scraper.session = FakeSession({"search": FakeResponse(200, SAMPLE_RESPONSE)})

    scraper.search("engineer", "Bandung")

    called = scraper.session.calls[0]
    assert called["url"] == f"{scraper.BASE}{scraper.SEARCH_ENDPOINT}"
    assert called["params"]["search"] == "engineer"
    assert called["params"]["city"] == "Bandung"
    assert called["params"]["status"] == "active"
    assert called["params"]["limit"] == str(cfg.max_per_platform)
    assert "X-Client-App-Name" in called["headers"]
    assert called["headers"]["Origin"] == "https://dealls.com"


def test_get_job_details(tmp_path):
    cfg = _config(tmp_path)
    scraper = DeallsScraper(cfg)
    scraper.session = FakeSession(
        {"search": FakeResponse(200, SAMPLE_RESPONSE), "detail": FakeResponse(200, DETAIL_RESPONSE)}
    )

    resp = scraper.get_job_details("backend-developer-golang-4")

    assert "responsibilities" in resp["result"]
    assert "Golang" in resp["result"]["candidatePreference"]["skills"][0]["name"]


def test_search_skips_items_without_id(tmp_path):
    no_id_response = {
        "data": {"docs": [SAMPLE_JOB, {"role": "Ghost Job"}], "totalDocs": 2}
    }
    cfg = _config(tmp_path)
    scraper = DeallsScraper(cfg)
    scraper.session = FakeSession({"search": FakeResponse(200, no_id_response)})

    jobs = scraper.search("backend developer", "Jakarta")

    assert len(jobs) == 1


def test_search_raises_on_non_200(tmp_path):
    cfg = _config(tmp_path)
    scraper = DeallsScraper(cfg)
    scraper.session = FakeSession({"search": FakeResponse(500, {}, text="boom")})

    try:
        scraper.search("backend developer", "Jakarta")
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "HTTP 500" in str(exc)


def test_unpaid_salary_flagged():
    from loker_agent.scrapers.dealls import _fmt_salary

    assert _fmt_salary({"salaryType": "unpaid"}) == "Unpaid"
    assert _fmt_salary({"salaryType": "paid", "salaryRange": None}) == ""
    assert _fmt_salary({"salaryType": "paid", "salaryRange": {"min": 1000}}) == "Rp1.000"


def test_employment_type_mapping():
    from loker_agent.scrapers.dealls import _fmt_employment

    assert _fmt_employment(["fullTime", "internship"]) == "Full-time, Internship"
    assert _fmt_employment(["weird"]) == "weird"
    assert _fmt_employment([]) == ""