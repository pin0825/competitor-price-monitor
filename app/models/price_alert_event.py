from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.price_alert_rule import PriceAlertRule


class PriceAlertEvent(Base):
    """관측 가격이 목표가를 충족해 실제 발생한 알림이다."""

    __tablename__ = "price_alert_events"
    __table_args__ = (
        UniqueConstraint(
            "rule_id",
            "observation_id",
            name="uq_price_alert_events_rule_observation",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(
        ForeignKey("price_alert_rules.id", ondelete="CASCADE"),
        index=True,
    )
    listing_id: Mapped[int | None] = mapped_column(
        ForeignKey("listings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    observation_id: Mapped[int | None] = mapped_column(
        ForeignKey("price_observations.id", ondelete="SET NULL"),
        nullable=True,
    )
    retailer: Mapped[str] = mapped_column(String(100))
    observed_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    target_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    rule: Mapped["PriceAlertRule"] = relationship(back_populates="events")
