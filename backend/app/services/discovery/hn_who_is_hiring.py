"""JobBoardSource for the `startup_outreach` profile: HN's monthly "Ask HN: Who is hiring?"
thread, via HN's public Algolia-backed search API (no auth, no key). Chosen over YC/Wellfound
for this first pass because those need per-source ToS/scraping review (see the Phase 1 plan's
risk notes); HN's API is explicitly public and has good density of seed-stage postings.

Parsing is deterministic only (regex on the HN convention "Company | Role | Location | ...")
-- no LLM call, so this works identically under `LLM_PROVIDER=stub`. Real-world comments don't
always follow the convention; unparseable ones are skipped rather than guessed at, and the full
comment text is always kept in `description` so nothing found is lost even when the
company/role/location split is imperfect.
"""

import html
import re
from datetime import date
from urllib.parse import urlparse

import httpx

from app.schemas.discovery import DiscoveredCompany, DiscoveredJob, DiscoveryQuery

_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
_ITEM_URL = "https://hn.algolia.com/api/v1/items/{item_id}"
_THREAD_TITLE_PREFIX = "ask hn: who is hiring?"

_TAG_RE = re.compile(r"<[^>]+>")
_URL_RE = re.compile(r"https?://\S+")
_DESCRIPTION_MAX_CHARS = 2000

# Domains that show up constantly in HN hiring posts but are never themselves the company's own
# site -- ATS/application-flow platforms, social/aggregators, generic doc/form tools. Found live:
# a posting with no URL in its structured header line but a real "read more: https://ojin.ai" in
# the free-text body used to fall through to a (wrong) search-engine guess at research time
# instead of just using the URL the company itself gave. Extending this list only ever makes the
# filter stricter -- a wrong ban is a missed website, not a wrong one (same tradeoff as
# services/research/website_lookup.py's _EXCLUDED_DOMAINS, which this deliberately overlaps
# with but isn't merged with: that list is tuned for "which search result is the real site,"
# this one for "which URL in a job posting's own body is the real site").
_NON_COMPANY_URL_DOMAINS = frozenset(
    {
        "news.ycombinator.com",
        "linkedin.com",
        "twitter.com",
        "x.com",
        "wellfound.com",
        "angel.co",
        "greenhouse.io",
        "lever.co",
        "ashbyhq.com",
        "workable.com",
        "bamboohr.com",
        "breezy.hr",
        "smartrecruiters.com",
        "jobvite.com",
        "icims.com",
        "myworkdayjobs.com",
        "notion.so",
        "airtable.com",
        "typeform.com",
        "calendly.com",
        "docs.google.com",
        "forms.gle",
        "youtube.com",
        "github.com",
    }
)


def _is_non_company_domain(domain: str) -> bool:
    """Suffix match, not exact -- ATS platforms are almost always used via a subdomain
    (`jobs.lever.co`, `apply.workable.com`), which a plain `in` check against the bare domain
    wouldn't catch (caught by this module's own test before shipping, not in production)."""
    return any(domain == d or domain.endswith(f".{d}") for d in _NON_COMPANY_URL_DOMAINS)


def _find_company_url_in_text(text: str) -> str | None:
    """First URL in the free-text body whose domain isn't an ATS/social/aggregator platform --
    conventionally the company's own site (posts commonly end with "more info: <url>" or "apply
    at <url>"), used only when the structured header line didn't already have one."""
    for match in _URL_RE.finditer(text):
        url = match.group(0).rstrip(").,/")
        domain = urlparse(url).netloc.lower().removeprefix("www.")
        if domain and not _is_non_company_domain(domain):
            return url
    return None


def _strip_html(raw: str) -> str:
    text = raw.replace("<p>", "\n")
    text = _TAG_RE.sub("", text)
    return html.unescape(text).strip()


class HNWhoIsHiringSource:
    name = "hn_who_is_hiring"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=15.0)

    def search_jobs(self, query: DiscoveryQuery) -> list[DiscoveredJob]:
        thread_id = self._find_latest_thread_id()
        if thread_id is None:
            return []
        thread = self._fetch_thread(thread_id)

        jobs: list[DiscoveredJob] = []
        for comment in thread.get("children", []):
            job = self._parse_comment(comment)
            if job is not None and self._matches_query(job, query):
                jobs.append(job)
        return jobs

    def _find_latest_thread_id(self) -> int | None:
        response = self._client.get(
            _SEARCH_URL,
            params={"tags": "story,author_whoishiring", "query": "Who is hiring"},
        )
        response.raise_for_status()
        for hit in response.json().get("hits", []):
            title = hit.get("title", "")
            if title.strip().lower().startswith(_THREAD_TITLE_PREFIX):
                return int(hit["objectID"])
        return None

    def _fetch_thread(self, thread_id: int) -> dict:
        response = self._client.get(_ITEM_URL.format(item_id=thread_id))
        response.raise_for_status()
        result: dict = response.json()
        return result

    def _parse_comment(self, comment: dict) -> DiscoveredJob | None:
        raw_text = comment.get("text")
        comment_id = comment.get("id")
        if not raw_text or comment_id is None:
            return None

        stripped = _strip_html(raw_text)
        first_line = stripped.splitlines()[0] if stripped else ""
        parts = [p.strip() for p in first_line.split("|")]
        if len(parts) < 2:
            return None

        company_name, website = self._split_company_field(parts[0])
        if not company_name:
            return None
        if website is None:
            # The structured header line didn't have one -- try the free-text body before
            # giving up (see _find_company_url_in_text: found live that this matters, a
            # search-engine guess at research time got the wrong company for a post that had
            # its own real URL sitting in the body the whole time).
            website = _find_company_url_in_text(stripped)

        rest = [p for p in parts[1:] if not _URL_RE.match(p)]
        role = rest[0] if rest else "Role not specified (see description)"
        location = rest[1] if len(rest) > 1 else None

        comment_url = f"https://news.ycombinator.com/item?id={comment_id}"
        posted_date = self._parse_posted_date(comment.get("created_at"))

        return DiscoveredJob(
            title=role,
            job_url=comment_url,
            location=location,
            description=stripped[:_DESCRIPTION_MAX_CHARS],
            work_mode=None,
            posted_date=posted_date,
            deadline_date=None,
            company=DiscoveredCompany(
                name=company_name,
                website=website,
                source_url=comment_url,
                source_type=self.name,
            ),
            source_url=comment_url,
            source_type=self.name,
        )

    @staticmethod
    def _split_company_field(field: str) -> tuple[str, str | None]:
        url_match = _URL_RE.search(field)
        if url_match is None:
            return field.strip(" -|()"), None
        website = url_match.group(0).rstrip(").,/")
        name = field[: url_match.start()].strip(" -|()")
        return name, website

    @staticmethod
    def _parse_posted_date(created_at: str | None) -> date | None:
        if not created_at:
            return None
        try:
            return date.fromisoformat(created_at[:10])
        except ValueError:
            return None

    @staticmethod
    def _matches_query(job: DiscoveredJob, query: DiscoveryQuery) -> bool:
        haystack = f"{job.title} {job.description or ''} {job.location or ''}".lower()
        if query.location_filters and not any(
            loc.lower() in haystack for loc in query.location_filters
        ):
            return False
        return not query.role_filters or any(
            role.lower() in haystack for role in query.role_filters
        )
