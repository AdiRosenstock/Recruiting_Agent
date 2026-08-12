from fastapi.testclient import TestClient


def test_create_company_and_add_job(client: TestClient) -> None:
    company_response = client.post(
        "/api/v1/companies",
        json={
            "name": "Acme Robotics",
            "website": "https://acme.example",
            "location": "New York, NY",
            "industry": "Robotics",
            "funding_stage": "seed",
        },
    )
    assert company_response.status_code == 201, company_response.text
    company = company_response.json()
    assert company["normalized_name"] == "acme robotics"

    job_response = client.post(
        f"/api/v1/companies/{company['id']}/jobs",
        json={
            "title": "Backend Engineer",
            "job_url": "https://acme.example/jobs/1",
            "location": "New York, NY",
            "technologies": ["Python", "PostgreSQL"],
        },
    )
    assert job_response.status_code == 201, job_response.text
    job = job_response.json()
    assert job["company_id"] == company["id"]
    assert job["technologies"] == ["Python", "PostgreSQL"]

    get_response = client.get(f"/api/v1/companies/{company['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Acme Robotics"


def test_duplicate_company_name_and_website_conflicts(client: TestClient) -> None:
    payload = {"name": "Acme Robotics", "website": "https://acme.example"}
    first = client.post("/api/v1/companies", json=payload)
    assert first.status_code == 201
    second = client.post("/api/v1/companies", json=payload)
    assert second.status_code == 409


def test_duplicate_job_url_conflicts(client: TestClient) -> None:
    company = client.post("/api/v1/companies", json={"name": "Acme"}).json()
    job_payload = {"title": "Engineer", "job_url": "https://acme.example/jobs/1"}
    first = client.post(f"/api/v1/companies/{company['id']}/jobs", json=job_payload)
    assert first.status_code == 201
    second = client.post(f"/api/v1/companies/{company['id']}/jobs", json=job_payload)
    assert second.status_code == 409


def test_add_job_to_unknown_company_404s(client: TestClient) -> None:
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.post(
        f"/api/v1/companies/{fake_id}/jobs",
        json={"title": "Engineer", "job_url": "https://example.com/j/1"},
    )
    assert response.status_code == 404


def test_update_company_sets_only_the_provided_fields(client: TestClient) -> None:
    company = client.post(
        "/api/v1/companies", json={"name": "Acme", "location": "New York, NY"}
    ).json()

    response = client.patch(f"/api/v1/companies/{company['id']}", json={"employee_count": 1300})
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["employee_count"] == 1300
    # Untouched fields survive the partial update.
    assert updated["location"] == "New York, NY"
    assert updated["name"] == "Acme"


def test_update_unknown_company_404s(client: TestClient) -> None:
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.patch(f"/api/v1/companies/{fake_id}", json={"employee_count": 10})
    assert response.status_code == 404
