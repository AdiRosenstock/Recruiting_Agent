"""A generated (never auto-sent) outreach message. `is_user_edited` flips to True the moment a
human edits the drafted content via the API -- see api/routers/applications.py. Nothing in this
codebase sends this anywhere; sending is always a manual, human action outside the app.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPk

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.contact import Contact
    from app.models.job import Job


class OutreachMessage(Base, UUIDPk, TimestampMixin):
    __tablename__ = "outreach_messages"

    # Overrides TimestampMixin's `created_at` (server_default=now(), which Postgres freezes for
    # the whole enclosing transaction -- multiple messages generated in one request/transaction
    # would all get the identical timestamp) with `clock_timestamp()`, real wall-clock time that
    # keeps advancing even within a transaction. Matters here specifically because
    # api/routers/outreach.py's "latest set of 3" query orders by created_at to find the most
    # recent generation -- found via a test that creates two generations back-to-back and failed
    # until this fix (they'd tie under now()).
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("clock_timestamp()")
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
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True
    )
    # linkedin_full | linkedin_connection | email
    message_type: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    personalization_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_user_edited: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    generated_by: Mapped[str] = mapped_column(String, nullable=False)

    candidate: Mapped["Candidate"] = relationship()
    job: Mapped["Job"] = relationship()
    contact: Mapped["Contact | None"] = relationship()
