"""add tiktok ads connections

Revision ID: 2026_07_06_1200
Revises: 2026_06_21_1835
Create Date: 2026-07-06 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2026_07_06_1200"
down_revision = "2026_06_21_1835"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tiktok_ads_connections",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("refresh_token_encrypted", sa.String(), nullable=False),
        sa.Column("access_token_encrypted", sa.String(), nullable=False),
        sa.Column("access_token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("scopes", sa.String(length=1024), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_tiktok_ads_connection_user"),
    )
    op.create_index(op.f("ix_tiktok_ads_connections_user_id"), "tiktok_ads_connections", ["user_id"], unique=False)

    op.create_table(
        "tiktok_ads_advertisers",
        sa.Column("connection_id", sa.String(length=36), nullable=False),
        sa.Column("advertiser_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=True),
        sa.Column("timezone_name", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["tiktok_ads_connections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("connection_id", "advertiser_id", name="uq_tiktok_ads_advertiser_connection_external"),
    )
    op.create_index(op.f("ix_tiktok_ads_advertisers_connection_id"), "tiktok_ads_advertisers", ["connection_id"], unique=False)
    op.create_index(
        op.f("ix_tiktok_ads_advertisers_advertiser_id"),
        "tiktok_ads_advertisers",
        ["advertiser_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_tiktok_ads_advertisers_advertiser_id"), table_name="tiktok_ads_advertisers")
    op.drop_index(op.f("ix_tiktok_ads_advertisers_connection_id"), table_name="tiktok_ads_advertisers")
    op.drop_table("tiktok_ads_advertisers")
    op.drop_index(op.f("ix_tiktok_ads_connections_user_id"), table_name="tiktok_ads_connections")
    op.drop_table("tiktok_ads_connections")
