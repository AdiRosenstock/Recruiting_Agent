"""Normalized, resume-provenanced candidate profile facts: education, experience, projects,
plus the candidate's stated preferences and the LLM-synthesized strengths/gaps summary.

`evidence_snippet` on education/experience/project rows is the literal quote the extraction
pulled from the resume's raw text -- it is *not* independently re-verified the way
`candidate_skills` evidence is (see candidate_skill.py), because these rows themselves came
from a specific, locatable block of resume text rather than a free-floating claim.
"""

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPk

if TYPE_CHECKING:
    from app.models.candidate import Candidate, Resume


class CandidateEducation(Base, UUIDPk, CreatedAtMixin):
    __tablename__ = "candidate_education"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution: Mapped[str] = mapped_column(String, nullable=False)
    degree: Mapped[str | None] = mapped_column(String, nullable=True)
    field_of_study: Mapped[str | None] = mapped_column(String, nullable=True)
    gpa: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    graduation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    honors: Mapped[str | None] = mapped_column(String, nullable=True)
    evidence_snippet: Mapped[str] = mapped_column(Text, nullable=False)

    candidate: Mapped["Candidate"] = relationship(back_populates="education")
    resume: Mapped["Resume"] = relationship()


class CandidateExperience(Base, UUIDPk, CreatedAtMixin):
    __tablename__ = "candidate_experiences"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # work | leadership | project -- kept as a plain string (see schema decision in the plan:
    # evolving categorical fields use VARCHAR + app-level enum, not a native PG ENUM).
    category: Mapped[str] = mapped_column(String, nullable=False, default="work")
    organization: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_snippet: Mapped[str] = mapped_column(Text, nullable=False)

    candidate: Mapped["Candidate"] = relationship(back_populates="experiences")
    resume: Mapped["Resume"] = relationship()


class CandidateProject(Base, UUIDPk, CreatedAtMixin):
    __tablename__ = "candidate_projects"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    technologies: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    evidence_snippet: Mapped[str] = mapped_column(Text, nullable=False)

    candidate: Mapped["Candidate"] = relationship(back_populates="projects")
    resume: Mapped["Resume"] = relationship()


class CandidatePreferences(Base, UUIDPk):
    """Single row per candidate (latest-wins), tracked via `updated_at`."""

    __tablename__ = "candidate_preferences"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    desired_roles: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    desired_stages: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    desired_locations: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    candidate: Mapped["Candidate"] = relationship(back_populates="preferences")


class CandidateProfileSummary(Base, UUIDPk, CreatedAtMixin):
    """LLM-synthesized narrative (strengths/gaps) -- deliberately separate from the
    deterministically-extracted, resume-evidenced tables above. Never treated as a factual
    claim on its own; the dashboard should always show it alongside (not instead of) the
    underlying skills/experience it was derived from.
    """

    __tablename__ = "candidate_profile_summary"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    strengths: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    gaps: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    generated_by: Mapped[str] = mapped_column(String, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)

    candidate: Mapped["Candidate"] = relationship(back_populates="summaries")
    resume: Mapped["Resume"] = relationship()
