"""summary jobs

Revision ID: 202607050002
Revises: 202607050001
Create Date: 2026-07-05 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "202607050002"
down_revision: str | None = "202607050001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


document_ids_type = sa.JSON().with_variant(
    postgresql.JSONB(astext_type=sa.Text()),
    "postgresql",
)


def upgrade() -> None:
    op.create_table(
        "summary_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("document_ids", document_ids_type, nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("summary_id", sa.Uuid(), nullable=True),
        sa.Column("integrated_summary_id", sa.Uuid(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "kind in ('individual', 'integrated')",
            name="ck_summary_jobs_kind",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'processing', 'completed', 'failed')",
            name="ck_summary_jobs_status",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["integrated_summary_id"],
            ["integrated_summaries.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["summary_id"], ["summaries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_summary_jobs_document_id"),
        "summary_jobs",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_summary_jobs_kind"),
        "summary_jobs",
        ["kind"],
        unique=False,
    )
    op.create_index(
        op.f("ix_summary_jobs_status"),
        "summary_jobs",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_summary_jobs_user_id"),
        "summary_jobs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_summary_jobs_user_status",
        "summary_jobs",
        ["user_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_summary_jobs_user_document_status",
        "summary_jobs",
        ["user_id", "document_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_summary_jobs_user_document_status", table_name="summary_jobs")
    op.drop_index("ix_summary_jobs_user_status", table_name="summary_jobs")
    op.drop_index(op.f("ix_summary_jobs_user_id"), table_name="summary_jobs")
    op.drop_index(op.f("ix_summary_jobs_status"), table_name="summary_jobs")
    op.drop_index(op.f("ix_summary_jobs_kind"), table_name="summary_jobs")
    op.drop_index(op.f("ix_summary_jobs_document_id"), table_name="summary_jobs")
    op.drop_table("summary_jobs")
