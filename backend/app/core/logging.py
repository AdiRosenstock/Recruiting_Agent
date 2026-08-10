"""Logging setup, plus a small helper for recording agent decisions.

Every LLM call and every non-trivial deterministic decision (evidence verification outcomes,
parsing warnings) should go through `log_agent_decision` so there's a consistent, greppable
trail to debug "why did the app produce this output" after the fact -- architectural
principle #12.
"""

import logging
from typing import Any

from app.config import get_settings


def configure_logging() -> None:
    logging.basicConfig(
        level=get_settings().log_level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


_agent_logger = logging.getLogger("app.agent_decisions")


def log_agent_decision(decision: str, **context: Any) -> None:
    """Structured, single-line log entry for an agent/pipeline decision.

    Example: log_agent_decision("skill_evidence_unverified", skill="Kubernetes", candidate_id=...)
    """
    details = " ".join(f"{key}={value!r}" for key, value in context.items())
    _agent_logger.info("%s %s", decision, details)
