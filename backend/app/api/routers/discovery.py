import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.search_profile import SearchProfile
from app.schemas.discovery import DiscoveryQuery, DiscoveryRunResult
from app.schemas.search_profile import SearchProfileRead
from app.services.applications import get_or_create_application
from app.services.discovery.base import CompanySource, JobBoardSource
from app.services.discovery.github_new_grad_list import GitHubNewGradListSource
from app.services.discovery.hn_who_is_hiring import HNWhoIsHiringSource
from app.services.discovery.upsert import CompanyJobUpsertService
from app.services.discovery.yc_directory import YCDirectorySource

router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])

# profile_key -> adapters configured for it, split by discovery pattern (see
# services/discovery/base.py). A profile can have both kinds at once.
_JOB_BOARD_ADAPTERS_BY_PROFILE_KEY: dict[str, list[type[JobBoardSource]]] = {
    "startup_outreach": [HNWhoIsHiringSource],
    "new_grad_2027": [GitHubNewGradListSource],
}
_COMPANY_ADAPTERS_BY_PROFILE_KEY: dict[str, list[type[CompanySource]]] = {
    "startup_outreach": [YCDirectorySource],
}


class DiscoveryRunRequest(BaseModel):
    profile_id: uuid.UUID


class _RunCounters:
    def __init__(self) -> None:
        self.sources_run: list[str] = []
        self.warnings: list[str] = []
        self.companies_created = 0
        self.jobs_created = 0


def _run_job_board_adapters(
    *,
    adapter_classes: list[type[JobBoardSource]],
    query: DiscoveryQuery,
    upsert_service: CompanyJobUpsertService,
    db: Session,
    profile: SearchProfileRead,
    counters: _RunCounters,
) -> None:
    for adapter_cls in adapter_classes:
        adapter = adapter_cls()
        counters.sources_run.append(adapter.name)
        try:
            discovered_jobs = adapter.search_jobs(query)
        except Exception as exc:  # noqa: BLE001 -- one bad source shouldn't fail the whole run
            counters.warnings.append(f"{adapter.name} failed: {exc}")
            continue

        for discovered_job in discovered_jobs:
            job, job_created, company_created = upsert_service.upsert_job(discovered_job)
            counters.jobs_created += int(job_created)
            counters.companies_created += int(company_created)
            get_or_create_application(
                db, candidate_id=profile.candidate_id, job_id=job.id, profile_id=profile.id
            )


def _run_company_adapters(
    *,
    adapter_classes: list[type[CompanySource]],
    query: DiscoveryQuery,
    upsert_service: CompanyJobUpsertService,
    db: Session,
    profile: SearchProfileRead,
    counters: _RunCounters,
) -> None:
    for adapter_cls in adapter_classes:
        adapter = adapter_cls()
        counters.sources_run.append(adapter.name)
        try:
            discovered_companies = adapter.search_companies(query)
        except Exception as exc:  # noqa: BLE001 -- one bad source shouldn't fail the whole run
            counters.warnings.append(f"{adapter.name} failed: {exc}")
            continue

        for discovered_company in discovered_companies:
            _, company_created = upsert_service.upsert_company(discovered_company)
            counters.companies_created += int(company_created)
            try:
                discovered_jobs = adapter.get_jobs(discovered_company)
            except Exception as exc:  # noqa: BLE001
                counters.warnings.append(
                    f"{adapter.name}: failed to get jobs for {discovered_company.name}: {exc}"
                )
                continue
            for discovered_job in discovered_jobs:
                job, job_created, _ = upsert_service.upsert_job(discovered_job)
                counters.jobs_created += int(job_created)
                get_or_create_application(
                    db, candidate_id=profile.candidate_id, job_id=job.id, profile_id=profile.id
                )


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

    query = DiscoveryQuery(
        role_filters=profile.config.role_filters,
        stage_filters=profile.config.stage_filters,
        location_filters=profile.config.location_filters,
    )
    upsert_service = CompanyJobUpsertService(db)
    counters = _RunCounters()

    _run_job_board_adapters(
        adapter_classes=_JOB_BOARD_ADAPTERS_BY_PROFILE_KEY.get(profile.profile_key, []),
        query=query,
        upsert_service=upsert_service,
        db=db,
        profile=profile,
        counters=counters,
    )
    _run_company_adapters(
        adapter_classes=_COMPANY_ADAPTERS_BY_PROFILE_KEY.get(profile.profile_key, []),
        query=query,
        upsert_service=upsert_service,
        db=db,
        profile=profile,
        counters=counters,
    )

    db.commit()
    return DiscoveryRunResult(
        profile_id=payload.profile_id,
        sources_run=counters.sources_run,
        companies_upserted=counters.companies_created,
        jobs_upserted=counters.jobs_created,
        warnings=counters.warnings,
    )
