from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


SummaryStatus = Literal["pending", "completed"]


class DocumentRead(BaseModel):
    id: UUID
    filename: str
    file_size: int
    mime_type: str
    created_at: datetime
    summary_status: SummaryStatus

    model_config = ConfigDict(from_attributes=True)


class DocumentUploadRead(DocumentRead):
    extraction_status: Literal["completed"] = "completed"
