from unittest.mock import MagicMock

import httpx
import pytest

from app.services.research.fetcher import PageFetcher, PageFetchError


def _make_client(
    *, html: str, content_type: str = "text/html; charset=utf-8", url: str = "https://acme.example"
) -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.headers = {"content-type": content_type}
    response.text = html
    response.url = url
    client.get.return_value = response
    return client


def test_extracts_title_and_strips_tags() -> None:
    html = (
        "<html><head><title>Acme Robotics</title></head><body><p>We build robots.</p></body></html>"
    )
    fetcher = PageFetcher(client=_make_client(html=html))
    page = fetcher.fetch("https://acme.example")
    assert page.title == "Acme Robotics"
    assert "We build robots." in page.text


def test_strips_script_and_style_content() -> None:
    html = (
        "<html><body><script>trackEverything();</script>"
        "<style>.hidden{display:none}</style><p>Real content here.</p></body></html>"
    )
    fetcher = PageFetcher(client=_make_client(html=html))
    page = fetcher.fetch("https://acme.example")
    assert "trackEverything" not in page.text
    assert "display:none" not in page.text
    assert "Real content here." in page.text


def test_unescapes_html_entities() -> None:
    html = "<html><body><p>We&#39;re building &amp; shipping fast.</p></body></html>"
    fetcher = PageFetcher(client=_make_client(html=html))
    page = fetcher.fetch("https://acme.example")
    assert "We're building & shipping fast." in page.text


def test_raises_on_non_html_content_type() -> None:
    fetcher = PageFetcher(client=_make_client(html="{}", content_type="application/json"))
    with pytest.raises(PageFetchError, match="did not return HTML"):
        fetcher.fetch("https://acme.example/api")


def test_raises_on_empty_extracted_text() -> None:
    fetcher = PageFetcher(client=_make_client(html="<html><body></body></html>"))
    with pytest.raises(PageFetchError, match="no extractable text"):
        fetcher.fetch("https://acme.example")


def test_raises_page_fetch_error_on_http_error() -> None:
    client = MagicMock()
    client.get.side_effect = httpx.ConnectTimeout("timed out")
    fetcher = PageFetcher(client=client)
    with pytest.raises(PageFetchError, match="Failed to fetch"):
        fetcher.fetch("https://unreachable.example")
