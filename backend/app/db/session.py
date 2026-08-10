"""Engine/session construction.

Sync SQLAlchemy is used throughout (not async) -- deliberate Phase 1 choice. At this scale
(single user, low request volume) async SQLAlchemy buys nothing but complexity; FastAPI runs
sync `def` endpoints in a threadpool automatically, so we lose no concurrency that matters here.
Revisit only if a real throughput need shows up.
"""

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def build_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


engine: Engine = build_engine(get_settings().database_url)
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
