"""Generic verbatim-or-near-verbatim text evidence checking, shared by every pipeline that asks
an LLM to quote its source rather than assert unsupported claims: resume parsing
(services/resume_parsing/evidence_validator.py) and company research
(services/research/agent.py). Deliberately has no domain knowledge of resumes or company
pages -- it just answers "does this snippet actually appear in this text?".
"""

import difflib
import re

_WHITESPACE_RE = re.compile(r"\s+")
_FUZZY_MATCH_THRESHOLD = 0.85


def _normalize(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip().lower()


def verify_snippet(snippet: str, source_text: str) -> bool:
    """True if `snippet` appears verbatim (normalized) in `source_text`, or is a close enough
    near-match to one of its lines to account for formatting artifacts (hyphenation, collapsed
    whitespace, etc.) -- not to account for genuine paraphrasing.
    """
    if not snippet.strip():
        return False

    normalized_snippet = _normalize(snippet)
    normalized_source = _normalize(source_text)
    if normalized_snippet in normalized_source:
        return True

    source_lines = [_normalize(line) for line in source_text.splitlines() if line.strip()]
    if not source_lines:
        return False
    best_ratio = max(
        difflib.SequenceMatcher(None, normalized_snippet, line).ratio() for line in source_lines
    )
    return best_ratio >= _FUZZY_MATCH_THRESHOLD
