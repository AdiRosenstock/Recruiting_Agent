"""Unit tests for the scheduler's on/off wiring. `_run_discovery_for_all_profiles`'s actual
behavior is exercised indirectly (it composes `run_discovery_for_profile`, already covered in
test_discovery_endpoint.py); these confirm the scheduler is a true no-op when disabled and
starts a real background job when enabled -- no live network calls (nothing fires until the
first interval elapses, which these tests don't wait for)."""

from app.config import Settings
from app.services.scheduler import start_scheduler, stop_scheduler


def test_disabled_by_default_settings() -> None:
    assert Settings().enable_scheduler is False


def test_start_scheduler_returns_none_when_disabled() -> None:
    settings = Settings(enable_scheduler=False)
    scheduler = start_scheduler(settings)
    assert scheduler is None
    stop_scheduler(scheduler)  # must not raise on None


def test_start_scheduler_starts_a_real_job_when_enabled() -> None:
    settings = Settings(enable_scheduler=True, discovery_refresh_hours=6.0)
    scheduler = start_scheduler(settings)
    try:
        assert scheduler is not None
        assert scheduler.running
        job = scheduler.get_job("discovery_refresh")
        assert job is not None
        # First fire is one full interval away, not immediate -- starting the API shouldn't
        # itself trigger a burst of network calls.
        assert job.next_run_time is not None
    finally:
        stop_scheduler(scheduler)
