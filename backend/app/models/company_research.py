"""One row per researched fact/inference about a company. The FACT-vs-INFERENCE split (and the
requirement that facts carry a source) is the enforcement point for "the research agent must
separate facts from inferences" / "avoid hallucinating company information" -- see
services/research/agent.py for how rows here get produced and validated.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPk

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.source import Source


class CompanyResearch(Base, UUIDPk, CreatedAtMixin):
    __tablename__ = "company_research"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # what_they_build | customers | problem | funding | founders | product_direction | launch |
    # engineering_challenge | personal_connection | other
    fact_type: Mapped[str] = mapped_column(String, nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    is_inference: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Required (at the application layer, not a DB constraint) when is_inference is False --
    # see services/research/agent.py.
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id"), nullable=True
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Which version of the company-researcher prompt produced this row (see
    # services/research/llm_researcher.py's PROMPT_VERSION, and services/llm/prompt_registry.py
    # for the full history) -- null for personal_connection rows, which are deterministic
    # keyword matches with no LLM call involved. Matches the traceability already kept for
    # candidate_profiles/outreach_messages; this table was the one gap.
    prompt_version: Mapped[str | None] = mapped_column(String, nullable=True)

    company: Mapped["Company"] = relationship()
    source: Mapped["Source | None"] = relationship()
