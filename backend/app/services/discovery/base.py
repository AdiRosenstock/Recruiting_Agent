"""Two discovery patterns, matching how the two current profiles actually source data:
company-first (startup directories, VC portfolios) and posting-first (job trackers, hiring
threads, where company info travels inline on each posting).
"""

from typing import Protocol

from app.schemas.discovery import DiscoveredCompany, DiscoveredJob, DiscoveryQuery


class CompanySource(Protocol):
    """Company-first discovery -- see `YCDirectorySource` for the first real implementation.
    Wellfound/VC-portfolio adapters are still future work, pending their ToS/scraping
    feasibility being checked per-source (see the Phase 1 plan's risk notes). `get_jobs()` is
    allowed to legitimately return `[]` when a source has no per-company job data -- never
    fabricate a job posting/URL that doesn't exist to satisfy the interface."""

    name: str

    def search_companies(self, query: DiscoveryQuery) -> list[DiscoveredCompany]: ...
    def get_jobs(self, company: DiscoveredCompany) -> list[DiscoveredJob]: ...


class JobBoardSource(Protocol):
    """Posting-first discovery -- company info travels inline on each `DiscoveredJob`."""

    name: str

    def search_jobs(self, query: DiscoveryQuery) -> list[DiscoveredJob]: ...
