import subprocess
import sys
import textwrap
from pathlib import Path


def test_worker_process_can_resolve_user_relationship_without_direct_import() -> None:
    script = textwrap.dedent(
        """
        import uuid
        import app.worker.tasks  # mesma cadeia de import que o Celery usa (include=["app.worker.tasks"])
        from sqlalchemy import create_engine
        from sqlalchemy.exc import InvalidRequestError
        from sqlalchemy.orm import Session
        from app.summaries.models import SummaryJob

        engine = create_engine("sqlite://")
        with Session(engine) as session:
            try:
                session.get(SummaryJob, uuid.uuid4())  # dispara configure_mappers()
            except InvalidRequestError:
                raise  # falha ao configurar os mappers (o bug original)
            except Exception:
                pass  # outros erros (ex.: tabela inexistente) sao irrelevantes aqui
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
