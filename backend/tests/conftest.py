"""Shared test fixtures.

DB fixtures run migrations once per session against `DATABASE_URL_TEST`, then wrap each test in
a transaction that's rolled back afterward -- fast, isolated tests without recreating the schema
per test. Requires the Dockerized Postgres from `docker-compose.yml` to be running; see README.
"""

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session, SessionTransaction, sessionmaker

from app.config import get_settings
from app.db.session import build_engine

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def database_url_test() -> str:
    return get_settings().database_url_test


@pytest.fixture(scope="session", autouse=True)
def _apply_migrations(database_url_test: str) -> None:
    """Run `alembic upgrade head` against the test database once per test session."""
    env = {**os.environ, "DATABASE_URL": database_url_test}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.exit(
            "Failed to migrate the test database -- is Postgres running (`docker compose up -d "
            f"db`)? Details:\n{result.stdout}\n{result.stderr}"
        )


@pytest.fixture(scope="session")
def engine(database_url_test: str):  # type: ignore[no-untyped-def]
    return build_engine(database_url_test)


@pytest.fixture
def db_session(engine) -> Iterator[Session]:  # type: ignore[no-untyped-def]
    """A session bound to a single transaction that's rolled back after the test -- keeps tests
    isolated from each other without paying for schema recreation every time.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection, autoflush=False, expire_on_commit=False)
    session = session_factory()

    # Nested savepoint so `session.commit()` inside the code under test doesn't end the outer
    # rollback-able transaction.
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess: Session, trans: SessionTransaction) -> None:
        if trans.nested and (trans._parent is not None) and not trans._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    from app.db.session import get_db
    from app.main import app

    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def sample_resume_bytes() -> bytes:
    return (Path(__file__).parent / "fixtures" / "sample_resume.pdf").read_bytes()


@pytest.fixture(autouse=True)
def _isolated_resume_storage(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    """Point resume file storage at a per-test tmp dir instead of the real data/ directory."""
    monkeypatch.setenv("RESUME_STORAGE_DIR", str(tmp_path / "resumes"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
