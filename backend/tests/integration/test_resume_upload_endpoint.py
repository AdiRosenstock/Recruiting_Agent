"""End-to-end test of the Phase 1 MVP flow: create candidate -> upload resume -> parsed,
evidence-validated profile persisted and returned -> GET returns the same data.

Runs against the real Dockerized Postgres (via the `client`/`db_session` fixtures) with
LLM_PROVIDER=stub (the repo default), so no API key is required.
"""

from fastapi.testclient import TestClient


def _create_candidate(client: TestClient) -> str:
    response = client.post("/api/v1/candidates", json={"full_name": "Placeholder Name"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_full_resume_upload_flow(client: TestClient, sample_resume_bytes: bytes) -> None:
    candidate_id = _create_candidate(client)

    upload_response = client.post(
        f"/api/v1/candidates/{candidate_id}/resume",
        files={"file": ("resume.pdf", sample_resume_bytes, "application/pdf")},
    )
    assert upload_response.status_code == 200, upload_response.text
    payload = upload_response.json()

    profile = payload["profile"]
    assert profile["id"] == candidate_id
    # Stub provider found the candidate's actual name at the top of the resume.
    assert "Rosenstock" in profile["full_name"]
    assert profile["email"] == "adirosenstock2026@u.northwestern.edu"

    skill_names = {s["skill_name"] for s in profile["skills"]}
    assert "python" in skill_names
    assert "sql" in skill_names
    python_skill = next(s for s in profile["skills"] if s["skill_name"] == "python")
    assert python_skill["verified"] is True
    assert python_skill["evidence"], "skill claims must carry evidence"

    # Stub provider doesn't reconstruct education/experience -- documented limitation surfaced
    # via the profile summary's `gaps`, since the (empty) evidence-validation `warnings` list
    # only flags claims that fail verification, and the stub's own evidence trivially
    # self-verifies (it's pulled straight from the same raw text).
    assert profile["education"] == []
    assert any("stub" in gap.lower() for gap in profile["summary"]["gaps"])

    get_response = client.get(f"/api/v1/candidates/{candidate_id}")
    assert get_response.status_code == 200
    assert get_response.json()["full_name"] == profile["full_name"]
    assert get_response.json()["active_resume_id"] == payload["resume_id"]


def test_upload_rejects_non_pdf(client: TestClient) -> None:
    candidate_id = _create_candidate(client)

    response = client.post(
        f"/api/v1/candidates/{candidate_id}/resume",
        files={"file": ("resume.txt", b"not a pdf", "text/plain")},
    )
    assert response.status_code == 415


def test_upload_for_unknown_candidate_returns_404(
    client: TestClient, sample_resume_bytes: bytes
) -> None:
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.post(
        f"/api/v1/candidates/{fake_id}/resume",
        files={"file": ("resume.pdf", sample_resume_bytes, "application/pdf")},
    )
    assert response.status_code == 404


def test_get_unknown_candidate_returns_404(client: TestClient) -> None:
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/candidates/{fake_id}")
    assert response.status_code == 404
