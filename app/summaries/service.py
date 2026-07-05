from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.documents.models import Document
from app.documents.service import get_user_document
from app.summaries.constants import (
    ACTIVE_JOB_STATUSES,
    JOB_KIND_INDIVIDUAL,
    JOB_KIND_INTEGRATED,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_PENDING,
)
from app.summaries.models import IntegratedSummary, Summary, SummaryJob
from app.summaries.schemas import IntegratedSummaryCreate
from app.users.models import User


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


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


def _active_user_job_count(db: Session, user: User) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(SummaryJob)
            .where(
                SummaryJob.user_id == user.id,
                SummaryJob.status.in_(ACTIVE_JOB_STATUSES),
            )
        )
        or 0
    )


def _ensure_user_can_create_job(db: Session, user: User, settings: Settings) -> None:
    if _active_user_job_count(db, user) >= settings.user_max_active_summary_jobs:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limite de resumos em processamento atingido. Aguarde um job finalizar.",
        )


def _enqueue_job(job: SummaryJob, settings: Settings) -> None:
    if not settings.enqueue_summary_jobs:
        return
    try:
        from app.worker.tasks import process_summary_job_task

        process_summary_job_task.delay(str(job.id))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível enviar o job para a fila RabbitMQ.",
        ) from exc


def _completed_individual_job_for_summary(
    db: Session,
    user: User,
    document: Document,
    summary: Summary,
) -> SummaryJob:
    existing_job = db.scalar(
        select(SummaryJob)
        .where(
            SummaryJob.user_id == user.id,
            SummaryJob.kind == JOB_KIND_INDIVIDUAL,
            SummaryJob.document_id == document.id,
            SummaryJob.status == JOB_STATUS_COMPLETED,
        )
        .order_by(SummaryJob.created_at.desc())
    )
    if existing_job:
        return existing_job

    job = SummaryJob(
        user_id=user.id,
        kind=JOB_KIND_INDIVIDUAL,
        status=JOB_STATUS_COMPLETED,
        document_id=document.id,
        summary_id=summary.id,
        attempt_count=1,
        started_at=summary.created_at,
        finished_at=summary.created_at,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def create_document_summary_job(
    db: Session,
    user: User,
    document_id: UUID,
    settings: Settings,
) -> SummaryJob:
    document = get_user_document(db, user, document_id)
    if document.summary:
        return _completed_individual_job_for_summary(db, user, document, document.summary)

    active_job = db.scalar(
        select(SummaryJob)
        .where(
            SummaryJob.user_id == user.id,
            SummaryJob.kind == JOB_KIND_INDIVIDUAL,
            SummaryJob.document_id == document.id,
            SummaryJob.status.in_(ACTIVE_JOB_STATUSES),
        )
        .order_by(SummaryJob.created_at.desc())
    )
    if active_job:
        return active_job

    _ensure_user_can_create_job(db, user, settings)

    job = SummaryJob(
        user_id=user.id,
        kind=JOB_KIND_INDIVIDUAL,
        status=JOB_STATUS_PENDING,
        document_id=document.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    _enqueue_job(job, settings)
    return job


def create_integrated_summary_job(
    db: Session,
    user: User,
    payload: IntegratedSummaryCreate,
    settings: Settings,
) -> SummaryJob:
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

    requested_key = [str(document_id) for document_id in requested_ids]
    active_jobs = list(
        db.scalars(
            select(SummaryJob).where(
                SummaryJob.user_id == user.id,
                SummaryJob.kind == JOB_KIND_INTEGRATED,
                SummaryJob.status.in_(ACTIVE_JOB_STATUSES),
            )
        )
    )
    for job in active_jobs:
        if job.document_ids == requested_key and job.title == payload.title:
            return job

    _ensure_user_can_create_job(db, user, settings)

    job = SummaryJob(
        user_id=user.id,
        kind=JOB_KIND_INTEGRATED,
        status=JOB_STATUS_PENDING,
        document_ids=requested_key,
        title=payload.title,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    _enqueue_job(job, settings)
    return job


def get_summary_job(db: Session, user: User, job_id: UUID) -> SummaryJob:
    job = db.scalar(
        select(SummaryJob).where(
            SummaryJob.id == job_id,
            SummaryJob.user_id == user.id,
        )
    )
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job de resumo não encontrado.",
        )
    return job


def retry_summary_job(
    db: Session,
    user: User,
    job_id: UUID,
    settings: Settings,
) -> SummaryJob:
    job = get_summary_job(db, user, job_id)
    if job.status != JOB_STATUS_FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas jobs com falha podem ser tentados novamente.",
        )
    if job.attempt_count >= settings.summary_max_attempts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limite de tentativas atingido para este job.",
        )
    _ensure_user_can_create_job(db, user, settings)

    job.status = JOB_STATUS_PENDING
    job.error_message = None
    job.started_at = None
    job.finished_at = None
    db.add(job)
    db.commit()
    db.refresh(job)
    _enqueue_job(job, settings)
    return job


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
