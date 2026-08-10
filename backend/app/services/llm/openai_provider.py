"""Real, network-calling OpenAI implementation of LLMProvider.

Uses the SDK's structured-output support (`chat.completions.parse` with a Pydantic
`response_format`) so the model is constrained to the schema at the API level rather than us
hoping it produces valid JSON.
"""

import time

from openai import OpenAI
from pydantic import BaseModel

from app.core.logging import get_logger, log_agent_decision
from app.services.llm.base import LLMProviderError, T

logger = get_logger(__name__)


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise LLMProviderError(
                "OPENAI_API_KEY is not set. Set it in .env or switch LLM_PROVIDER to 'stub'."
            )
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def structured_completion(
        self,
        *,
        system: str,
        prompt: str,
        response_model: type[T],
        prompt_version: str,
    ) -> T:
        started = time.monotonic()
        try:
            completion = self._client.chat.completions.parse(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                response_format=response_model,
            )
        except Exception as exc:  # noqa: BLE001 -- normalize every SDK failure mode
            raise LLMProviderError(f"OpenAI structured completion failed: {exc}") from exc

        duration_ms = round((time.monotonic() - started) * 1000)
        message = completion.choices[0].message
        if message.refusal:
            raise LLMProviderError(f"OpenAI refused the request: {message.refusal}")
        parsed: BaseModel | None = message.parsed
        if parsed is None:
            raise LLMProviderError("OpenAI returned no parsed structured output.")

        log_agent_decision(
            "llm_structured_completion",
            provider=self.name,
            model=self._model,
            prompt_version=prompt_version,
            response_model=response_model.__name__,
            duration_ms=duration_ms,
        )
        return response_model.model_validate(parsed)
