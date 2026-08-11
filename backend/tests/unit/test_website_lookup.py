from app.services.research.website_lookup import find_company_website
from app.services.search.base import SearchResult


class _FakeSearchProvider:
    name = "fake"

    def __init__(self, results: list[SearchResult]) -> None:
        self._results = results

    def search(self, query: str, *, num_results: int = 5) -> list[SearchResult]:
        return self._results[:num_results]


def test_picks_first_non_excluded_domain() -> None:
    provider = _FakeSearchProvider(
        [
            SearchResult(
                title="Acme Robotics | LinkedIn",
                url="https://www.linkedin.com/company/acme",
                snippet="...",
            ),
            SearchResult(
                title="Acme Robotics -- Official Site",
                url="https://acme.example/",
                snippet="...",
            ),
        ]
    )
    url, query = find_company_website("Acme Robotics", search_provider=provider)
    assert url == "https://acme.example/"
    assert "Acme Robotics" in query


def test_returns_none_when_only_aggregators_match() -> None:
    provider = _FakeSearchProvider(
        [
            SearchResult(
                title="Acme | Crunchbase", url="https://www.crunchbase.com/acme", snippet=""
            ),
            SearchResult(
                title="Acme | LinkedIn", url="https://linkedin.com/company/acme", snippet=""
            ),
        ]
    )
    url, _ = find_company_website("Acme Robotics", search_provider=provider)
    assert url is None


def test_returns_none_on_empty_results() -> None:
    url, _ = find_company_website("Nonexistent Co", search_provider=_FakeSearchProvider([]))
    assert url is None
