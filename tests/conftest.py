from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.llm.client import get_llm_client
from app.main import app
from app.summaries import service as summaries_service
from app.summaries.processor import process_summary_job


class FakeLLMClient:
    def generate(self, prompt: str) -> str:
        return f"Resumo fake gerado.\n\n{prompt[:120]}"


@pytest.fixture()
def test_context(tmp_path) -> Generator[dict[str, Any], None, None]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)

    test_settings = Settings(
        database_url="sqlite+pysqlite://",
        jwt_secret="test-secret",
        upload_dir=str(tmp_path / "uploads"),
        gemini_api_key="test-key",
        gemini_model="fake-gemini",
        enqueue_summary_jobs=True,
        summary_chunk_chars=120,
        summary_chunk_overlap_chars=10,
        summary_max_chunks=4,
        user_max_active_summary_jobs=2,
    )

    yield {"session_local": testing_session_local, "settings": test_settings}

    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(
    test_context: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    testing_session_local = test_context["session_local"]
    test_settings = test_context["settings"]

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient()

    def immediate_enqueue(job, settings) -> None:
        db = testing_session_local()
        try:
            process_summary_job(db, job.id, settings, FakeLLMClient())
        finally:
            db.close()

    monkeypatch.setattr(summaries_service, "_enqueue_job", immediate_enqueue)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
