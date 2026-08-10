"""Direct (non-HTTP) integration test of ResumeParsingService against the real test database."""

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.services.llm.stub_provider import StubProvider
from app.services.resume_parsing.evidence_validator import EvidenceValidator
from app.services.resume_parsing.llm_structurer import LLMResumeStructurer
from app.services.resume_parsing.pdf_extractor import PDFTextExtractor
from app.services.resume_parsing.service import CandidateNotFoundError, ResumeParsingService
from app.services.resume_parsing.storage import LocalFileStorage


@pytest.fixture
def service(tmp_path: Path) -> ResumeParsingService:
    return ResumeParsingService(
        storage=LocalFileStorage(base_dir=tmp_path),
        extractor=PDFTextExtractor(),
        structurer=LLMResumeStructurer(),
        validator=EvidenceValidator(),
        llm_provider=StubProvider(),
    )


def test_parse_and_store_raises_for_unknown_candidate(
    service: ResumeParsingService, db_session: Session, sample_resume_bytes: bytes
) -> None:
    with pytest.raises(CandidateNotFoundError):
        service.parse_and_store(
            db=db_session,
            candidate_id=uuid.uuid4(),
            filename="resume.pdf",
            content=sample_resume_bytes,
            mime_type="application/pdf",
        )


def test_parse_and_store_persists_skill_evidence(
    service: ResumeParsingService, db_session: Session, sample_resume_bytes: bytes
) -> None:
    candidate = Candidate(full_name="Placeholder")
    db_session.add(candidate)
    db_session.flush()

    profile, resume_id, warnings = service.parse_and_store(
        db=db_session,
        candidate_id=candidate.id,
        filename="resume.pdf",
        content=sample_resume_bytes,
        mime_type="application/pdf",
    )

    assert profile.active_resume_id == resume_id
    assert profile.skills, "expected at least one skill claim from the stub provider"
    for skill in profile.skills:
        # Every skill claim must carry evidence -- never bare assertions with no support.
        assert skill.evidence
        for evidence in skill.evidence:
            assert evidence.snippet_text

    # Re-uploading should deactivate the previous resume, not accumulate two active ones.
    profile2, resume_id2, _ = service.parse_and_store(
        db=db_session,
        candidate_id=candidate.id,
        filename="resume.pdf",
        content=sample_resume_bytes,
        mime_type="application/pdf",
    )
    assert resume_id2 != resume_id
    assert profile2.active_resume_id == resume_id2
