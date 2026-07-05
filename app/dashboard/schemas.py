from pydantic import BaseModel

from app.documents.schemas import DocumentRead
from app.summaries.schemas import IntegratedSummaryRead, SummaryRead


class DashboardRead(BaseModel):
    total_documents: int
    total_individual_summaries: int
    total_integrated_summaries: int
    latest_documents: list[DocumentRead]
    latest_summaries: list[SummaryRead]
    latest_integrated_summaries: list[IntegratedSummaryRead]
