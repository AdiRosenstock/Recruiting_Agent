import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_outreach_agent
from app.db.session import get_db
from app.models.application import Application
from app.models.company import Company
from app.models.contact import Contact
from app.models.job import Job
from app.models.search_profile import SearchProfile
from app.schemas.application import ApplicationRead, ApplicationUpdate
from app.schemas.outreach_message import OutreachGenerationResult, OutreachMessageRead
from app.services.candidate_reader import get_candidate_profile
from app.services.outreach.agent import OutreachMessageAgent

router = APIRouter(prefix="/api/v1/applications", tags=["applications"])

# Statuses that imply the candidate has actually been contacted / responded -- used to backfill
# contacted_at/responded_at automatically the first time a status transition reaches them, so
# the dashboard doesn't need a second "when did this happen" prompt.
_CONTACTED_STATUSES = {"CONTACTED", "RESPONDED", "INTERVIEW"}
_RESPONDED_STATUSES = {"RESPONDED", "INTERVIEW"}


@router.get("/{application_id}", response_model=ApplicationRead)
def read_application(application_id: uuid.UUID, db: Session = Depends(get_db)) -> ApplicationRead:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return ApplicationRead.model_validate(application)


@router.patch("/{application_id}", response_model=ApplicationRead)
def update_application(
    application_id: uuid.UUID, payload: ApplicationUpdate, db: Session = Depends(get_db)
) -> ApplicationRead:
    """Every human-approval-workflow action (approve, skip, mark contacted, add notes) goes
    through this one endpoint -- nothing here is ever set automatically by an agent."""
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    if payload.contact_id is not None:
        if db.get(Contact, payload.contact_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
        application.contact_id = payload.contact_id

    if payload.status is not None:
        application.status = payload.status
        now = datetime.now(UTC)
        if payload.status in _CONTACTED_STATUSES and application.contacted_at is None:
            application.contacted_at = now
        if payload.status in _RESPONDED_STATUSES and application.responded_at is None:
            application.responded_at = now

    if payload.notes is not None:
        application.notes = payload.notes

    db.commit()
    db.refresh(application)
    return ApplicationRead.model_validate(application)


@router.post("/{application_id}/outreach", response_model=OutreachGenerationResult)
def generate_outreach(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    agent: OutreachMessageAgent = Depends(get_outreach_agent),
) -> OutreachGenerationResult:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    profile = db.get(SearchProfile, application.profile_id)
    if profile is not None and not profile.outreach_enabled:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Outreach is not enabled for profile '{profile.profile_key}'.",
        )

    job = db.get(Job, application.job_id)
    if job is None:  # pragma: no cover -- FK guarantees this in practice
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    company = db.get(Company, job.company_id)
    if company is None:  # pragma: no cover -- FK guarantees this in practice
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    candidate_profile = get_candidate_profile(db, application.candidate_id)
    if candidate_profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    contact = db.get(Contact, application.contact_id) if application.contact_id else None

    messages, warnings = agent.generate(
        db=db, candidate=candidate_profile, job=job, company=company, contact=contact
    )
    by_type = {message.message_type: message for message in messages}

    application.outreach_message_id = by_type["linkedin_full"].id
    if application.status == "DISCOVERED":
        application.status = "REVIEW"  # drafted content is ready for human review

    db.commit()
    for message in messages:
        db.refresh(message)

    return OutreachGenerationResult(
        linkedin_full=OutreachMessageRead.model_validate(by_type["linkedin_full"]),
        linkedin_connection=OutreachMessageRead.model_validate(by_type["linkedin_connection"]),
        email=OutreachMessageRead.model_validate(by_type["email"]),
        warnings=warnings,
    )
