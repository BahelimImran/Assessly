"""add active upload session to documents

Revision ID: 0002_active_upload_session
Revises: 0001_initial_metadata
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_active_upload_session"
down_revision = "0001_initial_metadata"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "documents",
        sa.Column("active_upload_session_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_documents_active_upload_session",
        "documents",
        ["active_upload_session_id"],
    )


def downgrade():
    op.drop_index("ix_documents_active_upload_session", table_name="documents")
    op.drop_column("documents", "active_upload_session_id")
