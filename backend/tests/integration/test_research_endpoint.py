"""Integration tests for the Company Research Agent endpoints. The page fetch is swapped for a
fake `PageFetcher` via a FastAPI dependency override -- no live network calls in the test suite
(the fetcher itself is unit-tested against mocked HTTP in test_page_fetcher.py).
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.api.deps import get_research_agent
from app.main import app
from app.services.llm.stub_provider import StubProvider
from app.services.research.agent import CompanyResearchAgent
from app.services.research.fetcher import FetchedPage, PageFetchError
from app.services.research.llm_researcher import LLMCompanyResearcher


def _fake_agent(
    page_text: str = "Acme Robotics builds warehouse automation.\nWe serve logistics companies.",
) -> CompanyResearchAgent:
    fetcher = MagicMock()
    fetcher.fetch.return_value = FetchedPage(
        url="https://acme.example", text=page_text, title="Acme Robotics"
    )
    return CompanyResearchAgent(
        fetcher=fetcher, researcher=LLMCompanyResearcher(), llm_provider=StubProvider()
    )


def _failing_agent() -> CompanyResearchAgent:
    fetcher = MagicMock()
    fetcher.fetch.side_effect = PageFetchError("timed out")
    return CompanyResearchAgent(
        fetcher=fetcher, researcher=LLMCompanyResearcher(), llm_provider=StubProvider()
    )


def _create_company(client: TestClient, *, website: str | None = "https://acme.example") -> str:
    response = client.post("/api/v1/companies", json={"name": "Acme Robotics", "website": website})
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def test_run_research_persists_a_verified_fact(client: TestClient) -> None:
    app.dependency_overrides[get_research_agent] = _fake_agent
    try:
        company_id = _create_company(client)
        run_response = client.post(f"/api/v1/companies/{company_id}/research/run")
        assert run_response.status_code == 200, run_response.text
        result = run_response.json()
        assert result["facts_created"] == 1
        assert result["warnings"] == []

        list_response = client.get(f"/api/v1/companies/{company_id}/research")
        assert list_response.status_code == 200
        rows = list_response.json()
        assert len(rows) == 1
        assert rows[0]["is_inference"] is False
        assert rows[0]["source_id"] is not None
    finally:
        app.dependency_overrides.pop(get_research_agent, None)


def test_run_research_detects_personal_connection(client: TestClient) -> None:
    app.dependency_overrides[get_research_agent] = lambda: _fake_agent(
        "MedScan builds AI for radiology and diagnostic imaging teams."
    )
    try:
        company_id = _create_company(client)
        client.post(f"/api/v1/companies/{company_id}/research/run")
        rows = client.get(f"/api/v1/companies/{company_id}/research").json()
        connection_rows = [r for r in rows if r["fact_type"] == "personal_connection"]
        assert len(connection_rows) == 1
        assert connection_rows[0]["is_inference"] is True
    finally:
        app.dependency_overrides.pop(get_research_agent, None)


def test_run_research_with_no_website_returns_warning_not_error(client: TestClient) -> None:
    app.dependency_overrides[get_research_agent] = _fake_agent
    try:
        company_id = _create_company(client, website=None)
        response = client.post(f"/api/v1/companies/{company_id}/research/run")
        assert response.status_code == 200
        result = response.json()
        assert result["facts_created"] == 0
        assert "no website" in result["warnings"][0].lower()
    finally:
        app.dependency_overrides.pop(get_research_agent, None)


def test_run_research_handles_fetch_failure_gracefully(client: TestClient) -> None:
    app.dependency_overrides[get_research_agent] = _failing_agent
    try:
        company_id = _create_company(client)
        response = client.post(f"/api/v1/companies/{company_id}/research/run")
        assert response.status_code == 200
        result = response.json()
        assert result["facts_created"] == 0
        assert "timed out" in result["warnings"][0]
    finally:
        app.dependency_overrides.pop(get_research_agent, None)


def test_run_research_404s_for_unknown_company(client: TestClient) -> None:
    app.dependency_overrides[get_research_agent] = _fake_agent
    try:
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(f"/api/v1/companies/{fake_id}/research/run")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_research_agent, None)
