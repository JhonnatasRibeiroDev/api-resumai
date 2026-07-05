from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SummaryRead(BaseModel):
    id: UUID
    document_id: UUID
    content: str
    model_name: str | None = None
    source_truncated: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IntegratedSummaryCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    document_ids: list[UUID] = Field(min_length=2)


class IntegratedSummaryRead(BaseModel):
    id: UUID
    title: str | None = None
    document_ids: list[UUID]
    content: str
    model_name: str | None = None
    source_truncated: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


SummaryJobStatus = Literal["pending", "processing", "completed", "failed"]
SummaryJobKind = Literal["individual", "integrated"]


class SummaryJobRead(BaseModel):
    id: UUID
    user_id: UUID
    kind: SummaryJobKind
    status: SummaryJobStatus
    document_id: UUID | None = None
    document_ids: list[UUID] | None = None
    title: str | None = None
    summary_id: UUID | None = None
    integrated_summary_id: UUID | None = None
    error_message: str | None = None
    attempt_count: int
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
