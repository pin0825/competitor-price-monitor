from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.listing import Listing


class Product(Base):
    """여러 쇼핑몰에서 비교할 하나의 대표 상품을 나타낸다."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    brand: Mapped[str | None] = mapped_column(String(100))
    model_number: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # 상품 하나는 여러 쇼핑몰 listing을 가질 수 있다.
    # 상품을 삭제하면 소속 listing도 함께 삭제한다.
    listings: Mapped[list["Listing"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
