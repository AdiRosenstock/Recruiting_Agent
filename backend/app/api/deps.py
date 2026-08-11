from fastapi import Depends

from app.config import Settings, get_settings
from app.services.llm.factory import get_llm_provider
from app.services.outreach.agent import OutreachMessageAgent
from app.services.outreach.llm_outreach_writer import LLMOutreachWriter
from app.services.research.agent import CompanyResearchAgent
from app.services.research.fetcher import PageFetcher
from app.services.research.llm_researcher import LLMCompanyResearcher
from app.services.resume_parsing.evidence_validator import EvidenceValidator
from app.services.resume_parsing.llm_structurer import LLMResumeStructurer
from app.services.resume_parsing.pdf_extractor import PDFTextExtractor
from app.services.resume_parsing.service import ResumeParsingService
from app.services.resume_parsing.storage import LocalFileStorage
from app.services.search.factory import get_search_provider


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


def get_research_agent(settings: Settings = Depends(get_settings)) -> CompanyResearchAgent:
    return CompanyResearchAgent(
        fetcher=PageFetcher(),
        researcher=LLMCompanyResearcher(),
        llm_provider=get_llm_provider(settings),
        search_provider=get_search_provider(settings),
    )


def get_outreach_agent(settings: Settings = Depends(get_settings)) -> OutreachMessageAgent:
    return OutreachMessageAgent(writer=LLMOutreachWriter(), llm_provider=get_llm_provider(settings))


def get_page_fetcher() -> PageFetcher:
    return PageFetcher()
