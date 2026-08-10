"""Candidate identity + resume upload records."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, TimestampMixin, UUIDPk

if TYPE_CHECKING:
    from app.models.candidate_profile import (
        CandidateEducation,
        CandidateExperience,
        CandidatePreferences,
        CandidateProfileSummary,
        CandidateProject,
    )
    from app.models.candidate_skill import CandidateSkill


class Candidate(Base, UUIDPk, TimestampMixin):
    __tablename__ = "candidates"

    full_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    primary_location: Mapped[str | None] = mapped_column(String, nullable=True)
    # e.g. {"linkedin": "...", "github": "...", "portfolio": "..."}
    links: Mapped[dict[str, str]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    resumes: Mapped[list["Resume"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    education: Mapped[list["CandidateEducation"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    experiences: Mapped[list["CandidateExperience"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    projects: Mapped[list["CandidateProject"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    skills: Mapped[list["CandidateSkill"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    preferences: Mapped["CandidatePreferences | None"] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", uselist=False
    )
    summaries: Mapped[list["CandidateProfileSummary"]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="CandidateProfileSummary.created_at.desc()",
    )


class Resume(Base, UUIDPk, CreatedAtMixin):
    __tablename__ = "resumes"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    extraction_method: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    candidate: Mapped["Candidate"] = relationship(back_populates="resumes")
