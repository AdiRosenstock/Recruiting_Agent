"""Normalized shapes discovery adapters produce, before upsert into `companies`/`jobs`."""

import uuid
from datetime import date

from pydantic import BaseModel, Field


class DiscoveredCompany(BaseModel):
    name: str
    website: str | None = None
    location: str | None = None
    industry: str | None = None
    description: str | None = None
    funding_stage: str | None = None
    source_url: str
    source_type: str


class DiscoveredJob(BaseModel):
    title: str
    job_url: str
    location: str | None = None
    description: str | None = None
    work_mode: str | None = None
    posted_date: date | None = None
    deadline_date: date | None = None
    company: DiscoveredCompany
    source_url: str
    source_type: str


class DiscoveryQuery(BaseModel):
    """The slice of a profile's config passed to adapters so they can self-filter."""

    role_filters: list[str] = Field(default_factory=list)
    stage_filters: list[str] = Field(default_factory=list)
    location_filters: list[str] = Field(default_factory=list)


class DiscoveryRunResult(BaseModel):
    profile_id: uuid.UUID
    sources_run: list[str]
    companies_upserted: int
    jobs_upserted: int
    jobs_scored: int
    warnings: list[str] = Field(default_factory=list)
