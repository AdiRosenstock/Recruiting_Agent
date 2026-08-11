"""Orchestrates a single job's visa-sponsorship check: text already on file first (no network),
falling back to fetching the actual posting page only when there's nothing meaningful to search
in the first place (an empty `description` -- e.g. every job from the GitHub new-grad tracker,
which only ever captures Company/Role/Location/Link/Date, no posting text). Proportional network
use, not a blanket fetch-everything policy. Deterministic (services/visa_sponsorship.py) rather
than an LLM call -- sponsorship phrasing is boilerplate enough that regex is the right tool here.
"""

from datetime import UTC, datetime
from typing import Literal

from app.core.logging import log_agent_decision
from app.models.job import Job
from app.services.research.fetcher import PageFetcher, PageFetchError
from app.services.visa_sponsorship import detect_visa_sponsorship

CheckOutcome = Literal["found", "no_signal", "fetch_failed"]


def check_job_visa_sponsorship(job: Job, *, fetcher: PageFetcher) -> CheckOutcome:
    """Mutates `job` in place (`visa_sponsorship`/`visa_sponsorship_evidence`/
    `visa_sponsorship_checked_at`) -- caller owns the DB commit, same convention as
    `CompanyResearchAgent.research`."""
    haystack = f"{job.title} {job.description or ''}"
    result = detect_visa_sponsorship(haystack)
    source = "listing text"

    if result is None and not job.description:
        try:
            page = fetcher.fetch(job.job_url)
        except PageFetchError as exc:
            job.visa_sponsorship_checked_at = datetime.now(UTC)
            log_agent_decision("visa_check_fetch_failed", job_id=str(job.id), error=str(exc))
            return "fetch_failed"
        result = detect_visa_sponsorship(page.text)
        source = "fetched posting page"

    job.visa_sponsorship = result.signal if result else None
    job.visa_sponsorship_evidence = f"{result.evidence!r} (from {source})" if result else None
    job.visa_sponsorship_checked_at = datetime.now(UTC)

    if result:
        log_agent_decision(
            "visa_sponsorship_signal_found",
            job_id=str(job.id),
            signal=result.signal,
            source=source,
        )
    return "found" if result else "no_signal"
