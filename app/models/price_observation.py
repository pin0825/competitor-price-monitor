from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.listing import Listing


class PriceObservation(Base):
    """한 판매 페이지에서 특정 시각에 확인한 가격을 저장한다."""

    __tablename__ = "price_observations"
    __table_args__ = (
        CheckConstraint(
            "price > 0",
            name="ck_price_observations_price_positive",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"),
        index=True,
    )
    # 돈은 부동소수점 오차를 피하기 위해 Decimal/NUMERIC으로 저장한다.
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # observed_at은 실제 가격을 확인한 시각이다.
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    # created_at은 이 행이 DB에 입력된 시각이라 observed_at과 다를 수 있다.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    listing: Mapped["Listing"] = relationship(back_populates="price_observations")
