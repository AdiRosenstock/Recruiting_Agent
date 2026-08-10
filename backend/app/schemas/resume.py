import uuid

from pydantic import BaseModel

from app.schemas.candidate import CandidateProfile


class ResumeParseResult(BaseModel):
    """Response of `POST /candidates/{id}/resume` -- the freshly-parsed profile plus any
    warnings the deterministic evidence validator raised (e.g. an unverified skill claim).
    Warnings are surfaced, never silently swallowed.
    """

    resume_id: uuid.UUID
    profile: CandidateProfile
    warnings: list[str] = []
