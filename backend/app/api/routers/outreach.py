import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.outreach_message import OutreachMessage
from app.schemas.outreach_message import OutreachMessageRead, OutreachMessageUpdate

router = APIRouter(prefix="/api/v1/outreach-messages", tags=["outreach"])


@router.get("/{message_id}", response_model=OutreachMessageRead)
def read_outreach_message(message_id: uuid.UUID, db: Session = Depends(get_db)) -> OutreachMessageRead:
    message = db.get(OutreachMessage, message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return OutreachMessageRead.model_validate(message)


@router.patch("/{message_id}", response_model=OutreachMessageRead)
def edit_outreach_message(
    message_id: uuid.UUID, payload: OutreachMessageUpdate, db: Session = Depends(get_db)
) -> OutreachMessageRead:
    """The dashboard's "Edit message" action -- content is fully human-editable, and the row is
    flagged `is_user_edited` the moment it is (so we never confuse a human's final wording with
    what the LLM originally drafted)."""
    message = db.get(OutreachMessage, message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    message.content = payload.content
    message.is_user_edited = True
    db.commit()
    db.refresh(message)
    return OutreachMessageRead.model_validate(message)
