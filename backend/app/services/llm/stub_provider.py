"""Deterministic, no-network stand-in for a real LLM provider.

Exists so the whole pipeline (upload -> extract -> validate -> persist) is runnable and
testable without any API key. It is intentionally *not* a substitute for real extraction
quality: it only does keyword/regex matching over the raw resume text, so it reliably finds
contact info and skills present on a fixed known-skills list, but it does not attempt to
understand resume structure well enough to reconstruct education/experience/project entries.
Those come back empty, and callers should treat stub output as a smoke-test fixture, not a
usable candidate profile. This is explicitly documented in the README and in `.env.example`.
"""

import re

from app.schemas.llm_extraction import LLMExtractedCandidateData, LLMSkillClaim
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
        if response_model is not LLMExtractedCandidateData:
            raise LLMProviderError(
                f"StubProvider only supports LLMExtractedCandidateData, got "
                f"{response_model.__name__}. Use LLM_PROVIDER=openai or anthropic instead."
            )
        result = _extract(prompt)
        return response_model.model_validate(result)


def _extract(raw_text: str) -> LLMExtractedCandidateData:
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
