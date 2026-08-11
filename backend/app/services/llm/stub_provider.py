"""Deterministic, no-network stand-in for a real LLM provider.

Exists so the whole pipeline (resume extraction, company research, outreach drafting) is
runnable and testable without any API key. It is intentionally *not* a substitute for real
quality on any of the three -- each `_extract_*`/`_research_*`/`_draft_*` function below does
the minimum honest, deterministic thing (keyword matching, first-line/title extraction, a fixed
template) and documents its own limitation in its output, rather than pretending to understand
free text the way a real model would. Callers should treat stub output as a smoke-test fixture,
not production-quality data.
"""

import re

from app.schemas.llm_extraction import LLMExtractedCandidateData, LLMSkillClaim
from app.schemas.llm_outreach import LLMOutreachMessages
from app.schemas.llm_research import LLMCompanyResearchData, LLMResearchFact
from app.services.llm.base import LLMProviderError, T

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(\+?\d{1,2}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
_LINKEDIN_RE = re.compile(r"(https?://)?(www\.)?linkedin\.com/\S+", re.IGNORECASE)
_GITHUB_RE = re.compile(r"(https?://)?(www\.)?github\.com/\S+", re.IGNORECASE)

# A deliberately small, easily-extended list of common engineering-resume keywords. Real
# extraction quality (recognizing skills not on this list, inferring category, weighing
# context) is exactly what a real LLM provider is for.
_KNOWN_SKILLS: dict[str, str] = {
    "python": "language",
    "sql": "language",
    "c++": "language",
    "java": "language",
    "javascript": "language",
    "typescript": "language",
    "r": "language",
    "go": "language",
    "rust": "language",
    "pandas": "framework",
    "react": "framework",
    "fastapi": "framework",
    "django": "framework",
    "flask": "framework",
    "node": "framework",
    "postgresql": "database",
    "mysql": "database",
    "mongodb": "database",
    "sqlite": "database",
    "machine learning": "ai",
    "llm": "ai",
    "agentic": "ai",
    "jupyter": "tool",
    "git": "tool",
    "docker": "tool",
    "kubernetes": "tool",
    "aws": "tool",
    "apache iceberg": "data",
}

_STUB_MESSAGE_NOTE = (
    "[Stub-generated placeholder -- configure LLM_PROVIDER=openai or anthropic for a real, "
    "personalized draft.]"
)


class StubProvider:
    name = "stub"

    def structured_completion(
        self,
        *,
        system: str,
        prompt: str,
        response_model: type[T],
        prompt_version: str,
    ) -> T:
        if response_model is LLMExtractedCandidateData:
            return response_model.model_validate(_extract_candidate(prompt))
        if response_model is LLMCompanyResearchData:
            return response_model.model_validate(_research_company(prompt))
        if response_model is LLMOutreachMessages:
            return response_model.model_validate(_draft_outreach(prompt))
        raise LLMProviderError(
            f"StubProvider does not support {response_model.__name__}. "
            "Use LLM_PROVIDER=openai or anthropic instead."
        )


def _extract_candidate(raw_text: str) -> LLMExtractedCandidateData:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    full_name = lines[0] if lines else "Unknown Candidate"

    email_match = _EMAIL_RE.search(raw_text)
    phone_match = _PHONE_RE.search(raw_text)

    links: dict[str, str] = {}
    if match := _LINKEDIN_RE.search(raw_text):
        links["linkedin"] = match.group(0)
    if match := _GITHUB_RE.search(raw_text):
        links["github"] = match.group(0)

    skills: list[LLMSkillClaim] = []
    lower_text = raw_text.lower()
    for keyword, category in _KNOWN_SKILLS.items():
        if keyword not in lower_text:
            continue
        evidence_lines = [line for line in lines if keyword in line.lower()][:2]
        skills.append(
            LLMSkillClaim(
                skill_name=keyword,
                category=category,
                confidence=0.6,  # capped below real-LLM confidence: this is keyword matching only
                evidence=evidence_lines or [keyword],
            )
        )

    return LLMExtractedCandidateData(
        full_name=full_name,
        email=email_match.group(0) if email_match else None,
        phone=phone_match.group(0) if phone_match else None,
        primary_location=None,
        links=links,
        education=[],
        experiences=[],
        projects=[],
        skills=skills,
        preferences=None,
        strengths=[],
        gaps=[
            "Parsed with LLM_PROVIDER=stub: education/experience/project entries were not "
            "extracted. Configure a real provider (openai/anthropic) for full extraction."
        ],
    )


def _research_company(page_text: str) -> LLMCompanyResearchData:
    """The only thing the stub can honestly claim as a "fact" is the page's own first line
    (typically a title/heading) -- because it's the same text used as evidence, it trivially
    verifies, unlike guessing at what the page "is about"."""
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    if not lines:
        return LLMCompanyResearchData(facts=[], inferences=[])
    headline = lines[0]
    return LLMCompanyResearchData(
        facts=[
            LLMResearchFact(fact_type="what_they_build", statement=headline, evidence=headline)
        ],
        inferences=[],
    )


def _draft_outreach(context_prompt: str) -> LLMOutreachMessages:
    company_line = next(
        (line for line in context_prompt.splitlines() if line.startswith("COMPANY: ")), "COMPANY:"
    )
    company_name = company_line.removeprefix("COMPANY:").strip() or "your company"

    body = (
        f"Hi,\n\nI came across {company_name} and wanted to reach out about the role.\n\n"
        f"{_STUB_MESSAGE_NOTE}\n\nBest,\nAdi"
    )
    return LLMOutreachMessages(
        linkedin_full=body,
        linkedin_connection=f"Hi -- interested in {company_name}, would love to connect. {_STUB_MESSAGE_NOTE}",
        email=f"Subject: Interest in {company_name}\n\n{body}",
        personalization_rationale=(
            "Stub provider: no real personalization was performed. Configure a real LLM "
            "provider for a genuinely personalized draft."
        ),
    )
