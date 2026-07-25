from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.price_alert_event import PriceAlertEvent
    from app.models.product import Product


class PriceAlertRule(Base):
    """상품 가격이 목표 이하가 되었을 때 평가할 알림 규칙이다."""

    __tablename__ = "price_alert_rules"
    __table_args__ = (
        CheckConstraint(
            "target_price > 0",
            name="ck_price_alert_rules_target_positive",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
    )
    target_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="GBP")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    product: Mapped["Product"] = relationship(back_populates="alert_rules")
    events: Mapped[list["PriceAlertEvent"]] = relationship(
        back_populates="rule",
        cascade="all, delete-orphan",
    )
