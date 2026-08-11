"""Integration tests for score_and_persist/score_if_unscored (app/services/scoring/service.py)
-- real Postgres via the db_session fixture, ORM rows created directly (not through the API)
since this is testing the service layer discovery/the scoring endpoint both sit on top of.
"""

import uuid

from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.candidate import Candidate
from app.models.company import Company
from app.models.fit_score import FitScore
from app.models.job import Job
from app.models.search_profile import SearchProfile
from app.schemas.candidate import CandidateProfile
from app.schemas.search_profile import SearchProfileConfig, SearchProfileRead
from app.services.scoring.service import score_and_persist, score_if_unscored


def _make_candidate_row(db: Session) -> Candidate:
    candidate = Candidate(full_name="Test Candidate")
    db.add(candidate)
    db.flush()
    return candidate


def _make_candidate_profile(candidate_id: uuid.UUID) -> CandidateProfile:
    return CandidateProfile(
        id=candidate_id,
        full_name="Test Candidate",
        email=None,
        phone=None,
        primary_location=None,
        links={},
        education=[],
        experiences=[],
        projects=[],
        skills=[],
        preferences=None,
        summary=None,
        active_resume_id=None,
    )


def _make_company(db: Session) -> Company:
    company = Company(name="Acme", normalized_name="acme")
    db.add(company)
    db.flush()
    return company


def _make_job(db: Session, company_id: uuid.UUID) -> Job:
    job = Job(
        company_id=company_id,
        title="Backend Engineer",
        job_url=f"https://acme.example/jobs/{uuid.uuid4()}",
    )
    db.add(job)
    db.flush()
    return job


def _make_profile_row(db: Session, candidate_id: uuid.UUID) -> SearchProfile:
    profile = SearchProfile(
        candidate_id=candidate_id,
        profile_key="startup_outreach",
        display_name="Startup Outreach",
        outreach_enabled=True,
        config={},
    )
    db.add(profile)
    db.flush()
    return profile


def _make_application(
    db: Session, *, candidate_id: uuid.UUID, job_id: uuid.UUID, profile_id: uuid.UUID
) -> Application:
    application = Application(candidate_id=candidate_id, job_id=job_id, profile_id=profile_id)
    db.add(application)
    db.flush()
    return application


def test_score_and_persist_creates_a_fit_score_and_links_the_application(
    db_session: Session,
) -> None:
    candidate_row = _make_candidate_row(db_session)
    company = _make_company(db_session)
    job = _make_job(db_session, company.id)
    profile_row = _make_profile_row(db_session, candidate_row.id)
    application = _make_application(
        db_session, candidate_id=candidate_row.id, job_id=job.id, profile_id=profile_row.id
    )
    profile = SearchProfileRead(
        id=profile_row.id,
        candidate_id=candidate_row.id,
        profile_key="startup_outreach",
        display_name="Startup Outreach",
        outreach_enabled=True,
        config=SearchProfileConfig(),
    )

    fit_score = score_and_persist(
        db_session,
        candidate=_make_candidate_profile(candidate_row.id),
        job=job,
        company=company,
        profile=profile,
        application=application,
    )

    assert application.fit_score_id == fit_score.id
    assert 0 <= fit_score.overall_score <= 100
    assert fit_score.tier in ("excellent", "strong", "worth_reviewing", "weak", "ignore")


def test_score_if_unscored_skips_when_candidate_is_none(db_session: Session) -> None:
    candidate_row = _make_candidate_row(db_session)
    company = _make_company(db_session)
    job = _make_job(db_session, company.id)
    profile_row = _make_profile_row(db_session, candidate_row.id)
    application = _make_application(
        db_session, candidate_id=candidate_row.id, job_id=job.id, profile_id=profile_row.id
    )
    profile = SearchProfileRead(
        id=profile_row.id,
        candidate_id=candidate_row.id,
        profile_key="startup_outreach",
        display_name="Startup Outreach",
        outreach_enabled=True,
        config=SearchProfileConfig(),
    )

    result = score_if_unscored(
        db_session,
        candidate=None,
        job=job,
        company=company,
        profile=profile,
        application=application,
    )

    assert result is None
    assert application.fit_score_id is None


def test_score_if_unscored_never_overwrites_an_existing_score(db_session: Session) -> None:
    candidate_row = _make_candidate_row(db_session)
    company = _make_company(db_session)
    job = _make_job(db_session, company.id)
    profile_row = _make_profile_row(db_session, candidate_row.id)
    application = _make_application(
        db_session, candidate_id=candidate_row.id, job_id=job.id, profile_id=profile_row.id
    )
    profile = SearchProfileRead(
        id=profile_row.id,
        candidate_id=candidate_row.id,
        profile_key="startup_outreach",
        display_name="Startup Outreach",
        outreach_enabled=True,
        config=SearchProfileConfig(),
    )
    candidate = _make_candidate_profile(candidate_row.id)

    first_id = score_if_unscored(
        db_session,
        candidate=candidate,
        job=job,
        company=company,
        profile=profile,
        application=application,
    )
    assert first_id is not None

    second_result = score_if_unscored(
        db_session,
        candidate=candidate,
        job=job,
        company=company,
        profile=profile,
        application=application,
    )

    assert second_result is None  # not re-scored
    assert application.fit_score_id == first_id
    # exactly one fit_scores row exists for this job/profile pair -- no silent duplicate
    assert (
        db_session.query(FitScore).filter_by(job_id=job.id, profile_id=profile_row.id).count() == 1
    )
