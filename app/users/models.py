from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.documents.models import Document
    from app.summaries.models import IntegratedSummary, Summary


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    profile_image: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=utc_now
    )

    documents: Mapped[list[Document]] = relationship(
        "Document", back_populates="user", cascade="all, delete-orphan"
    )
    summaries: Mapped[list[Summary]] = relationship(
        "Summary", back_populates="user", cascade="all, delete-orphan"
    )
    integrated_summaries: Mapped[list[IntegratedSummary]] = relationship(
        "IntegratedSummary", back_populates="user", cascade="all, delete-orphan"
    )
