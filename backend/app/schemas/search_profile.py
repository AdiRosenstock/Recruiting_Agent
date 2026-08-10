"""A `SearchProfile`'s `config` shape. Kept as its own small model (rather than a bare dict)
so the fields adapters/scorer read have a documented, validated contract."""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class SearchProfileConfig(BaseModel):
    # Overrides for FitScoreWeights' defaults, e.g. {"stage": 0.0}. Missing keys keep the
    # scorer's built-in default for that component -- see services/scoring/weights.py.
    weights: dict[str, float] = Field(default_factory=dict)
    role_filters: list[str] = Field(default_factory=list)
    stage_filters: list[str] = Field(default_factory=list)
    location_filters: list[str] = Field(default_factory=list)
    notes: str | None = None


class SearchProfileCreate(BaseModel):
    candidate_id: uuid.UUID
    profile_key: str
    display_name: str
    outreach_enabled: bool = False
    config: SearchProfileConfig = Field(default_factory=SearchProfileConfig)


class SearchProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    profile_key: str
    display_name: str
    outreach_enabled: bool
    config: SearchProfileConfig
