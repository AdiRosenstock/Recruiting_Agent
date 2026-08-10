import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.company import Company
from app.models.job import Job
from app.schemas.company import CompanyCreate, CompanyRead
from app.schemas.job import JobCreate, JobRead
from app.services.discovery.upsert import normalize_company_name

router = APIRouter(prefix="/api/v1/companies", tags=["companies"])


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)) -> CompanyRead:
    normalized = normalize_company_name(payload.name)
    existing = (
        db.query(Company)
        .filter_by(normalized_name=normalized, website=payload.website)
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A company with this name/website already exists.",
        )
    company = Company(normalized_name=normalized, **payload.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return CompanyRead.model_validate(company)


@router.get("/{company_id}", response_model=CompanyRead)
def read_company(company_id: uuid.UUID, db: Session = Depends(get_db)) -> CompanyRead:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return CompanyRead.model_validate(company)


@router.post("/{company_id}/jobs", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(company_id: uuid.UUID, payload: JobCreate, db: Session = Depends(get_db)) -> JobRead:
    if db.get(Company, company_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    existing = db.query(Job).filter_by(job_url=payload.job_url).one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A job with this URL already exists."
        )
    job = Job(company_id=company_id, **payload.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return JobRead.model_validate(job)
