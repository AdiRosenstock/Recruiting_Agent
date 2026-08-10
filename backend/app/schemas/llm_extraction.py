"""The schema an LLM is constrained to fill when structuring a resume.

Deliberately narrower than `schemas.candidate.CandidateProfile`: it carries only what an LLM
can plausibly know from reading resume text once (raw claims + the snippets it says support
them). Anything derived *from* those claims -- `verified`, database ids, a
skill's confidence after evidence-checking -- is computed afterward by deterministic code in
`services/resume_parsing/evidence_validator.py`, never trusted directly from the model output.
"""

from pydantic import BaseModel, Field


class LLMEducationClaim(BaseModel):
    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    gpa: str | None = None
    location: str | None = None
    start_date: str | None = None  # free-text as written on the resume; parsed later
    end_date: str | None = None
    graduation_date: str | None = None
    honors: str | None = None
    evidence_snippet: str = Field(
        description="A literal, verbatim quote from the resume text that this entry came from."
    )


class LLMExperienceClaim(BaseModel):
    category: str = Field(description="One of: work, leadership, project")
    organization: str
    title: str
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False
    description: str | None = None
    evidence_snippet: str = Field(
        description="A literal, verbatim quote from the resume text that this entry came from."
    )


class LLMProjectClaim(BaseModel):
    name: str
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    url: str | None = None
    evidence_snippet: str


class LLMSkillClaim(BaseModel):
    skill_name: str
    category: str = Field(
        description="One of: language, framework, database, ai, data, tool, domain"
    )
    confidence: float = Field(ge=0, le=1, description="The model's own confidence in this claim.")
    evidence: list[str] = Field(
        default_factory=list,
        description="Literal, verbatim quotes from the resume text supporting this skill claim.",
    )


class LLMPreferencesClaim(BaseModel):
    desired_roles: list[str] = Field(default_factory=list)
    desired_stages: list[str] = Field(default_factory=list)
    desired_locations: list[str] = Field(default_factory=list)
    notes: str | None = None


class LLMExtractedCandidateData(BaseModel):
    """Top-level structured-output schema passed to the LLM provider."""

    full_name: str
    email: str | None = None
    phone: str | None = None
    primary_location: str | None = None
    links: dict[str, str] = Field(default_factory=dict)
    education: list[LLMEducationClaim] = Field(default_factory=list)
    experiences: list[LLMExperienceClaim] = Field(default_factory=list)
    projects: list[LLMProjectClaim] = Field(default_factory=list)
    skills: list[LLMSkillClaim] = Field(default_factory=list)
    preferences: LLMPreferencesClaim | None = None
    strengths: list[str] = Field(
        default_factory=list, description="Short, synthesized strengths -- not verbatim quotes."
    )
    gaps: list[str] = Field(
        default_factory=list, description="Honest, synthesized experience gaps."
    )
