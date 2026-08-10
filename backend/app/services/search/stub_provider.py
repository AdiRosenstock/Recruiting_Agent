"""No-op placeholder -- there's no search API key configured yet (see .env.example). Clearly
labeled, like `services.llm.stub_provider.StubProvider`: it lets code that depends on
`SearchProvider` run without a key, but it never fabricates results. Replace with a real
provider (Brave/Bing/SerpAPI) once a key is available -- no caller changes needed.
"""

from app.services.search.base import SearchResult


class StubSearchProvider:
    name = "stub"

    def search(self, query: str, *, num_results: int = 5) -> list[SearchResult]:
        return []
