"""backfill summary model names

Revision ID: 202607050003
Revises: 202607050002
Create Date: 2026-07-05 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = "202607050003"
down_revision: str | None = "202607050002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        update summaries
        set model_name = 'gemini-2.0-flash'
        where model_name is null or trim(model_name) = ''
        """
    )
    op.execute(
        """
        update integrated_summaries
        set model_name = 'gemini-2.0-flash'
        where model_name is null or trim(model_name) = ''
        """
    )


def downgrade() -> None:
    pass
