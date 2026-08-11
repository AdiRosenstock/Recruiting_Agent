"""Orchestrates outreach generation: assemble real context (candidate + job + company +
research + contact) -> LLM drafts three variants -> deterministic banned-phrase scan -> persist.
Nothing here sends anything anywhere; these are drafts for a human to review, edit, and send
manually (see the compliance notes in the README/spec).
"""

from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_agent_decision
from app.models.company import Company
from app.models.company_research import CompanyResearch
from app.models.contact import Contact
from app.models.job import Job
from app.models.outreach_message import OutreachMessage
from app.schemas.candidate import CandidateProfile
from app.services.llm.base import LLMProvider
from app.services.outreach.banned_phrases import find_banned_phrases
from app.services.outreach.llm_outreach_writer import PROMPT_VERSION, LLMOutreachWriter

logger = get_logger(__name__)

_MAX_RESEARCH_FACTS_IN_PROMPT = 8


class OutreachGenerationError(Exception):
    pass


def _build_context_prompt(
    *,
    candidate: CandidateProfile,
    job: Job,
    company: Company,
    research: list[CompanyResearch],
    contact: Contact | None,
) -> str:
    lines: list[str] = []

    lines.append(f"CANDIDATE: {candidate.full_name}")
    work_experiences = [e for e in candidate.experiences if e.category == "work"][:3]
    for exp in work_experiences:
        lines.append(f"- {exp.title} at {exp.organization}: {exp.description or exp.evidence_snippet}")
    verified_skills = sorted({s.skill_name for s in candidate.skills if s.verified})
    if verified_skills:
        lines.append(f"Verified skills: {', '.join(verified_skills)}")

    lines.append("")
    lines.append(f"COMPANY: {company.name}")
    if company.description:
        lines.append(f"Description: {company.description}")
    if company.industry:
        lines.append(f"Industry: {company.industry}")
    if company.funding_stage:
        lines.append(f"Funding stage: {company.funding_stage}")

    lines.append("")
    lines.append(f"JOB: {job.title}")
    if job.location:
        lines.append(f"Location: {job.location}")
    if job.description:
        lines.append(f"Description: {job.description[:1500]}")

    facts = [r for r in research if not r.is_inference][:_MAX_RESEARCH_FACTS_IN_PROMPT]
    connections = [r for r in research if r.fact_type == "personal_connection"]
    if facts:
        lines.append("")
        lines.append("RESEARCHED FACTS ABOUT THE COMPANY (use only what's genuinely useful):")
        for fact in facts:
            lines.append(f"- ({fact.fact_type}) {fact.statement}")
    if connections:
        lines.append("")
        lines.append("GENUINE PERSONAL CONNECTION (use only if it fits naturally, don't force it):")
        for connection in connections:
            lines.append(f"- {connection.statement}")

    if contact is not None:
        lines.append("")
        lines.append(f"RECIPIENT: {contact.name}" + (f", {contact.title}" if contact.title else ""))

    return "\n".join(lines)


class OutreachMessageAgent:
    def __init__(self, *, writer: LLMOutreachWriter, llm_provider: LLMProvider) -> None:
        self._writer = writer
        self._llm_provider = llm_provider

    def generate(
        self,
        *,
        db: Session,
        candidate: CandidateProfile,
        job: Job,
        company: Company,
        contact: Contact | None,
    ) -> tuple[list[OutreachMessage], list[str]]:
        research = db.query(CompanyResearch).filter_by(company_id=company.id).all()
        context_prompt = _build_context_prompt(
            candidate=candidate, job=job, company=company, research=research, contact=contact
        )

        drafted = self._writer.write(context_prompt, self._llm_provider)

        warnings: list[str] = []
        variants = {
            "linkedin_full": drafted.linkedin_full,
            "linkedin_connection": drafted.linkedin_connection,
            "email": drafted.email,
        }

        messages: list[OutreachMessage] = []
        for message_type, content in variants.items():
            banned = find_banned_phrases(content)
            if banned:
                warnings.append(
                    f"{message_type}: contains flagged phrase(s) {banned} -- review before sending."
                )
            message = OutreachMessage(
                candidate_id=candidate.id,
                job_id=job.id,
                contact_id=contact.id if contact else None,
                message_type=message_type,
                content=content,
                personalization_rationale=drafted.personalization_rationale,
                is_user_edited=False,
                prompt_version=PROMPT_VERSION,
                generated_by=self._llm_provider.name,
            )
            db.add(message)
            messages.append(message)

        db.flush()

        log_agent_decision(
            "outreach_generated",
            candidate_id=str(candidate.id),
            job_id=str(job.id),
            company_id=str(company.id),
            llm_provider=self._llm_provider.name,
            warning_count=len(warnings),
        )

        return messages, warnings
