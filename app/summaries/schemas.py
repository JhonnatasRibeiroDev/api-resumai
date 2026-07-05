from datetime import datetime
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
