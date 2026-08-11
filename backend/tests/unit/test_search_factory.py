from app.config import Settings
from app.services.search.duckduckgo_provider import DuckDuckGoSearchProvider
from app.services.search.factory import get_search_provider
from app.services.search.stub_provider import StubSearchProvider


def test_stub_setting_returns_stub_provider() -> None:
    settings = Settings(search_provider="stub")
    assert isinstance(get_search_provider(settings), StubSearchProvider)


def test_duckduckgo_setting_returns_duckduckgo_provider() -> None:
    settings = Settings(search_provider="duckduckgo")
    assert isinstance(get_search_provider(settings), DuckDuckGoSearchProvider)
