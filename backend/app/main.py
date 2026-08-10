from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import candidates, health
from app.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="Recruiting Agent API",
        description="Personal startup recruiting CRM + research agent -- backend API.",
        version="0.1.0",
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

    return app


app = create_app()
