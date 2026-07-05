from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.llm.client import LLMClient, get_llm_client
from app.summaries.schemas import (
    IntegratedSummaryCreate,
    IntegratedSummaryRead,
    SummaryRead,
)
from app.summaries.service import (
    create_integrated_summary,
    get_document_summary,
    get_integrated_summary,
    list_integrated_summaries,
    summarize_document,
)
from app.users.models import User


router = APIRouter(tags=["summaries"])


@router.post(
    "/documents/{document_id}/summarize",
    response_model=SummaryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_document_summary(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    llm_client: LLMClient = Depends(get_llm_client),
    settings: Settings = Depends(get_settings),
) -> SummaryRead:
    return summarize_document(db, current_user, document_id, llm_client, settings)


@router.get("/documents/{document_id}/summary", response_model=SummaryRead)
def read_document_summary(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SummaryRead:
    return get_document_summary(db, current_user, document_id)


@router.post(
    "/summaries/integrated",
    response_model=IntegratedSummaryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_integrated(
    payload: IntegratedSummaryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    llm_client: LLMClient = Depends(get_llm_client),
    settings: Settings = Depends(get_settings),
) -> IntegratedSummaryRead:
    return create_integrated_summary(db, current_user, payload, llm_client, settings)


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
