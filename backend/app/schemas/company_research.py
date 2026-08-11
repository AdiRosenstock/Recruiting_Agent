import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompanyResearchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    fact_type: str
    statement: str
    is_inference: bool
    source_id: uuid.UUID | None
    confidence: float | None
    created_at: datetime


class CompanyResearchRunResult(BaseModel):
    company_id: uuid.UUID
    facts_created: int
    inferences_created: int
    warnings: list[str] = Field(default_factory=list)
