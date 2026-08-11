"""An open (or once-open) position at a `Company`. Profile-agnostic -- see `FitScore` for how
the same job is scored differently per `SearchProfile`."""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPk

if TYPE_CHECKING:
    from app.models.company import Company


class Job(Base, UUIDPk, TimestampMixin):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("job_url", name="uq_jobs_job_url"),)

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    job_url: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    experience_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    technologies: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    responsibilities: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    compensation_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compensation_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compensation_currency: Mapped[str | None] = mapped_column(String, nullable=True)
    # remote | hybrid | onsite
    work_mode: Mapped[str | None] = mapped_column(String, nullable=True)
    posted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Common on new-grad postings ("apply by <date>" or a rolling-admission cutoff); nullable
    # since startup postings often don't have one.
    deadline_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # open | closed | unknown
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="open", server_default=text("'open'")
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id"), nullable=True
    )
    # likely_sponsors | likely_no_sponsorship | null (never checked, or checked and no known
    # phrasing found either way -- see services/visa_sponsorship.py). A deterministic keyword
    # signal, not a confirmed fact -- always paired with `visa_sponsorship_evidence`, the
    # literal matched phrase, so it can be verified against the actual posting.
    visa_sponsorship: Mapped[str | None] = mapped_column(String, nullable=True)
    visa_sponsorship_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    visa_sponsorship_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    date_discovered: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    date_last_checked: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    company: Mapped["Company"] = relationship(back_populates="jobs")
