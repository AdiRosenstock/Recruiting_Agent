"""Orchestrates the full resume-parsing pipeline and persists the result.

Flow: deterministic PDF extraction -> save file -> LLM structuring -> deterministic evidence
validation -> persist normalized rows -> return the assembled CandidateProfile. Every step's
provenance (resume_id, evidence snippet, verified flag) is preserved on the way through.
"""

import uuid
from datetime import UTC, date, datetime

from dateutil import parser as date_parser
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_agent_decision
from app.models.candidate import Candidate, Resume
from app.models.candidate_profile import (
    CandidateEducation,
    CandidateExperience,
    CandidatePreferences,
    CandidateProfileSummary,
    CandidateProject,
)
from app.models.candidate_skill import CandidateSkill, CandidateSkillEvidence
from app.schemas.candidate import CandidateProfile
from app.schemas.llm_extraction import LLMExtractedCandidateData
from app.services.candidate_reader import get_candidate_profile
from app.services.llm.base import LLMProvider
from app.services.resume_parsing.evidence_validator import (
    EvidenceValidationResult,
    EvidenceValidator,
)
from app.services.resume_parsing.llm_structurer import PROMPT_VERSION, LLMResumeStructurer
from app.services.resume_parsing.pdf_extractor import PDFTextExtractor
from app.services.resume_parsing.storage import ResumeStorage

logger = get_logger(__name__)


class CandidateNotFoundError(Exception):
    pass


def _parse_date(value: str | None) -> date | None:
    """Best-effort parse of a free-text resume date ("June 2026", "Expected 2027", ...).

    Uses a fixed default (not "today") so missing day/year components resolve the same way on
    every run rather than depending on when the pipeline happens to execute.
    """
    if not value or not value.strip():
        return None
    try:
        return date_parser.parse(value, fuzzy=True, default=datetime(1900, 1, 1)).date()
    except (ValueError, OverflowError, TypeError):
        return None


class ResumeParsingService:
    def __init__(
        self,
        *,
        storage: ResumeStorage,
        extractor: PDFTextExtractor,
        structurer: LLMResumeStructurer,
        validator: EvidenceValidator,
        llm_provider: LLMProvider,
    ) -> None:
        self._storage = storage
        self._extractor = extractor
        self._structurer = structurer
        self._validator = validator
        self._llm_provider = llm_provider

    def parse_and_store(
        self,
        *,
        db: Session,
        candidate_id: uuid.UUID,
        filename: str,
        content: bytes,
        mime_type: str,
    ) -> tuple[CandidateProfile, uuid.UUID, list[str]]:
        candidate = db.get(Candidate, candidate_id)
        if candidate is None:
            raise CandidateNotFoundError(f"Candidate {candidate_id} not found")

        raw = self._extractor.extract_text(content)
        file_path = self._storage.save(
            candidate_id=candidate_id, filename=filename, content=content
        )

        # Only one resume is "active" per candidate at a time. Issued as a bulk UPDATE rather
        # than iterating `candidate.resumes` -- touching that relationship here would cache it
        # (without the row we're about to add) for the rest of this session, and
        # get_candidate_profile()'s later read of `candidate.resumes` would miss the new resume.
        db.query(Resume).filter(
            Resume.candidate_id == candidate_id, Resume.is_active.is_(True)
        ).update({"is_active": False})

        resume = Resume(
            candidate_id=candidate_id,
            file_path=file_path,
            original_filename=filename,
            mime_type=mime_type,
            raw_text=raw.text,
            extraction_method=raw.extraction_method,
            is_active=True,
            parsed_at=datetime.now(UTC),
        )
        db.add(resume)
        db.flush()  # populate resume.id

        extracted = self._structurer.structure(raw.text, self._llm_provider)
        validation = self._validator.validate(extracted, raw.text)
        warnings = list(validation.warnings)

        self._apply_identity_fields(candidate, extracted)
        self._persist_education(candidate_id, resume.id, extracted, db)
        self._persist_experiences(candidate_id, resume.id, extracted, db)
        self._persist_projects(candidate_id, resume.id, extracted, db)
        self._persist_skills(candidate_id, resume.id, extracted, validation, db)
        self._persist_preferences(candidate_id, extracted, db)

        db.add(
            CandidateProfileSummary(
                candidate_id=candidate_id,
                resume_id=resume.id,
                strengths=extracted.strengths,
                gaps=extracted.gaps,
                generated_by=self._llm_provider.name,
                prompt_version=PROMPT_VERSION,
            )
        )

        db.commit()

        log_agent_decision(
            "resume_parsed",
            candidate_id=str(candidate_id),
            resume_id=str(resume.id),
            llm_provider=self._llm_provider.name,
            warning_count=len(warnings),
        )

        profile = get_candidate_profile(db, candidate_id)
        assert profile is not None  # candidate was just confirmed to exist above
        return profile, resume.id, warnings

    @staticmethod
    def _apply_identity_fields(candidate: Candidate, extracted: LLMExtractedCandidateData) -> None:
        # Never overwrite an existing value with a blank -- a later, worse extraction shouldn't
        # erase a good one.
        if extracted.full_name:
            candidate.full_name = extracted.full_name
        if extracted.email:
            candidate.email = extracted.email
        if extracted.phone:
            candidate.phone = extracted.phone
        if extracted.primary_location:
            candidate.primary_location = extracted.primary_location
        if extracted.links:
            candidate.links = {**candidate.links, **extracted.links}

    @staticmethod
    def _persist_education(
        candidate_id: uuid.UUID,
        resume_id: uuid.UUID,
        extracted: LLMExtractedCandidateData,
        db: Session,
    ) -> None:
        for edu in extracted.education:
            db.add(
                CandidateEducation(
                    candidate_id=candidate_id,
                    resume_id=resume_id,
                    institution=edu.institution,
                    degree=edu.degree,
                    field_of_study=edu.field_of_study,
                    gpa=edu.gpa,
                    location=edu.location,
                    start_date=_parse_date(edu.start_date),
                    end_date=_parse_date(edu.end_date),
                    graduation_date=_parse_date(edu.graduation_date),
                    honors=edu.honors,
                    evidence_snippet=edu.evidence_snippet,
                )
            )

    @staticmethod
    def _persist_experiences(
        candidate_id: uuid.UUID,
        resume_id: uuid.UUID,
        extracted: LLMExtractedCandidateData,
        db: Session,
    ) -> dict[int, uuid.UUID]:
        experience_id_by_index: dict[int, uuid.UUID] = {}
        for index, exp in enumerate(extracted.experiences):
            row = CandidateExperience(
                candidate_id=candidate_id,
                resume_id=resume_id,
                category=exp.category,
                organization=exp.organization,
                title=exp.title,
                location=exp.location,
                start_date=_parse_date(exp.start_date),
                end_date=_parse_date(exp.end_date),
                is_current=exp.is_current,
                description=exp.description,
                evidence_snippet=exp.evidence_snippet,
            )
            db.add(row)
            db.flush()
            experience_id_by_index[index] = row.id
        return experience_id_by_index

    @staticmethod
    def _persist_projects(
        candidate_id: uuid.UUID,
        resume_id: uuid.UUID,
        extracted: LLMExtractedCandidateData,
        db: Session,
    ) -> None:
        for proj in extracted.projects:
            db.add(
                CandidateProject(
                    candidate_id=candidate_id,
                    resume_id=resume_id,
                    name=proj.name,
                    description=proj.description,
                    technologies=proj.technologies,
                    url=proj.url,
                    evidence_snippet=proj.evidence_snippet,
                )
            )

    @staticmethod
    def _persist_skills(
        candidate_id: uuid.UUID,
        resume_id: uuid.UUID,
        extracted: LLMExtractedCandidateData,
        validation: EvidenceValidationResult,
        db: Session,
    ) -> None:
        for skill_claim, skill_validation in zip(extracted.skills, validation.skills, strict=True):
            skill_row = CandidateSkill(
                candidate_id=candidate_id,
                resume_id=resume_id,
                skill_name=skill_claim.skill_name,
                category=skill_claim.category,
                confidence=skill_validation.confidence,
                verified=skill_validation.verified,
            )
            db.add(skill_row)
            db.flush()
            for snippet, evidence_verified in zip(
                skill_claim.evidence, skill_validation.evidence_verified, strict=True
            ):
                db.add(
                    CandidateSkillEvidence(
                        skill_id=skill_row.id,
                        snippet_text=snippet,
                        verified=evidence_verified,
                    )
                )

    @staticmethod
    def _persist_preferences(
        candidate_id: uuid.UUID, extracted: LLMExtractedCandidateData, db: Session
    ) -> None:
        if extracted.preferences is None:
            return
        existing = db.query(CandidatePreferences).filter_by(candidate_id=candidate_id).one_or_none()
        if existing is None:
            db.add(
                CandidatePreferences(
                    candidate_id=candidate_id,
                    desired_roles=extracted.preferences.desired_roles,
                    desired_stages=extracted.preferences.desired_stages,
                    desired_locations=extracted.preferences.desired_locations,
                    notes=extracted.preferences.notes,
                )
            )
        else:
            existing.desired_roles = extracted.preferences.desired_roles
            existing.desired_stages = extracted.preferences.desired_stages
            existing.desired_locations = extracted.preferences.desired_locations
            existing.notes = extracted.preferences.notes
