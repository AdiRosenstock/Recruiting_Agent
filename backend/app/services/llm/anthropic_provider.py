"""Real, network-calling Anthropic implementation of LLMProvider.

Anthropic has no `response_format` equivalent, so structured output is obtained via a forced
tool call: we register one tool whose `input_schema` is the Pydantic model's JSON schema and
force the model to use it (`tool_choice={"type": "tool", ...}`), then validate the tool call's
`input` against the same model.
"""

import time

from anthropic import Anthropic

from app.core.logging import get_logger, log_agent_decision
from app.services.llm.base import LLMProviderError, T

logger = get_logger(__name__)

_TOOL_NAME = "record_structured_output"
_MAX_TOKENS = 4096


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise LLMProviderError(
                "ANTHROPIC_API_KEY is not set. Set it in .env or switch LLM_PROVIDER to 'stub'."
            )
        self._client = Anthropic(api_key=api_key)
        self._model = model

    def structured_completion(
        self,
        *,
        system: str,
        prompt: str,
        response_model: type[T],
        prompt_version: str,
    ) -> T:
        schema = response_model.model_json_schema()

        started = time.monotonic()
        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=_MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                tools=[
                    {
                        "name": _TOOL_NAME,
                        "description": f"Record the extracted {response_model.__name__} data.",
                        "input_schema": schema,
                    }
                ],
                tool_choice={"type": "tool", "name": _TOOL_NAME},
            )
        except Exception as exc:  # noqa: BLE001 -- normalize every SDK failure mode
            raise LLMProviderError(f"Anthropic structured completion failed: {exc}") from exc

        duration_ms = round((time.monotonic() - started) * 1000)
        tool_use = next(
            (block for block in message.content if block.type == "tool_use"),
            None,
        )
        if tool_use is None:
            raise LLMProviderError("Anthropic did not return a tool_use block.")

        log_agent_decision(
            "llm_structured_completion",
            provider=self.name,
            model=self._model,
            prompt_version=prompt_version,
            response_model=response_model.__name__,
            duration_ms=duration_ms,
        )
        return response_model.model_validate(tool_use.input)
