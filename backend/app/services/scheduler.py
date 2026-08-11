"""Optional periodic discovery refresh -- off by default (`ENABLE_SCHEDULER=false`) so the app
never makes background network calls (to HN/YC/GitHub) without being explicitly asked to. When
enabled, re-runs `run_discovery_for_profile` (the same logic `POST /discovery/run` uses) for
every existing search profile on a fixed interval, via an in-process APScheduler
`BackgroundScheduler` -- not a separate worker/queue, per "avoid premature microservices" /
"don't add unnecessary distributed infrastructure for the MVP."
"""

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import Settings
from app.core.logging import get_logger, log_agent_decision
from app.db.session import SessionLocal
from app.models.search_profile import SearchProfile
from app.schemas.search_profile import SearchProfileRead
from app.services.discovery.runner import run_discovery_for_profile

logger = get_logger(__name__)

_JOB_ID = "discovery_refresh"


def _run_discovery_for_all_profiles() -> None:
    db = SessionLocal()
    try:
        profile_rows = db.query(SearchProfile).all()
        for profile_row in profile_rows:
            profile = SearchProfileRead.model_validate(profile_row)
            try:
                counters = run_discovery_for_profile(db, profile)
                db.commit()
            except Exception:
                db.rollback()
                logger.exception(
                    "Scheduled discovery run failed for profile %s (%s)",
                    profile.id,
                    profile.profile_key,
                )
                continue
            log_agent_decision(
                "scheduled_discovery_run",
                profile_id=str(profile.id),
                profile_key=profile.profile_key,
                sources_run=counters.sources_run,
                companies_upserted=counters.companies_created,
                jobs_upserted=counters.jobs_created,
                jobs_scored=counters.jobs_scored,
                warning_count=len(counters.warnings),
            )
    finally:
        db.close()


def start_scheduler(settings: Settings) -> BackgroundScheduler | None:
    if not settings.enable_scheduler:
        logger.info("Scheduler disabled (set ENABLE_SCHEDULER=true to turn it on)")
        return None

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _run_discovery_for_all_profiles,
        trigger="interval",
        hours=settings.discovery_refresh_hours,
        id=_JOB_ID,
        # IntervalTrigger's default start_date is "now", so the first fire is naturally one
        # full interval from now, not immediate -- starting the API doesn't itself trigger a
        # burst of network calls.
    )
    scheduler.start()
    logger.info(
        "Scheduler started: discovery refresh every %s hour(s)", settings.discovery_refresh_hours
    )
    return scheduler


def stop_scheduler(scheduler: BackgroundScheduler | None) -> None:
    if scheduler is not None:
        scheduler.shutdown(wait=False)
