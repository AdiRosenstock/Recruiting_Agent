"""A company, deduplicated across however many sources/profiles discover it. Profile-agnostic
by design -- the same company can surface under both `startup_outreach` and `new_grad_2027`
(scored differently per profile via `fit_scores.profile_id`)."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPk

if TYPE_CHECKING:
    from app.models.job import Job


class Company(Base, UUIDPk, TimestampMixin):
    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint("normalized_name", "website", name="uq_companies_normalized_name_website"),
    )

    name: Mapped[str] = mapped_column(String, nullable=False)
    normalized_name: Mapped[str] = mapped_column(String, nullable=False)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    industry: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    founders: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    # pre_seed|seed|series_a|series_b|series_c_plus|growth|unknown|n/a -- see the "VARCHAR, not
    # native ENUM" decision from the Phase 1 plan; validated at the Pydantic layer.
    funding_stage: Mapped[str | None] = mapped_column(String, nullable=True)
    amount_raised_usd: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    investors: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    technologies: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    date_discovered: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    date_last_checked: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    jobs: Mapped[list["Job"]] = relationship(back_populates="company", cascade="all, delete-orphan")
