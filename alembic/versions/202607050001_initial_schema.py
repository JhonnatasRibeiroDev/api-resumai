"""initial schema

Revision ID: 202607050001
Revises:
Create Date: 2026-07-05 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "202607050001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("profile_image", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_user_id"), "documents", ["user_id"])

    op.create_table(
        "integrated_summaries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("document_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("source_truncated", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_integrated_summaries_user_id"),
        "integrated_summaries",
        ["user_id"],
    )

    op.create_table(
        "summaries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("source_truncated", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_summaries_document_id"), "summaries", ["document_id"], unique=True)
    op.create_index(op.f("ix_summaries_user_id"), "summaries", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_summaries_user_id"), table_name="summaries")
    op.drop_index(op.f("ix_summaries_document_id"), table_name="summaries")
    op.drop_table("summaries")

    op.drop_index(
        op.f("ix_integrated_summaries_user_id"),
        table_name="integrated_summaries",
    )
    op.drop_table("integrated_summaries")

    op.drop_index(op.f("ix_documents_user_id"), table_name="documents")
    op.drop_table("documents")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
