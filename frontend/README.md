# Recruiting Agent -- Dashboard

Next.js 16 (App Router) + TypeScript + React 19. A client-rendered dashboard talking directly to
the FastAPI backend over plain `fetch` (see `lib/api.ts`) -- no server-side data layer, no
Server Actions, no data-fetching library. Everything here is inherently dynamic and
single-user, and the backend already exists as its own service, so there was nothing for
Next.js's server-rendering/caching machinery to add; keeping it to plain client components and
`fetch` is the simpler, more honest architecture for what this actually is.

See the [root README](../README.md) for what the whole system does. This covers the frontend
specifically.

## Setup

```bash
npm install
cp .env.example .env.local   # only needed if the backend isn't at http://localhost:8000
npm run dev
```

Requires the backend running (`cd ../backend && .venv/bin/uvicorn app.main:app --reload`) --
CORS is already configured for `http://localhost:3000` on the backend side.

## What's here

- **Onboarding** (`components/CandidateOnboarding.tsx`): create a candidate, optionally attach a
  resume PDF, right from the browser instead of curl.
- **Profile setup** (`components/ProfileSetup.tsx`): one-click creation of the default
  `startup_outreach` search profile (mirrors `backend/scripts/seed_profiles.py` exactly), so a
  fresh candidate doesn't need the Python script at all.
- **Dashboard** (`app/page.tsx` + `components/JobsTable.tsx`): profile tabs, a "Run discovery"
  button, and a table of every job tracked under the active profile -- sortable on any column
  (fit score, stage, location, visa status, ...), plus client-side location/visa filters.
- **All Applications** (`components/ApplicationsTable.tsx`): a cross-profile tab alongside the
  per-profile ones -- every application regardless of which profile found it, with a free-text
  search (job title/company, server-side via `GET /api/v1/applications`'s `q`/`status` params)
  plus client-side location/visa filters and click-to-sort columns, same as the per-profile table.
- **Job detail panel** (`components/JobDetailPanel.tsx`): fit-score breakdown (strengths/gaps),
  company info, visa sponsorship (a deterministic signal -- check/re-check it for one job),
  research (run it, see FACTS vs. INFERENCES separated), contacts (add one, ranked by the
  backend's priority logic), outreach (generate all three variants, edit inline, copy to
  clipboard), and the status workflow dropdown -- this is where every "human approval" action
  from the spec actually happens.

The candidate id is kept in `localStorage` (this is a single-user personal tool, not a
multi-tenant app -- there's no login).

## Tests / checks

```bash
npm run typecheck
npm run lint
npm run build
```

### End-to-end smoke test

`e2e/smoke.mjs` drives the real dashboard against a real running backend with headless Chromium
(Playwright) -- onboarding, profile setup, discovery (hits the real HN/YC sources), opening a
job, running research, generating and editing outreach, changing status. Screenshots land in
`e2e/screenshots/` (gitignored); exits non-zero if the browser logged any console error.

```bash
npx playwright install chromium   # once
# backend running on :8000, frontend dev server running on :3000
npm run test:e2e
```

This is a manual/pre-release check (real network calls, real backend state), not part of
`npm run lint`/CI.

---

Built by Adi Rosenstock -- see the [root README](../README.md#about-the-author) for what the
whole system does and how to reach me.
