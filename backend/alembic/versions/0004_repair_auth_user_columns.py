"""repair missing auth columns on users

Revision ID: 0004_repair_auth_user_columns
Revises: 0003_auth_users_refresh_tokens
Create Date: 2026-05-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_repair_auth_user_columns"
down_revision = "0003_auth_users_refresh_tokens"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade():
    if not _column_exists("users", "password_hash"):
        op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))

    if not _column_exists("users", "role"):
        op.add_column(
            "users",
            sa.Column("role", sa.String(length=50), nullable=False, server_default="user"),
        )
        op.alter_column("users", "role", server_default=None)


def downgrade():
    if _column_exists("users", "role"):
        op.drop_column("users", "role")

    if _column_exists("users", "password_hash"):
        op.drop_column("users", "password_hash")
