"""Best-effort "find this company's homepage" helper, used only when a company has no
`website` on file. Deterministic filtering on top of a `SearchProvider`'s results -- never picks
a result the LLM hasn't seen and never fabricates a URL; if nothing plausible comes back, it
says so and the caller falls back to its existing no-website warning.

This is *not* a general web-search tool. It answers exactly one question (what's this company's
own homepage) and is deliberately conservative: aggregators, social networks, and job boards are
excluded even though they'd often "match" the query, because a `company_research` fact sourced
from LinkedIn's marketing copy about itself is worse than no fact at all.
"""

from urllib.parse import urlparse

from app.services.search.base import SearchProvider

# Domains that routinely rank for "<company> official website" but are never themselves the
# company's own site -- aggregators, social networks, job/funding directories. Extending this
# list is cheap and safe (it only ever makes the filter stricter); a wrong ban is a missed
# website, not a wrong one.
_EXCLUDED_DOMAINS = frozenset(
    {
        "linkedin.com",
        "facebook.com",
        "twitter.com",
        "x.com",
        "instagram.com",
        "youtube.com",
        "wikipedia.org",
        "crunchbase.com",
        "glassdoor.com",
        "indeed.com",
        "ycombinator.com",
        "angel.co",
        "wellfound.com",
        "github.com",
        "medium.com",
        "bloomberg.com",
        "pitchbook.com",
        "builtin.com",
        "levels.fyi",
        "reddit.com",
        "news.ycombinator.com",
    }
)


def _registrable_domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[len("www.") :]
    return host


def find_company_website(
    company_name: str, *, search_provider: SearchProvider
) -> tuple[str | None, str]:
    """Returns `(url_or_none, query_used)`. `url_or_none` is the first search result whose
    domain isn't an excluded aggregator/social site -- unverified, the caller still has to fetch
    it before trusting anything on the page."""
    query = f"{company_name} official website"
    results = search_provider.search(query, num_results=5)
    for result in results:
        domain = _registrable_domain(result.url)
        if domain and domain not in _EXCLUDED_DOMAINS:
            return result.url, query
    return None, query
