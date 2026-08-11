import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.company import CompanyRead
from app.schemas.fit_score import FitScoreRead
from app.schemas.job import JobRead

ApplicationStatus = Literal[
    "DISCOVERED",
    "RESEARCHING",
    "REVIEW",
    "READY_TO_CONTACT",
    "CONTACTED",
    "RESPONDED",
    "INTERVIEW",
    "REJECTED",
    "ARCHIVED",
]


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    profile_id: uuid.UUID
    contact_id: uuid.UUID | None
    fit_score_id: uuid.UUID | None
    outreach_message_id: uuid.UUID | None
    status: str
    notes: str | None
    contacted_at: datetime | None
    responded_at: datetime | None


class ApplicationWithDetails(BaseModel):
    """What `GET /api/v1/applications` returns -- the cross-profile "everything, filterable and
    searchable" view. `ApplicationRead`'s bare id/status fields would make a dashboard table
    issue one extra request per row just to show a job title; this carries the job/company/score
    inline instead (same reasoning as `JobWithScore` for the per-profile table), plus which
    profile each row belongs to, since that's the whole point of a view that spans profiles.
    """

    id: uuid.UUID
    candidate_id: uuid.UUID
    profile_id: uuid.UUID
    profile_key: str
    profile_display_name: str
    contact_id: uuid.UUID | None
    fit_score_id: uuid.UUID | None
    outreach_message_id: uuid.UUID | None
    status: str
    notes: str | None
    contacted_at: datetime | None
    responded_at: datetime | None
    updated_at: datetime
    job: JobRead
    company: CompanyRead
    fit_score: FitScoreRead | None


class ApplicationUpdate(BaseModel):
    """Human-driven state changes -- approve/edit/skip/mark-contacted all go through this.
    Nothing here is ever set automatically by an agent; status transitions are a human action.
    """

    status: ApplicationStatus | None = None
    notes: str | None = None
    contact_id: uuid.UUID | None = None
