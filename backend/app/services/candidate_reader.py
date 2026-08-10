"""Assembles the `CandidateProfile` read-model from the normalized candidate-domain tables.

Shared by the resume-upload endpoint (returns the fresh profile immediately after parsing) and
`GET /candidates/{id}`, so both always agree on shape.
"""

import uuid

from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.schemas.candidate import (
    CandidatePreferencesSchema,
    CandidateProfile,
    EducationEntry,
    ExperienceEntry,
    ProfileSummary,
    ProjectEntry,
    SkillClaim,
)


def get_candidate_profile(db: Session, candidate_id: uuid.UUID) -> CandidateProfile | None:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        return None

    # Force a fresh load of every relationship collection rather than trusting whatever this
    # session may have cached from an earlier read. Without this, a second parse-and-store call
    # within the same session (e.g. an upload immediately followed by re-reading the profile)
    # can see a stale `candidate.resumes`/`.skills`/etc. that predates rows just committed by
    # this same request, because SQLAlchemy only lazy-loads a relationship once per session.
    db.expire(candidate)

    active_resume = next((r for r in candidate.resumes if r.is_active), None)
    # `summaries` is relationship-ordered newest-first (see models/candidate.py).
    latest_summary = candidate.summaries[0] if candidate.summaries else None

    return CandidateProfile(
        id=candidate.id,
        full_name=candidate.full_name,
        email=candidate.email,
        phone=candidate.phone,
        primary_location=candidate.primary_location,
        links=candidate.links,
        education=[EducationEntry.model_validate(e) for e in candidate.education],
        experiences=[ExperienceEntry.model_validate(e) for e in candidate.experiences],
        projects=[ProjectEntry.model_validate(p) for p in candidate.projects],
        skills=[SkillClaim.model_validate(s) for s in candidate.skills],
        preferences=(
            CandidatePreferencesSchema.model_validate(candidate.preferences)
            if candidate.preferences
            else None
        ),
        summary=ProfileSummary.model_validate(latest_summary) if latest_summary else None,
        active_resume_id=active_resume.id if active_resume else None,
    )
