from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.collection_attempt import CollectionAttempt


class CollectionRun(Base):
    """여러 판매처를 대상으로 실행한 한 번의 수집 작업을 기록한다."""

    __tablename__ = "collection_runs"
    __table_args__ = (
        CheckConstraint(
            "requested_count >= 0 AND created_count >= 0 "
            "AND unchanged_count >= 0 AND failed_count >= 0",
            name="ck_collection_runs_counts_non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="running", index=True)
    requested_count: Mapped[int] = mapped_column(Integer, default=0)
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    unchanged_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    attempts: Mapped[list["CollectionAttempt"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="CollectionAttempt.id",
    )
