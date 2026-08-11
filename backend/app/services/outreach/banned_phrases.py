"""Deterministic post-generation filter for the corporate/AI-written phrases the spec explicitly
rules out. Runs after every LLM generation; never silently rewrites the text (that would just be
another LLM guess) -- it flags what it finds so a human reviewing the draft sees the warning
before ever sending it. See services/outreach/agent.py.
"""

_BANNED_PHRASES = (
    "significant ownership",
    "synergy",
    "revolutionary",
    "i am extremely passionate",
    "i am thrilled to apply",
)


def find_banned_phrases(text: str) -> list[str]:
    lowered = text.lower()
    return [phrase for phrase in _BANNED_PHRASES if phrase in lowered]
