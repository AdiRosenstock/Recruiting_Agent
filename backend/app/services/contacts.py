"""Deterministic contact-priority ranking -- lower rank number = higher priority. This only
ranks a person the user already found and entered (manually, or in a later phase via permitted
public search); nothing here scrapes or auto-discovers people. Mirrors the two priority lists
from the original spec: a very-early startup's best contact differs from a larger one's.
"""

import re

# Below this employee count (or unknown), a company is treated as "very early stage" -- the
# founder/CTO are still doing the hiring themselves. Arbitrary but reasonable threshold,
# documented here rather than buried; adjust if it stops matching reality.
_VERY_EARLY_EMPLOYEE_THRESHOLD = 15

_VERY_EARLY_PRIORITY: list[tuple[str, re.Pattern[str]]] = [
    ("Founder / CEO", re.compile(r"\bfounder\b|\bceo\b|chief executive", re.IGNORECASE)),
    ("CTO", re.compile(r"\bcto\b|chief technology officer", re.IGNORECASE)),
    ("Founding Engineer", re.compile(r"founding engineer", re.IGNORECASE)),
    (
        "Head of Engineering",
        re.compile(r"head of engineering|vp\s*of?\s*engineering", re.IGNORECASE),
    ),
]

_LARGER_COMPANY_PRIORITY: list[tuple[str, re.Pattern[str]]] = [
    (
        "Engineering hiring manager",
        re.compile(r"engineering manager|hiring manager", re.IGNORECASE),
    ),
    (
        "Head/VP of Engineering",
        re.compile(
            r"head of engineering|vp\s*of?\s*engineering|director of engineering", re.IGNORECASE
        ),
    ),
    (
        "Technical recruiter",
        re.compile(r"recruiter|talent acquisition|technical sourcer", re.IGNORECASE),
    ),
    (
        "Relevant engineering leader",
        re.compile(
            r"engineering lead|staff engineer|principal engineer|eng(?:ineering)? lead",
            re.IGNORECASE,
        ),
    ),
    ("Founder", re.compile(r"\bfounder\b|\bceo\b", re.IGNORECASE)),
]


def rank_contact_priority(
    *, title: str | None, company_employee_count: int | None
) -> tuple[int, str]:
    """Returns `(priority_rank, rationale)` -- lower rank is higher priority. Always returns a
    rank (never None) so contacts sort predictably; a title that matches nothing known lands at
    the bottom of its company-size tier rather than being excluded from the list entirely.
    """
    is_very_early = (
        company_employee_count is None or company_employee_count < _VERY_EARLY_EMPLOYEE_THRESHOLD
    )
    priority_list = _VERY_EARLY_PRIORITY if is_very_early else _LARGER_COMPANY_PRIORITY
    tier_label = "very-early-stage" if is_very_early else "larger"

    if title:
        for rank, (label, pattern) in enumerate(priority_list, start=1):
            if pattern.search(title):
                return rank, f"Matches '{label}' -- a priority contact at a {tier_label} company."

    fallback_rank = len(priority_list) + 1
    return (
        fallback_rank,
        f"Title didn't match a known priority category for a {tier_label} company.",
    )
