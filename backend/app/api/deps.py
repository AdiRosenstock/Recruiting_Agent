from fastapi import Depends

from app.config import Settings, get_settings
from app.services.llm.factory import get_llm_provider
from app.services.resume_parsing.evidence_validator import EvidenceValidator
from app.services.resume_parsing.llm_structurer import LLMResumeStructurer
from app.services.resume_parsing.pdf_extractor import PDFTextExtractor
from app.services.resume_parsing.service import ResumeParsingService
from app.services.resume_parsing.storage import LocalFileStorage


def get_resume_parsing_service(
    settings: Settings = Depends(get_settings),
) -> ResumeParsingService:
    settings.resume_storage_path.mkdir(parents=True, exist_ok=True)
    return ResumeParsingService(
        storage=LocalFileStorage(base_dir=settings.resume_storage_path),
        extractor=PDFTextExtractor(),
        structurer=LLMResumeStructurer(),
        validator=EvidenceValidator(),
        llm_provider=get_llm_provider(settings),
    )
