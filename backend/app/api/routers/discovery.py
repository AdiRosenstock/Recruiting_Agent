import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.search_profile import SearchProfile
from app.schemas.discovery import DiscoveryQuery, DiscoveryRunResult
from app.schemas.search_profile import SearchProfileRead
from app.services.applications import get_or_create_application
from app.services.discovery.base import JobBoardSource
from app.services.discovery.github_new_grad_list import GitHubNewGradListSource
from app.services.discovery.hn_who_is_hiring import HNWhoIsHiringSource
from app.services.discovery.upsert import CompanyJobUpsertService

router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])

# profile_key -> adapters configured for it. Both current adapters are JobBoardSource; a
# CompanySource-based profile (YC/Wellfound/VC portfolios, Phase 2b/4) would run through the
# same upsert path via `upsert_job`'s inline company.
_ADAPTERS_BY_PROFILE_KEY: dict[str, list[type[JobBoardSource]]] = {
    "startup_outreach": [HNWhoIsHiringSource],
    "new_grad_2027": [GitHubNewGradListSource],
}


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

    adapter_classes = _ADAPTERS_BY_PROFILE_KEY.get(profile.profile_key, [])
    query = DiscoveryQuery(
        role_filters=profile.config.role_filters,
        stage_filters=profile.config.stage_filters,
        location_filters=profile.config.location_filters,
    )

    upsert_service = CompanyJobUpsertService(db)
    warnings: list[str] = []
    sources_run: list[str] = []
    companies_created = 0
    jobs_created = 0

    for adapter_cls in adapter_classes:
        adapter = adapter_cls()
        sources_run.append(adapter.name)
        try:
            discovered_jobs = adapter.search_jobs(query)
        except Exception as exc:  # noqa: BLE001 -- one bad source shouldn't fail the whole run
            warnings.append(f"{adapter.name} failed: {exc}")
            continue

        for discovered_job in discovered_jobs:
            job, job_created, company_created = upsert_service.upsert_job(discovered_job)
            jobs_created += int(job_created)
            companies_created += int(company_created)
            get_or_create_application(
                db, candidate_id=profile.candidate_id, job_id=job.id, profile_id=profile.id
            )

    db.commit()
    return DiscoveryRunResult(
        profile_id=payload.profile_id,
        sources_run=sources_run,
        companies_upserted=companies_created,
        jobs_upserted=jobs_created,
        warnings=warnings,
    )
