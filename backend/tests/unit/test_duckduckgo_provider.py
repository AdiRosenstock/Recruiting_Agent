"""Unit tests for DuckDuckGoSearchProvider. Mocks the httpx client -- no live network -- using a
result-page shape confirmed against html.duckduckgo.com's real markup during development."""

from unittest.mock import MagicMock

import httpx

from app.services.search.duckduckgo_provider import DuckDuckGoSearchProvider

_SAMPLE_RESULTS_HTML = """
<div class="results">
  <div class="result results_links results_links_deep web-result">
    <div class="result__body">
      <h2 class="result__title">
        <a rel="nofollow" class="result__a"
           href="//duckduckgo.com/l/?uddg=https%3A%2F%2Facme.example%2F&amp;rut=abc">
          Acme Robotics &ndash; Official Site
        </a>
      </h2>
      <a class="result__snippet" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Facme.example%2F">
        Acme Robotics builds <b>warehouse</b> automation robots.
      </a>
    </div>
  </div>
  <div class="result results_links results_links_deep web-result">
    <div class="result__body">
      <h2 class="result__title">
        <a rel="nofollow" class="result__a"
           href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.linkedin.com%2Fcompany%2Facme">
          Acme Robotics | LinkedIn
        </a>
      </h2>
      <a class="result__snippet">See who works at Acme Robotics.</a>
    </div>
  </div>
</div>
"""


def _make_client(html: str) -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.text = html
    client.post.return_value = response
    return client


def test_parses_results_and_unwraps_redirect_urls() -> None:
    provider = DuckDuckGoSearchProvider(client=_make_client(_SAMPLE_RESULTS_HTML))
    results = provider.search("acme robotics official website")

    assert len(results) == 2
    assert results[0].url == "https://acme.example/"
    assert "Acme Robotics" in results[0].title
    assert "warehouse" in results[0].snippet
    assert results[1].url == "https://www.linkedin.com/company/acme"


def test_respects_num_results() -> None:
    provider = DuckDuckGoSearchProvider(client=_make_client(_SAMPLE_RESULTS_HTML))
    results = provider.search("acme robotics", num_results=1)
    assert len(results) == 1


def test_returns_empty_list_on_no_matches() -> None:
    html = "<div class='results'>no results</div>"
    provider = DuckDuckGoSearchProvider(client=_make_client(html))
    assert provider.search("something obscure") == []


def test_returns_empty_list_on_http_error_instead_of_raising() -> None:
    client = MagicMock()
    client.post.side_effect = httpx.ConnectTimeout("timed out")
    provider = DuckDuckGoSearchProvider(client=client)
    assert provider.search("acme robotics") == []
