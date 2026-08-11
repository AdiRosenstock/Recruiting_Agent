"""The deterministic "Personal Connection Detection" trigger list -- shared by the fit scorer
(`services/scoring/scorer.py`, which uses a hit to bump `domain_match`) and the Company Research
Agent (`services/research/agent.py`, which uses a hit to write one `personal_connection`
inference row). Kept in one place so both always agree on what counts as a genuine connection --
per spec, these are used only when genuinely relevant, never forced into every result.
"""

# label -> keywords whose presence in company text constitutes a genuine, pre-confirmed personal
# connection. Deliberately short and specific, not a general "interesting company" heuristic.
DOMAIN_TRIGGERS: dict[str, tuple[str, ...]] = {
    "healthcare/radiology (Adi's mother is a radiologist)": (
        "radiology",
        "medical imaging",
        "ultrasound",
        "healthcare ai",
        "diagnostic imaging",
    ),
    "Costa Rica / Latin America background": (
        "costa rica",
        "latin america",
        "latam",
        "cross-border payments",
    ),
    "fintech / financial-data (Bloomberg experience)": (
        "fintech",
        "financial data",
        "market data",
        "trading platform",
        "financial infrastructure",
    ),
}


def detect_domain_connections(text: str) -> list[str]:
    """Returns the labels of every trigger whose keywords appear in `text` (case-insensitive)."""
    haystack = text.lower()
    return [
        label
        for label, keywords in DOMAIN_TRIGGERS.items()
        if any(keyword in haystack for keyword in keywords)
    ]
