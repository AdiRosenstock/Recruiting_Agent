"""Unit tests for the stub LLM provider's research/outreach branches added in Phase 3 -- the
existing resume-extraction branch is covered in test_llm_providers.py."""

import pytest
from pydantic import BaseModel

from app.schemas.llm_outreach import LLMOutreachMessages
from app.schemas.llm_research import LLMCompanyResearchData
from app.services.evidence import verify_snippet
from app.services.llm.base import LLMProviderError
from app.services.llm.stub_provider import StubProvider


class _UnsupportedSchema(BaseModel):
    value: str = "x"


def test_research_stub_produces_a_self_verifying_fact() -> None:
    page_text = "Acme Robotics builds warehouse automation robots.\nWe are hiring engineers."
    result = StubProvider().structured_completion(
        system="sys", prompt=page_text, response_model=LLMCompanyResearchData, prompt_version="v1"
    )
    assert len(result.facts) == 1
    fact = result.facts[0]
    # The stub's whole design point: its "fact" must verify against the same source text.
    assert verify_snippet(fact.evidence, page_text)
    assert result.inferences == []


def test_research_stub_handles_empty_page_text() -> None:
    result = StubProvider().structured_completion(
        system="sys", prompt="", response_model=LLMCompanyResearchData, prompt_version="v1"
    )
    assert result.facts == []
    assert result.inferences == []


def test_outreach_stub_produces_all_three_variants_labeled_as_stub() -> None:
    prompt = "CANDIDATE: Adi Rosenstock\n\nCOMPANY: Acme Robotics\nDescription: warehouse robots\n"
    result = StubProvider().structured_completion(
        system="sys", prompt=prompt, response_model=LLMOutreachMessages, prompt_version="v1"
    )
    assert "Acme Robotics" in result.linkedin_full
    assert "Acme Robotics" in result.linkedin_connection
    assert "Acme Robotics" in result.email
    assert "stub" in result.personalization_rationale.lower()
    for variant in (result.linkedin_full, result.linkedin_connection, result.email):
        assert "Stub-generated placeholder" in variant


def test_outreach_stub_falls_back_gracefully_with_no_company_line() -> None:
    result = StubProvider().structured_completion(
        system="sys",
        prompt="no structured fields here",
        response_model=LLMOutreachMessages,
        prompt_version="v1",
    )
    assert "your company" in result.linkedin_full


def test_stub_rejects_unsupported_schema() -> None:
    with pytest.raises(LLMProviderError, match="does not support"):
        StubProvider().structured_completion(
            system="sys", prompt="x", response_model=_UnsupportedSchema, prompt_version="v1"
        )
