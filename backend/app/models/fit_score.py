"""One explainable fit score for a (candidate, job, profile) triple. Multiple rows can exist
per triple over time (re-scoring history) -- callers read the latest by `created_at`."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPk

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.job import Job
    from app.models.search_profile import SearchProfile


class FitScore(Base, UUIDPk, CreatedAtMixin):
    __tablename__ = "fit_scores"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    technical_match: Mapped[float] = mapped_column(Float, nullable=False)
    role_match: Mapped[float] = mapped_column(Float, nullable=False)
    ai_data_match: Mapped[float] = mapped_column(Float, nullable=False)
    experience_match: Mapped[float] = mapped_column(Float, nullable=False)
    stage_match: Mapped[float] = mapped_column(Float, nullable=False)
    location_match: Mapped[float] = mapped_column(Float, nullable=False)
    domain_match: Mapped[float] = mapped_column(Float, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    # excellent | strong | worth_reviewing | weak | ignore
    tier: Mapped[str] = mapped_column(String, nullable=False)
    strengths: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    gaps: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    weights_version: Mapped[str] = mapped_column(String, nullable=False)

    candidate: Mapped["Candidate"] = relationship()
    job: Mapped["Job"] = relationship()
    profile: Mapped["SearchProfile"] = relationship()
