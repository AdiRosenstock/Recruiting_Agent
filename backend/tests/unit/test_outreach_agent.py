"""Unit tests for `_build_context_prompt` and the banned-phrase warning path in
`OutreachMessageAgent.generate` -- neither had any dedicated coverage before (only exercised
incidentally, with minimal fixture data, via the applications endpoint's outreach-generation
integration test), which meant every optional-field branch here (company description/industry/
funding stage, job location/description, research facts/personal connections, a named contact)
was untested. Plain, unpersisted model instances -- no DB needed for prompt-string assembly.
"""

import uuid
from unittest.mock import MagicMock

from app.models.company import Company
from app.models.company_research import CompanyResearch
from app.models.contact import Contact
from app.models.job import Job
from app.schemas.candidate import CandidateProfile, ExperienceEntry, SkillClaim
from app.schemas.llm_outreach import LLMOutreachMessages
from app.services.outreach.agent import OutreachMessageAgent, _build_context_prompt
from app.services.outreach.llm_outreach_writer import LLMOutreachWriter


def _candidate() -> CandidateProfile:
    return CandidateProfile(
        id=uuid.uuid4(),
        full_name="Jordan Test",
        email=None,
        phone=None,
        primary_location=None,
        links={},
        education=[],
        experiences=[
            ExperienceEntry(
                id=uuid.uuid4(),
                category="work",
                organization="Bloomberg",
                title="Software Engineer Intern",
                location="New York, NY",
                start_date=None,
                end_date=None,
                is_current=True,
                description="Built agentic AI tooling.",
                evidence_snippet="x",
            )
        ],
        projects=[],
        skills=[
            SkillClaim(
                id=uuid.uuid4(),
                skill_name="python",
                category="language",
                confidence=0.9,
                verified=True,
                evidence=[],
            )
        ],
        preferences=None,
        summary=None,
        active_resume_id=None,
    )


def _rich_company() -> Company:
    return Company(
        id=uuid.uuid4(),
        name="Acme Robotics",
        normalized_name="acme robotics",
        description="Warehouse automation for mid-market logistics.",
        industry="Robotics",
        funding_stage="seed",
    )


def _rich_job(company_id: uuid.UUID) -> Job:
    return Job(
        id=uuid.uuid4(),
        company_id=company_id,
        title="Founding Backend Engineer",
        location="New York, NY",
        job_url="https://acme.example/jobs/1",
        description="Own the fleet-coordination backend end to end.",
    )


def test_build_context_prompt_includes_every_optional_section_when_present() -> None:
    company = _rich_company()
    job = _rich_job(company.id)
    research = [
        CompanyResearch(
            id=uuid.uuid4(),
            company_id=company.id,
            fact_type="funding",
            statement="Closed a $14M Series A led by Founders Fund.",
            is_inference=False,
            confidence=1.0,
        ),
        CompanyResearch(
            id=uuid.uuid4(),
            company_id=company.id,
            fact_type="personal_connection",
            statement="Genuine personal connection: healthcare/radiology.",
            is_inference=True,
            confidence=1.0,
        ),
    ]
    contact = Contact(id=uuid.uuid4(), company_id=company.id, name="Jane Doe", title="CEO")

    prompt = _build_context_prompt(
        candidate=_candidate(), job=job, company=company, research=research, contact=contact
    )

    assert "Bloomberg" in prompt
    assert "Verified skills: python" in prompt
    assert "Description: Warehouse automation" in prompt
    assert "Industry: Robotics" in prompt
    assert "Funding stage: seed" in prompt
    assert "Location: New York, NY" in prompt
    assert "Own the fleet-coordination" in prompt
    assert "Closed a $14M Series A" in prompt
    assert "GENUINE PERSONAL CONNECTION" in prompt
    assert "healthcare/radiology" in prompt
    assert "RECIPIENT: Jane Doe, CEO" in prompt


def test_build_context_prompt_omits_optional_sections_when_absent() -> None:
    company = Company(id=uuid.uuid4(), name="Bare Co", normalized_name="bare co")
    job = Job(
        id=uuid.uuid4(),
        company_id=company.id,
        title="Engineer",
        job_url="https://bare.example/jobs/1",
    )

    prompt = _build_context_prompt(
        candidate=_candidate(), job=job, company=company, research=[], contact=None
    )

    assert "Description:" not in prompt
    assert "Industry:" not in prompt
    assert "Funding stage:" not in prompt
    assert "Location:" not in prompt
    assert "RESEARCHED FACTS" not in prompt
    assert "GENUINE PERSONAL CONNECTION" not in prompt
    assert "RECIPIENT" not in prompt


def test_generate_flags_a_banned_phrase_in_a_drafted_variant() -> None:
    writer = MagicMock(spec=LLMOutreachWriter)
    writer.write.return_value = LLMOutreachMessages(
        linkedin_full="I am extremely passionate about this role.",
        linkedin_connection="Would love to connect.",
        email="Subject: Hi\n\nWould love to chat.",
        personalization_rationale="test",
    )
    llm_provider = MagicMock()
    llm_provider.name = "stub"

    db = MagicMock()
    db.query.return_value.filter_by.return_value.all.return_value = []

    agent = OutreachMessageAgent(writer=writer, llm_provider=llm_provider)
    company = _rich_company()
    job = _rich_job(company.id)
    _, warnings = agent.generate(
        db=db, candidate=_candidate(), job=job, company=company, contact=None
    )

    assert len(warnings) == 1
    assert "linkedin_full" in warnings[0]
    assert "i am extremely passionate" in warnings[0].lower()
