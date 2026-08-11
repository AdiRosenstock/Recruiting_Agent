"""Deterministic company-page fetching -- works from a company's `website` URL alone, no search
API needed (see services/search for why there's no live search yet). Strips HTML down to
readable text; extraction quality depends on how the page is built (a heavy JS single-page app
won't yield much from a plain GET without a real browser) -- a known, documented limitation, not
silently papered over: `PageFetchError` is raised rather than fabricating page content.
"""

import html
import re
from dataclasses import dataclass

import httpx

_SCRIPT_STYLE_RE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.DOTALL | re.IGNORECASE)
_INLINE_WHITESPACE_RE = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n\s*\n+")
# Keep prompts small -- a company homepage rarely needs more than this to research well, and it
# bounds LLM cost/latency regardless of how large the fetched page is.
_MAX_TEXT_CHARS = 8000


@dataclass(frozen=True)
class FetchedPage:
    url: str
    text: str
    title: str | None


class PageFetchError(Exception):
    pass


def _clean_text(raw: str) -> str:
    text = html.unescape(raw)
    text = _INLINE_WHITESPACE_RE.sub(" ", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    return text.strip()


class PageFetcher:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": "RecruitingAgent/1.0 (personal research tool)"},
        )

    def fetch(self, url: str) -> FetchedPage:
        try:
            response = self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise PageFetchError(f"Failed to fetch {url}: {exc}") from exc

        content_type = response.headers.get("content-type", "")
        if "html" not in content_type.lower():
            raise PageFetchError(
                f"{url} did not return HTML content (content-type: {content_type!r})"
            )

        raw_html = response.text
        title_match = _TITLE_RE.search(raw_html)
        title = _clean_text(title_match.group(1)) if title_match else None

        text = _SCRIPT_STYLE_RE.sub(" ", raw_html)
        text = _TAG_RE.sub("\n", text)
        text = _clean_text(text)[:_MAX_TEXT_CHARS]

        if not text:
            raise PageFetchError(f"{url} returned no extractable text.")

        return FetchedPage(url=str(response.url), text=text, title=title)
