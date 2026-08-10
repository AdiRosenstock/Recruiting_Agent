"""API/domain-facing candidate schemas -- the trusted, post-validation shape of a candidate
profile. Contrast with `schemas.llm_extraction`, which is the untrusted shape an LLM fills in.
"""

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class CandidateCreate(BaseModel):
    full_name: str
    email: str | None = None
    phone: str | None = None
    primary_location: str | None = None
    links: dict[str, str] = Field(default_factory=dict)


class EvidenceSnippet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snippet_text: str
    experience_id: uuid.UUID | None = None
    verified: bool


class SkillClaim(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    skill_name: str
    category: str
    confidence: float
    verified: bool
    evidence: list[EvidenceSnippet] = Field(default_factory=list)


class EducationEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    institution: str
    degree: str | None
    field_of_study: str | None
    gpa: str | None
    location: str | None
    start_date: date | None
    end_date: date | None
    graduation_date: date | None
    honors: str | None
    evidence_snippet: str


class ExperienceEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    organization: str
    title: str
    location: str | None
    start_date: date | None
    end_date: date | None
    is_current: bool
    description: str | None
    evidence_snippet: str


class ProjectEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    technologies: list[str]
    url: str | None
    evidence_snippet: str


class CandidatePreferencesSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    desired_roles: list[str]
    desired_stages: list[str]
    desired_locations: list[str]
    notes: str | None


class ProfileSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    strengths: list[str]
    gaps: list[str]
    generated_by: str
    prompt_version: str


class CandidateProfile(BaseModel):
    """The aggregate read-model returned by the API -- everything the dashboard needs to show
    for one candidate, assembled from the normalized tables.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str | None
    phone: str | None
    primary_location: str | None
    links: dict[str, str]
    education: list[EducationEntry] = Field(default_factory=list)
    experiences: list[ExperienceEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    skills: list[SkillClaim] = Field(default_factory=list)
    preferences: CandidatePreferencesSchema | None = None
    summary: ProfileSummary | None = None
    active_resume_id: uuid.UUID | None = None
