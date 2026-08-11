"""The CRM pipeline row: one per (candidate, job, profile), tracking status through the human
approval workflow. `contact_id`/`outreach_message_id`/`fit_score_id` are set as the pipeline
progresses (discovery creates the row; scoring sets `fit_score_id`; research/contact-lookup sets
`contact_id`; outreach generation sets `outreach_message_id`).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPk

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.contact import Contact
    from app.models.fit_score import FitScore
    from app.models.job import Job
    from app.models.outreach_message import OutreachMessage
    from app.models.search_profile import SearchProfile

# DISCOVERED | RESEARCHING | REVIEW | READY_TO_CONTACT | CONTACTED | RESPONDED | INTERVIEW |
# REJECTED | ARCHIVED
DEFAULT_STATUS = "DISCOVERED"
VALID_STATUSES = (
    "DISCOVERED",
    "RESEARCHING",
    "REVIEW",
    "READY_TO_CONTACT",
    "CONTACTED",
    "RESPONDED",
    "INTERVIEW",
    "REJECTED",
    "ARCHIVED",
)


class Application(Base, UUIDPk, TimestampMixin):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint(
            "candidate_id", "job_id", "profile_id", name="uq_applications_candidate_job_profile"
        ),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True
    )
    fit_score_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fit_scores.id"), nullable=True
    )
    outreach_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("outreach_messages.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String, nullable=False, default=DEFAULT_STATUS, server_default=text(f"'{DEFAULT_STATUS}'")
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    candidate: Mapped["Candidate"] = relationship()
    job: Mapped["Job"] = relationship()
    profile: Mapped["SearchProfile"] = relationship()
    fit_score: Mapped["FitScore | None"] = relationship()
    contact: Mapped["Contact | None"] = relationship()
    outreach_message: Mapped["OutreachMessage | None"] = relationship()
