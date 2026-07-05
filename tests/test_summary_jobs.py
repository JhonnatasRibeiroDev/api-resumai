from typing import Any

import pytest

from app.documents.models import Document
from app.summaries import service as summaries_service
from app.summaries.constants import (
    JOB_KIND_INDIVIDUAL,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_PENDING,
)
from app.summaries.models import Summary, SummaryJob
from app.summaries.processor import process_summary_job
from app.users.models import User


class FailingLLMClient:
    def generate(self, prompt: str) -> str:
        raise RuntimeError("LLM indisponível")


class FakeLLMClient:
    def generate(self, prompt: str) -> str:
        return f"Resumo fake: {prompt[:40]}"


def create_user_document_and_job(db):
    user = User(
        full_name="Teste",
        username="teste",
        email="teste@example.com",
        password_hash="hash",
    )
    db.add(user)
    db.flush()

    document = Document(
        user_id=user.id,
        filename="doc.pdf",
        file_path="/tmp/doc.pdf",
        file_size=100,
        mime_type="application/pdf",
        extracted_text="Conteúdo do documento para resumir. " * 20,
    )
    db.add(document)
    db.flush()

    job = SummaryJob(
        user_id=user.id,
        kind=JOB_KIND_INDIVIDUAL,
        status=JOB_STATUS_PENDING,
        document_id=document.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return user, document, job


def test_worker_completes_individual_summary_job(test_context: dict[str, Any]) -> None:
    session_local = test_context["session_local"]
    settings = test_context["settings"]
    db = session_local()
    try:
        _, _, job = create_user_document_and_job(db)

        processed_job = process_summary_job(db, job.id, settings, FakeLLMClient())
        summary = db.get(Summary, processed_job.summary_id)

        assert processed_job.status == JOB_STATUS_COMPLETED
        assert processed_job.attempt_count == 1
        assert summary is not None
        assert "Resumo fake" in summary.content
    finally:
        db.close()


def test_worker_saves_failure_message(test_context: dict[str, Any]) -> None:
    session_local = test_context["session_local"]
    settings = test_context["settings"]
    db = session_local()
    try:
        _, _, job = create_user_document_and_job(db)

        processed_job = process_summary_job(db, job.id, settings, FailingLLMClient())

        assert processed_job.status == JOB_STATUS_FAILED
        assert processed_job.attempt_count == 1
        assert "LLM indisponível" in (processed_job.error_message or "")
    finally:
        db.close()


def test_retry_failed_job_resets_status(
    test_context: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_local = test_context["session_local"]
    settings = test_context["settings"]
    db = session_local()
    try:
        user, _, job = create_user_document_and_job(db)
        job.status = JOB_STATUS_FAILED
        job.error_message = "falhou"
        job.attempt_count = 1
        db.add(job)
        db.commit()

        monkeypatch.setattr(summaries_service, "_enqueue_job", lambda job, settings: None)

        retried_job = summaries_service.retry_summary_job(db, user, job.id, settings)

        assert retried_job.status == JOB_STATUS_PENDING
        assert retried_job.error_message is None
        assert retried_job.attempt_count == 1
    finally:
        db.close()
