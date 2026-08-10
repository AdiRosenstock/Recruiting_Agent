# Recruiting Agent

A personal "startup recruiting CRM + research agent": upload a resume, get a structured,
evidence-backed candidate profile, then run **search profiles** -- named, independently
configured agents (discovery sources, fit-scoring weights, whether outreach is enabled) that
share one underlying pipeline (Discovery -> Score -> [Research -> Contact -> Outreach, if
enabled]). Two profiles exist out of the box:

- **`startup_outreach`** -- seed-Series B NYC startups, small teams, outreach enabled (drafted,
  human-approved, human-sent -- see [Roadmap](#roadmap), outreach generation isn't built yet).
- **`new_grad_2027`** -- a wide net across company sizes for new-grad 2027 roles (including
  finance/quant-adjacent ones), tracking-only, no outreach.

Nothing in this system automates LinkedIn (no scraping, no login automation, no auto-sending).
Outreach is always human-approved and human-sent; see the compliance note in the original spec.

## What's here

**Phase 1 -- candidate profile:**
- Resume upload (PDF) -> deterministic text extraction -> LLM-structured extraction ->
  deterministic evidence verification against the resume's own text -> normalized, persisted
  candidate profile.
- Every skill claim carries evidence snippets cross-checked against the resume; unverifiable
  claims are kept (not silently dropped) but flagged `verified: false` with downgraded
  confidence, so nothing invented by the LLM is presented as confirmed fact.
- An `LLMProvider` abstraction: real OpenAI/Anthropic implementations plus a deterministic,
  no-network `stub` so the whole pipeline runs without any API key.

**Phase 2 -- search profiles, discovery, fit scoring:**
- `search_profiles`: one row per agent (see above), holding its own `config` (role/stage/
  location filters, fit-score weight overrides) and `outreach_enabled` flag.
- Discovery adapters (`services/discovery/`), both real and network-verified against live data:
  `HNWhoIsHiringSource` (HN's public "who is hiring" thread, for `startup_outreach`) and
  `GitHubNewGradListSource` (a public new-grad tracker repo's README, for `new_grad_2027`). Both
  need no login/API key and are entirely deterministic (regex/HTML parsing, no LLM call).
  Company/job dedup goes through `CompanyJobUpsertService`.
- A deterministic, explainable `FitScorer` (`services/scoring/`) -- seven independently
  unit-testable components (technical/role/AI-data/experience/stage/location/domain match),
  weighted-summed into a 0-100 score with a tier and human-readable strengths/gaps. No LLM call.
  Never hard-rejects for a job asking slightly more experience than the candidate has; a missing
  personal connection is neutral, never scored as a weakness.
- A `SearchProvider` abstraction (`services/search/`), stubbed for now -- no search API key is
  wired up yet (that's Phase 3's Company Research Agent).

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

The API is now at `http://localhost:8000` (interactive docs at `/docs`).

### Getting from a resume to scored, discovered jobs

```bash
# 1. Create a candidate and upload a resume (Phase 1)
CAND_ID=$(curl -s -X POST http://localhost:8000/api/v1/candidates \
  -H "Content-Type: application/json" -d '{"full_name": "Your Name"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")

curl -s -X POST http://localhost:8000/api/v1/candidates/$CAND_ID/resume \
  -F "file=@/path/to/resume.pdf;type=application/pdf"

# 2. Seed the two search profiles for that candidate (idempotent, safe to re-run)
.venv/bin/python scripts/seed_profiles.py --candidate-id $CAND_ID

# 3. List the profiles to get their ids
curl -s "http://localhost:8000/api/v1/search-profiles?candidate_id=$CAND_ID"

# 4. Run discovery for a profile (hits the real HN/GitHub sources)
curl -s -X POST http://localhost:8000/api/v1/discovery/run \
  -H "Content-Type: application/json" -d '{"profile_id": "<profile-id>"}'

# 5. Score a discovered job
curl -s -X POST http://localhost:8000/api/v1/jobs/<job-id>/score \
  -H "Content-Type: application/json" \
  -d "{\"candidate_id\": \"$CAND_ID\", \"profile_id\": \"<profile-id>\"}"

# 6. See every job tracked under a profile, highest score first
curl -s "http://localhost:8000/api/v1/search-profiles/<profile-id>/jobs"
```

Companies/jobs can also be added manually: `POST /api/v1/companies`, then `POST
/api/v1/companies/{id}/jobs`.

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

`SEARCH_PROVIDER` has only one valid value (`stub`) as of Phase 2 -- no search API key is wired
up yet; that lands with Phase 3's Company Research Agent.

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

Unit tests for the discovery adapters mock HTTP (fixture shapes were confirmed against the real
HN Algolia API and the real GitHub tracker README during development, but tests never hit the
network) -- integration tests use a monkeypatched adapter registry for the same reason. Nothing
in the test suite makes a live network call.

The test suite creates/migrates a separate `recruiting_agent_test` database automatically (see
`tests/conftest.py`); it does not touch the dev database. If it doesn't exist yet:

```bash
docker compose exec db psql -U recruiting_agent -d recruiting_agent -c "CREATE DATABASE recruiting_agent_test;"
```

## Architecture notes

- **Sync SQLAlchemy, not async.** At single-user scale, async buys nothing but complexity;
  FastAPI runs sync routes in a threadpool automatically.
- **Evolving categorical fields** (skill/experience category, funding stage, work mode,
  application status) are plain `VARCHAR` validated at the Pydantic layer, not native Postgres
  `ENUM` types, so adding a new value later is a data change, not a schema migration.
- **Provenance is structural, not incidental.** Every extracted candidate row carries a
  `resume_id` + evidence snippet; every discovered company/job carries a `sources`/
  `company_sources` link recording where it came from.
- **Companies/jobs are profile-agnostic; `applications` and `fit_scores` are not.** The same job
  can be discovered and scored differently under two profiles (see `applications.profile_id`,
  `fit_scores.profile_id`) without duplicating the job row itself.
- **`applications` is the join between "a job" and "a profile that cares about it."** Discovery
  creates one per job found (status `DISCOVERED`); scoring attaches its `fit_score_id`. This is
  also why `GET /search-profiles/{id}/jobs` reads from `applications`, not `fit_scores` directly
  -- a discovered-but-unscored job still needs to show up, not silently disappear.
- **LLM calls always return validated Pydantic models**, never free text to parse ad hoc -- see
  `services/llm/base.py`. Discovery and scoring this phase are entirely LLM-free by design
  (regex/HTML parsing, weighted arithmetic) -- see the deterministic-vs-LLM table in the Phase 1
  plan.
- Full architecture, PostgreSQL schema (including tables for later phases), and both phases'
  plans were reviewed with the user before implementation.

## Roadmap

- **Phase 3:** Outreach Message Agent (multi-variant, buzzword-filtered, `startup_outreach`
  only), contact identification, Company Research Agent (FACT vs. INFERENCE, with sources),
  full CRM dashboard (Next.js -- approve/edit/copy/mark-contacted), personal-connection
  detection's LLM-written rationale layered on Phase 2's deterministic triggers.
- **Phase 4:** additional discovery adapters (YC, Wellfound, VC portfolios) behind
  `CompanySource`, once their ToS/scraping feasibility is checked per-source; a real
  `SearchProvider`; a simple scheduler (APScheduler) for periodic re-runs.
- **Phase 5:** hardening -- fuller agent-decision logging, prompt-version registry, configurable
  scoring weights UI, evaluation harness, deployment packaging.
