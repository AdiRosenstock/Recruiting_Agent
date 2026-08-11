import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_page_fetcher
from app.core.logging import log_agent_decision
from app.db.session import get_db
from app.models.company import Company
from app.models.fit_score import FitScore
from app.models.job import Job
from app.models.search_profile import SearchProfile
from app.schemas.company import CompanyRead
from app.schemas.fit_score import FitScoreRead
from app.schemas.job import JobRead
from app.schemas.search_profile import SearchProfileRead
from app.services.applications import get_or_create_application
from app.services.candidate_reader import get_candidate_profile
from app.services.research.fetcher import PageFetcher
from app.services.scoring.scorer import FitScorer
from app.services.visa_check import check_job_visa_sponsorship

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


class ScoreJobRequest(BaseModel):
    candidate_id: uuid.UUID
    profile_id: uuid.UUID


@router.post("/{job_id}/score", response_model=FitScoreRead, status_code=status.HTTP_201_CREATED)
def score_job(
    job_id: uuid.UUID, payload: ScoreJobRequest, db: Session = Depends(get_db)
) -> FitScoreRead:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    company = db.get(Company, job.company_id)
    if company is None:  # pragma: no cover -- FK guarantees this in practice
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    profile_row = db.get(SearchProfile, payload.profile_id)
    if profile_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Search profile not found"
        )

    candidate_profile = get_candidate_profile(db, payload.candidate_id)
    if candidate_profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    result = FitScorer().score(
        candidate=candidate_profile,
        job=JobRead.model_validate(job),
        company=CompanyRead.model_validate(company),
        profile=SearchProfileRead.model_validate(profile_row),
    )

    fit_score = FitScore(
        candidate_id=payload.candidate_id,
        job_id=job_id,
        profile_id=payload.profile_id,
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

    log_agent_decision(
        "job_scored",
        job_id=str(job_id),
        profile_id=str(payload.profile_id),
        overall_score=result.overall_score,
        tier=result.tier,
        weights_version=result.weights_version,
    )

    application = get_or_create_application(
        db, candidate_id=payload.candidate_id, job_id=job_id, profile_id=payload.profile_id
    )
    application.fit_score_id = fit_score.id

    db.commit()
    db.refresh(fit_score)
    return FitScoreRead.model_validate(fit_score)


@router.post("/{job_id}/check-visa-sponsorship", response_model=JobRead)
def check_visa_sponsorship(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    fetcher: PageFetcher = Depends(get_page_fetcher),
) -> JobRead:
    """Deterministic keyword scan (see services/visa_sponsorship.py) for whether the posting
    mentions visa sponsorship either way -- a lead to verify on the actual posting, never a
    confirmed fact. Only fetches the live posting page when there's no description already on
    file to search (see services/visa_check.py)."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    check_job_visa_sponsorship(job, fetcher=fetcher)
    db.commit()
    db.refresh(job)
    return JobRead.model_validate(job)
