from app.services.discovery.upsert import normalize_company_name


def test_normalize_strips_common_suffixes_and_punctuation() -> None:
    assert normalize_company_name("Acme, Inc.") == "acme"
    assert normalize_company_name("Acme LLC") == "acme"
    assert normalize_company_name("Acme Corp.") == "acme"


def test_normalize_collapses_whitespace_and_case() -> None:
    assert normalize_company_name("  Acme   Robotics  ") == "acme robotics"
    assert normalize_company_name("ACME ROBOTICS") == "acme robotics"


def test_normalize_is_stable_for_already_clean_names() -> None:
    assert normalize_company_name("acme robotics") == "acme robotics"
