"""add google ads connections

Revision ID: 2026_06_21_1428
Revises: 2026_06_21_1405
Create Date: 2026-06-21 14:28:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2026_06_21_1428"
down_revision = "2026_06_21_1405"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "google_ads_connections",
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
        sa.UniqueConstraint("user_id", name="uq_google_ads_connection_user"),
    )
    op.create_index(op.f("ix_google_ads_connections_user_id"), "google_ads_connections", ["user_id"], unique=False)

    op.create_table(
        "google_ads_customers",
        sa.Column("connection_id", sa.String(length=36), nullable=False),
        sa.Column("external_customer_id", sa.String(length=32), nullable=False),
        sa.Column("resource_name", sa.String(length=64), nullable=False),
        sa.Column("descriptive_name", sa.String(length=255), nullable=False),
        sa.Column("currency_code", sa.String(length=16), nullable=True),
        sa.Column("time_zone", sa.String(length=64), nullable=True),
        sa.Column("is_manager", sa.Boolean(), nullable=False),
        sa.Column("is_directly_accessible", sa.Boolean(), nullable=False),
        sa.Column("hierarchy_level", sa.Integer(), nullable=False),
        sa.Column("root_customer_id", sa.String(length=32), nullable=True),
        sa.Column("manager_customer_id", sa.String(length=32), nullable=True),
        sa.Column("login_customer_id", sa.String(length=32), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["google_ads_connections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("connection_id", "external_customer_id", name="uq_google_ads_customer_connection_external"),
    )
    op.create_index(op.f("ix_google_ads_customers_connection_id"), "google_ads_customers", ["connection_id"], unique=False)
    op.create_index(
        op.f("ix_google_ads_customers_external_customer_id"),
        "google_ads_customers",
        ["external_customer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_google_ads_customers_external_customer_id"), table_name="google_ads_customers")
    op.drop_index(op.f("ix_google_ads_customers_connection_id"), table_name="google_ads_customers")
    op.drop_table("google_ads_customers")
    op.drop_index(op.f("ix_google_ads_connections_user_id"), table_name="google_ads_connections")
    op.drop_table("google_ads_connections")
