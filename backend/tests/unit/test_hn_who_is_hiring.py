"""Unit tests for HNWhoIsHiringSource. Mocks the httpx client -- no live network -- using
response shapes confirmed against the real HN Algolia API during development."""

from unittest.mock import MagicMock

from app.schemas.discovery import DiscoveryQuery
from app.services.discovery.hn_who_is_hiring import HNWhoIsHiringSource


def _make_client(search_json: dict, item_json: dict) -> MagicMock:
    client = MagicMock()

    def get(url: str, params: dict | None = None, **kwargs: object) -> MagicMock:
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.json.return_value = search_json if "search_by_date" in url else item_json
        return response

    client.get.side_effect = get
    return client


def test_finds_who_is_hiring_thread_and_skips_companion_thread() -> None:
    search_json = {
        "hits": [
            {"objectID": "111", "title": "Ask HN: Who wants to be hired? (August 2026)"},
            {"objectID": "222", "title": "Ask HN: Who is hiring? (August 2026)"},
        ]
    }
    client = _make_client(search_json, {"children": []})
    jobs = HNWhoIsHiringSource(client=client).search_jobs(DiscoveryQuery())
    assert jobs == []
    called_urls = [call.args[0] for call in client.get.call_args_list]
    assert any("222" in url for url in called_urls)
    assert not any("111" in url for url in called_urls)


def test_parses_well_formed_comment() -> None:
    search_json = {"hits": [{"objectID": "222", "title": "Ask HN: Who is hiring? (August 2026)"}]}
    item_json = {
        "children": [
            {
                "id": 999,
                "created_at": "2026-08-03T15:00:59.000Z",
                "text": (
                    "Snout https://snout.com/ | Backend Engineer | Remote US | Full Time"
                    "<p>We build things."
                ),
            }
        ]
    }
    client = _make_client(search_json, item_json)
    jobs = HNWhoIsHiringSource(client=client).search_jobs(DiscoveryQuery())

    assert len(jobs) == 1
    job = jobs[0]
    assert job.company.name == "Snout"
    assert job.company.website == "https://snout.com"
    assert job.title == "Backend Engineer"
    assert job.location == "Remote US"
    assert job.job_url == "https://news.ycombinator.com/item?id=999"
    assert job.posted_date is not None
    assert "We build things" in (job.description or "")


def test_finds_company_url_in_free_text_body_when_header_has_none() -> None:
    """Found live: a real posting with no URL in its structured header line but a real
    "read more: https://ojin.ai" in the body used to leave website=None, forcing a
    search-engine guess at research time that got the wrong company entirely."""
    search_json = {"hits": [{"objectID": "222", "title": "Ask HN: Who is hiring? (August 2026)"}]}
    item_json = {
        "children": [
            {
                "id": 999,
                "created_at": "2026-08-03T15:00:59.000Z",
                "text": (
                    "Ojin | Product Engineer | Remote<p>We build AI infrastructure."
                    "<p>Apply or read more about us here: https://ojin.ai"
                ),
            }
        ]
    }
    client = _make_client(search_json, item_json)
    jobs = HNWhoIsHiringSource(client=client).search_jobs(DiscoveryQuery())

    assert len(jobs) == 1
    assert jobs[0].company.website == "https://ojin.ai"


def test_body_url_is_normalized_to_root_domain() -> None:
    """Found live: a company's own domain still showed up as a job-posting-specific deep link
    ("lokker.com/careers/openings/senior-backend-engineer-...") that 404s once that individual
    posting is taken down -- the root domain reliably still resolves."""
    search_json = {"hits": [{"objectID": "222", "title": "Ask HN: Who is hiring? (August 2026)"}]}
    item_json = {
        "children": [
            {
                "id": 999,
                "created_at": "2026-08-03T15:00:59.000Z",
                "text": (
                    "Acme | Backend Engineer | Remote<p>We build things."
                    "<p>Apply: https://acme.example/careers/openings/backend-engineer-123?ref=hn"
                ),
            }
        ]
    }
    client = _make_client(search_json, item_json)
    jobs = HNWhoIsHiringSource(client=client).search_jobs(DiscoveryQuery())

    assert len(jobs) == 1
    assert jobs[0].company.website == "https://acme.example"


def test_ignores_ats_and_social_urls_in_free_text_body() -> None:
    search_json = {"hits": [{"objectID": "222", "title": "Ask HN: Who is hiring? (August 2026)"}]}
    item_json = {
        "children": [
            {
                "id": 999,
                "created_at": "2026-08-03T15:00:59.000Z",
                "text": (
                    "Acme | Backend Engineer | Remote<p>We build things."
                    "<p>Apply here: https://jobs.lever.co/acme/abc123"
                    "<p>Follow us: https://twitter.com/acmehq"
                    "<p>Learn more: https://acme.example"
                ),
            }
        ]
    }
    client = _make_client(search_json, item_json)
    jobs = HNWhoIsHiringSource(client=client).search_jobs(DiscoveryQuery())

    assert len(jobs) == 1
    assert jobs[0].company.website == "https://acme.example"


def test_ignores_url_shorteners_in_free_text_body() -> None:
    """Found live: a real posting whose actual application link was correctly excluded
    (ashbyhq.com), but whose "or reach out directly: https://bit.ly/juliaLN" line wasn't --
    a shortener can point anywhere, including a person's LinkedIn, never trustworthy as "the
    company site" from the URL text alone."""
    search_json = {"hits": [{"objectID": "222", "title": "Ask HN: Who is hiring? (August 2026)"}]}
    item_json = {
        "children": [
            {
                "id": 999,
                "created_at": "2026-08-03T15:00:59.000Z",
                "text": (
                    "Acme | Backend Engineer | Remote<p>We build things."
                    "<p>Apply: https://jobs.ashbyhq.com/acme"
                    "<p>Or reach out directly: https://bit.ly/janeLN"
                ),
            }
        ]
    }
    client = _make_client(search_json, item_json)
    jobs = HNWhoIsHiringSource(client=client).search_jobs(DiscoveryQuery())

    assert len(jobs) == 1
    assert jobs[0].company.website is None


def test_falls_back_to_a_hiring_email_domain_when_no_url_anywhere() -> None:
    """Found live: a real posting with no URL in the header or body at all, only an "apply:
    hiring@interviewresources.app" contact line -- the search fallback guessed a US federal
    government interview-prep portal instead of the actual startup."""
    search_json = {"hits": [{"objectID": "222", "title": "Ask HN: Who is hiring? (August 2026)"}]}
    item_json = {
        "children": [
            {
                "id": 999,
                "created_at": "2026-08-03T15:00:59.000Z",
                "text": (
                    "Acme | Backend Engineer | Remote<p>We build things."
                    "<p>Apply: hiring@acme.example with your resume."
                ),
            }
        ]
    }
    client = _make_client(search_json, item_json)
    jobs = HNWhoIsHiringSource(client=client).search_jobs(DiscoveryQuery())

    assert len(jobs) == 1
    assert jobs[0].company.website == "https://acme.example"


def test_ignores_personal_email_domains() -> None:
    search_json = {"hits": [{"objectID": "222", "title": "Ask HN: Who is hiring? (August 2026)"}]}
    item_json = {
        "children": [
            {
                "id": 999,
                "created_at": "2026-08-03T15:00:59.000Z",
                "text": "Acme | Backend Engineer | Remote<p>Reach out: jane@gmail.com",
            }
        ]
    }
    client = _make_client(search_json, item_json)
    jobs = HNWhoIsHiringSource(client=client).search_jobs(DiscoveryQuery())

    assert len(jobs) == 1
    assert jobs[0].company.website is None


def test_skips_comment_with_no_pipe_delimited_fields() -> None:
    search_json = {"hits": [{"objectID": "222", "title": "Ask HN: Who is hiring? (August 2026)"}]}
    item_json = {
        "children": [
            {
                "id": 1,
                "created_at": "2026-08-03T15:00:59.000Z",
                "text": "Just a general comment with no pipes.",
            }
        ]
    }
    client = _make_client(search_json, item_json)
    jobs = HNWhoIsHiringSource(client=client).search_jobs(DiscoveryQuery())
    assert jobs == []


def test_role_filter_excludes_non_matching_postings() -> None:
    search_json = {"hits": [{"objectID": "222", "title": "Ask HN: Who is hiring? (August 2026)"}]}
    item_json = {
        "children": [
            {
                "id": 1,
                "created_at": "2026-08-03T15:00:59.000Z",
                "text": "Foo | Sales Manager | NYC<p>desc",
            },
            {
                "id": 2,
                "created_at": "2026-08-03T15:00:59.000Z",
                "text": "Bar | Backend Engineer | NYC<p>desc",
            },
        ]
    }
    client = _make_client(search_json, item_json)
    jobs = HNWhoIsHiringSource(client=client).search_jobs(DiscoveryQuery(role_filters=["backend"]))
    assert [j.company.name for j in jobs] == ["Bar"]


def test_returns_empty_when_no_who_is_hiring_thread_found() -> None:
    client = _make_client({"hits": []}, {"children": []})
    jobs = HNWhoIsHiringSource(client=client).search_jobs(DiscoveryQuery())
    assert jobs == []
