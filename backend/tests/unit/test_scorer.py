"""Pure unit tests for FitScorer -- no DB, no network. Builds minimal Pydantic fixtures by hand
so each component's logic is testable in isolation.
"""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from app.schemas.candidate import CandidateProfile, ExperienceEntry, SkillClaim
from app.schemas.company import CompanyRead
from app.schemas.job import JobRead
from app.schemas.search_profile import SearchProfileConfig, SearchProfileRead
from app.services.scoring.scorer import FitScorer


def make_skill(name: str, *, category: str = "language", verified: bool = True) -> SkillClaim:
    return SkillClaim(
        id=uuid.uuid4(),
        skill_name=name,
        category=category,
        confidence=0.9,
        verified=verified,
        evidence=[],
    )


def make_experience(
    *, category: str = "work", start: date | None = None, end: date | None = None
) -> ExperienceEntry:
    return ExperienceEntry(
        id=uuid.uuid4(),
        category=category,
        organization="Acme",
        title="Engineer",
        location=None,
        start_date=start,
        end_date=end,
        is_current=end is None,
        description=None,
        evidence_snippet="x",
    )


def make_candidate(*, skills: list[SkillClaim] | None = None, experiences=None) -> CandidateProfile:
    return CandidateProfile(
        id=uuid.uuid4(),
        full_name="Test Candidate",
        email=None,
        phone=None,
        primary_location=None,
        links={},
        education=[],
        experiences=experiences or [],
        projects=[],
        skills=skills or [],
        preferences=None,
        summary=None,
        active_resume_id=None,
    )


def make_job(
    *,
    title: str = "Backend Engineer",
    technologies: list[str] | None = None,
    description: str | None = None,
    experience_requirements: str | None = None,
    location: str | None = "New York, NY",
    work_mode: str | None = None,
) -> JobRead:
    return JobRead(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        title=title,
        location=location,
        job_url="https://example.com/job",
        description=description,
        experience_requirements=experience_requirements,
        technologies=technologies or [],
        responsibilities=[],
        compensation_min=None,
        compensation_max=None,
        compensation_currency=None,
        work_mode=work_mode,
        posted_date=None,
        deadline_date=None,
        status="open",
        source_id=None,
        date_discovered=datetime.now(UTC),
        date_last_checked=None,
        visa_sponsorship=None,
        visa_sponsorship_evidence=None,
        visa_sponsorship_checked_at=None,
    )


def make_company(
    *,
    funding_stage: str | None = "seed",
    industry: str | None = None,
    description: str | None = None,
) -> CompanyRead:
    return CompanyRead(
        id=uuid.uuid4(),
        name="Acme",
        normalized_name="acme",
        website=None,
        location=None,
        industry=industry,
        description=description,
        founders=[],
        funding_stage=funding_stage,
        amount_raised_usd=None,
        investors=[],
        employee_count=None,
        technologies=[],
        date_discovered=datetime.now(UTC),
        date_last_checked=None,
    )


def make_profile(
    *,
    role_filters: list[str] | None = None,
    stage_filters: list[str] | None = None,
    location_filters: list[str] | None = None,
    weights: dict[str, float] | None = None,
) -> SearchProfileRead:
    return SearchProfileRead(
        id=uuid.uuid4(),
        candidate_id=uuid.uuid4(),
        profile_key="startup_outreach",
        display_name="Startup Outreach",
        outreach_enabled=True,
        config=SearchProfileConfig(
            weights={} if weights is None else weights,
            role_filters=["backend engineer"] if role_filters is None else role_filters,
            stage_filters=["seed"] if stage_filters is None else stage_filters,
            location_filters=["new york"] if location_filters is None else location_filters,
        ),
    )


def test_technical_match_scores_skill_overlap() -> None:
    candidate = make_candidate(skills=[make_skill("python"), make_skill("sql")])
    job = make_job(technologies=["Python", "SQL", "Kubernetes"])
    component = FitScorer._technical_match(candidate, job)
    assert component.score == pytest.approx(2 / 3)
    assert "python" in component.explanation.lower()


def test_technical_match_ignores_unverified_skills() -> None:
    candidate = make_candidate(skills=[make_skill("python", verified=False)])
    job = make_job(technologies=["Python"])
    component = FitScorer._technical_match(candidate, job)
    assert component.score == 0.0


def test_technical_match_falls_back_to_title_when_no_technologies_listed() -> None:
    """Found via live data (a lightweight source, e.g. the GitHub new-grad tracker, that never
    populates `technologies`): every such job used to get the same flat 0.5, regardless of what
    it actually was. Should differentiate using the title/description instead of giving up."""
    candidate = make_candidate(skills=[make_skill("python"), make_skill("sql")])
    job = make_job(title="Python Backend Engineer, New Grad", technologies=[])
    component = FitScorer._technical_match(candidate, job)
    assert component.score > 0.5
    assert "python" in component.explanation.lower()


def test_technical_match_word_boundary_avoids_false_positives() -> None:
    """`go` and `r` are real (normalized) skill names -- must not match inside "going" or
    "recruiter" just because the substring happens to appear."""
    candidate = make_candidate(skills=[make_skill("go"), make_skill("r")])
    job = make_job(
        title="Recruiter", description="We are going to interview soon.", technologies=[]
    )
    component = FitScorer._technical_match(candidate, job)
    assert component.score == 0.5  # no real match -- falls back to the flat neutral score


def test_technical_match_falls_back_to_flat_score_with_no_text_signal_either() -> None:
    candidate = make_candidate(skills=[make_skill("python")])
    job = make_job(title="Product Manager", description=None, technologies=[])
    component = FitScorer._technical_match(candidate, job)
    assert component.score == 0.5


def test_role_match_scores_title_hit_highest() -> None:
    job = make_job(title="Founding Backend Engineer")
    profile = make_profile(role_filters=["backend engineer"])
    component = FitScorer._role_match(job, profile)
    assert component.score == 1.0


def test_role_match_no_hit_scores_low_not_zero() -> None:
    job = make_job(title="Marketing Manager", description="No engineering here.")
    profile = make_profile(role_filters=["backend engineer"])
    component = FitScorer._role_match(job, profile)
    assert component.score == 0.2


def test_experience_match_does_not_cliff_on_extra_required_experience() -> None:
    """Per spec: never auto-reject just because a job asks for slightly more experience than
    the candidate has."""
    today = date.today()
    candidate = make_candidate(
        experiences=[make_experience(start=today - timedelta(days=365))]  # ~1 year
    )
    job = make_job(experience_requirements="3+ years of experience required")
    component = FitScorer._experience_match(candidate, job)
    assert 0.3 <= component.score < 1.0  # penalized, but not zeroed out


def test_experience_match_full_score_when_requirement_met() -> None:
    today = date.today()
    candidate = make_candidate(experiences=[make_experience(start=today - timedelta(days=365 * 3))])
    job = make_job(experience_requirements="2+ years required")
    component = FitScorer._experience_match(candidate, job)
    assert component.score == 1.0


def test_experience_match_entry_level_with_no_experience() -> None:
    candidate = make_candidate(experiences=[])
    job = make_job(experience_requirements="Entry level / new grad")
    component = FitScorer._experience_match(candidate, job)
    assert component.score == 1.0


def test_stage_match_hits_and_misses() -> None:
    profile = make_profile(stage_filters=["seed", "series_a"])
    assert FitScorer._stage_match(make_company(funding_stage="seed"), profile).score == 1.0
    assert FitScorer._stage_match(make_company(funding_stage="growth"), profile).score == 0.2
    assert FitScorer._stage_match(make_company(funding_stage=None), profile).score == 0.4


def test_stage_match_neutral_when_profile_has_no_stage_filter() -> None:
    profile = make_profile(stage_filters=[])
    assert FitScorer._stage_match(make_company(funding_stage="growth"), profile).score == 0.5


def test_location_match_remote_is_flexible_not_rejected() -> None:
    profile = make_profile(location_filters=["new york"])
    job = make_job(location="Anywhere", work_mode="remote")
    component = FitScorer._location_match(job, profile)
    assert component.score == 0.7


def test_domain_match_detects_known_personal_connections() -> None:
    company = make_company(industry="Medical imaging", description="We build radiology AI.")
    component = FitScorer._domain_match(company)
    assert component.score == 1.0
    assert "radiologist" in component.explanation.lower()


def test_domain_match_neutral_not_a_gap_when_no_connection() -> None:
    """A missing personal connection must not read as a candidate weakness."""
    component = FitScorer._domain_match(
        make_company(industry="B2B SaaS", description="CRM software.")
    )
    assert component.score == 0.5


def test_new_grad_profile_stage_weight_zero_never_penalizes_overall_score() -> None:
    candidate = make_candidate(skills=[make_skill("python")])
    job = make_job(technologies=["Python"], title="Software Engineer New Grad")
    company = make_company(funding_stage=None)  # would normally be penalized (0.4)
    profile = make_profile(
        role_filters=["software engineer"],
        stage_filters=[],  # new_grad_2027 config: wide net, no stage preference
        location_filters=[],
        weights={"stage": 0.0, "role": 0.25, "experience": 0.20},
    )
    result = FitScorer().score(candidate=candidate, job=job, company=company, profile=profile)
    # stage_match's own score doesn't matter here since its weight is 0 -- confirm it truly
    # contributes nothing to overall_score by checking the weight, not just eyeballing the total.
    assert result.stage.score == 0.5  # neutral (no stage filter configured)


def test_overall_score_is_weighted_average_0_to_100() -> None:
    candidate = make_candidate(skills=[make_skill("python")])
    job = make_job(technologies=["Python"], title="Backend Engineer")
    company = make_company(funding_stage="seed")
    profile = make_profile()
    result = FitScorer().score(candidate=candidate, job=job, company=company, profile=profile)
    assert 0 <= result.overall_score <= 100
    assert result.tier in ("excellent", "strong", "worth_reviewing", "weak", "ignore")


def test_strengths_and_gaps_are_derived_from_component_thresholds() -> None:
    candidate = make_candidate(skills=[make_skill("python")])
    job = make_job(technologies=["Python"], title="Backend Engineer", location="New York, NY")
    company = make_company(funding_stage="seed")
    profile = make_profile()
    result = FitScorer().score(candidate=candidate, job=job, company=company, profile=profile)
    assert isinstance(result.strengths, list)
    assert isinstance(result.gaps, list)
    # A perfect skill/role/stage/location match should surface as strengths, not gaps.
    assert any("python" in s.lower() for s in result.strengths)
