# Runtime image only -- this project's dev workflow (pytest/ruff/mypy) runs against the local
# .venv (see ../README.md), not in Docker. This Dockerfile exists for actually running the app
# (and its Postgres dependency) as a deployable stack; see ../docker-compose.yml.

FROM python:3.12-slim AS base
WORKDIR /app

# libpq is needed at runtime by psycopg[binary]'s C extension on slim images.
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts ./scripts

# Editable-less install: this image only ever runs the built package, nothing edits it in
# place. No [dev] extras (pytest/ruff/mypy) -- keeps the runtime image smaller.
RUN pip install --no-cache-dir .

RUN useradd --system --create-home appuser \
    && mkdir -p /app/data/resumes \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Migrations run on every container start -- idempotent (Alembic no-ops if already at head), and
# this is a single-instance personal tool, not a fleet where concurrent migration races matter.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
