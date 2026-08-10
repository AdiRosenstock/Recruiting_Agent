"""Import every model module so SQLAlchemy's mapper registry is fully populated -- required for
relationship() string resolution and for Alembic's autogenerate to see all tables via
`Base.metadata`.
"""

from app.models.candidate import Candidate, Resume
from app.models.candidate_profile import (
    CandidateEducation,
    CandidateExperience,
    CandidatePreferences,
    CandidateProfileSummary,
    CandidateProject,
)
from app.models.candidate_skill import CandidateSkill, CandidateSkillEvidence

__all__ = [
    "Candidate",
    "Resume",
    "CandidateEducation",
    "CandidateExperience",
    "CandidateProject",
    "CandidatePreferences",
    "CandidateProfileSummary",
    "CandidateSkill",
    "CandidateSkillEvidence",
]
