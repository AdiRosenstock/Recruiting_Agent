"""Generic provenance record: a URL a fact/company/job was discovered or verified from.
Reused across discovery adapters and (from Phase 3 on) the Company Research Agent.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPk


class Source(Base, UUIDPk, CreatedAtMixin):
    __tablename__ = "sources"

    url: Mapped[str] = mapped_column(String, nullable=False)
    # hn_who_is_hiring | github_new_grad_list | manual | ... (see discovery adapters' `name`)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CompanySourceLink(Base):
    """Join table: which source(s) a company was discovered/confirmed through."""

    __tablename__ = "company_sources"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        primary_key=True,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        primary_key=True,
    )
