from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.documents.models import Document
from app.llm.client import LLMClient
from app.llm.prompts import (
    build_individual_chunk_prompt,
    build_individual_final_prompt,
    build_integrated_chunk_prompt,
    build_integrated_final_prompt,
    split_text_into_chunks,
)
from app.summaries.constants import (
    JOB_KIND_INDIVIDUAL,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_PROCESSING,
)
from app.summaries.models import IntegratedSummary, Summary, SummaryJob


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _summarize_chunks(
    text: str,
    settings: Settings,
    llm_client: LLMClient,
    chunk_prompt_builder,
    final_prompt_builder,
) -> tuple[str, bool]:
    chunks, truncated = split_text_into_chunks(
        text,
        settings.summary_chunk_chars,
        settings.summary_chunk_overlap_chars,
        settings.summary_max_chunks,
    )
    if not chunks:
        raise ValueError("Texto vazio para resumo.")

    if len(chunks) == 1 and not truncated:
        partial_summaries = llm_client.generate(chunk_prompt_builder(chunks[0], 1, 1))
        return llm_client.generate(final_prompt_builder(partial_summaries)), False

    partials = []
    for index, chunk in enumerate(chunks, start=1):
        prompt = chunk_prompt_builder(chunk, index, len(chunks))
        partials.append(f"Parte {index}:\n{llm_client.generate(prompt)}")

    final_prompt = final_prompt_builder("\n\n---\n\n".join(partials))
    return llm_client.generate(final_prompt), truncated


def _process_individual_job(
    db: Session,
    job: SummaryJob,
    settings: Settings,
    llm_client: LLMClient,
) -> Summary:
    if job.document_id is None:
        raise ValueError("Job individual sem document_id.")

    document = db.get(Document, job.document_id)
    if document is None:
        raise ValueError("Documento não encontrado.")

    if document.summary:
        return document.summary

    content, source_truncated = _summarize_chunks(
        document.extracted_text,
        settings,
        llm_client,
        build_individual_chunk_prompt,
        build_individual_final_prompt,
    )
    summary = Summary(
        user_id=job.user_id,
        document_id=document.id,
        content=content,
        model_name=settings.gemini_model,
        source_truncated=source_truncated,
    )
    db.add(summary)
    db.flush()
    return summary


def _process_integrated_job(
    db: Session,
    job: SummaryJob,
    settings: Settings,
    llm_client: LLMClient,
) -> IntegratedSummary:
    requested_ids = [UUID(str(document_id)) for document_id in (job.document_ids or [])]
    if len(requested_ids) < 2:
        raise ValueError("Job integrado precisa de pelo menos dois documentos.")

    documents = list(
        db.scalars(
            select(Document).where(
                Document.user_id == job.user_id,
                Document.id.in_(requested_ids),
            )
        )
    )
    if len(documents) != len(requested_ids):
        raise ValueError("Um ou mais documentos não foram encontrados.")

    documents_by_id = {document.id: document for document in documents}
    ordered_documents = [documents_by_id[document_id] for document_id in requested_ids]
    combined_content = "\n\n---\n\n".join(
        f"Documento {index}: {document.filename}\n\n{document.extracted_text}"
        for index, document in enumerate(ordered_documents, start=1)
    )

    content, source_truncated = _summarize_chunks(
        combined_content,
        settings,
        llm_client,
        build_integrated_chunk_prompt,
        build_integrated_final_prompt,
    )
    integrated_summary = IntegratedSummary(
        user_id=job.user_id,
        title=job.title,
        document_ids=[str(document_id) for document_id in requested_ids],
        content=content,
        model_name=settings.gemini_model,
        source_truncated=source_truncated,
    )
    db.add(integrated_summary)
    db.flush()
    return integrated_summary


def process_summary_job(
    db: Session,
    job_id: UUID,
    settings: Settings,
    llm_client: LLMClient,
) -> SummaryJob:
    job = db.get(SummaryJob, job_id)
    if job is None:
        raise ValueError("Job não encontrado.")
    if job.status == JOB_STATUS_COMPLETED:
        return job

    job.status = JOB_STATUS_PROCESSING
    job.started_at = utc_now()
    job.finished_at = None
    job.error_message = None
    job.attempt_count += 1
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        if job.kind == JOB_KIND_INDIVIDUAL:
            summary = _process_individual_job(db, job, settings, llm_client)
            job.summary_id = summary.id
        else:
            integrated_summary = _process_integrated_job(db, job, settings, llm_client)
            job.integrated_summary_id = integrated_summary.id

        job.status = JOB_STATUS_COMPLETED
        job.finished_at = utc_now()
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
    except Exception as exc:
        db.rollback()
        job = db.get(SummaryJob, job_id)
        if job is None:
            raise
        job.status = JOB_STATUS_FAILED
        job.error_message = str(exc)
        job.finished_at = utc_now()
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
