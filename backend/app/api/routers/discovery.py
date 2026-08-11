import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.search_profile import SearchProfile
from app.schemas.discovery import DiscoveryRunResult
from app.schemas.search_profile import SearchProfileRead
from app.services.discovery.runner import run_discovery_for_profile

router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])


class DiscoveryRunRequest(BaseModel):
    profile_id: uuid.UUID


@router.post("/run", response_model=DiscoveryRunResult)
def run_discovery(
    payload: DiscoveryRunRequest, db: Session = Depends(get_db)
) -> DiscoveryRunResult:
    profile_row = db.get(SearchProfile, payload.profile_id)
    if profile_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Search profile not found"
        )
    profile = SearchProfileRead.model_validate(profile_row)

    counters = run_discovery_for_profile(db, profile)
    db.commit()

    return DiscoveryRunResult(
        profile_id=payload.profile_id,
        sources_run=counters.sources_run,
        companies_upserted=counters.companies_created,
        jobs_upserted=counters.jobs_created,
        jobs_scored=counters.jobs_scored,
        warnings=counters.warnings,
    )
