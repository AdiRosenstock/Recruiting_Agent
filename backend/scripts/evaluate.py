#!/usr/bin/env python
"""Evaluation harness: a repeatable report on the two things pytest's exact-equality assertions
don't cover well.

1. **FitScorer over a small, realistic golden set.** Unit tests (tests/unit/test_scorer.py)
   check individual components in isolation; this runs the *whole* scorer, with the two real
   seeded profile configs (scripts/seed_profiles.py), over cases chosen to each exercise one
   documented design decision (extra-experience doesn't cliff to zero, a domain-connection hit
   moves the score, a new-grad profile's zeroed stage weight actually zeroes it out, ...) and
   checks the resulting tier lands in an expected range. This is a PASS/FAIL section -- a
   surprising tier shift here after touching scoring/weights code is exactly what this is for.

2. **The LLM-driven agents' output, read by a human.** There's no boolean to assert against a
   real model's prose -- this section runs the company researcher and outreach writer against
   canned inputs and prints the actual output (fact verification rate, drafted messages, banned-
   phrase scan) for a human to judge quality against. Useful before/after a prompt change to see
   what actually moved, not just whether tests still pass. Runs the LLM_PROVIDER configured in
   the environment (defaults to stub, like everywhere else) -- meaningful review requires a real
   provider; the stub path still runs, deterministically, to confirm the harness itself works.

Runs standalone: no database, no HTTP server, no network beyond whatever LLM_PROVIDER needs.

Usage: `.venv/bin/python scripts/evaluate.py`
"""

import sys
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.schemas.candidate import CandidateProfile, ExperienceEntry, SkillClaim  # noqa: E402
from app.schemas.company import CompanyRead  # noqa: E402
from app.schemas.job import JobRead  # noqa: E402
from app.schemas.search_profile import SearchProfileConfig, SearchProfileRead  # noqa: E402
from app.services.evidence import verify_snippet  # noqa: E402
from app.services.llm.factory import get_llm_provider  # noqa: E402
from app.services.outreach.banned_phrases import find_banned_phrases  # noqa: E402
from app.services.outreach.llm_outreach_writer import LLMOutreachWriter  # noqa: E402
from app.services.research.llm_researcher import LLMCompanyResearcher  # noqa: E402
from app.services.scoring.scorer import FitScorer, Tier  # noqa: E402

# Mirrors scripts/seed_profiles.py's two real profile configs exactly -- these are what the
# scorer actually runs against in production, not a synthetic test config.
_STARTUP_OUTREACH = SearchProfileRead(
    id=uuid.uuid4(),
    candidate_id=uuid.uuid4(),
    profile_key="startup_outreach",
    display_name="Startup Outreach",
    outreach_enabled=True,
    config=SearchProfileConfig(
        weights={},
        role_filters=[
            "software engineer",
            "backend engineer",
            "founding engineer",
            "ai engineer",
            "data engineer",
        ],
        stage_filters=["pre_seed", "seed", "series_a", "series_b"],
        location_filters=["nyc", "new york", "remote"],
    ),
)
_NEW_GRAD_2027 = SearchProfileRead(
    id=uuid.uuid4(),
    candidate_id=uuid.uuid4(),
    profile_key="new_grad_2027",
    display_name="New Grad 2027",
    outreach_enabled=False,
    config=SearchProfileConfig(
        weights={"stage": 0.0, "role": 0.25, "experience": 0.20},
        role_filters=["software engineer", "quant", "quantitative", "data analyst"],
        stage_filters=[],
        location_filters=[],
    ),
)


def _skill(name: str, category: str, *, verified: bool = True) -> SkillClaim:
    return SkillClaim(
        id=uuid.uuid4(),
        skill_name=name,
        category=category,
        confidence=0.9,
        verified=verified,
        evidence=[],
    )


def _experience(*, years_ago_start: float, years_ago_end: float | None) -> ExperienceEntry:
    today = date.today()
    start = today - timedelta(days=round(years_ago_start * 365))
    end = None if years_ago_end is None else today - timedelta(days=round(years_ago_end * 365))
    return ExperienceEntry(
        id=uuid.uuid4(),
        category="work",
        organization="Bloomberg",
        title="Software Engineer Intern",
        location="New York, NY",
        start_date=start,
        end_date=end,
        is_current=end is None,
        description=None,
        evidence_snippet="Data engineering and agentic AI tooling.",
    )


# A single realistic candidate (Adi-shaped, not literally his data) reused across every case --
# what varies is the job/company/profile, same as in real use where one candidate profile scores
# against many jobs.
_CANDIDATE = CandidateProfile(
    id=uuid.uuid4(),
    full_name="Golden Candidate",
    email=None,
    phone=None,
    primary_location="New York, NY",
    links={},
    education=[],
    projects=[],
    preferences=None,
    summary=None,
    active_resume_id=None,
    experiences=[_experience(years_ago_start=1.5, years_ago_end=1.0)],
    skills=[
        _skill("python", "language"),
        _skill("typescript", "language"),
        _skill("postgresql", "database"),
        _skill("aws", "tool"),
        _skill("kubernetes", "tool"),
        _skill("agentic", "ai"),
        _skill("data pipeline", "data"),
    ],
)


def _job(
    *,
    title: str,
    technologies: list[str],
    location: str | None,
    work_mode: str | None = None,
    experience_requirements: str | None = None,
    description: str | None = None,
) -> JobRead:
    return JobRead(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        title=title,
        location=location,
        job_url="https://example.com/job",
        description=description,
        experience_requirements=experience_requirements,
        technologies=technologies,
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
    )


def _company(
    *, funding_stage: str | None, industry: str | None = None, description: str | None = None
) -> CompanyRead:
    return CompanyRead(
        id=uuid.uuid4(),
        name="Golden Co",
        normalized_name="golden co",
        website=None,
        location="New York, NY",
        industry=industry,
        description=description,
        founders=[],
        funding_stage=funding_stage,
        amount_raised_usd=None,
        investors=[],
        employee_count=12,
        technologies=[],
        date_discovered=datetime.now(UTC),
        date_last_checked=None,
    )


@dataclass
class GoldenCase:
    name: str
    note: str
    job: JobRead
    company: CompanyRead
    profile: SearchProfileRead
    expected_tiers: set[Tier] = field(default_factory=set)


GOLDEN_CASES: list[GoldenCase] = [
    GoldenCase(
        name="strong startup fit",
        note="Skills, role, stage, and location all line up -- should score high.",
        job=_job(
            title="Founding Backend Engineer",
            technologies=["Python", "PostgreSQL", "AWS"],
            location="New York, NY",
        ),
        company=_company(funding_stage="seed"),
        profile=_STARTUP_OUTREACH,
        expected_tiers={"excellent", "strong"},
    ),
    GoldenCase(
        name="extra experience required doesn't cliff",
        note="Job asks for 5+ years, candidate has ~0.5y dated -- should get partial credit, "
        "not zero (see scorer's smooth experience_match, never a hard cutoff).",
        job=_job(
            title="Backend Engineer",
            technologies=["Python", "PostgreSQL"],
            location="New York, NY",
            experience_requirements="5+ years professional experience",
        ),
        company=_company(funding_stage="seed"),
        profile=_STARTUP_OUTREACH,
        expected_tiers={"strong", "worth_reviewing", "weak"},  # anything but "ignore"
    ),
    GoldenCase(
        name="remote-Bay-Area job under startup_outreach (NYC-primary)",
        note="Good skill fit, but onsite-in-SF -- location_match should pull the score down "
        "without a hard rejection.",
        job=_job(
            title="Backend Engineer",
            technologies=["Python", "AWS", "Kubernetes"],
            location="San Francisco, CA",
            work_mode="onsite",
        ),
        company=_company(funding_stage="seed"),
        profile=_STARTUP_OUTREACH,
        expected_tiers={"worth_reviewing", "weak"},
    ),
    GoldenCase(
        name="personal-connection domain trigger",
        note="Company description hits the radiology/imaging trigger -- domain_match should be "
        "near-maximal, nudging an already-decent fit up a notch.",
        job=_job(
            title="Backend Engineer",
            technologies=["Python", "PostgreSQL"],
            location="New York, NY",
        ),
        company=_company(
            funding_stage="seed",
            description="We build AI-assisted radiology and diagnostic imaging software.",
        ),
        profile=_STARTUP_OUTREACH,
        expected_tiers={"excellent", "strong"},
    ),
    GoldenCase(
        name="growth-stage quant role under new_grad_2027 (stage weight zeroed)",
        note="startup_outreach's stage_filters would reject a growth-stage company outright; "
        "new_grad_2027 zeroes the stage weight in its config specifically so this doesn't "
        "happen -- should score on role/skill fit alone.",
        job=_job(
            title="Quantitative Developer",
            technologies=["Python", "PostgreSQL"],
            location="New York, NY",
        ),
        company=_company(funding_stage="growth"),
        profile=_NEW_GRAD_2027,
        expected_tiers={"excellent", "strong", "worth_reviewing"},
    ),
    GoldenCase(
        name="clear non-fit",
        note="Wrong stack, wrong role entirely -- should land at the bottom.",
        job=_job(
            title="Sales Development Representative",
            technologies=["Salesforce"],
            location="Chicago, IL",
        ),
        company=_company(funding_stage="seed"),
        profile=_STARTUP_OUTREACH,
        expected_tiers={"weak", "ignore"},
    ),
]


def run_scoring_evaluation() -> bool:
    print("=" * 78)
    print("FitScorer golden-set evaluation")
    print("=" * 78)
    scorer = FitScorer()
    all_passed = True
    for case in GOLDEN_CASES:
        result = scorer.score(
            candidate=_CANDIDATE, job=case.job, company=case.company, profile=case.profile
        )
        passed = result.tier in case.expected_tiers
        all_passed = all_passed and passed
        status = "PASS" if passed else "FAIL"
        print(f"\n[{status}] {case.name}")
        print(f"  {case.note}")
        print(
            f"  score={result.overall_score:.1f} tier={result.tier!r} "
            f"expected={sorted(case.expected_tiers)}"
        )
        if result.strengths:
            print(f"  strengths: {'; '.join(result.strengths)}")
        if result.gaps:
            print(f"  gaps: {'; '.join(result.gaps)}")
    print()
    return all_passed


_RESEARCH_PAGES: dict[str, str] = {
    "content-rich page": (
        "Acme Robotics builds warehouse automation for mid-market logistics companies.\n\n"
        "We're a Series A startup founded in 2023 by robotics engineers from Boston Dynamics "
        "and MIT. Our customers include three of the top ten US 3PLs. We recently closed a "
        "$14M Series A led by Founders Fund.\n\n"
        "We're hiring backend engineers to work on our fleet coordination system, built on "
        "Python, PostgreSQL, and Kubernetes."
    ),
    "thin marketing page": "Acme | The future of logistics. Contact sales to learn more.",
}

_OUTREACH_CONTEXTS: dict[str, str] = {
    "startup with real research": (
        "CANDIDATE: Golden Candidate\n"
        "- Software Engineer Intern at Bloomberg: Data engineering and agentic AI tooling.\n"
        "Verified skills: python, typescript, postgresql, aws, kubernetes\n\n"
        "COMPANY: Acme Robotics\n"
        "JOB: Founding Backend Engineer\n\n"
        "RESEARCH:\n"
        "- [FACT] Acme Robotics builds warehouse automation for mid-market logistics "
        "companies.\n"
        "- [FACT] Recently closed a $14M Series A led by Founders Fund.\n"
        "- [INFERENCE] Likely needs engineers comfortable with real-time systems, given the "
        "fleet-coordination focus.\n\n"
        "CONTACT: Jane Doe, Co-Founder & CEO"
    ),
}


def run_llm_agent_evaluation() -> None:
    settings = get_settings()
    provider = get_llm_provider(settings)
    print("=" * 78)
    print(f"LLM agent output review (LLM_PROVIDER={provider.name})")
    print("=" * 78)
    if provider.name == "stub":
        print(
            "\nNote: running under the stub provider -- output below is deterministic "
            "keyword/template filler, not a real quality signal. Set LLM_PROVIDER=openai or "
            "anthropic (with a key) for a meaningful review.\n"
        )

    researcher = LLMCompanyResearcher()
    print("\n--- Company Research Agent ---")
    for label, page_text in _RESEARCH_PAGES.items():
        extracted = researcher.research(page_text, provider)
        verified_count = sum(
            1 for fact in extracted.facts if verify_snippet(fact.evidence, page_text)
        )
        total_facts = len(extracted.facts)
        rate = f"{verified_count}/{total_facts}" if total_facts else "n/a (0 facts)"
        print(
            f"\n[{label}] facts={total_facts} inferences={len(extracted.inferences)} "
            f"verified={rate}"
        )
        for fact in extracted.facts:
            verified = verify_snippet(fact.evidence, page_text)
            print(
                f"  FACT ({'verified' if verified else 'UNVERIFIED -- would demote'}): "
                f"{fact.statement}"
            )
        for inference in extracted.inferences:
            print(f"  INFERENCE: {inference.statement}")

    writer = LLMOutreachWriter()
    print("\n--- Outreach Message Agent ---")
    for label, context in _OUTREACH_CONTEXTS.items():
        drafts = writer.write(context, provider)
        print(f"\n[{label}]")
        for variant_name, text in (
            ("linkedin_full", drafts.linkedin_full),
            ("linkedin_connection", drafts.linkedin_connection),
            ("email", drafts.email),
        ):
            hits = find_banned_phrases(text)
            flag = f"  ** BANNED PHRASES FOUND: {hits} **" if hits else ""
            print(f"  {variant_name} ({len(text)} chars){flag}")
            print(f"    {text[:200]}{'...' if len(text) > 200 else ''}")
        print(f"  rationale: {drafts.personalization_rationale}")
    print()


def main() -> int:
    scoring_passed = run_scoring_evaluation()
    run_llm_agent_evaluation()
    print("=" * 78)
    print(f"Scoring golden set: {'ALL PASSED' if scoring_passed else 'SOME FAILED'}")
    print("LLM agent output: informational, read above -- no automatic pass/fail.")
    print("=" * 78)
    return 0 if scoring_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
