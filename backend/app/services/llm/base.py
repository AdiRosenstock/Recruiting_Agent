"""Vendor-agnostic LLM abstraction.

Every semantic (LLM-powered) task in the app calls through this Protocol rather than an SDK
directly, so `LLM_PROVIDER` can switch between openai/anthropic/stub without touching calling
code. Structured output is mandatory: callers pass a Pydantic `response_model` and always get
back a validated instance of it -- never free-form text to parse themselves.
"""

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProviderError(RuntimeError):
    """Raised when a provider fails to produce a valid, schema-conforming response."""


class LLMProvider(Protocol):
    """Implemented by OpenAIProvider, AnthropicProvider, and StubProvider."""

    name: str

    def structured_completion(
        self,
        *,
        system: str,
        prompt: str,
        response_model: type[T],
        prompt_version: str,
    ) -> T:
        """Run a structured completion and return a validated `response_model` instance.

        `prompt_version` identifies the prompt template used (see services/resume_parsing for
        the concrete prompt strings) -- it is not sent to the model, only logged, so we can
        trace which prompt produced which stored data as prompts evolve.
        """
        ...
