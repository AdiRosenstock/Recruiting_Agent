"""Skill claims and their evidence.

This is the table the "do not let the LLM invent experience" requirement bears on most
directly: every skill has 0+ `CandidateSkillEvidence` rows, each holding the literal snippet
the LLM claimed as support. The deterministic evidence validator (see
services/resume_parsing/evidence_validator.py) checks each snippet against the resume's raw
text and sets `verified` accordingly; `CandidateSkill.verified` is true only if at least one of
its evidence rows verified. Confidence is downgraded, not silently dropped, when evidence fails
to verify -- the claim stays visible for human review rather than disappearing.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPk

if TYPE_CHECKING:
    from app.models.candidate import Candidate, Resume
    from app.models.candidate_profile import CandidateExperience


class CandidateSkill(Base, UUIDPk, CreatedAtMixin):
    __tablename__ = "candidate_skills"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_candidate_skills_confidence"
        ),
        UniqueConstraint(
            "candidate_id", "resume_id", "skill_name", name="uq_candidate_skills_name"
        ),
    )

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
    skill_name: Mapped[str] = mapped_column(String, nullable=False)
    # language | framework | database | ai | data | tool | domain
    category: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    candidate: Mapped["Candidate"] = relationship(back_populates="skills")
    resume: Mapped["Resume"] = relationship()
    evidence: Mapped[list["CandidateSkillEvidence"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )


class CandidateSkillEvidence(Base, UUIDPk, CreatedAtMixin):
    __tablename__ = "candidate_skill_evidence"

    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    experience_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_experiences.id", ondelete="SET NULL"),
        nullable=True,
    )
    snippet_text: Mapped[str] = mapped_column(Text, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    skill: Mapped["CandidateSkill"] = relationship(back_populates="evidence")
    experience: Mapped["CandidateExperience | None"] = relationship()
