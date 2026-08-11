#!/usr/bin/env python
"""One-time, idempotent setup: creates the `startup_outreach` search profile against an
existing candidate. Run from `backend/`:

    .venv/bin/python scripts/seed_profiles.py [--candidate-id UUID]

If `--candidate-id` is omitted and exactly one candidate exists in the database, that candidate
is used automatically (the common case for this single-user tool). Safe to re-run -- an existing
profile is left untouched.

Startup-only by design: this app is scoped entirely to early-stage startup outreach, not a
general job tracker. (An earlier `new_grad_2027` "wide net across company sizes" profile existed
and was removed -- see the Roadmap in the root README for why.) `_PROFILES` stays a list, not a
single dict, so a second *startup-focused* profile (a different stage/location cut, say) is
still just a config addition here, not a new code path.
"""

import argparse
import sys
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.candidate import Candidate  # noqa: E402
from app.models.search_profile import SearchProfile  # noqa: E402

_STARTUP_OUTREACH_CONFIG: dict[str, Any] = {
    "weights": {},  # use FitScoreWeights' defaults as-is
    "role_filters": [
        "software engineer",
        "backend engineer",
        "founding engineer",
        "ai engineer",
        "data engineer",
        "ai infrastructure engineer",
        "product engineer",
        "forward deployed engineer",
    ],
    "stage_filters": ["pre_seed", "seed", "series_a", "series_b"],
    "location_filters": ["nyc", "new york", "remote"],
    "notes": "Early-stage NYC startups, small technical teams. Outreach enabled.",
}

_PROFILES: list[tuple[str, str, bool, dict[str, Any]]] = [
    ("startup_outreach", "Startup Outreach", True, _STARTUP_OUTREACH_CONFIG),
]


def resolve_candidate_id(db: Session, explicit_id: str | None) -> uuid.UUID:
    if explicit_id:
        return uuid.UUID(explicit_id)
    candidates = db.query(Candidate).all()
    if len(candidates) == 1:
        return candidates[0].id
    if not candidates:
        raise SystemExit("No candidates found -- upload a resume first (see README).")
    listing = ", ".join(f"{c.id} ({c.full_name})" for c in candidates)
    raise SystemExit(f"Multiple candidates found -- pass --candidate-id explicitly: {listing}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-id", default=None, help="UUID of the candidate to seed for")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        candidate_id = resolve_candidate_id(db, args.candidate_id)
        for profile_key, display_name, outreach_enabled, config in _PROFILES:
            existing = (
                db.query(SearchProfile)
                .filter_by(candidate_id=candidate_id, profile_key=profile_key)
                .one_or_none()
            )
            if existing is not None:
                print(f"Skipping '{profile_key}' -- already exists.")
                continue
            db.add(
                SearchProfile(
                    candidate_id=candidate_id,
                    profile_key=profile_key,
                    display_name=display_name,
                    outreach_enabled=outreach_enabled,
                    config=config,
                )
            )
            print(f"Created '{profile_key}' for candidate {candidate_id}.")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
