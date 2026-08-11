"""CompanySource for `startup_outreach`: Y Combinator's public company directory, published as
a static JSON dataset (no login, no API key, no scraping YC's own site at request time -- see
https://github.com/yc-oss/api, a community-maintained mirror of YC's public directory served via
GitHub Pages). This is the first real `CompanySource` adapter (company-first discovery); the
existing HN/GitHub adapters are `JobBoardSource` (posting-first).

Important, deliberate limitation: this dataset has no per-company job postings, only an
`isHiring` flag. `get_jobs()` therefore always returns `[]` -- we will not fabricate a job URL
that doesn't exist. The value here is company discovery (richer, more accurate data -- real
batch/stage/description -- than what HN postings self-report), not job discovery; a discovered
company still needs either a Company Research Agent run or a manually-added job to go further.
"""

import httpx

from app.schemas.discovery import DiscoveredCompany, DiscoveredJob, DiscoveryQuery

_DEFAULT_DATASET_URL = "https://yc-oss.github.io/api/companies/all.json"
_MAX_RESULTS = 100

# YC's own stage taxonomy is just "Early"/"Growth" -- much coarser than our seed/series_a/... .
# This is a documented approximation, not a precise mapping: any of our early-stage filter
# values match YC's "Early"; anything else (growth, series_c_plus) also allows "Growth".
_EARLY_STAGE_FILTER_VALUES = {"pre_seed", "seed", "series_a", "series_b", "early"}


class YCDirectorySource:
    name = "yc_directory"

    def __init__(
        self, client: httpx.Client | None = None, dataset_url: str = _DEFAULT_DATASET_URL
    ) -> None:
        self._client = client or httpx.Client(timeout=20.0)
        self._dataset_url = dataset_url

    def search_companies(self, query: DiscoveryQuery) -> list[DiscoveredCompany]:
        response = self._client.get(self._dataset_url)
        response.raise_for_status()
        companies = response.json()

        results: list[DiscoveredCompany] = []
        for entry in companies:
            if not entry.get("isHiring") or entry.get("status") != "Active":
                continue
            if not self._matches_location(entry, query):
                continue
            if not self._matches_stage(entry, query):
                continue
            results.append(self._to_discovered_company(entry))
            if len(results) >= _MAX_RESULTS:
                break
        return results

    def get_jobs(self, company: DiscoveredCompany) -> list[DiscoveredJob]:
        # Deliberately empty -- see module docstring. Never invent a job URL that doesn't exist.
        return []

    def _to_discovered_company(self, entry: dict) -> DiscoveredCompany:
        yc_stage = entry.get("stage")
        stage = "seed" if yc_stage == "Early" else "growth" if yc_stage == "Growth" else None
        description = entry.get("long_description") or entry.get("one_liner")
        return DiscoveredCompany(
            name=entry["name"],
            website=entry.get("website"),
            location=entry.get("all_locations"),
            industry=entry.get("industry"),
            description=description,
            funding_stage=stage,
            source_url=entry.get("url") or self._dataset_url,
            source_type=self.name,
        )

    @staticmethod
    def _matches_location(entry: dict, query: DiscoveryQuery) -> bool:
        if not query.location_filters:
            return True
        locations = (entry.get("all_locations") or "").lower()
        return any(loc.lower() in locations for loc in query.location_filters)

    @staticmethod
    def _matches_stage(entry: dict, query: DiscoveryQuery) -> bool:
        if not query.stage_filters:
            return True
        wants_early = any(s.lower() in _EARLY_STAGE_FILTER_VALUES for s in query.stage_filters)
        stage = entry.get("stage")
        if wants_early:
            return stage in ("Early", "Growth")  # Growth still allowed as a loose upper bound
        return True
