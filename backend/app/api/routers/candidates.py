import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_resume_parsing_service
from app.db.session import get_db
from app.models.candidate import Candidate
from app.schemas.candidate import CandidateCreate, CandidateProfile
from app.schemas.resume import ResumeParseResult
from app.services.candidate_reader import get_candidate_profile
from app.services.resume_parsing.service import CandidateNotFoundError, ResumeParsingService

router = APIRouter(prefix="/api/v1/candidates", tags=["candidates"])

_ALLOWED_CONTENT_TYPES = {"application/pdf"}
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("", response_model=CandidateProfile, status_code=status.HTTP_201_CREATED)
def create_candidate(payload: CandidateCreate, db: Session = Depends(get_db)) -> CandidateProfile:
    candidate = Candidate(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        primary_location=payload.primary_location,
        links=payload.links,
    )
    db.add(candidate)
    db.commit()

    profile = get_candidate_profile(db, candidate.id)
    assert profile is not None  # just committed above
    return profile


@router.get("/{candidate_id}", response_model=CandidateProfile)
def read_candidate(candidate_id: uuid.UUID, db: Session = Depends(get_db)) -> CandidateProfile:
    profile = get_candidate_profile(db, candidate_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return profile


@router.post("/{candidate_id}/resume", response_model=ResumeParseResult)
def upload_resume(
    candidate_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    service: ResumeParsingService = Depends(get_resume_parsing_service),
) -> ResumeParseResult:
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported content type '{file.content_type}'; only PDF is accepted.",
        )

    content = file.file.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Resume file too large."
        )

    try:
        profile, resume_id, warnings = service.parse_and_store(
            db=db,
            candidate_id=candidate_id,
            filename=file.filename or "resume.pdf",
            content=content,
            mime_type=file.content_type,
        )
    except CandidateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    return ResumeParseResult(resume_id=resume_id, profile=profile, warnings=warnings)
