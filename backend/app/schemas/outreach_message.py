import uuid

from pydantic import BaseModel, ConfigDict, Field


class OutreachMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    contact_id: uuid.UUID | None
    message_type: str
    content: str
    personalization_rationale: str | None
    is_user_edited: bool
    prompt_version: str
    generated_by: str


class OutreachMessageUpdate(BaseModel):
    """Human edits to a drafted message -- flips `is_user_edited` to True."""

    content: str


class OutreachGenerationResult(BaseModel):
    """What `POST /applications/{id}/outreach` returns -- all three variants generated together
    from the same context, so they stay consistent with each other."""

    linkedin_full: OutreachMessageRead
    linkedin_connection: OutreachMessageRead
    email: OutreachMessageRead
    warnings: list[str] = Field(default_factory=list)
