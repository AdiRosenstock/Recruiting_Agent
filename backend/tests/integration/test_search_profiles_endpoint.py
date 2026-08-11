from fastapi.testclient import TestClient


def _create_candidate(client: TestClient) -> str:
    response = client.post("/api/v1/candidates", json={"full_name": "Test Candidate"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_create_and_list_search_profiles(client: TestClient) -> None:
    candidate_id = _create_candidate(client)

    create_response = client.post(
        "/api/v1/search-profiles",
        json={
            "candidate_id": candidate_id,
            "profile_key": "startup_outreach",
            "display_name": "Startup Outreach",
            "outreach_enabled": True,
            "config": {
                "role_filters": ["backend engineer"],
                "stage_filters": ["seed"],
                "location_filters": ["new york"],
            },
        },
    )
    assert create_response.status_code == 201, create_response.text
    body = create_response.json()
    assert body["profile_key"] == "startup_outreach"
    assert body["outreach_enabled"] is True
    assert body["config"]["role_filters"] == ["backend engineer"]

    list_response = client.get("/api/v1/search-profiles", params={"candidate_id": candidate_id})
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_duplicate_profile_key_for_same_candidate_conflicts(client: TestClient) -> None:
    candidate_id = _create_candidate(client)
    payload = {
        "candidate_id": candidate_id,
        "profile_key": "tracking_only",
        "display_name": "Tracking Only",
    }
    first = client.post("/api/v1/search-profiles", json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/search-profiles", json=payload)
    assert second.status_code == 409


def test_profile_jobs_empty_before_any_discovery_or_scoring(client: TestClient) -> None:
    candidate_id = _create_candidate(client)
    create_response = client.post(
        "/api/v1/search-profiles",
        json={
            "candidate_id": candidate_id,
            "profile_key": "startup_outreach",
            "display_name": "Startup Outreach",
        },
    )
    profile_id = create_response.json()["id"]

    jobs_response = client.get(f"/api/v1/search-profiles/{profile_id}/jobs")
    assert jobs_response.status_code == 200
    assert jobs_response.json() == []


def test_profile_jobs_404_for_unknown_profile(client: TestClient) -> None:
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/search-profiles/{fake_id}/jobs")
    assert response.status_code == 404


def test_read_search_profile(client: TestClient) -> None:
    candidate_id = _create_candidate(client)
    created = client.post(
        "/api/v1/search-profiles",
        json={
            "candidate_id": candidate_id,
            "profile_key": "startup_outreach",
            "display_name": "Startup Outreach",
        },
    ).json()

    response = client.get(f"/api/v1/search-profiles/{created['id']}")
    assert response.status_code == 200
    assert response.json()["profile_key"] == "startup_outreach"


def test_read_search_profile_404_for_unknown_id(client: TestClient) -> None:
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/search-profiles/{fake_id}")
    assert response.status_code == 404


def test_update_search_profile_weights_and_filters(client: TestClient) -> None:
    candidate_id = _create_candidate(client)
    created = client.post(
        "/api/v1/search-profiles",
        json={
            "candidate_id": candidate_id,
            "profile_key": "startup_outreach",
            "display_name": "Startup Outreach",
            "outreach_enabled": True,
            "config": {"role_filters": ["backend engineer"], "stage_filters": ["seed"]},
        },
    ).json()

    response = client.patch(
        f"/api/v1/search-profiles/{created['id']}",
        json={
            "outreach_enabled": False,
            "config": {
                "weights": {"stage": 0.0},
                "role_filters": ["ai engineer", "data engineer"],
                "stage_filters": [],
                "location_filters": [],
            },
        },
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["outreach_enabled"] is False
    assert updated["config"]["weights"] == {"stage": 0.0}
    assert updated["config"]["role_filters"] == ["ai engineer", "data engineer"]

    # Persisted, not just returned -- re-fetch to confirm.
    refetched = client.get(f"/api/v1/search-profiles/{created['id']}").json()
    assert refetched["config"]["role_filters"] == ["ai engineer", "data engineer"]


def test_update_search_profile_partial_leaves_other_fields_untouched(client: TestClient) -> None:
    candidate_id = _create_candidate(client)
    created = client.post(
        "/api/v1/search-profiles",
        json={
            "candidate_id": candidate_id,
            "profile_key": "startup_outreach",
            "display_name": "Startup Outreach",
            "outreach_enabled": True,
            "config": {"role_filters": ["backend engineer"]},
        },
    ).json()

    response = client.patch(
        f"/api/v1/search-profiles/{created['id']}", json={"display_name": "Renamed Profile"}
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["display_name"] == "Renamed Profile"
    assert updated["outreach_enabled"] is True  # untouched
    assert updated["config"]["role_filters"] == ["backend engineer"]  # untouched


def test_update_search_profile_404_for_unknown_id(client: TestClient) -> None:
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.patch(f"/api/v1/search-profiles/{fake_id}", json={"display_name": "X"})
    assert response.status_code == 404
