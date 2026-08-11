from fastapi.testclient import TestClient


def _create_company(client: TestClient, *, employee_count: int | None = None) -> str:
    payload = {"name": "Acme Robotics"}
    if employee_count is not None:
        payload["employee_count"] = employee_count
    response = client.post("/api/v1/companies", json=payload)
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def test_create_contact_computes_priority_rank(client: TestClient) -> None:
    company_id = _create_company(client, employee_count=5)
    response = client.post(
        f"/api/v1/companies/{company_id}/contacts",
        json={"name": "Jane Doe", "title": "Co-Founder & CEO"},
    )
    assert response.status_code == 201, response.text
    contact = response.json()
    assert contact["priority_rank"] == 1
    assert "Founder" in contact["rationale"]


def test_list_contacts_sorted_by_priority(client: TestClient) -> None:
    company_id = _create_company(client, employee_count=5)
    client.post(
        f"/api/v1/companies/{company_id}/contacts",
        json={"name": "Eng Lead", "title": "Head of Engineering"},
    )
    client.post(
        f"/api/v1/companies/{company_id}/contacts", json={"name": "CEO", "title": "Founder / CEO"}
    )

    listed = client.get(f"/api/v1/companies/{company_id}/contacts").json()
    assert [c["name"] for c in listed] == ["CEO", "Eng Lead"]


def test_create_contact_for_unknown_company_404s(client: TestClient) -> None:
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.post(f"/api/v1/companies/{fake_id}/contacts", json={"name": "Someone"})
    assert response.status_code == 404


def test_contact_with_public_profile_url_and_email(client: TestClient) -> None:
    company_id = _create_company(client)
    response = client.post(
        f"/api/v1/companies/{company_id}/contacts",
        json={
            "name": "Jane Doe",
            "title": "VP Engineering",
            "public_profile_url": "https://linkedin.com/in/janedoe",
            "email": "jane@acme.example",
        },
    )
    assert response.status_code == 201
    contact = response.json()
    assert contact["public_profile_url"] == "https://linkedin.com/in/janedoe"
    assert contact["email"] == "jane@acme.example"
