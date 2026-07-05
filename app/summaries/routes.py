from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.summaries.schemas import (
    IntegratedSummaryCreate,
    IntegratedSummaryRead,
    SummaryJobRead,
    SummaryRead,
)
from app.summaries.service import (
    create_document_summary_job,
    create_integrated_summary_job,
    get_document_summary,
    get_integrated_summary,
    get_summary_job,
    list_integrated_summaries,
    retry_summary_job,
)
from app.users.models import User


router = APIRouter(tags=["summaries"])


@router.post(
    "/documents/{document_id}/summarize",
    response_model=SummaryJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_document_summary(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> SummaryJobRead:
    return create_document_summary_job(db, current_user, document_id, settings)


@router.get("/documents/{document_id}/summary", response_model=SummaryRead)
def read_document_summary(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SummaryRead:
    return get_document_summary(db, current_user, document_id)


@router.post(
    "/summaries/integrated",
    response_model=SummaryJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_integrated(
    payload: IntegratedSummaryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> SummaryJobRead:
    return create_integrated_summary_job(db, current_user, payload, settings)


@router.get("/summary-jobs/{job_id}", response_model=SummaryJobRead)
def read_summary_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SummaryJobRead:
    return get_summary_job(db, current_user, job_id)


@router.post("/summary-jobs/{job_id}/retry", response_model=SummaryJobRead)
def retry_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> SummaryJobRead:
    return retry_summary_job(db, current_user, job_id, settings)


@router.get("/summaries/integrated", response_model=list[IntegratedSummaryRead])
def list_integrated(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[IntegratedSummaryRead]:
    return list_integrated_summaries(db, current_user)


@router.get("/summaries/integrated/{summary_id}", response_model=IntegratedSummaryRead)
def read_integrated(
    summary_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IntegratedSummaryRead:
    return get_integrated_summary(db, current_user, summary_id)
