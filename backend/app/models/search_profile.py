"""A `SearchProfile` is one named "agent" a candidate runs -- e.g. "startup_outreach". Profiles
share the same downstream pipeline (discovery -> scoring -> optional outreach); they differ only
in `config` (sources/weights/filters) and `outreach_enabled`. Only one profile is seeded today
(this app is startup-only by design -- see scripts/seed_profiles.py), but the table stays
profile-shaped rather than a single hardcoded config so a second startup-focused profile (a
different stage/location cut) is a config row, not a new code path. See
`app/services/scoring/weights.py` for how `config["weights"]` is consumed.
"""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPk

if TYPE_CHECKING:
    from app.models.candidate import Candidate


class SearchProfile(Base, UUIDPk, TimestampMixin):
    __tablename__ = "search_profiles"
    __table_args__ = (
        UniqueConstraint("candidate_id", "profile_key", name="uq_search_profiles_candidate_key"),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_key: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    outreach_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    # weights, role_filters, stage_filters, location_filters, notes -- see FitScoreWeights /
    # DiscoveryQuery for the shape each key is expected to have.
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    candidate: Mapped["Candidate"] = relationship()
