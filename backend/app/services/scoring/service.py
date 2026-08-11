"""Scores a job and persists it -- the one place that turns a `FitScorer` result into a
`FitScore` row linked onto an `Application`. Shared by `POST /jobs/{id}/score` (a human
re-scoring one job from the dashboard) and `run_discovery_for_profile` (scoring every job
automatically as it's discovered, so a fit score is there to look at without a manual click --
see services/discovery/runner.py). One implementation, two triggers, same as the
request-vs-scheduler split for discovery itself.
"""

import uuid

from sqlalchemy.orm import Session

from app.core.logging import log_agent_decision
from app.models.application import Application
from app.models.company import Company
from app.models.fit_score import FitScore
from app.models.job import Job
from app.schemas.candidate import CandidateProfile
from app.schemas.company import CompanyRead
from app.schemas.job import JobRead
from app.schemas.search_profile import SearchProfileRead
from app.services.scoring.scorer import FitScorer


def score_and_persist(
    db: Session,
    *,
    candidate: CandidateProfile,
    job: Job,
    company: Company,
    profile: SearchProfileRead,
    application: Application,
) -> FitScore:
    """Scores `job` for `candidate` under `profile`, persists the result, and links it onto
    `application`. Does not commit -- caller owns the transaction boundary (matches every other
    service function here, e.g. `CompanyJobUpsertService`)."""
    result = FitScorer().score(
        candidate=candidate,
        job=JobRead.model_validate(job),
        company=CompanyRead.model_validate(company),
        profile=profile,
    )

    fit_score = FitScore(
        candidate_id=candidate.id,
        job_id=job.id,
        profile_id=profile.id,
        technical_match=result.technical.score,
        role_match=result.role.score,
        ai_data_match=result.ai_data.score,
        experience_match=result.experience.score,
        stage_match=result.stage.score,
        location_match=result.location.score,
        domain_match=result.domain.score,
        overall_score=result.overall_score,
        tier=result.tier,
        strengths=result.strengths,
        gaps=result.gaps,
        weights_version=result.weights_version,
    )
    db.add(fit_score)
    db.flush()
    application.fit_score_id = fit_score.id

    log_agent_decision(
        "job_scored",
        job_id=str(job.id),
        profile_id=str(profile.id),
        overall_score=result.overall_score,
        tier=result.tier,
        weights_version=result.weights_version,
    )
    return fit_score


def score_if_unscored(
    db: Session,
    *,
    candidate: CandidateProfile | None,
    job: Job,
    company: Company,
    profile: SearchProfileRead,
    application: Application,
) -> uuid.UUID | None:
    """Discovery's entry point: score `application` only if it doesn't already have a score
    (never overwrites a re-scored/edited history -- same "don't touch what's already there"
    rule as `CompanyJobUpsertService._backfill`). Returns None, without raising, when there's no
    candidate profile yet to score against -- discovery still has to work before a resume has
    been uploaded, just without scores until then."""
    if application.fit_score_id is not None or candidate is None:
        return None
    fit_score = score_and_persist(
        db, candidate=candidate, job=job, company=company, profile=profile, application=application
    )
    return fit_score.id
