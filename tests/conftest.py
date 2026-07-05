from collections.abc import Generator

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


class FakeLLMClient:
    def generate(self, prompt: str) -> str:
        return f"Resumo fake gerado.\n\n{prompt[:120]}"


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
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
    )

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
