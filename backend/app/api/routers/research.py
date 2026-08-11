import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_research_agent
from app.db.session import get_db
from app.models.company import Company
from app.models.company_research import CompanyResearch
from app.schemas.company_research import CompanyResearchRead, CompanyResearchRunResult
from app.services.research.agent import CompanyNotFoundError, CompanyResearchAgent

router = APIRouter(prefix="/api/v1/companies", tags=["research"])


@router.post("/{company_id}/research/run", response_model=CompanyResearchRunResult)
def run_research(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    agent: CompanyResearchAgent = Depends(get_research_agent),
) -> CompanyResearchRunResult:
    try:
        result = agent.research(db=db, company_id=company_id)
    except CompanyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    db.commit()
    return result


@router.get("/{company_id}/research", response_model=list[CompanyResearchRead])
def list_research(company_id: uuid.UUID, db: Session = Depends(get_db)) -> list[CompanyResearchRead]:
    if db.get(Company, company_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    rows = (
        db.query(CompanyResearch)
        .filter_by(company_id=company_id)
        .order_by(CompanyResearch.is_inference, CompanyResearch.created_at.desc())
        .all()
    )
    return [CompanyResearchRead.model_validate(row) for row in rows]
