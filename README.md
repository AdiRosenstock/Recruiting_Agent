# Recruiting Agent

A personal "startup recruiting CRM + research agent": upload a resume, get a structured,
evidence-backed candidate profile. This is **Phase 1** of a larger pipeline (see
[Roadmap](#roadmap) below) -- startup/job discovery, fit scoring, company research, contact
identification, and outreach-message generation are not built yet.

Nothing in this system automates LinkedIn (no scraping, no login automation, no auto-sending).
Outreach is always human-approved and human-sent; see the compliance note in the original spec.

## What's here (Phase 1)

- FastAPI backend (`backend/`) with a Postgres-backed candidate domain.
- Resume upload (PDF) -> deterministic text extraction -> LLM-structured extraction ->
  deterministic evidence verification against the resume's own text -> normalized, persisted
  candidate profile.
- Every skill claim carries evidence snippets that are cross-checked against the resume; claims
  that can't be verified are kept (not silently dropped) but flagged `verified: false` with a
  downgraded confidence, so nothing invented by the LLM is presented as confirmed fact.
- An `LLMProvider` abstraction with real OpenAI and Anthropic implementations plus a
  deterministic, no-network `stub` implementation so the whole pipeline runs without any API key.

## Prerequisites

- Python 3.12+ (3.11+ also works)
- Docker + Docker Compose, for Postgres. If you don't already have Docker Desktop, the
  lightweight option on macOS is [colima](https://github.com/abiquo/colima):
  ```
  brew install colima docker docker-compose
  colima start
  ```

## Local setup

```bash
# 1. Clone / open this repo, then from the repo root:
cp .env.example .env

# 2. Start Postgres (runs on port 5433, not 5432, to avoid clashing with any Postgres you
#    already run locally -- see "Why port 5433?" below)
docker compose up -d db

# 3. Backend setup
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# 4. Run migrations
.venv/bin/alembic upgrade head

# 5. Run the API
.venv/bin/uvicorn app.main:app --reload
```

The API is now at `http://localhost:8000` (interactive docs at `/docs`). Try it:

```bash
# Create a candidate
curl -s -X POST http://localhost:8000/api/v1/candidates \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Your Name"}'

# Upload a resume (replace the id and path)
curl -s -X POST http://localhost:8000/api/v1/candidates/<id>/resume \
  -F "file=@/path/to/resume.pdf;type=application/pdf"

# Fetch the structured profile
curl -s http://localhost:8000/api/v1/candidates/<id>
```

### LLM provider configuration

By default `.env` sets `LLM_PROVIDER=stub` -- a deterministic, keyword/regex-based extractor
that needs no API key. It reliably finds contact info and a small fixed list of skill keywords,
but does **not** reconstruct education/experience/project entries (this is called out explicitly
in its output's `gaps` field). It exists so the pipeline is runnable and testable without a key,
not as a substitute for real extraction quality.

For real extraction, set in `.env`:

```
LLM_PROVIDER=openai        # or: anthropic
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...
```

### Why port 5433?

This machine had a native (Homebrew) Postgres already running on the default 5432 -- something
this project didn't set up. Rather than touch or stop a service we don't own, `docker-compose.yml`
maps the project's Postgres to `5433` on the host instead. Change `POSTGRES_PORT` in `.env` (and
the matching `DATABASE_URL*` host:port) if 5433 is also taken on your machine.

## Tests, lint, types

```bash
cd backend
docker compose -f ../docker-compose.yml up -d db   # if not already running
.venv/bin/pytest                 # unit tests need nothing external; integration tests need Postgres
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy app
```

The test suite creates/migrates a separate `recruiting_agent_test` database automatically (see
`tests/conftest.py`); it does not touch the dev database. If it doesn't exist yet:

```bash
docker compose exec db psql -U recruiting_agent -d recruiting_agent -c "CREATE DATABASE recruiting_agent_test;"
```

## Architecture notes

- **Sync SQLAlchemy, not async.** At single-user scale, async buys nothing but complexity;
  FastAPI runs sync routes in a threadpool automatically.
- **Evolving categorical fields** (skill category, experience category, and -- in later phases --
  funding stage, work mode, application status) are plain `VARCHAR` validated at the Pydantic
  layer, not native Postgres `ENUM` types, so adding a new value later is a data change, not a
  schema migration.
- **Provenance is structural, not incidental.** Every extracted row (`candidate_education`,
  `candidate_experiences`, `candidate_projects`, `candidate_skills`) carries a `resume_id` FK and
  an `evidence_snippet`/`evidence` field. Skill claims additionally get a normalized-substring +
  fuzzy-match check against the resume's raw text (`services/resume_parsing/evidence_validator.py`),
  and unverified claims are downgraded, never invented-away or silently hidden.
- **LLM calls always return validated Pydantic models**, never free text to parse ad hoc --
  see `services/llm/base.py`.
- Full architecture, PostgreSQL schema (including tables for later phases), and the phased plan
  live in this repo's commit history / were reviewed with the user before implementation.

## Roadmap

- **Phase 2:** manual company/job entry, Company Research Agent (FACT vs. INFERENCE, with
  sources), deterministic Fit Scoring engine, a minimal Next.js dashboard.
- **Phase 3:** Outreach Message Agent (multi-variant, buzzword-filtered), contact identification,
  full CRM dashboard (approve/edit/copy/mark-contacted), personal-connection detection.
- **Phase 4:** automated startup/job discovery adapters (YC, Wellfound, VC portfolios, web
  search) behind a `StartupSource` interface, with dedup and a simple scheduler.
- **Phase 5:** hardening -- fuller agent-decision logging, prompt-version registry, configurable
  scoring weights UI, evaluation harness, deployment packaging.
