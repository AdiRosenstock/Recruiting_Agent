import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompanyCreate(BaseModel):
    name: str
    website: str | None = None
    location: str | None = None
    industry: str | None = None
    description: str | None = None
    founders: list[str] = Field(default_factory=list)
    funding_stage: str | None = None
    amount_raised_usd: int | None = None
    investors: list[str] = Field(default_factory=list)
    employee_count: int | None = None
    technologies: list[str] = Field(default_factory=list)


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    normalized_name: str
    website: str | None
    location: str | None
    industry: str | None
    description: str | None
    founders: list[str]
    funding_stage: str | None
    amount_raised_usd: int | None
    investors: list[str]
    employee_count: int | None
    technologies: list[str]
    date_discovered: datetime
    date_last_checked: datetime | None
