"""add auth fields and refresh tokens

Revision ID: 0003_auth_users_refresh_tokens
Revises: 0002_active_upload_session
Create Date: 2026-05-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_auth_users_refresh_tokens"
down_revision = "0002_active_upload_session"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("role", sa.String(length=50), nullable=False, server_default="user"))
    op.alter_column("users", "role", server_default=None)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])
    op.create_index("ix_refresh_tokens_user_revoked", "refresh_tokens", ["user_id", "revoked_at"])


def downgrade():
    op.drop_index("ix_refresh_tokens_user_revoked", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_column("users", "role")
    op.drop_column("users", "password_hash")
