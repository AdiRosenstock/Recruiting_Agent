from app.services.evidence import verify_snippet

_SOURCE = "Acme builds AI infrastructure for healthcare radiology teams.\nWe raised a seed round."


def test_verify_snippet_exact_match() -> None:
    assert verify_snippet("Acme builds AI infrastructure", _SOURCE)


def test_verify_snippet_case_and_whitespace_insensitive() -> None:
    assert verify_snippet("acme   builds ai infrastructure", _SOURCE)


def test_verify_snippet_fuzzy_near_match() -> None:
    assert verify_snippet("We raised a seed round ", _SOURCE)


def test_verify_snippet_rejects_fabricated_text() -> None:
    assert not verify_snippet("Acme has 500 employees worldwide", _SOURCE)


def test_verify_snippet_rejects_empty_string() -> None:
    assert not verify_snippet("", _SOURCE)
    assert not verify_snippet("   ", _SOURCE)


def test_verify_snippet_false_on_empty_source() -> None:
    assert not verify_snippet("anything", "")
