"""Unit tests for the LLM provider adapters. These mock the vendor SDK clients directly -- no
network calls, no API keys required -- and check that request/response mapping to/from our
Pydantic response_model is correct.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from app.schemas.llm_extraction import LLMExtractedCandidateData
from app.services.llm.anthropic_provider import AnthropicProvider
from app.services.llm.base import LLMProviderError
from app.services.llm.factory import get_llm_provider
from app.services.llm.openai_provider import OpenAIProvider
from app.services.llm.stub_provider import StubProvider


class _Dummy(BaseModel):
    value: str


def test_openai_provider_requires_api_key() -> None:
    with pytest.raises(LLMProviderError, match="OPENAI_API_KEY"):
        OpenAIProvider(api_key="", model="gpt-4.1")


def test_openai_provider_parses_structured_response() -> None:
    with patch("app.services.llm.openai_provider.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        parsed = _Dummy(value="hello")
        mock_client.chat.completions.parse.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(parsed=parsed, refusal=None))]
        )

        provider = OpenAIProvider(api_key="sk-test", model="gpt-4.1")
        result = provider.structured_completion(
            system="sys", prompt="user", response_model=_Dummy, prompt_version="v1"
        )

        assert result == parsed
        mock_client.chat.completions.parse.assert_called_once()


def test_openai_provider_raises_on_refusal() -> None:
    with patch("app.services.llm.openai_provider.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.parse.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(parsed=None, refusal="cannot comply"))]
        )

        provider = OpenAIProvider(api_key="sk-test", model="gpt-4.1")
        with pytest.raises(LLMProviderError, match="refused"):
            provider.structured_completion(
                system="sys", prompt="user", response_model=_Dummy, prompt_version="v1"
            )


def test_anthropic_provider_requires_api_key() -> None:
    with pytest.raises(LLMProviderError, match="ANTHROPIC_API_KEY"):
        AnthropicProvider(api_key="", model="claude-sonnet-5")


def test_anthropic_provider_parses_tool_use_response() -> None:
    with patch("app.services.llm.anthropic_provider.Anthropic") as mock_anthropic_cls:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        tool_use_block = SimpleNamespace(type="tool_use", input={"value": "hello"})
        mock_client.messages.create.return_value = SimpleNamespace(content=[tool_use_block])

        provider = AnthropicProvider(api_key="sk-ant-test", model="claude-sonnet-5")
        result = provider.structured_completion(
            system="sys", prompt="user", response_model=_Dummy, prompt_version="v1"
        )

        assert result == _Dummy(value="hello")
        mock_client.messages.create.assert_called_once()
        _, kwargs = mock_client.messages.create.call_args
        assert kwargs["tool_choice"] == {"type": "tool", "name": "record_structured_output"}


def test_anthropic_provider_raises_when_no_tool_use_block() -> None:
    with patch("app.services.llm.anthropic_provider.Anthropic") as mock_anthropic_cls:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = SimpleNamespace(content=[])

        provider = AnthropicProvider(api_key="sk-ant-test", model="claude-sonnet-5")
        with pytest.raises(LLMProviderError, match="tool_use"):
            provider.structured_completion(
                system="sys", prompt="user", response_model=_Dummy, prompt_version="v1"
            )


def test_stub_provider_rejects_unsupported_schemas() -> None:
    with pytest.raises(LLMProviderError, match="does not support"):
        StubProvider().structured_completion(
            system="sys", prompt="user", response_model=_Dummy, prompt_version="v1"
        )


def test_stub_provider_extracts_contact_info_and_known_skills() -> None:
    resume_text = (
        "Adi Rosenstock\n"
        "adi@example.com | (470) 838-8404 | linkedin.com/in/adirosenstock\n"
        "Built things with Python and SQL.\n"
    )
    result = StubProvider().structured_completion(
        system="sys",
        prompt=resume_text,
        response_model=LLMExtractedCandidateData,
        prompt_version="v1",
    )

    assert result.full_name == "Adi Rosenstock"
    assert result.email == "adi@example.com"
    assert result.links["linkedin"].startswith("linkedin.com")
    skill_names = {s.skill_name for s in result.skills}
    assert "python" in skill_names
    assert "sql" in skill_names
    assert result.education == []  # documented stub limitation


@pytest.mark.parametrize(
    ("provider_name", "expected_type"),
    [("stub", StubProvider), ("openai", OpenAIProvider), ("anthropic", AnthropicProvider)],
)
def test_factory_returns_expected_provider_type(provider_name, expected_type) -> None:  # type: ignore[no-untyped-def]
    from app.config import Settings

    settings = Settings(
        llm_provider=provider_name,  # type: ignore[arg-type]
        openai_api_key="sk-test",
        anthropic_api_key="sk-ant-test",
    )
    provider = get_llm_provider(settings)
    assert isinstance(provider, expected_type)
