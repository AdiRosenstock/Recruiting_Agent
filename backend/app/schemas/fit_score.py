import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Tier = Literal["excellent", "strong", "worth_reviewing", "weak", "ignore"]


class FitScoreComponent(BaseModel):
    score: float = Field(ge=0, le=1)
    explanation: str


class FitScoreResult(BaseModel):
    """What `FitScorer.score()` returns, before persistence -- one component per weight in
    `FitScoreWeights`."""

    technical: FitScoreComponent
    role: FitScoreComponent
    ai_data: FitScoreComponent
    experience: FitScoreComponent
    stage: FitScoreComponent
    location: FitScoreComponent
    domain: FitScoreComponent
    overall_score: float = Field(ge=0, le=100)
    tier: Tier
    strengths: list[str]
    gaps: list[str]
    weights_version: str


class FitScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    profile_id: uuid.UUID
    technical_match: float
    role_match: float
    ai_data_match: float
    experience_match: float
    stage_match: float
    location_match: float
    domain_match: float
    overall_score: float
    tier: str
    strengths: list[str]
    gaps: list[str]
    weights_version: str
    created_at: datetime
