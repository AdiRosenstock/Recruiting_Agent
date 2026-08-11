import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.company import Company
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactRead
from app.services.contacts import rank_contact_priority

router = APIRouter(prefix="/api/v1/companies", tags=["contacts"])


@router.post("/{company_id}/contacts", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
def create_contact(
    company_id: uuid.UUID, payload: ContactCreate, db: Session = Depends(get_db)
) -> ContactRead:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    priority_rank, rationale = rank_contact_priority(
        title=payload.title, company_employee_count=company.employee_count
    )
    contact = Contact(
        company_id=company_id,
        name=payload.name,
        title=payload.title,
        public_profile_url=payload.public_profile_url,
        email=payload.email,
        priority_rank=priority_rank,
        rationale=rationale,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return ContactRead.model_validate(contact)


@router.get("/{company_id}/contacts", response_model=list[ContactRead])
def list_contacts(company_id: uuid.UUID, db: Session = Depends(get_db)) -> list[ContactRead]:
    if db.get(Company, company_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    contacts = (
        db.query(Contact).filter_by(company_id=company_id).order_by(Contact.priority_rank).all()
    )
    return [ContactRead.model_validate(contact) for contact in contacts]
