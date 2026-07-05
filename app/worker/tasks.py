from uuid import UUID

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.llm.client import GeminiLLMClient
from app.summaries.processor import process_summary_job
from app.worker.celery_app import celery_app


@celery_app.task(name="summary.process")
def process_summary_job_task(job_id: str) -> str:
    settings = get_settings()
    llm_client = GeminiLLMClient(settings.gemini_api_key, settings.gemini_model)
    db = SessionLocal()
    try:
        job = process_summary_job(db, UUID(job_id), settings, llm_client)
        return str(job.id)
    finally:
        db.close()
