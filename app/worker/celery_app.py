from celery import Celery

import app.db.base  # noqa: F401  # garante que todos os modelos ORM (incl. User) estejam registrados
from app.core.config import get_settings


settings = get_settings()

celery_app = Celery(
    "resumai",
    broker=settings.celery_broker_url,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
