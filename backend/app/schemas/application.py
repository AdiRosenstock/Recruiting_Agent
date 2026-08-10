import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

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
