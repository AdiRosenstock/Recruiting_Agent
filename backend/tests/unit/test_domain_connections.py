from app.domain_connections import detect_domain_connections


def test_detects_healthcare_radiology_connection() -> None:
    hits = detect_domain_connections("We build AI for medical imaging and diagnostic imaging.")
    assert any("radiologist" in h for h in hits)


def test_detects_costa_rica_connection() -> None:
    hits = detect_domain_connections("Expanding operations across Costa Rica and Latin America.")
    assert any("Costa Rica" in h for h in hits)


def test_detects_fintech_connection() -> None:
    hits = detect_domain_connections("We provide real-time market data to trading desks.")
    assert any("Bloomberg" in h for h in hits)


def test_no_hits_for_unrelated_text() -> None:
    assert detect_domain_connections("We sell project management software for SMBs.") == []


def test_case_insensitive() -> None:
    assert detect_domain_connections("RADIOLOGY AI PLATFORM") != []
