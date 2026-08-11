#!/usr/bin/env python
"""Score every unscored (or all, with --rescore) job under a search profile in one pass.

`POST /jobs/{id}/score` (one job at a time) is what the dashboard's per-row "Score" button
calls -- fine for scoring one job you just looked at, painfully slow for "I just ran discovery
and have 300 new postings to see fit scores for." This does the identical scoring logic
(FitScorer -> persist a fit_scores row -> link it onto the application) in one DB session
instead of one HTTP round-trip per job.

Usage (from backend/):
    .venv/bin/python scripts/batch_score.py --profile-id <uuid>
    # re-score jobs that already have a score too, not just unscored ones:
    .venv/bin/python scripts/batch_score.py --profile-id <uuid> --rescore
    # every profile for a candidate, not just one:
    .venv/bin/python scripts/batch_score.py --candidate-id <uuid>
"""

import argparse
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session  # noqa: E402

from app.core.logging import log_agent_decision  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.application import Application  # noqa: E402
from app.models.company import Company  # noqa: E402
from app.models.fit_score import FitScore  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.search_profile import SearchProfile  # noqa: E402
from app.schemas.company import CompanyRead  # noqa: E402
from app.schemas.job import JobRead  # noqa: E402
from app.schemas.search_profile import SearchProfileRead  # noqa: E402
from app.services.candidate_reader import get_candidate_profile  # noqa: E402
from app.services.scoring.scorer import FitScorer  # noqa: E402


def score_profile(db: Session, profile: SearchProfile, *, rescore: bool) -> tuple[int, int]:
    """Returns (scored_count, skipped_no_candidate_profile_count)."""
    candidate_profile = get_candidate_profile(db, profile.candidate_id)
    if candidate_profile is None:
        print(f"  {profile.display_name}: candidate {profile.candidate_id} not found, skipping")
        return 0, 0

    query = (
        db.query(Application, Job, Company)
        .join(Job, Application.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .filter(Application.profile_id == profile.id)
    )
    if not rescore:
        query = query.filter(Application.fit_score_id.is_(None))
    rows = query.all()

    scorer = FitScorer()
    profile_read = SearchProfileRead.model_validate(profile)
    scored = 0
    for application, job, company in rows:
        result = scorer.score(
            candidate=candidate_profile,
            job=JobRead.model_validate(job),
            company=CompanyRead.model_validate(company),
            profile=profile_read,
        )
        fit_score = FitScore(
            candidate_id=profile.candidate_id,
            job_id=job.id,
            profile_id=profile.id,
            technical_match=result.technical.score,
            role_match=result.role.score,
            ai_data_match=result.ai_data.score,
            experience_match=result.experience.score,
            stage_match=result.stage.score,
            location_match=result.location.score,
            domain_match=result.domain.score,
            overall_score=result.overall_score,
            tier=result.tier,
            strengths=result.strengths,
            gaps=result.gaps,
            weights_version=result.weights_version,
        )
        db.add(fit_score)
        db.flush()
        application.fit_score_id = fit_score.id
        scored += 1

    db.commit()
    if scored:
        log_agent_decision(
            "batch_scored",
            profile_id=str(profile.id),
            profile_key=profile.profile_key,
            jobs_scored=scored,
        )
    print(f"  {profile.display_name}: scored {scored} job(s)")
    return scored, 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-id", type=str, help="Score only this search profile")
    parser.add_argument("--candidate-id", type=str, help="Score every profile for this candidate")
    parser.add_argument(
        "--rescore",
        action="store_true",
        help="Re-score jobs that already have a fit score too (default: unscored only)",
    )
    args = parser.parse_args()

    if not args.profile_id and not args.candidate_id:
        parser.error("pass --profile-id or --candidate-id")

    db = SessionLocal()
    try:
        profiles: list[SearchProfile]
        if args.profile_id:
            single = db.get(SearchProfile, uuid.UUID(args.profile_id))
            if single is None:
                print(f"No search profile with id {args.profile_id}", file=sys.stderr)
                return 1
            profiles = [single]
        else:
            profiles = (
                db.query(SearchProfile).filter_by(candidate_id=uuid.UUID(args.candidate_id)).all()
            )
            if not profiles:
                print(f"No search profiles for candidate {args.candidate_id}", file=sys.stderr)
                return 1

        total = 0
        for profile in profiles:
            scored, _ = score_profile(db, profile, rescore=args.rescore)
            total += scored
        print(f"Total scored: {total}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
