from app.services.contacts import rank_contact_priority


def test_very_early_startup_ranks_founder_ceo_first() -> None:
    rank, rationale = rank_contact_priority(title="Co-Founder & CEO", company_employee_count=5)
    assert rank == 1
    assert "Founder" in rationale


def test_very_early_startup_ranks_cto_second() -> None:
    rank, _ = rank_contact_priority(title="CTO", company_employee_count=None)
    assert rank == 2


def test_larger_company_ranks_hiring_manager_first() -> None:
    rank, rationale = rank_contact_priority(
        title="Engineering Hiring Manager", company_employee_count=200
    )
    assert rank == 1
    assert "larger" in rationale


def test_larger_company_treats_founder_as_lowest_priority() -> None:
    early_rank, _ = rank_contact_priority(title="Founder", company_employee_count=5)
    larger_rank, _ = rank_contact_priority(title="Founder", company_employee_count=200)
    assert early_rank == 1  # top priority at a very-early-stage company
    assert larger_rank == 5  # last of the 5 known "larger company" priority categories


def test_unmatched_title_falls_back_to_last_rank_not_excluded() -> None:
    rank, rationale = rank_contact_priority(title="Office Manager", company_employee_count=5)
    assert rank == 5  # one past the 4 known very-early categories
    assert "didn't match" in rationale


def test_missing_title_still_returns_a_rank() -> None:
    rank, rationale = rank_contact_priority(title=None, company_employee_count=5)
    assert isinstance(rank, int)
    assert rationale


def test_employee_count_threshold_boundary() -> None:
    # Exactly at the threshold should be treated as "larger", not "very early".
    rank, rationale = rank_contact_priority(title="Founder", company_employee_count=15)
    assert "larger" in rationale
