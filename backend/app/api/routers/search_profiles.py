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
from app.schemas.search_profile import SearchProfileCreate, SearchProfileRead, SearchProfileUpdate

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


@router.get("/{profile_id}", response_model=SearchProfileRead)
def read_search_profile(profile_id: uuid.UUID, db: Session = Depends(get_db)) -> SearchProfileRead:
    profile = db.get(SearchProfile, profile_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Search profile not found"
        )
    return SearchProfileRead.model_validate(profile)


@router.patch("/{profile_id}", response_model=SearchProfileRead)
def update_search_profile(
    profile_id: uuid.UUID, payload: SearchProfileUpdate, db: Session = Depends(get_db)
) -> SearchProfileRead:
    profile = db.get(SearchProfile, profile_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Search profile not found"
        )
    if payload.display_name is not None:
        profile.display_name = payload.display_name
    if payload.outreach_enabled is not None:
        profile.outreach_enabled = payload.outreach_enabled
    if payload.config is not None:
        profile.config = payload.config.model_dump()
    db.commit()
    db.refresh(profile)
    return SearchProfileRead.model_validate(profile)


@router.get("/{profile_id}/jobs", response_model=list[JobWithScore])
def list_profile_jobs(profile_id: uuid.UUID, db: Session = Depends(get_db)) -> list[JobWithScore]:
    """Every job tracked under this profile (via its `applications` row -- see
    services/applications.py), highest fit score first. Jobs discovered but not yet scored come
    back with `fit_score: null` rather than being omitted, so nothing found silently disappears.

    One joined query, not one-plus-three-per-application -- this list can run into the hundreds
    (a single discovery run against the YC directory alone can add 100 companies), so avoiding
    an N+1 round-trip pattern here actually matters, unlike most other endpoints in this app.
    """
    if db.get(SearchProfile, profile_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Search profile not found"
        )

    rows = (
        db.query(Application, Job, Company, FitScore)
        .join(Job, Application.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .outerjoin(FitScore, Application.fit_score_id == FitScore.id)
        .filter(Application.profile_id == profile_id)
        .all()
    )

    results = [
        JobWithScore(
            application_id=application.id,
            application_status=application.status,
            job=JobRead.model_validate(job),
            company=CompanyRead.model_validate(company),
            fit_score=FitScoreRead.model_validate(fit_score) if fit_score else None,
        )
        for application, job, company, fit_score in rows
    ]
    results.sort(key=lambda r: r.fit_score.overall_score if r.fit_score else -1, reverse=True)
    return results
