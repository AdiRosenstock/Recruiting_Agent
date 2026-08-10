"""Two discovery patterns, matching how the two current profiles actually source data:
company-first (startup directories, VC portfolios) and posting-first (job trackers, hiring
threads, where company info travels inline on each posting).
"""

from typing import Protocol

from app.schemas.discovery import DiscoveredCompany, DiscoveredJob, DiscoveryQuery


class CompanySource(Protocol):
    """Company-first discovery. Not yet implemented by any adapter this phase -- YC/Wellfound/
    VC-portfolio adapters land in Phase 2b/4 once their ToS/scraping feasibility is checked
    per-source (see the Phase 1 plan's risk notes)."""

    name: str

    def search_companies(self, query: DiscoveryQuery) -> list[DiscoveredCompany]: ...
    def get_jobs(self, company: DiscoveredCompany) -> list[DiscoveredJob]: ...


class JobBoardSource(Protocol):
    """Posting-first discovery -- company info travels inline on each `DiscoveredJob`."""

    name: str

    def search_jobs(self, query: DiscoveryQuery) -> list[DiscoveredJob]: ...
