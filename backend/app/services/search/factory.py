from app.config import Settings
from app.services.search.base import SearchProvider
from app.services.search.duckduckgo_provider import DuckDuckGoSearchProvider
from app.services.search.stub_provider import StubSearchProvider


def get_search_provider(settings: Settings) -> SearchProvider:
    # Same registration pattern as services.llm.factory: one branch per provider, settings pick
    # which one, callers never import a concrete provider directly.
    if settings.search_provider == "stub":
        return StubSearchProvider()
    return DuckDuckGoSearchProvider()
