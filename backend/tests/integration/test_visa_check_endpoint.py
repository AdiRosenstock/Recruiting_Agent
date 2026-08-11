"""Integration tests for POST /api/v1/jobs/{id}/check-visa-sponsorship. The page fetch is
swapped for a fake `PageFetcher` via dependency override -- no live network calls in the test
suite (the fetcher itself is unit-tested against mocked HTTP in test_page_fetcher.py; the
check's fetch-only-when-no-description logic is unit-tested directly in test_visa_check.py)."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.api.deps import get_page_fetcher
from app.main import app
from app.services.research.fetcher import FetchedPage


def _fake_fetcher(text: str = "Apply today, great benefits!") -> MagicMock:
    fetcher = MagicMock()
    fetcher.fetch.return_value = FetchedPage(
        url="https://acme.example/jobs/1", text=text, title="Careers"
    )
    return fetcher


def _create_job(client: TestClient, *, description: str | None = None) -> str:
    company = client.post("/api/v1/companies", json={"name": "Acme Robotics"}).json()
    job = client.post(
        f"/api/v1/companies/{company['id']}/jobs",
        json={
            "title": "Backend Engineer",
            "job_url": "https://acme.example/jobs/1",
            "description": description,
        },
    ).json()
    return str(job["id"])


def test_check_visa_sponsorship_finds_signal_in_existing_description(client: TestClient) -> None:
    job_id = _create_job(
        client, description="Great team. We are unable to sponsor visas for this role."
    )
    app.dependency_overrides[get_page_fetcher] = _fake_fetcher
    try:
        response = client.post(f"/api/v1/jobs/{job_id}/check-visa-sponsorship")
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["visa_sponsorship"] == "likely_no_sponsorship"
        assert "unable to sponsor" in result["visa_sponsorship_evidence"]
        assert result["visa_sponsorship_checked_at"] is not None
    finally:
        app.dependency_overrides.pop(get_page_fetcher, None)


def test_check_visa_sponsorship_fetches_when_no_description(client: TestClient) -> None:
    job_id = _create_job(client, description=None)
    fetcher = _fake_fetcher("Visa sponsorship is available for qualified candidates.")
    app.dependency_overrides[get_page_fetcher] = lambda: fetcher
    try:
        response = client.post(f"/api/v1/jobs/{job_id}/check-visa-sponsorship")
        assert response.status_code == 200, response.text
        assert response.json()["visa_sponsorship"] == "likely_sponsors"
        fetcher.fetch.assert_called_once()
    finally:
        app.dependency_overrides.pop(get_page_fetcher, None)


def test_check_visa_sponsorship_404s_for_unknown_job(client: TestClient) -> None:
    app.dependency_overrides[get_page_fetcher] = _fake_fetcher
    try:
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(f"/api/v1/jobs/{fake_id}/check-visa-sponsorship")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_page_fetcher, None)
