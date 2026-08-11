"""Unit tests for YCDirectorySource. Mocks the httpx client with a small fixture mirroring the
real yc-oss dataset's shape (confirmed against the live dataset during development) -- no live
network calls in tests."""

from unittest.mock import MagicMock

from app.schemas.discovery import DiscoveryQuery
from app.services.discovery.yc_directory import YCDirectorySource

_FIXTURE_COMPANIES = [
    {
        "name": "NYC Hiring Startup",
        "website": "https://nychiring.example",
        "all_locations": "New York City, NY, USA",
        "industry": "B2B",
        "one_liner": "We do things in NYC.",
        "long_description": "A longer description of what we do in NYC.",
        "stage": "Early",
        "status": "Active",
        "isHiring": True,
        "url": "https://ycombinator.com/companies/nyc-hiring-startup",
    },
    {
        "name": "SF Hiring Startup",
        "website": "https://sfhiring.example",
        "all_locations": "San Francisco, CA, USA",
        "industry": "B2B",
        "one_liner": "We do things in SF.",
        "stage": "Early",
        "status": "Active",
        "isHiring": True,
        "url": "https://ycombinator.com/companies/sf-hiring-startup",
    },
    {
        "name": "NYC Not Hiring",
        "website": "https://notnyc.example",
        "all_locations": "New York City, NY, USA",
        "industry": "B2B",
        "one_liner": "Not currently hiring.",
        "stage": "Early",
        "status": "Active",
        "isHiring": False,
        "url": "https://ycombinator.com/companies/nyc-not-hiring",
    },
    {
        "name": "NYC Inactive",
        "website": "https://inactive.example",
        "all_locations": "New York City, NY, USA",
        "industry": "B2B",
        "one_liner": "No longer active.",
        "stage": "Early",
        "status": "Inactive",
        "isHiring": True,
        "url": "https://ycombinator.com/companies/nyc-inactive",
    },
    {
        "name": "NYC Growth Stage",
        "website": "https://growth.example",
        "all_locations": "New York City, NY, USA",
        "industry": "B2B",
        "one_liner": "A later-stage company.",
        "stage": "Growth",
        "status": "Active",
        "isHiring": True,
        "url": "https://ycombinator.com/companies/nyc-growth",
    },
]


def _make_client() -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = _FIXTURE_COMPANIES
    client.get.return_value = response
    return client


def test_filters_to_hiring_active_companies_only() -> None:
    source = YCDirectorySource(client=_make_client())
    results = source.search_companies(DiscoveryQuery())
    names = {c.name for c in results}
    assert "NYC Not Hiring" not in names
    assert "NYC Inactive" not in names
    assert "NYC Hiring Startup" in names


def test_location_filter_narrows_to_matching_companies() -> None:
    source = YCDirectorySource(client=_make_client())
    results = source.search_companies(DiscoveryQuery(location_filters=["new york"]))
    names = {c.name for c in results}
    assert "SF Hiring Startup" not in names
    assert "NYC Hiring Startup" in names


def test_stage_filter_maps_seed_series_a_b_to_yc_early() -> None:
    source = YCDirectorySource(client=_make_client())
    # "Early" always passes; "Growth" is allowed too (documented loose upper bound).
    results = source.search_companies(
        DiscoveryQuery(location_filters=["new york"], stage_filters=["seed", "series_a"])
    )
    names = {c.name for c in results}
    assert "NYC Hiring Startup" in names
    assert "NYC Growth Stage" in names  # allowed as a loose upper bound, not excluded


def test_maps_yc_stage_to_our_funding_stage_taxonomy() -> None:
    source = YCDirectorySource(client=_make_client())
    results = source.search_companies(DiscoveryQuery(location_filters=["new york"]))
    early = next(c for c in results if c.name == "NYC Hiring Startup")
    growth = next(c for c in results if c.name == "NYC Growth Stage")
    assert early.funding_stage == "seed"
    assert growth.funding_stage == "growth"


def test_get_jobs_always_returns_empty_list() -> None:
    """Documented, deliberate limitation -- the dataset has no per-company job postings."""
    source = YCDirectorySource(client=_make_client())
    company = source.search_companies(DiscoveryQuery())[0]
    assert source.get_jobs(company) == []


def test_falls_back_to_one_liner_when_no_long_description() -> None:
    source = YCDirectorySource(client=_make_client())
    results = source.search_companies(DiscoveryQuery(location_filters=["san francisco"]))
    sf_company = next(c for c in results if c.name == "SF Hiring Startup")
    assert sf_company.description == "We do things in SF."
