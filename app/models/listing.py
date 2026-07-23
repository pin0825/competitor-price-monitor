from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.price_observation import PriceObservation
    from app.models.product import Product


class Listing(Base):
    """특정 쇼핑몰에 존재하는 상품 페이지 하나를 나타낸다."""

    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    # listings.product_id가 products.id를 참조한다.
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
    )
    retailer: Mapped[str] = mapped_column(String(100))
    # 같은 상품 페이지가 중복 등록되지 않도록 URL을 unique로 설정한다.
    url: Mapped[str] = mapped_column(Text, unique=True)
    currency: Mapped[str] = mapped_column(String(3), default="GBP")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    product: Mapped["Product"] = relationship(back_populates="listings")
    # listing 하나에서 시간에 따라 여러 가격 기록이 생성된다.
    price_observations: Mapped[list["PriceObservation"]] = relationship(
        back_populates="listing",
        cascade="all, delete-orphan",
    )
