"""Integration tests for POST /api/v1/discovery/run. Adapters are swapped for fakes via
monkeypatching `app.services.discovery.runner`'s adapter registries -- no live network calls to
HN/GitHub/YC in the test suite; those are covered separately (with mocked HTTP) in
tests/unit/test_hn_who_is_hiring.py, test_github_new_grad_list.py, and test_yc_directory.py.

Every test that uses the `startup_outreach` profile key must also clear
`COMPANY_ADAPTERS_BY_PROFILE_KEY["startup_outreach"]` (real `YCDirectorySource` is wired to it
by default) so no test ever makes a live network call by accident.
"""

import pytest
from fastapi.testclient import TestClient

import app.services.discovery.runner as discovery_runner
from app.schemas.discovery import DiscoveredCompany, DiscoveredJob, DiscoveryQuery


class _FakeJobBoardSource:
    name = "fake_source"

    def search_jobs(self, query: DiscoveryQuery) -> list[DiscoveredJob]:
        return [
            DiscoveredJob(
                title="Fake Role",
                job_url="https://fake.example/jobs/1",
                location="New York, NY",
                description="desc",
                work_mode=None,
                posted_date=None,
                deadline_date=None,
                company=DiscoveredCompany(
                    name="FakeCo",
                    website="https://fakeco.example",
                    location="NYC",
                    industry=None,
                    description=None,
                    funding_stage="seed",
                    source_url="https://fake.example/jobs/1",
                    source_type="fake_source",
                ),
                source_url="https://fake.example/jobs/1",
                source_type="fake_source",
            )
        ]


class _BrokenSource:
    name = "broken_source"

    def search_jobs(self, query: DiscoveryQuery) -> list[DiscoveredJob]:
        raise RuntimeError("network down")


class _FakeCompanySource:
    name = "fake_company_source"

    def search_companies(self, query: DiscoveryQuery) -> list[DiscoveredCompany]:
        return [
            DiscoveredCompany(
                name="DirectoryCo",
                website="https://directoryco.example",
                location="New York, NY",
                industry="B2B",
                description="A company found via directory listing.",
                funding_stage="seed",
                source_url="https://directory.example/directoryco",
                source_type=self.name,
            )
        ]

    def get_jobs(self, company: DiscoveredCompany) -> list[DiscoveredJob]:
        return []  # mirrors YCDirectorySource's real, documented limitation


def _clear_startup_outreach_company_adapters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(discovery_runner.COMPANY_ADAPTERS_BY_PROFILE_KEY, "startup_outreach", [])


def _create_candidate(client: TestClient) -> str:
    return str(client.post("/api/v1/candidates", json={"full_name": "Test"}).json()["id"])


def _create_profile(client: TestClient, candidate_id: str) -> dict:
    response = client.post(
        "/api/v1/search-profiles",
        json={
            "candidate_id": candidate_id,
            "profile_key": "startup_outreach",
            "display_name": "Startup Outreach",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_discovery_run_upserts_companies_jobs_and_applications(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(
        discovery_runner.JOB_BOARD_ADAPTERS_BY_PROFILE_KEY,
        "startup_outreach",
        [_FakeJobBoardSource],
    )
    _clear_startup_outreach_company_adapters(monkeypatch)
    candidate_id = _create_candidate(client)
    profile = _create_profile(client, candidate_id)

    run_response = client.post("/api/v1/discovery/run", json={"profile_id": profile["id"]})
    assert run_response.status_code == 200, run_response.text
    result = run_response.json()
    assert result["sources_run"] == ["fake_source"]
    assert result["jobs_upserted"] == 1
    assert result["companies_upserted"] == 1
    assert result["jobs_scored"] == 1  # scored automatically -- no manual "Score" click needed
    assert result["warnings"] == []

    listed = client.get(f"/api/v1/search-profiles/{profile['id']}/jobs").json()
    assert len(listed) == 1
    assert listed[0]["job"]["title"] == "Fake Role"
    assert listed[0]["company"]["name"] == "FakeCo"
    assert listed[0]["fit_score"] is not None


def test_discovery_run_is_idempotent(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        discovery_runner.JOB_BOARD_ADAPTERS_BY_PROFILE_KEY,
        "startup_outreach",
        [_FakeJobBoardSource],
    )
    _clear_startup_outreach_company_adapters(monkeypatch)
    candidate_id = _create_candidate(client)
    profile = _create_profile(client, candidate_id)

    first = client.post("/api/v1/discovery/run", json={"profile_id": profile["id"]}).json()
    second = client.post("/api/v1/discovery/run", json={"profile_id": profile["id"]}).json()

    assert first["jobs_scored"] == 1
    assert second["jobs_upserted"] == 0
    assert second["companies_upserted"] == 0
    assert second["jobs_scored"] == 0  # already scored -- never silently re-scored on a re-run
    listed = client.get(f"/api/v1/search-profiles/{profile['id']}/jobs").json()
    assert len(listed) == 1  # no duplicate application row


def test_discovery_run_does_not_overwrite_a_score_edited_since(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A job manually re-scored (e.g. via POST /jobs/{id}/score after a weights change) must
    keep that score -- a later discovery re-run (which only fills in what's missing) must not
    clobber it with a fresh automatic one."""
    monkeypatch.setitem(
        discovery_runner.JOB_BOARD_ADAPTERS_BY_PROFILE_KEY,
        "startup_outreach",
        [_FakeJobBoardSource],
    )
    _clear_startup_outreach_company_adapters(monkeypatch)
    candidate_id = _create_candidate(client)
    profile = _create_profile(client, candidate_id)

    client.post("/api/v1/discovery/run", json={"profile_id": profile["id"]})
    listed = client.get(f"/api/v1/search-profiles/{profile['id']}/jobs").json()
    job_id = listed[0]["job"]["id"]
    original_score_id = listed[0]["fit_score"]["id"]

    rescored = client.post(
        f"/api/v1/jobs/{job_id}/score",
        json={"candidate_id": candidate_id, "profile_id": profile["id"]},
    ).json()
    assert rescored["id"] != original_score_id  # a genuinely new row, human-triggered

    again = client.post("/api/v1/discovery/run", json={"profile_id": profile["id"]}).json()
    assert again["jobs_scored"] == 0

    listed_after = client.get(f"/api/v1/search-profiles/{profile['id']}/jobs").json()
    assert listed_after[0]["fit_score"]["id"] == rescored["id"]  # untouched by the re-run


def test_discovery_run_404s_for_unknown_profile(client: TestClient) -> None:
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.post("/api/v1/discovery/run", json={"profile_id": fake_id})
    assert response.status_code == 404


def test_discovery_run_warns_but_does_not_fail_on_adapter_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setitem(
        discovery_runner.JOB_BOARD_ADAPTERS_BY_PROFILE_KEY, "startup_outreach", [_BrokenSource]
    )
    _clear_startup_outreach_company_adapters(monkeypatch)
    candidate_id = _create_candidate(client)
    profile = _create_profile(client, candidate_id)

    with caplog.at_level("INFO", logger="app.agent_decisions"):
        response = client.post("/api/v1/discovery/run", json={"profile_id": profile["id"]})
    assert response.status_code == 200
    result = response.json()
    assert result["jobs_upserted"] == 0
    assert any("broken_source" in warning for warning in result["warnings"])

    # A scheduled (non-HTTP-triggered) run has no response for anyone to read counters/warnings
    # off of -- this log line is the only durable record it ever produces, so it has to actually
    # fire, not just the API response.
    assert "discovery_adapter_failed" in caplog.text
    assert "broken_source" in caplog.text
    assert "discovery_run_completed" in caplog.text


def test_profile_with_no_configured_adapters_runs_cleanly(client: TestClient) -> None:
    candidate_id = _create_candidate(client)
    profile = client.post(
        "/api/v1/search-profiles",
        json={
            "candidate_id": candidate_id,
            "profile_key": "some_other_profile",
            "display_name": "Other",
        },
    ).json()

    response = client.post("/api/v1/discovery/run", json={"profile_id": profile["id"]})
    assert response.status_code == 200
    assert response.json()["sources_run"] == []


def test_discovery_run_with_company_source_upserts_company_without_jobs(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The company-first path: a CompanySource can add a company even when it produces no jobs
    (YCDirectorySource's real, documented behavior) -- no application row without a job, since
    applications requires one."""
    monkeypatch.setitem(discovery_runner.JOB_BOARD_ADAPTERS_BY_PROFILE_KEY, "startup_outreach", [])
    monkeypatch.setitem(
        discovery_runner.COMPANY_ADAPTERS_BY_PROFILE_KEY, "startup_outreach", [_FakeCompanySource]
    )
    candidate_id = _create_candidate(client)
    profile = _create_profile(client, candidate_id)

    response = client.post("/api/v1/discovery/run", json={"profile_id": profile["id"]})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["sources_run"] == ["fake_company_source"]
    assert result["companies_upserted"] == 1
    assert result["jobs_upserted"] == 0

    company = client.post(
        "/api/v1/companies", json={"name": "DirectoryCo", "website": "https://directoryco.example"}
    )
    assert company.status_code == 409  # confirms it was already upserted by discovery
