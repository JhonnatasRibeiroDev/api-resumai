from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.documents.models import Document
    from app.users.models import User


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


document_ids_type = JSON().with_variant(JSONB, "postgresql")


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(100))
    source_truncated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    user: Mapped[User] = relationship("User", back_populates="summaries")
    document: Mapped[Document] = relationship("Document", back_populates="summary")


class IntegratedSummary(Base):
    __tablename__ = "integrated_summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str | None] = mapped_column(String(255))
    document_ids: Mapped[list[Any]] = mapped_column(document_ids_type, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(100))
    source_truncated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    user: Mapped[User] = relationship("User", back_populates="integrated_summaries")
