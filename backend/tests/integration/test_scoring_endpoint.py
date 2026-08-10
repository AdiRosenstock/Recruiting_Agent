from fastapi.testclient import TestClient


def _create_candidate_with_skills(client: TestClient, sample_resume_bytes: bytes) -> str:
    """Uploads the real resume fixture through the stub LLM provider so the candidate ends up
    with real, verified skill claims (python, sql, ...) to score against."""
    candidate = client.post("/api/v1/candidates", json={"full_name": "Placeholder"}).json()
    upload = client.post(
        f"/api/v1/candidates/{candidate['id']}/resume",
        files={"file": ("resume.pdf", sample_resume_bytes, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    return str(candidate["id"])


def _create_profile(client: TestClient, candidate_id: str) -> str:
    response = client.post(
        "/api/v1/search-profiles",
        json={
            "candidate_id": candidate_id,
            "profile_key": "startup_outreach",
            "display_name": "Startup Outreach",
            "outreach_enabled": True,
            "config": {
                "role_filters": ["data engineer", "backend engineer"],
                "stage_filters": ["seed"],
                "location_filters": ["new york"],
            },
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _create_job(client: TestClient) -> str:
    company = client.post(
        "/api/v1/companies",
        json={"name": "Acme Data", "funding_stage": "seed", "industry": "Fintech"},
    ).json()
    job = client.post(
        f"/api/v1/companies/{company['id']}/jobs",
        json={
            "title": "Data Engineer",
            "job_url": "https://acme.example/jobs/data-eng",
            "location": "New York, NY",
            "technologies": ["Python", "SQL"],
        },
    ).json()
    return str(job["id"])


def test_score_job_persists_fit_score_and_links_application(
    client: TestClient, sample_resume_bytes: bytes
) -> None:
    candidate_id = _create_candidate_with_skills(client, sample_resume_bytes)
    profile_id = _create_profile(client, candidate_id)
    job_id = _create_job(client)

    score_response = client.post(
        f"/api/v1/jobs/{job_id}/score",
        json={"candidate_id": candidate_id, "profile_id": profile_id},
    )
    assert score_response.status_code == 201, score_response.text
    score = score_response.json()
    assert score["candidate_id"] == candidate_id
    assert score["job_id"] == job_id
    assert score["profile_id"] == profile_id
    assert 0 <= score["overall_score"] <= 100
    assert score["tier"] in ("excellent", "strong", "worth_reviewing", "weak", "ignore")
    # Candidate's real resume has verified python/sql skills matching the job's technologies.
    assert score["technical_match"] > 0

    jobs_response = client.get(f"/api/v1/search-profiles/{profile_id}/jobs")
    assert jobs_response.status_code == 200
    listed = jobs_response.json()
    assert len(listed) == 1
    assert listed[0]["fit_score"]["id"] == score["id"]


def test_score_job_404s_for_unknown_job(client: TestClient, sample_resume_bytes: bytes) -> None:
    candidate_id = _create_candidate_with_skills(client, sample_resume_bytes)
    profile_id = _create_profile(client, candidate_id)
    fake_job_id = "00000000-0000-0000-0000-000000000000"

    response = client.post(
        f"/api/v1/jobs/{fake_job_id}/score",
        json={"candidate_id": candidate_id, "profile_id": profile_id},
    )
    assert response.status_code == 404


def test_rescoring_creates_a_new_fit_score_row_and_updates_application(
    client: TestClient, sample_resume_bytes: bytes
) -> None:
    candidate_id = _create_candidate_with_skills(client, sample_resume_bytes)
    profile_id = _create_profile(client, candidate_id)
    job_id = _create_job(client)

    first = client.post(
        f"/api/v1/jobs/{job_id}/score",
        json={"candidate_id": candidate_id, "profile_id": profile_id},
    ).json()
    second = client.post(
        f"/api/v1/jobs/{job_id}/score",
        json={"candidate_id": candidate_id, "profile_id": profile_id},
    ).json()

    assert first["id"] != second["id"]

    jobs_response = client.get(f"/api/v1/search-profiles/{profile_id}/jobs").json()
    assert jobs_response[0]["fit_score"]["id"] == second["id"]
