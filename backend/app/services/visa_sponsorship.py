"""Deterministic visa-sponsorship signal detection -- same philosophy as
`app/domain_connections.py`: a fixed, specific keyword/phrase list, not an LLM guess, so a
result is either a real quote found in the text or no result at all (`None`), never a
fabricated inference. Job postings that mention sponsorship at all overwhelmingly use one of a
small set of boilerplate phrasings (recruiters reuse the same lines constantly), so regex
matching on a curated list has good precision -- it will miss postings that say something
unusual, but it will not confidently claim a signal that isn't actually there.

Always treat this as a lead to verify on the actual posting, not a filter to blindly trust --
see `evidence` in the result, which is the literal matched phrase.
"""

import re
from dataclasses import dataclass

# Order matters: sponsorship-related "not" phrases are checked before the bare positive
# patterns, since text like "unable to offer visa sponsorship" would otherwise match a naive
# `r"visa sponsorship"` positive pattern.
_NO_SPONSORSHIP_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?:not?|unable to|won't|will not|does not|doesn't|do not) "
        r"(?:currently )?(?:able to )?(?:sponsor|offer.{0,20}sponsorship)",
        re.IGNORECASE,
    ),
    re.compile(r"no (?:visa )?sponsorship", re.IGNORECASE),
    re.compile(r"sponsorship is not (?:currently )?available", re.IGNORECASE),
    re.compile(r"without (?:the need for |requiring )?sponsorship", re.IGNORECASE),
    re.compile(r"must be (?:a )?(?:u\.?s\.?|united states) citizen", re.IGNORECASE),
    re.compile(r"(?:u\.?s\.?|united states) citizens? only", re.IGNORECASE),
    re.compile(
        r"must be authorized to work (?:in the (?:u\.?s\.?|united states) )?without sponsorship",
        re.IGNORECASE,
    ),
    # Found live: "US citizenship or a greencard is required for this role" -- the noun form
    # ("citizenship ... is required") wasn't caught by the "must be a US citizen" verb-form
    # pattern above, a real posting slipped through as "no signal" when it's actually a hard
    # disqualifier for a candidate who needs sponsorship.
    re.compile(
        r"(?:u\.?s\.?|united states) citizenship"
        r"(?: or (?:a )?(?:green ?card|permanent residency))?"
        r"\s*(?:is\s+)?required",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:u\.?s\.?|united states) citizens?(?:/| or )green ?card holders? only", re.IGNORECASE
    ),
)

_SPONSORSHIP_AVAILABLE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:will|can|do we) sponsor", re.IGNORECASE),
    re.compile(r"visa sponsorship (?:is )?available", re.IGNORECASE),
    re.compile(r"sponsorship (?:is )?available", re.IGNORECASE),
    re.compile(r"we sponsor (?:visas?|employment visas?|work visas?)", re.IGNORECASE),
    re.compile(r"h-?1b sponsorship", re.IGNORECASE),
    re.compile(r"eligible for (?:visa )?sponsorship", re.IGNORECASE),
    re.compile(r"opt(?:/| and |,\s*)cpt (?:welcome|eligible|accepted)", re.IGNORECASE),
    re.compile(r"open to (?:visa )?sponsorship", re.IGNORECASE),
)

Signal = str  # "likely_sponsors" | "likely_no_sponsorship"

# Catches phrasings the explicit negative pattern list doesn't happen to enumerate -- e.g. "not
# eligible for visa sponsorship" would otherwise match the positive `eligible for sponsorship`
# pattern outright. Rather than trying to hand-list every possible negated phrasing (a losing
# battle), a positive match preceded closely by a negation word gets reclassified as negative
# instead of silently mis-firing. This can't fire on the negative-pattern list itself; those are
# already unambiguous on their own.
_NEGATION_WORDS_RE = re.compile(r"\b(?:not|n't|no|unable|cannot|never)\b", re.IGNORECASE)
_NEGATION_LOOKBACK_CHARS = 25


def _negated_nearby(text: str, match_start: int) -> bool:
    window = text[max(0, match_start - _NEGATION_LOOKBACK_CHARS) : match_start]
    return bool(_NEGATION_WORDS_RE.search(window))


@dataclass(frozen=True)
class VisaSponsorshipResult:
    signal: Signal
    evidence: str  # the literal matched phrase (extended a bit further back when reclassified
    # by a nearby negation, so the evidence itself shows the "not" that flipped it)


def detect_visa_sponsorship(text: str) -> VisaSponsorshipResult | None:
    """Returns the first match found, checking "no sponsorship" phrasing first (see module
    docstring for why). `None` means no known phrasing was found either way -- most postings
    say nothing about it at all, and that is not evidence of anything."""
    for pattern in _NO_SPONSORSHIP_PATTERNS:
        match = pattern.search(text)
        if match:
            return VisaSponsorshipResult(signal="likely_no_sponsorship", evidence=match.group(0))
    for pattern in _SPONSORSHIP_AVAILABLE_PATTERNS:
        match = pattern.search(text)
        if match:
            if _negated_nearby(text, match.start()):
                window_start = max(0, match.start() - _NEGATION_LOOKBACK_CHARS)
                return VisaSponsorshipResult(
                    signal="likely_no_sponsorship", evidence=text[window_start : match.end()]
                )
            return VisaSponsorshipResult(signal="likely_sponsors", evidence=match.group(0))
    return None
