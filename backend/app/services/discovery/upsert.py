"""Dedups and persists whatever a discovery adapter finds. Both `CompanySource` and
`JobBoardSource` adapters feed into this identically -- neither needs to know how dedup or
provenance-tracking works.
"""

import re
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.job import Job
from app.models.source import CompanySourceLink, Source
from app.schemas.discovery import DiscoveredCompany, DiscoveredJob

_SUFFIX_RE = re.compile(r"\b(inc|llc|ltd|corp|co|company)\.?\b", re.IGNORECASE)
_PUNCTUATION_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_company_name(name: str) -> str:
    """Lowercase, drop common legal suffixes/punctuation, collapse whitespace -- used as half of
    the dedup key in `companies.normalized_name` (paired with `website`)."""
    without_suffix = _SUFFIX_RE.sub("", name)
    without_punctuation = _PUNCTUATION_RE.sub("", without_suffix)
    return _WHITESPACE_RE.sub(" ", without_punctuation).strip().lower()


class CompanyJobUpsertService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_or_create_source(
        self, *, url: str, source_type: str, title: str | None = None
    ) -> Source:
        existing = self._db.query(Source).filter_by(url=url, source_type=source_type).one_or_none()
        if existing is not None:
            return existing
        source = Source(url=url, source_type=source_type, title=title, fetched_at=datetime.now(UTC))
        self._db.add(source)
        self._db.flush()
        return source

    def upsert_company(self, discovered: DiscoveredCompany) -> tuple[Company, bool]:
        """Returns `(company, created)` -- `created=False` means an existing company (matched by
        `normalized_name` + `website`) was refreshed rather than inserted."""
        normalized = normalize_company_name(discovered.name)
        existing = (
            self._db.query(Company)
            .filter_by(normalized_name=normalized, website=discovered.website)
            .one_or_none()
        )
        if existing is not None:
            existing.date_last_checked = datetime.now(UTC)
            self._backfill(existing, discovered)
            company, created = existing, False
        else:
            company = Company(
                name=discovered.name,
                normalized_name=normalized,
                website=discovered.website,
                location=discovered.location,
                industry=discovered.industry,
                description=discovered.description,
                funding_stage=discovered.funding_stage,
            )
            self._db.add(company)
            self._db.flush()
            created = True

        source = self.get_or_create_source(
            url=discovered.source_url, source_type=discovered.source_type
        )
        self._link_source(company_id=company.id, source_id=source.id)
        return company, created

    def upsert_job(self, discovered: DiscoveredJob) -> tuple[Job, bool, bool]:
        """Returns `(job, job_created, company_created)`."""
        company, company_created = self.upsert_company(discovered.company)
        source = self.get_or_create_source(
            url=discovered.source_url, source_type=discovered.source_type
        )

        existing = self._db.query(Job).filter_by(job_url=discovered.job_url).one_or_none()
        if existing is not None:
            existing.date_last_checked = datetime.now(UTC)
            return existing, False, company_created

        job = Job(
            company_id=company.id,
            title=discovered.title,
            job_url=discovered.job_url,
            location=discovered.location,
            description=discovered.description,
            work_mode=discovered.work_mode,
            posted_date=discovered.posted_date,
            deadline_date=discovered.deadline_date,
            source_id=source.id,
        )
        self._db.add(job)
        self._db.flush()
        return job, True, company_created

    @staticmethod
    def _backfill(company: Company, discovered: DiscoveredCompany) -> None:
        """Fill in fields a previous, less-informative sighting left empty -- never overwrite an
        existing value with a blank one."""
        if not company.location and discovered.location:
            company.location = discovered.location
        if not company.industry and discovered.industry:
            company.industry = discovered.industry
        if not company.description and discovered.description:
            company.description = discovered.description
        if not company.funding_stage and discovered.funding_stage:
            company.funding_stage = discovered.funding_stage

    def _link_source(self, *, company_id: uuid.UUID, source_id: uuid.UUID) -> None:
        existing_link = self._db.get(CompanySourceLink, (company_id, source_id))
        if existing_link is None:
            self._db.add(CompanySourceLink(company_id=company_id, source_id=source_id))
