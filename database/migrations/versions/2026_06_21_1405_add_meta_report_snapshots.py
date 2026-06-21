"""add meta report snapshots

Revision ID: 2026_06_21_1405
Revises: 2026_06_18_0715
Create Date: 2026-06-21 14:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2026_06_21_1405"
down_revision = "2026_06_18_0715"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meta_report_snapshots",
        sa.Column("meta_ad_account_id", sa.String(length=36), nullable=False),
        sa.Column("requested_days", sa.Integer(), nullable=False),
        sa.Column("current_since", sa.Date(), nullable=False),
        sa.Column("current_until", sa.Date(), nullable=False),
        sa.Column("previous_since", sa.Date(), nullable=False),
        sa.Column("previous_until", sa.Date(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("source_fetched_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["meta_ad_account_id"], ["meta_ad_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "meta_ad_account_id",
            "current_since",
            "current_until",
            "previous_since",
            "previous_until",
            name="uq_meta_report_snapshot_account_period",
        ),
    )
    op.create_index(op.f("ix_meta_report_snapshots_meta_ad_account_id"), "meta_report_snapshots", ["meta_ad_account_id"], unique=False)
    op.create_index(op.f("ix_meta_report_snapshots_expires_at"), "meta_report_snapshots", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_meta_report_snapshots_expires_at"), table_name="meta_report_snapshots")
    op.drop_index(op.f("ix_meta_report_snapshots_meta_ad_account_id"), table_name="meta_report_snapshots")
    op.drop_table("meta_report_snapshots")
