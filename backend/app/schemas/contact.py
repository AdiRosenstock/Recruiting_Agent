import uuid

from pydantic import BaseModel, ConfigDict


class ContactCreate(BaseModel):
    name: str
    title: str | None = None
    public_profile_url: str | None = None
    email: str | None = None


class ContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    title: str | None
    public_profile_url: str | None
    email: str | None
    source_id: uuid.UUID | None
    priority_rank: int | None
    rationale: str | None
