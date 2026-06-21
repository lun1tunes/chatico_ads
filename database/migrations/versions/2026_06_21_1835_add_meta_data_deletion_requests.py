"""add meta data deletion requests

Revision ID: 2026_06_21_1835
Revises: 2026_06_21_1428
Create Date: 2026-06-21 18:35:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2026_06_21_1835"
down_revision = "2026_06_21_1428"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meta_data_deletion_requests",
        sa.Column("meta_user_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("detail", sa.String(length=512), nullable=False),
        sa.Column("deleted_users_count", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_meta_data_deletion_requests_meta_user_id"),
        "meta_data_deletion_requests",
        ["meta_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_meta_data_deletion_requests_meta_user_id"), table_name="meta_data_deletion_requests")
    op.drop_table("meta_data_deletion_requests")
