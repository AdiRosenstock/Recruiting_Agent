from app.config import Settings
from app.services.search.base import SearchProvider
from app.services.search.stub_provider import StubSearchProvider


def get_search_provider(settings: Settings) -> SearchProvider:
    # Only "stub" exists this phase -- see module docstring in base.py. Real providers register
    # here the same way services.llm.factory registers openai/anthropic.
    return StubSearchProvider()
