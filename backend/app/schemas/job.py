import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.company import CompanyRead
from app.schemas.fit_score import FitScoreRead


class JobCreate(BaseModel):
    title: str
    job_url: str
    location: str | None = None
    description: str | None = None
    experience_requirements: str | None = None
    technologies: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    compensation_min: int | None = None
    compensation_max: int | None = None
    compensation_currency: str | None = None
    work_mode: str | None = None
    posted_date: date | None = None
    deadline_date: date | None = None


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    title: str
    location: str | None
    job_url: str
    description: str | None
    experience_requirements: str | None
    technologies: list[str]
    responsibilities: list[str]
    compensation_min: int | None
    compensation_max: int | None
    compensation_currency: str | None
    work_mode: str | None
    posted_date: date | None
    deadline_date: date | None
    status: str
    source_id: uuid.UUID | None
    date_discovered: datetime
    date_last_checked: datetime | None


class JobWithScore(BaseModel):
    """What `GET /search-profiles/{id}/jobs` returns -- the data the dashboard renders. Includes
    `application_id`/`application_status` (not just the job/score) because every subsequent
    action -- generate outreach, mark contacted, add notes -- is keyed off the application, not
    the job; without this the API would have no way to look an application id up at all.
    """

    application_id: uuid.UUID
    application_status: str
    job: JobRead
    company: CompanyRead
    fit_score: FitScoreRead | None
