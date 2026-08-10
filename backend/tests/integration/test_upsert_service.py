from sqlalchemy.orm import Session

from app.schemas.discovery import DiscoveredCompany, DiscoveredJob
from app.services.discovery.upsert import CompanyJobUpsertService


def _discovered_company(**overrides: object) -> DiscoveredCompany:
    defaults: dict[str, object] = {
        "name": "Acme Inc.",
        "website": "https://acme.com",
        "location": "New York, NY",
        "industry": "Fintech",
        "description": "We build things.",
        "funding_stage": "seed",
        "source_url": "https://source.example/acme",
        "source_type": "manual",
    }
    defaults.update(overrides)
    return DiscoveredCompany(**defaults)  # type: ignore[arg-type]


def _discovered_job(**overrides: object) -> DiscoveredJob:
    defaults: dict[str, object] = {
        "title": "Backend Engineer",
        "job_url": "https://acme.com/jobs/1",
        "location": "New York, NY",
        "description": "Build the backend.",
        "work_mode": "hybrid",
        "posted_date": None,
        "deadline_date": None,
        "company": _discovered_company(),
        "source_url": "https://source.example/acme/jobs/1",
        "source_type": "manual",
    }
    defaults.update(overrides)
    return DiscoveredJob(**defaults)  # type: ignore[arg-type]


def test_upsert_company_dedups_by_normalized_name_and_website(db_session: Session) -> None:
    service = CompanyJobUpsertService(db_session)
    company1, created1 = service.upsert_company(_discovered_company(name="Acme Inc."))
    company2, created2 = service.upsert_company(_discovered_company(name="ACME, INC."))

    assert created1 is True
    assert created2 is False
    assert company1.id == company2.id


def test_upsert_company_backfills_blank_fields_without_overwriting(db_session: Session) -> None:
    service = CompanyJobUpsertService(db_session)
    company1, _ = service.upsert_company(_discovered_company(industry=None, description=None))
    assert company1.industry is None

    company2, created = service.upsert_company(
        _discovered_company(industry="Fintech", description="We build things.")
    )
    assert created is False
    assert company2.id == company1.id
    assert company2.industry == "Fintech"  # backfilled
    assert company2.description == "We build things."

    # A later sighting with blank fields must never erase what's already there.
    company3, _ = service.upsert_company(_discovered_company(industry=None, description=None))
    assert company3.industry == "Fintech"


def test_upsert_job_dedups_by_job_url(db_session: Session) -> None:
    service = CompanyJobUpsertService(db_session)
    job1, job_created1, _ = service.upsert_job(_discovered_job())
    job2, job_created2, _ = service.upsert_job(_discovered_job())

    assert job_created1 is True
    assert job_created2 is False
    assert job1.id == job2.id


def test_upsert_job_links_source_provenance(db_session: Session) -> None:
    from app.models.source import CompanySourceLink

    service = CompanyJobUpsertService(db_session)
    job, _, _ = service.upsert_job(_discovered_job())

    link = db_session.query(CompanySourceLink).filter_by(company_id=job.company_id).one_or_none()
    assert link is not None
