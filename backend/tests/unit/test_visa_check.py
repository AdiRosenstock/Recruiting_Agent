"""Unit tests for check_job_visa_sponsorship -- mocks PageFetcher, no live network (the fetcher
itself is unit-tested against mocked HTTP separately in test_page_fetcher.py)."""

import uuid
from unittest.mock import MagicMock

from app.models.job import Job
from app.services.research.fetcher import FetchedPage, PageFetchError
from app.services.visa_check import check_job_visa_sponsorship


def _job(*, title: str = "Backend Engineer", description: str | None = None) -> Job:
    return Job(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        title=title,
        job_url="https://acme.example/jobs/1",
        description=description,
    )


def test_finds_signal_in_existing_description_without_fetching() -> None:
    job = _job(description="Great team. We are unable to sponsor visas for this role.")
    fetcher = MagicMock()

    outcome = check_job_visa_sponsorship(job, fetcher=fetcher)

    assert outcome == "found"
    assert job.visa_sponsorship == "likely_no_sponsorship"
    assert "unable to sponsor" in job.visa_sponsorship_evidence
    assert job.visa_sponsorship_checked_at is not None
    fetcher.fetch.assert_not_called()  # no need to hit the network -- text was already enough


def test_falls_back_to_fetching_when_no_description_on_file() -> None:
    job = _job(description=None)
    fetcher = MagicMock()
    fetcher.fetch.return_value = FetchedPage(
        url=job.job_url,
        text="Apply now. Visa sponsorship is available for qualified candidates.",
        title="Careers",
    )

    outcome = check_job_visa_sponsorship(job, fetcher=fetcher)

    assert outcome == "found"
    assert job.visa_sponsorship == "likely_sponsors"
    assert "fetched posting page" in job.visa_sponsorship_evidence
    fetcher.fetch.assert_called_once_with(job.job_url)


def test_does_not_fetch_when_description_exists_but_has_no_signal() -> None:
    """A description with nothing about sponsorship either way is still real information (not
    an empty listing) -- fetching further isn't proportional to what's actually missing."""
    job = _job(description="We build great backend systems. Apply today!")
    fetcher = MagicMock()

    outcome = check_job_visa_sponsorship(job, fetcher=fetcher)

    assert outcome == "no_signal"
    assert job.visa_sponsorship is None
    assert job.visa_sponsorship_checked_at is not None
    fetcher.fetch.assert_not_called()


def test_no_signal_anywhere_leaves_visa_sponsorship_null() -> None:
    job = _job(description=None)
    fetcher = MagicMock()
    fetcher.fetch.return_value = FetchedPage(
        url=job.job_url, text="Apply today, great benefits!", title="Careers"
    )

    outcome = check_job_visa_sponsorship(job, fetcher=fetcher)

    assert outcome == "no_signal"
    assert job.visa_sponsorship is None
    assert job.visa_sponsorship_evidence is None
    assert job.visa_sponsorship_checked_at is not None


def test_fetch_failure_is_handled_gracefully() -> None:
    job = _job(description=None)
    fetcher = MagicMock()
    fetcher.fetch.side_effect = PageFetchError("timed out")

    outcome = check_job_visa_sponsorship(job, fetcher=fetcher)

    assert outcome == "fetch_failed"
    assert job.visa_sponsorship is None
    assert job.visa_sponsorship_checked_at is not None  # still recorded as attempted
