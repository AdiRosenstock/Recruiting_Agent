"""Web search abstraction, mirroring `services.llm.base.LLMProvider`'s pattern: callers depend
on this Protocol, never a vendor SDK directly, so a real provider (Brave/Bing/SerpAPI) slots in
later without touching callers. No callers exist yet this phase -- this exists so Phase 3's
Company Research Agent can build on it immediately.
"""

from typing import Protocol

from pydantic import BaseModel


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class SearchProvider(Protocol):
    name: str

    def search(self, query: str, *, num_results: int = 5) -> list[SearchResult]: ...
