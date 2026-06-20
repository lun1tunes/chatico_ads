"""add user ai provider keys

Revision ID: 2026_06_18_0715
Revises: d3a5f57a7c59
Create Date: 2026-06-18 07:15:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2026_06_18_0715"
down_revision = "d3a5f57a7c59"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_ai_provider_keys",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("api_key_encrypted", sa.String(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "provider", name="uq_user_ai_provider_key_user_provider"),
    )
    op.create_index(op.f("ix_user_ai_provider_keys_user_id"), "user_ai_provider_keys", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_ai_provider_keys_user_id"), table_name="user_ai_provider_keys")
    op.drop_table("user_ai_provider_keys")
