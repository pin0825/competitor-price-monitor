"""Create collection run audit tables.

Revision ID: 20260725_0002
Revises: 20260723_0001
Create Date: 2026-07-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260725_0002"
down_revision: str | None = "20260723_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """수집 실행 요약과 판매처별 시도 기록 테이블을 생성한다."""
    op.create_table(
        "collection_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("requested_count", sa.Integer(), nullable=False),
        sa.Column("created_count", sa.Integer(), nullable=False),
        sa.Column("unchanged_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "requested_count >= 0 AND created_count >= 0 "
            "AND unchanged_count >= 0 AND failed_count >= 0",
            name="ck_collection_runs_counts_non_negative",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_collection_runs_started_at"),
        "collection_runs",
        ["started_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_collection_runs_status"),
        "collection_runs",
        ["status"],
        unique=False,
    )

    op.create_table(
        "collection_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=True),
        sa.Column("retailer", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "price",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("observation_id", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
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
            ["run_id"],
            ["collection_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_collection_attempts_listing_id"),
        "collection_attempts",
        ["listing_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_collection_attempts_run_id"),
        "collection_attempts",
        ["run_id"],
        unique=False,
    )


def downgrade() -> None:
    """수집 감사 테이블을 의존성 역순으로 제거한다."""
    op.drop_index(
        op.f("ix_collection_attempts_run_id"),
        table_name="collection_attempts",
    )
    op.drop_index(
        op.f("ix_collection_attempts_listing_id"),
        table_name="collection_attempts",
    )
    op.drop_table("collection_attempts")
    op.drop_index(
        op.f("ix_collection_runs_status"),
        table_name="collection_runs",
    )
    op.drop_index(
        op.f("ix_collection_runs_started_at"),
        table_name="collection_runs",
    )
    op.drop_table("collection_runs")
