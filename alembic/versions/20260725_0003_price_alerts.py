"""Create price alert rules and events.

Revision ID: 20260725_0003
Revises: 20260725_0002
Create Date: 2026-07-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260725_0003"
down_revision: str | None = "20260725_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """목표 가격 규칙과 중복 방지된 알림 이벤트 테이블을 생성한다."""
    op.create_table(
        "price_alert_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("target_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "target_price > 0",
            name="ck_price_alert_rules_target_positive",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_price_alert_rules_product_id"),
        "price_alert_rules",
        ["product_id"],
        unique=False,
    )

    op.create_table(
        "price_alert_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=True),
        sa.Column("observation_id", sa.Integer(), nullable=True),
        sa.Column("retailer", sa.String(length=100), nullable=False),
        sa.Column("observed_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("target_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "acknowledged_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["listing_id"],
            ["listings.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["price_observations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["price_alert_rules.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "rule_id",
            "observation_id",
            name="uq_price_alert_events_rule_observation",
        ),
    )
    op.create_index(
        op.f("ix_price_alert_events_listing_id"),
        "price_alert_events",
        ["listing_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_price_alert_events_rule_id"),
        "price_alert_events",
        ["rule_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_price_alert_events_triggered_at"),
        "price_alert_events",
        ["triggered_at"],
        unique=False,
    )


def downgrade() -> None:
    """알림 이벤트와 규칙을 의존성 역순으로 제거한다."""
    op.drop_index(
        op.f("ix_price_alert_events_triggered_at"),
        table_name="price_alert_events",
    )
    op.drop_index(
        op.f("ix_price_alert_events_rule_id"),
        table_name="price_alert_events",
    )
    op.drop_index(
        op.f("ix_price_alert_events_listing_id"),
        table_name="price_alert_events",
    )
    op.drop_table("price_alert_events")
    op.drop_index(
        op.f("ix_price_alert_rules_product_id"),
        table_name="price_alert_rules",
    )
    op.drop_table("price_alert_rules")
