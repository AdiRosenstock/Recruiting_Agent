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
