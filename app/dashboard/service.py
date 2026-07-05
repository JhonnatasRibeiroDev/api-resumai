from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.dashboard.schemas import DashboardRead
from app.documents.models import Document
from app.documents.service import document_to_read
from app.summaries.models import IntegratedSummary, Summary
from app.users.models import User


def get_dashboard(db: Session, user: User) -> DashboardRead:
    total_documents = db.scalar(
        select(func.count()).select_from(Document).where(Document.user_id == user.id)
    )
    total_individual_summaries = db.scalar(
        select(func.count()).select_from(Summary).where(Summary.user_id == user.id)
    )
    total_integrated_summaries = db.scalar(
        select(func.count())
        .select_from(IntegratedSummary)
        .where(IntegratedSummary.user_id == user.id)
    )

    latest_documents = list(
        db.scalars(
            select(Document)
            .options(selectinload(Document.summary))
            .where(Document.user_id == user.id)
            .order_by(Document.created_at.desc())
            .limit(5)
        )
    )
    latest_summaries = list(
        db.scalars(
            select(Summary)
            .where(Summary.user_id == user.id)
            .order_by(Summary.created_at.desc())
            .limit(5)
        )
    )
    latest_integrated_summaries = list(
        db.scalars(
            select(IntegratedSummary)
            .where(IntegratedSummary.user_id == user.id)
            .order_by(IntegratedSummary.created_at.desc())
            .limit(5)
        )
    )

    return DashboardRead(
        total_documents=total_documents or 0,
        total_individual_summaries=total_individual_summaries or 0,
        total_integrated_summaries=total_integrated_summaries or 0,
        latest_documents=[document_to_read(document) for document in latest_documents],
        latest_summaries=latest_summaries,
        latest_integrated_summaries=latest_integrated_summaries,
    )
