"""Runs every adapter configured for a profile and upserts what they find. Shared by
`POST /discovery/run` (api/routers/discovery.py) and the optional periodic scheduler
(services/scheduler.py) -- one implementation, two triggers (a request vs. a timer).
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.logging import log_agent_decision
from app.schemas.discovery import DiscoveryQuery
from app.schemas.search_profile import SearchProfileRead
from app.services.applications import get_or_create_application
from app.services.discovery.base import CompanySource, JobBoardSource
from app.services.discovery.github_new_grad_list import GitHubNewGradListSource
from app.services.discovery.hn_who_is_hiring import HNWhoIsHiringSource
from app.services.discovery.upsert import CompanyJobUpsertService
from app.services.discovery.yc_directory import YCDirectorySource

# profile_key -> adapters configured for it, split by discovery pattern (see
# services/discovery/base.py). A profile can have both kinds at once.
JOB_BOARD_ADAPTERS_BY_PROFILE_KEY: dict[str, list[type[JobBoardSource]]] = {
    "startup_outreach": [HNWhoIsHiringSource],
    "new_grad_2027": [GitHubNewGradListSource],
}
COMPANY_ADAPTERS_BY_PROFILE_KEY: dict[str, list[type[CompanySource]]] = {
    "startup_outreach": [YCDirectorySource],
}


@dataclass
class DiscoveryRunCounters:
    sources_run: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    companies_created: int = 0
    jobs_created: int = 0


def run_discovery_for_profile(db: Session, profile: SearchProfileRead) -> DiscoveryRunCounters:
    """Does NOT commit -- callers (an HTTP request, a scheduled job) own the transaction
    boundary, since they differ in whether other work should share it."""
    query = DiscoveryQuery(
        role_filters=profile.config.role_filters,
        stage_filters=profile.config.stage_filters,
        location_filters=profile.config.location_filters,
    )
    upsert_service = CompanyJobUpsertService(db)
    counters = DiscoveryRunCounters()

    _run_job_board_adapters(
        adapter_classes=JOB_BOARD_ADAPTERS_BY_PROFILE_KEY.get(profile.profile_key, []),
        query=query,
        upsert_service=upsert_service,
        db=db,
        profile=profile,
        counters=counters,
    )
    _run_company_adapters(
        adapter_classes=COMPANY_ADAPTERS_BY_PROFILE_KEY.get(profile.profile_key, []),
        query=query,
        upsert_service=upsert_service,
        db=db,
        profile=profile,
        counters=counters,
    )

    # One summary per run (not one log line per company/job -- that would drown a real discovery
    # run, which can add hundreds of rows, in noise) -- but every run, HTTP-triggered or
    # scheduler-triggered, since the scheduler has no HTTP response for anyone to see counters
    # in otherwise. This log line is the only durable record a scheduled run ever produces.
    log_agent_decision(
        "discovery_run_completed",
        profile_id=str(profile.id),
        profile_key=profile.profile_key,
        sources_run=counters.sources_run,
        companies_created=counters.companies_created,
        jobs_created=counters.jobs_created,
        warnings_count=len(counters.warnings),
    )
    return counters


def _run_job_board_adapters(
    *,
    adapter_classes: list[type[JobBoardSource]],
    query: DiscoveryQuery,
    upsert_service: CompanyJobUpsertService,
    db: Session,
    profile: SearchProfileRead,
    counters: DiscoveryRunCounters,
) -> None:
    for adapter_cls in adapter_classes:
        adapter = adapter_cls()
        counters.sources_run.append(adapter.name)
        try:
            discovered_jobs = adapter.search_jobs(query)
        except Exception as exc:  # noqa: BLE001 -- one bad source shouldn't fail the whole run
            counters.warnings.append(f"{adapter.name} failed: {exc}")
            log_agent_decision("discovery_adapter_failed", adapter=adapter.name, error=str(exc))
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
    counters: DiscoveryRunCounters,
) -> None:
    for adapter_cls in adapter_classes:
        adapter = adapter_cls()
        counters.sources_run.append(adapter.name)
        try:
            discovered_companies = adapter.search_companies(query)
        except Exception as exc:  # noqa: BLE001
            counters.warnings.append(f"{adapter.name} failed: {exc}")
            log_agent_decision("discovery_adapter_failed", adapter=adapter.name, error=str(exc))
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
