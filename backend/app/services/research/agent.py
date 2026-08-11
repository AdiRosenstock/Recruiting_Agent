"""Orchestrates company research: fetch the company's website -> LLM FACT/INFERENCE extraction
-> deterministic evidence verification -> persist. This is the enforcement point for "avoid
hallucinating company information": every FACT is verified against the actually-fetched page
text before being stored as a fact; a claim the LLM tagged as a fact but that can't be verified
is *demoted* to an inference (never silently dropped, never left posing as a fact) -- same
never-invent, never-silently-drop philosophy as resume evidence handling.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_agent_decision
from app.domain_connections import detect_domain_connections
from app.models.company import Company
from app.models.company_research import CompanyResearch
from app.models.source import Source
from app.schemas.company_research import CompanyResearchRunResult
from app.services.evidence import verify_snippet
from app.services.llm.base import LLMProvider
from app.services.research.fetcher import PageFetcher, PageFetchError
from app.services.research.llm_researcher import PROMPT_VERSION, LLMCompanyResearcher

logger = get_logger(__name__)


class CompanyNotFoundError(Exception):
    pass


class CompanyResearchAgent:
    def __init__(
        self,
        *,
        fetcher: PageFetcher,
        researcher: LLMCompanyResearcher,
        llm_provider: LLMProvider,
    ) -> None:
        self._fetcher = fetcher
        self._researcher = researcher
        self._llm_provider = llm_provider

    def research(self, *, db: Session, company_id: uuid.UUID) -> CompanyResearchRunResult:
        company = db.get(Company, company_id)
        if company is None:
            raise CompanyNotFoundError(f"Company {company_id} not found")

        warnings: list[str] = []
        if not company.website:
            warnings.append("Company has no website on file -- nothing to research from.")
            return CompanyResearchRunResult(
                company_id=company_id, facts_created=0, inferences_created=0, warnings=warnings
            )

        try:
            page = self._fetcher.fetch(company.website)
        except PageFetchError as exc:
            warnings.append(str(exc))
            return CompanyResearchRunResult(
                company_id=company_id, facts_created=0, inferences_created=0, warnings=warnings
            )

        source = self._get_or_create_source(db, url=page.url, title=page.title)

        extracted = self._researcher.research(page.text, self._llm_provider)

        # Re-running research on an unchanged (or lightly changed) page shouldn't pile up exact
        # duplicate rows -- skip anything identical to what's already on file for this company.
        existing_statements = {
            (row.fact_type, row.statement, row.is_inference)
            for row in db.query(CompanyResearch).filter_by(company_id=company_id).all()
        }

        facts_created = 0
        inferences_created = 0
        duplicates_skipped = 0

        def add_if_new(
            *, fact_type: str, statement: str, is_inference: bool, confidence: float | None
        ) -> bool:
            """Returns True if a row was actually added (False if it's an exact duplicate of
            something already on file for this company -- re-running research on an unchanged
            page shouldn't pile up repeats)."""
            key = (fact_type, statement, is_inference)
            if key in existing_statements:
                return False
            existing_statements.add(key)
            db.add(
                CompanyResearch(
                    company_id=company_id,
                    fact_type=fact_type,
                    statement=statement,
                    is_inference=is_inference,
                    source_id=source.id,
                    confidence=confidence,
                )
            )
            return True

        for fact in extracted.facts:
            verified = verify_snippet(fact.evidence, page.text)
            if verified:
                if add_if_new(
                    fact_type=fact.fact_type,
                    statement=fact.statement,
                    is_inference=False,
                    confidence=1.0,
                ):
                    facts_created += 1
                else:
                    duplicates_skipped += 1
            else:
                # Demoted, not dropped: the LLM claimed this as fact but we can't verify it
                # against the actually-fetched text, so it's stored as an inference instead of
                # a confirmed fact -- never presented as more certain than it is.
                if add_if_new(
                    fact_type=fact.fact_type,
                    statement=fact.statement,
                    is_inference=True,
                    confidence=0.3,
                ):
                    inferences_created += 1
                    warnings.append(
                        f"Claimed fact '{fact.statement[:80]}' could not be verified verbatim "
                        "against the fetched page -- stored as an inference instead."
                    )
                    log_agent_decision(
                        "research_fact_unverified",
                        company_id=str(company_id),
                        statement=fact.statement,
                    )
                else:
                    duplicates_skipped += 1

        for inference in extracted.inferences:
            if add_if_new(
                fact_type=inference.fact_type,
                statement=inference.statement,
                is_inference=True,
                confidence=None,
            ):
                inferences_created += 1
            else:
                duplicates_skipped += 1

        for label in detect_domain_connections(page.text):
            if add_if_new(
                fact_type="personal_connection",
                statement=f"Genuine personal connection: {label}.",
                is_inference=True,
                confidence=1.0,  # the keyword match itself is deterministic and certain
            ):
                inferences_created += 1
            else:
                duplicates_skipped += 1

        if duplicates_skipped:
            log_agent_decision(
                "research_duplicates_skipped",
                company_id=str(company_id),
                duplicates_skipped=duplicates_skipped,
            )

        company.date_last_checked = datetime.now(UTC)

        log_agent_decision(
            "company_researched",
            company_id=str(company_id),
            llm_provider=self._llm_provider.name,
            prompt_version=PROMPT_VERSION,
            facts_created=facts_created,
            inferences_created=inferences_created,
        )

        return CompanyResearchRunResult(
            company_id=company_id,
            facts_created=facts_created,
            inferences_created=inferences_created,
            warnings=warnings,
        )

    @staticmethod
    def _get_or_create_source(db: Session, *, url: str, title: str | None) -> Source:
        existing = db.query(Source).filter_by(url=url, source_type="company_website").one_or_none()
        if existing is not None:
            existing.fetched_at = datetime.now(UTC)
            return existing
        source = Source(
            url=url, source_type="company_website", title=title, fetched_at=datetime.now(UTC)
        )
        db.add(source)
        db.flush()
        return source
