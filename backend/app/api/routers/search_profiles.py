import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.application import Application
from app.models.company import Company
from app.models.fit_score import FitScore
from app.models.job import Job
from app.models.search_profile import SearchProfile
from app.schemas.company import CompanyRead
from app.schemas.fit_score import FitScoreRead
from app.schemas.job import JobRead, JobWithScore
from app.schemas.search_profile import SearchProfileCreate, SearchProfileRead

router = APIRouter(prefix="/api/v1/search-profiles", tags=["search-profiles"])


@router.post("", response_model=SearchProfileRead, status_code=status.HTTP_201_CREATED)
def create_search_profile(
    payload: SearchProfileCreate, db: Session = Depends(get_db)
) -> SearchProfileRead:
    existing = (
        db.query(SearchProfile)
        .filter_by(candidate_id=payload.candidate_id, profile_key=payload.profile_key)
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Profile '{payload.profile_key}' already exists for this candidate.",
        )
    profile = SearchProfile(
        candidate_id=payload.candidate_id,
        profile_key=payload.profile_key,
        display_name=payload.display_name,
        outreach_enabled=payload.outreach_enabled,
        config=payload.config.model_dump(),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return SearchProfileRead.model_validate(profile)


@router.get("", response_model=list[SearchProfileRead])
def list_search_profiles(
    candidate_id: uuid.UUID, db: Session = Depends(get_db)
) -> list[SearchProfileRead]:
    profiles = db.query(SearchProfile).filter_by(candidate_id=candidate_id).all()
    return [SearchProfileRead.model_validate(p) for p in profiles]


@router.get("/{profile_id}/jobs", response_model=list[JobWithScore])
def list_profile_jobs(profile_id: uuid.UUID, db: Session = Depends(get_db)) -> list[JobWithScore]:
    """Every job tracked under this profile (via its `applications` row -- see
    services/applications.py), highest fit score first. Jobs discovered but not yet scored come
    back with `fit_score: null` rather than being omitted, so nothing found silently disappears.
    """
    if db.get(SearchProfile, profile_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Search profile not found"
        )

    applications = db.query(Application).filter_by(profile_id=profile_id).all()

    results: list[JobWithScore] = []
    for application in applications:
        job = db.get(Job, application.job_id)
        if job is None:
            continue
        company = db.get(Company, job.company_id)
        if company is None:
            continue
        fit_score = db.get(FitScore, application.fit_score_id) if application.fit_score_id else None
        results.append(
            JobWithScore(
                application_id=application.id,
                application_status=application.status,
                job=JobRead.model_validate(job),
                company=CompanyRead.model_validate(company),
                fit_score=FitScoreRead.model_validate(fit_score) if fit_score else None,
            )
        )

    results.sort(key=lambda r: r.fit_score.overall_score if r.fit_score else -1, reverse=True)
    return results
