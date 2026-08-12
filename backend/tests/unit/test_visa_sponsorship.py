import pytest

from app.services.visa_sponsorship import detect_visa_sponsorship

_CASES: list[tuple[str, str | None]] = [
    ("We are unable to sponsor visas for this role.", "likely_no_sponsorship"),
    ("This role is not eligible for visa sponsorship.", "likely_no_sponsorship"),
    ("Must be a US citizen or green card holder.", "likely_no_sponsorship"),
    ("We will sponsor H1B visas for exceptional candidates.", "likely_sponsors"),
    ("Visa sponsorship is available for this position.", "likely_sponsors"),
    ("OPT/CPT welcome to apply.", "likely_sponsors"),
    ("Great benefits and a fun team culture!", None),
    (
        "Candidates must be authorized to work in the United States without sponsorship.",
        "likely_no_sponsorship",
    ),
    ("This role is eligible for visa sponsorship.", "likely_sponsors"),
    ("Unfortunately we cannot sponsor visas at this time.", "likely_no_sponsorship"),
    ("No, we do not offer visa sponsorship for this position.", "likely_no_sponsorship"),
    # Must not false-positive just because "OPT"/"eligible" appear near an unrelated negation.
    ("International students on OPT are not eligible.", None),
    # Found live (Legion Intelligence, HN "Who is hiring?"): the noun-phrase form wasn't caught
    # by the "must be a US citizen" verb-form pattern.
    (
        "US citizenship or a greencard is required for this role.",
        "likely_no_sponsorship",
    ),
    ("US citizenship is required for this position.", "likely_no_sponsorship"),
]


@pytest.mark.parametrize("text,expected", _CASES)
def test_detect_visa_sponsorship(text: str, expected: str | None) -> None:
    result = detect_visa_sponsorship(text)
    assert (result.signal if result else None) == expected


def test_evidence_is_a_verbatim_substring_of_the_input() -> None:
    text = "This role is not eligible for visa sponsorship at this time."
    result = detect_visa_sponsorship(text)
    assert result is not None
    assert result.evidence in text
