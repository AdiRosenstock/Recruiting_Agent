"""A person at a company who might be worth reaching out to. Never populated by scraping an
authenticated source -- see services/contacts.py's priority ranking (deterministic, company-size
based) and the README's compliance notes. `public_profile_url` may hold a LinkedIn URL only when
it was found through permitted public search or entered manually by the user.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPk

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.source import Source


class Contact(Base, UUIDPk, TimestampMixin):
    __tablename__ = "contacts"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    public_profile_url: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id"), nullable=True
    )
    # Lower is higher priority -- see services/contacts.py:rank_contact_priority.
    priority_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    company: Mapped["Company"] = relationship()
    source: Mapped["Source | None"] = relationship()
