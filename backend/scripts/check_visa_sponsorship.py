#!/usr/bin/env python
"""Run the deterministic visa-sponsorship check (services/visa_check.py) across every job under
a profile in one pass -- the dashboard's per-job "Check visa sponsorship" button does one job at
a time; this is for "check all 300 of them."

Some jobs have no description on file at all (a source can be light on structured/free-text
fields), so part of the work here can be a live fetch of the actual posting page, one at a time,
with a short delay between requests -- this is slow by design (network-bound, potentially
hundreds of individual sites), not something to run automatically in a hot path. Run it once
when you actually want the signal, not on every discovery run.

Usage (from backend/):
    .venv/bin/python scripts/check_visa_sponsorship.py --profile-id <uuid>
    # re-check jobs that already have a result too, not just never-checked ones:
    .venv/bin/python scripts/check_visa_sponsorship.py --profile-id <uuid> --recheck
"""

import argparse
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal  # noqa: E402
from app.models.application import Application  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.services.research.fetcher import PageFetcher  # noqa: E402
from app.services.visa_check import check_job_visa_sponsorship  # noqa: E402

# Politeness delay between live fetches -- these are hundreds of individual company career
# sites, not one API we control the load on.
_DELAY_BETWEEN_FETCHES_SECONDS = 0.5


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-id", required=True, type=str)
    parser.add_argument(
        "--recheck",
        action="store_true",
        help="Re-check jobs that already have a visa_sponsorship_checked_at too",
    )
    args = parser.parse_args()

    db = SessionLocal()
    fetcher = PageFetcher()
    try:
        query = (
            db.query(Job)
            .join(Application, Application.job_id == Job.id)
            .filter(Application.profile_id == uuid.UUID(args.profile_id))
        )
        if not args.recheck:
            query = query.filter(Job.visa_sponsorship_checked_at.is_(None))
        jobs = query.all()

        if not jobs:
            print("Nothing to check.")
            return 0

        counts = {"found": 0, "no_signal": 0, "fetch_failed": 0}
        for i, job in enumerate(jobs, start=1):
            needs_fetch = not job.description
            outcome = check_job_visa_sponsorship(job, fetcher=fetcher)
            counts[outcome] += 1
            db.commit()
            marker = f" -> {job.visa_sponsorship}" if outcome == "found" else ""
            print(f"[{i}/{len(jobs)}] {job.title[:60]!r}{marker}")
            if needs_fetch:
                time.sleep(_DELAY_BETWEEN_FETCHES_SECONDS)

        print(
            f"\nDone: {counts['found']} with a signal, {counts['no_signal']} no signal found, "
            f"{counts['fetch_failed']} fetch failures, out of {len(jobs)} checked."
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
