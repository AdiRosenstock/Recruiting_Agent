"""Unit tests for GitHubNewGradListSource. Mocks the httpx client with a small, hand-crafted
fixture that mirrors the real README's HTML-table structure (confirmed against the live file
during development) -- no live network in tests."""

from datetime import date
from unittest.mock import MagicMock

from app.schemas.discovery import DiscoveryQuery
from app.services.discovery.github_new_grad_list import GitHubNewGradListSource

_FIXTURE_MARKDOWN = """
# 2026 New Grad Positions

## \U0001f4bb Software Engineering New Grad Roles

<table>
<thead>
<tr><th>Company</th><th>Role</th><th>Location</th><th>Application</th><th>Age</th></tr>
</thead>
<tbody>
<tr>
<td><strong><a href="https://simplify.jobs/c/Acme">Acme</a></strong></td>
<td>Software Engineer I</td>
<td>New York, NY</td>
<td><div align="center"><a href="https://acme.com/apply"><img src="x" alt="Apply"></a></div></td>
<td>0d</td>
</tr>
<tr>
<td>↳</td>
<td>Software Engineer II</td>
<td>Remote</td>
<td><div align="center"><a href="https://acme.com/apply2"><img src="x" alt="Apply"></a></div></td>
<td>3d</td>
</tr>
<tr>
<td><strong><a href="https://simplify.jobs/c/Closed">ClosedCo</a></strong></td>
<td>Backend Engineer</td>
<td>SF, CA</td>
<td>\U0001f512</td>
<td>5d</td>
</tr>
</tbody>
</table>

## \U0001f527 Hardware Engineering New Grad Roles

<table>
<thead>
<tr><th>Company</th><th>Role</th><th>Location</th><th>Application</th><th>Age</th></tr>
</thead>
<tbody>
<tr>
<td><strong><a href="https://simplify.jobs/c/HW">HWCo</a></strong></td>
<td>Hardware Engineer</td>
<td>Austin, TX</td>
<td><div align="center"><a href="https://hw.com/apply"><img src="x" alt="Apply"></a></div></td>
<td>1d</td>
</tr>
</tbody>
</table>
"""


def _make_client(markdown_text: str) -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.text = markdown_text
    client.get.return_value = response
    return client


def test_parses_active_rows_including_continuation_rows() -> None:
    source = GitHubNewGradListSource(client=_make_client(_FIXTURE_MARKDOWN))
    jobs = {job.title: job for job in source.search_jobs(DiscoveryQuery())}

    assert "Software Engineer I" in jobs
    assert "Software Engineer II" in jobs
    # The continuation row ("↳") inherits the company from the row above it.
    assert jobs["Software Engineer I"].company.name == "Acme"
    assert jobs["Software Engineer II"].company.name == "Acme"
    assert jobs["Software Engineer I"].job_url == "https://acme.com/apply"


def test_skips_closed_listings_with_no_application_link() -> None:
    jobs = GitHubNewGradListSource(client=_make_client(_FIXTURE_MARKDOWN)).search_jobs(
        DiscoveryQuery()
    )
    assert all(job.title != "Backend Engineer" for job in jobs)


def test_excludes_sections_outside_the_included_list() -> None:
    jobs = GitHubNewGradListSource(client=_make_client(_FIXTURE_MARKDOWN)).search_jobs(
        DiscoveryQuery()
    )
    assert all(job.title != "Hardware Engineer" for job in jobs)


def test_location_filter_narrows_results() -> None:
    jobs = GitHubNewGradListSource(client=_make_client(_FIXTURE_MARKDOWN)).search_jobs(
        DiscoveryQuery(location_filters=["remote"])
    )
    assert {job.title for job in jobs} == {"Software Engineer II"}


def test_age_in_days_converts_to_approximate_posted_date() -> None:
    jobs = {
        job.title: job
        for job in GitHubNewGradListSource(client=_make_client(_FIXTURE_MARKDOWN)).search_jobs(
            DiscoveryQuery()
        )
    }
    assert jobs["Software Engineer I"].posted_date == date.today()
