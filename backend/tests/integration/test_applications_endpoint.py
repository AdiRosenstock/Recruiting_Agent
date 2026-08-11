from fastapi.testclient import TestClient


def _create_candidate_with_skills(client: TestClient, sample_resume_bytes: bytes) -> str:
    candidate = client.post("/api/v1/candidates", json={"full_name": "Placeholder"}).json()
    upload = client.post(
        f"/api/v1/candidates/{candidate['id']}/resume",
        files={"file": ("resume.pdf", sample_resume_bytes, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    return str(candidate["id"])


def _create_profile(client: TestClient, candidate_id: str, *, outreach_enabled: bool) -> str:
    response = client.post(
        "/api/v1/search-profiles",
        json={
            "candidate_id": candidate_id,
            "profile_key": "startup_outreach" if outreach_enabled else "tracking_only",
            "display_name": "Test Profile",
            "outreach_enabled": outreach_enabled,
            "config": {"role_filters": ["data engineer"], "location_filters": ["new york"]},
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _create_scored_application(
    client: TestClient, sample_resume_bytes: bytes, *, outreach_enabled: bool
) -> str:
    """Creates a candidate, profile, company/job, scores it, and returns the application id --
    the id every downstream action (outreach generation, status updates) is keyed off.
    """
    candidate_id = _create_candidate_with_skills(client, sample_resume_bytes)
    profile_id = _create_profile(client, candidate_id, outreach_enabled=outreach_enabled)

    company = client.post(
        "/api/v1/companies",
        json={"name": "Acme Data", "funding_stage": "seed", "employee_count": 5},
    ).json()
    job = client.post(
        f"/api/v1/companies/{company['id']}/jobs",
        json={
            "title": "Data Engineer",
            "job_url": f"https://acme.example/jobs/{outreach_enabled}",
            "technologies": ["Python", "SQL"],
        },
    ).json()

    score_response = client.post(
        f"/api/v1/jobs/{job['id']}/score",
        json={"candidate_id": candidate_id, "profile_id": profile_id},
    )
    assert score_response.status_code == 201, score_response.text

    listed = client.get(f"/api/v1/search-profiles/{profile_id}/jobs").json()
    matching = next(entry for entry in listed if entry["job"]["id"] == job["id"])
    return str(matching["application_id"])


def test_score_then_generate_outreach_when_enabled(
    client: TestClient, sample_resume_bytes: bytes
) -> None:
    application_id = _create_scored_application(client, sample_resume_bytes, outreach_enabled=True)

    outreach_response = client.post(f"/api/v1/applications/{application_id}/outreach")
    assert outreach_response.status_code == 200, outreach_response.text
    body = outreach_response.json()
    assert body["linkedin_full"]["message_type"] == "linkedin_full"
    assert body["linkedin_connection"]["message_type"] == "linkedin_connection"
    assert body["email"]["message_type"] == "email"
    assert body["linkedin_full"]["generated_by"] == "stub"

    application = client.get(f"/api/v1/applications/{application_id}").json()
    assert application["status"] == "REVIEW"
    assert application["outreach_message_id"] == body["linkedin_full"]["id"]


def test_generate_outreach_422s_when_profile_disables_it(
    client: TestClient, sample_resume_bytes: bytes
) -> None:
    application_id = _create_scored_application(client, sample_resume_bytes, outreach_enabled=False)
    response = client.post(f"/api/v1/applications/{application_id}/outreach")
    assert response.status_code == 422


def test_patch_application_status_and_notes(client: TestClient, sample_resume_bytes: bytes) -> None:
    application_id = _create_scored_application(client, sample_resume_bytes, outreach_enabled=True)

    response = client.patch(
        f"/api/v1/applications/{application_id}",
        json={"status": "CONTACTED", "notes": "Sent via LinkedIn"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "CONTACTED"
    assert body["notes"] == "Sent via LinkedIn"
    assert body["contacted_at"] is not None


def test_patch_application_does_not_overwrite_contacted_at_on_repeat(
    client: TestClient, sample_resume_bytes: bytes
) -> None:
    application_id = _create_scored_application(client, sample_resume_bytes, outreach_enabled=True)
    first = client.patch(
        f"/api/v1/applications/{application_id}", json={"status": "CONTACTED"}
    ).json()
    second = client.patch(
        f"/api/v1/applications/{application_id}", json={"status": "RESPONDED"}
    ).json()
    assert first["contacted_at"] == second["contacted_at"]
    assert second["responded_at"] is not None


def test_edit_outreach_message_flags_user_edited(
    client: TestClient, sample_resume_bytes: bytes
) -> None:
    application_id = _create_scored_application(client, sample_resume_bytes, outreach_enabled=True)
    outreach = client.post(f"/api/v1/applications/{application_id}/outreach").json()

    message_id = outreach["linkedin_full"]["id"]
    edit_response = client.patch(
        f"/api/v1/outreach-messages/{message_id}", json={"content": "My hand-edited version."}
    )
    assert edit_response.status_code == 200
    edited = edit_response.json()
    assert edited["content"] == "My hand-edited version."
    assert edited["is_user_edited"] is True


def test_edit_outreach_message_can_replace_the_stale_rationale(
    client: TestClient, sample_resume_bytes: bytes
) -> None:
    """A full hand-rewrite (discarding a stub placeholder for real content) should be able to
    replace the rationale that came with the original draft too -- otherwise the dashboard keeps
    showing "no real personalization was performed" next to content that now genuinely is."""
    application_id = _create_scored_application(client, sample_resume_bytes, outreach_enabled=True)
    outreach = client.post(f"/api/v1/applications/{application_id}/outreach").json()
    message_id = outreach["linkedin_full"]["id"]

    edit_response = client.patch(
        f"/api/v1/outreach-messages/{message_id}",
        json={"content": "Real content.", "personalization_rationale": "Real rationale."},
    )
    assert edit_response.status_code == 200
    assert edit_response.json()["personalization_rationale"] == "Real rationale."

    # Omitting it entirely (a plain content tweak) must leave the existing rationale alone.
    second_edit = client.patch(
        f"/api/v1/outreach-messages/{message_id}", json={"content": "Tweaked content."}
    )
    assert second_edit.json()["personalization_rationale"] == "Real rationale."


def test_get_latest_outreach_returns_none_before_any_generation(
    client: TestClient, sample_resume_bytes: bytes
) -> None:
    application_id = _create_scored_application(client, sample_resume_bytes, outreach_enabled=True)
    application = client.get(f"/api/v1/applications/{application_id}").json()

    response = client.get(
        "/api/v1/outreach-messages",
        params={
            "candidate_id": application["candidate_id"],
            "job_id": application["job_id"],
        },
    )
    assert response.status_code == 200
    assert response.json() is None


def test_get_latest_outreach_reflects_a_hand_edit_without_regenerating(
    client: TestClient, sample_resume_bytes: bytes
) -> None:
    """The dashboard's job detail panel loads this on open -- it has to show what's actually
    there (including a prior hand edit), not force a fresh regeneration just to view it."""
    application_id = _create_scored_application(client, sample_resume_bytes, outreach_enabled=True)
    application = client.get(f"/api/v1/applications/{application_id}").json()

    outreach = client.post(f"/api/v1/applications/{application_id}/outreach").json()
    message_id = outreach["linkedin_full"]["id"]
    client.patch(
        f"/api/v1/outreach-messages/{message_id}", json={"content": "My hand-edited version."}
    )

    response = client.get(
        "/api/v1/outreach-messages",
        params={
            "candidate_id": application["candidate_id"],
            "job_id": application["job_id"],
        },
    )
    assert response.status_code == 200
    latest = response.json()
    assert latest["linkedin_full"]["content"] == "My hand-edited version."
    assert latest["linkedin_full"]["is_user_edited"] is True
    assert latest["linkedin_connection"]["message_type"] == "linkedin_connection"
    assert latest["email"]["message_type"] == "email"


def test_get_latest_outreach_returns_the_newest_generation_not_the_first(
    client: TestClient, sample_resume_bytes: bytes
) -> None:
    application_id = _create_scored_application(client, sample_resume_bytes, outreach_enabled=True)
    application = client.get(f"/api/v1/applications/{application_id}").json()

    first = client.post(f"/api/v1/applications/{application_id}/outreach").json()
    second = client.post(f"/api/v1/applications/{application_id}/outreach").json()
    assert first["linkedin_full"]["id"] != second["linkedin_full"]["id"]

    response = client.get(
        "/api/v1/outreach-messages",
        params={
            "candidate_id": application["candidate_id"],
            "job_id": application["job_id"],
        },
    )
    assert response.json()["linkedin_full"]["id"] == second["linkedin_full"]["id"]


def test_patch_application_404s_for_unknown_id(client: TestClient) -> None:
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.patch(f"/api/v1/applications/{fake_id}", json={"status": "ARCHIVED"})
    assert response.status_code == 404


def test_generate_outreach_404s_for_unknown_application(client: TestClient) -> None:
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.post(f"/api/v1/applications/{fake_id}/outreach")
    assert response.status_code == 404


def test_list_applications_filters_by_candidate(
    client: TestClient, sample_resume_bytes: bytes
) -> None:
    app_id_1 = _create_scored_application(client, sample_resume_bytes, outreach_enabled=True)
    application_1 = client.get(f"/api/v1/applications/{app_id_1}").json()

    listed = client.get(
        "/api/v1/applications", params={"candidate_id": application_1["candidate_id"]}
    ).json()
    assert len(listed) == 1
    assert listed[0]["id"] == app_id_1


def test_list_applications_filters_by_status(
    client: TestClient, sample_resume_bytes: bytes
) -> None:
    app_id = _create_scored_application(client, sample_resume_bytes, outreach_enabled=True)
    application = client.get(f"/api/v1/applications/{app_id}").json()
    candidate_id = application["candidate_id"]

    client.patch(f"/api/v1/applications/{app_id}", json={"status": "ARCHIVED"})

    matching = client.get(
        "/api/v1/applications", params={"candidate_id": candidate_id, "status": "ARCHIVED"}
    ).json()
    assert len(matching) == 1

    non_matching = client.get(
        "/api/v1/applications", params={"candidate_id": candidate_id, "status": "DISCOVERED"}
    ).json()
    assert len(non_matching) == 0


def test_list_applications_filters_by_profile(
    client: TestClient, sample_resume_bytes: bytes
) -> None:
    app_id = _create_scored_application(client, sample_resume_bytes, outreach_enabled=True)
    application = client.get(f"/api/v1/applications/{app_id}").json()

    matching = client.get(
        "/api/v1/applications",
        params={
            "candidate_id": application["candidate_id"],
            "profile_id": application["profile_id"],
        },
    ).json()
    assert len(matching) == 1

    other_profile_id = "00000000-0000-0000-0000-000000000000"
    non_matching = client.get(
        "/api/v1/applications",
        params={"candidate_id": application["candidate_id"], "profile_id": other_profile_id},
    ).json()
    assert len(non_matching) == 0


def test_list_applications_includes_job_company_and_profile_details(
    client: TestClient, sample_resume_bytes: bytes
) -> None:
    """The cross-profile view (unlike the bare `ApplicationRead` returned by GET /{id}) has to
    carry enough to render a table row without a follow-up request per row."""
    app_id = _create_scored_application(client, sample_resume_bytes, outreach_enabled=True)
    application = client.get(f"/api/v1/applications/{app_id}").json()

    [row] = client.get(
        "/api/v1/applications", params={"candidate_id": application["candidate_id"]}
    ).json()
    assert row["job"]["title"] == "Data Engineer"
    assert row["company"]["name"] == "Acme Data"
    assert row["profile_key"] == "startup_outreach"
    assert row["profile_display_name"] == "Test Profile"
    assert row["fit_score"]["overall_score"] >= 0


def test_list_applications_filters_by_search_query(
    client: TestClient, sample_resume_bytes: bytes
) -> None:
    app_id = _create_scored_application(client, sample_resume_bytes, outreach_enabled=True)
    application = client.get(f"/api/v1/applications/{app_id}").json()
    candidate_id = application["candidate_id"]

    matching_by_job_title = client.get(
        "/api/v1/applications", params={"candidate_id": candidate_id, "q": "data engineer"}
    ).json()
    assert len(matching_by_job_title) == 1

    matching_by_company = client.get(
        "/api/v1/applications", params={"candidate_id": candidate_id, "q": "acme"}
    ).json()
    assert len(matching_by_company) == 1

    non_matching = client.get(
        "/api/v1/applications", params={"candidate_id": candidate_id, "q": "nonexistent widget"}
    ).json()
    assert len(non_matching) == 0
