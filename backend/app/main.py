from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import (
    applications,
    candidates,
    companies,
    contacts,
    discovery,
    health,
    jobs,
    outreach,
    research,
    search_profiles,
)
from app.config import get_settings
from app.core.logging import configure_logging
from app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    scheduler = start_scheduler(get_settings())
    try:
        yield
    finally:
        stop_scheduler(scheduler)


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="Recruiting Agent API",
        description="Personal startup recruiting CRM + research agent -- backend API.",
        version="0.1.0",
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(candidates.router)
    app.include_router(search_profiles.router)
    app.include_router(companies.router)
    app.include_router(jobs.router)
    app.include_router(discovery.router)
    app.include_router(research.router)
    app.include_router(contacts.router)
    app.include_router(outreach.router)
    app.include_router(applications.router)

    return app


app = create_app()
