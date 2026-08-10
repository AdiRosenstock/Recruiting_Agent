"""The `Application` row is what ties a job to a profile (jobs/companies themselves are
profile-agnostic -- see models/job.py). Discovery creates one per job it finds (status
DISCOVERED); scoring attaches its `fit_score_id`. Shared here since both the discovery and
scoring endpoints need to get-or-create the same row.
"""

import uuid

from sqlalchemy.orm import Session

from app.models.application import DEFAULT_STATUS, Application


def get_or_create_application(
    db: Session, *, candidate_id: uuid.UUID, job_id: uuid.UUID, profile_id: uuid.UUID
) -> Application:
    existing = (
        db.query(Application)
        .filter_by(candidate_id=candidate_id, job_id=job_id, profile_id=profile_id)
        .one_or_none()
    )
    if existing is not None:
        return existing
    application = Application(
        candidate_id=candidate_id, job_id=job_id, profile_id=profile_id, status=DEFAULT_STATUS
    )
    db.add(application)
    db.flush()
    return application
