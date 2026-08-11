"""Import every model module so SQLAlchemy's mapper registry is fully populated -- required for
relationship() string resolution and for Alembic's autogenerate to see all tables via
`Base.metadata`.
"""

from app.models.application import Application
from app.models.candidate import Candidate, Resume
from app.models.candidate_profile import (
    CandidateEducation,
    CandidateExperience,
    CandidatePreferences,
    CandidateProfileSummary,
    CandidateProject,
)
from app.models.candidate_skill import CandidateSkill, CandidateSkillEvidence
from app.models.company import Company
from app.models.company_research import CompanyResearch
from app.models.contact import Contact
from app.models.fit_score import FitScore
from app.models.job import Job
from app.models.outreach_message import OutreachMessage
from app.models.search_profile import SearchProfile
from app.models.source import CompanySourceLink, Source

__all__ = [
    "Application",
    "Candidate",
    "Resume",
    "CandidateEducation",
    "CandidateExperience",
    "CandidateProject",
    "CandidatePreferences",
    "CandidateProfileSummary",
    "CandidateSkill",
    "CandidateSkillEvidence",
    "Company",
    "CompanyResearch",
    "Contact",
    "CompanySourceLink",
    "FitScore",
    "Job",
    "OutreachMessage",
    "SearchProfile",
    "Source",
]
