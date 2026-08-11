"""A real `SearchProvider` that needs no API key: DuckDuckGo's plain HTML results page
(`html.duckduckgo.com/html/`), the same no-JS endpoint DuckDuckGo serves to browsers with
JavaScript disabled. No login, no key, no rate-limit tier to pay for -- exactly the "no-login
public page" bar the discovery adapters (`HNWhoIsHiringSource`, `YCDirectorySource`) are already
held to, applied here to search instead of a single known source.

Parsing is deterministic regex on the fixed result markup (`result__a` / `result__snippet`
anchors), same style as `services/research/fetcher.py` and the discovery adapters -- no LLM
call, no extra HTML-parsing dependency. DuckDuckGo wraps result hrefs in a redirect
(`//duckduckgo.com/l/?uddg=<url-encoded-target>`); those are unwrapped back to the real target
URL before being returned, since callers (company-website lookup) need the actual destination.

This is used for exactly one thing right now: `CompanyResearchAgent` falling back to a search
when a company has no `website` on file (see `services/research/agent.py`). It is never used to
look up or contact a *person* -- there is no code path from here to outreach.
"""

import re
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from app.services.search.base import SearchResult

_RESULTS_URL = "https://html.duckduckgo.com/html/"

# DuckDuckGo's HTML result markup: each result is an <a class="result__a" href="...">Title</a>
# followed later by an <a class="result__snippet" ...>snippet text</a>. Matched independently
# (snippets aren't always present) and paired up by position.
_RESULT_LINK_RE = re.compile(
    r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL
)
_SNIPPET_RE = re.compile(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(fragment: str) -> str:
    return _TAG_RE.sub("", fragment).strip()


def _unwrap_redirect(href: str) -> str:
    """DuckDuckGo's HTML results link through `//duckduckgo.com/l/?uddg=<encoded-url>&rut=...`
    rather than the destination directly. Unwrap it; if the href doesn't look like that
    redirect (already a direct URL, or a future markup change), return it unchanged rather than
    raising -- a slightly-wrong URL is a caller-visible fetch failure later, not worth crashing
    the search over."""
    if "uddg=" not in href:
        return href
    query = urlparse(href if href.startswith("http") else f"https:{href}").query
    params = parse_qs(query)
    target = params.get("uddg")
    return unquote(target[0]) if target else href


class DuckDuckGoSearchProvider:
    """Real `SearchProvider` implementation. No API key needed; see module docstring."""

    name = "duckduckgo"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(
            timeout=15.0,
            headers={"User-Agent": "RecruitingAgent/1.0 (personal job-search research tool)"},
        )

    def search(self, query: str, *, num_results: int = 5) -> list[SearchResult]:
        try:
            response = self._client.post(_RESULTS_URL, data={"q": query})
            response.raise_for_status()
        except httpx.HTTPError:
            # Search is a best-effort fallback (company research still works without it, just
            # with a warning) -- never let a flaky search request take down a research run.
            return []

        raw_html = response.text
        links = _RESULT_LINK_RE.findall(raw_html)
        snippets = _SNIPPET_RE.findall(raw_html)

        results: list[SearchResult] = []
        for index, (href, title_html) in enumerate(links[:num_results]):
            url = _unwrap_redirect(href)
            if not url.startswith("http"):
                continue
            snippet = _strip_tags(snippets[index]) if index < len(snippets) else ""
            results.append(SearchResult(title=_strip_tags(title_html), url=url, snippet=snippet))
        return results
