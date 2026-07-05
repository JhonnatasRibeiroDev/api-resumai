from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.documents.models import Document
from app.documents.service import get_user_document
from app.llm.client import LLMClient, LLMError
from app.llm.prompts import (
    build_individual_summary_prompt,
    build_integrated_summary_prompt,
    truncate_text,
)
from app.summaries.models import IntegratedSummary, Summary
from app.summaries.schemas import IntegratedSummaryCreate
from app.users.models import User


def _generate_or_502(llm_client: LLMClient, prompt: str) -> str:
    try:
        return llm_client.generate(prompt)
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


def summarize_document(
    db: Session,
    user: User,
    document_id: UUID,
    llm_client: LLMClient,
    settings: Settings,
) -> Summary:
    document = get_user_document(db, user, document_id)
    if document.summary:
        return document.summary

    text_to_summarize, source_truncated = truncate_text(
        document.extracted_text,
        settings.max_llm_chars,
    )
    prompt = build_individual_summary_prompt(text_to_summarize)
    content = _generate_or_502(llm_client, prompt)

    summary = Summary(
        user_id=user.id,
        document_id=document.id,
        content=content,
        model_name=settings.gemini_model,
        source_truncated=source_truncated,
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary


def get_document_summary(db: Session, user: User, document_id: UUID) -> Summary:
    summary = db.scalar(
        select(Summary).where(
            Summary.document_id == document_id,
            Summary.user_id == user.id,
        )
    )
    if summary is None:
        get_user_document(db, user, document_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resumo não encontrado para este documento.",
        )
    return summary


def create_integrated_summary(
    db: Session,
    user: User,
    payload: IntegratedSummaryCreate,
    llm_client: LLMClient,
    settings: Settings,
) -> IntegratedSummary:
    requested_ids = payload.document_ids
    if len(set(requested_ids)) != len(requested_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não repita documentos no resumo integrado.",
        )

    documents = list(
        db.scalars(
            select(Document).where(
                Document.user_id == user.id,
                Document.id.in_(requested_ids),
            )
        )
    )
    if len(documents) != len(requested_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Um ou mais documentos não foram encontrados.",
        )

    documents_by_id = {document.id: document for document in documents}
    ordered_documents = [documents_by_id[document_id] for document_id in requested_ids]

    content_parts = []
    for index, document in enumerate(ordered_documents, start=1):
        if not document.extracted_text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"O documento {document.filename} não possui texto extraído.",
            )
        content_parts.append(
            f"Documento {index}: {document.filename}\n\n{document.extracted_text}"
        )

    combined_content = "\n\n---\n\n".join(content_parts)
    text_to_summarize, source_truncated = truncate_text(
        combined_content,
        settings.max_llm_chars,
    )
    prompt = build_integrated_summary_prompt(text_to_summarize)
    content = _generate_or_502(llm_client, prompt)

    integrated_summary = IntegratedSummary(
        user_id=user.id,
        title=payload.title,
        document_ids=[str(document_id) for document_id in requested_ids],
        content=content,
        model_name=settings.gemini_model,
        source_truncated=source_truncated,
    )
    db.add(integrated_summary)
    db.commit()
    db.refresh(integrated_summary)
    return integrated_summary


def list_integrated_summaries(db: Session, user: User) -> list[IntegratedSummary]:
    return list(
        db.scalars(
            select(IntegratedSummary)
            .where(IntegratedSummary.user_id == user.id)
            .order_by(IntegratedSummary.created_at.desc())
        )
    )


def get_integrated_summary(
    db: Session,
    user: User,
    summary_id: UUID,
) -> IntegratedSummary:
    summary = db.scalar(
        select(IntegratedSummary).where(
            IntegratedSummary.id == summary_id,
            IntegratedSummary.user_id == user.id,
        )
    )
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resumo integrado não encontrado.",
        )
    return summary
