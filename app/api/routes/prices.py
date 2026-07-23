from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.listing import Listing
from app.models.price_observation import PriceObservation
from app.models.product import Product
from app.schemas.price import (
    CurrentPrice,
    ListingStatistics,
    PriceHistoryItem,
    ProductCurrentPrices,
    ProductPriceHistory,
    ProductStatistics,
)

router = APIRouter(prefix="/products", tags=["prices"])
DbSession = Annotated[Session, Depends(get_db)]
PeriodDays = Annotated[int, Query(ge=1, le=3650)]


def _require_product(product_id: int, db: Session) -> None:
    """조회 전에 product 존재 여부를 확인해 일관된 404를 반환한다."""
    if db.get(Product, product_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )


@router.get(
    "/{product_id}/prices/current",
    response_model=ProductCurrentPrices,
)
def get_current_prices(
    product_id: int,
    db: DbSession,
) -> ProductCurrentPrices:
    """상품에 연결된 각 판매처의 가장 최근 가격을 반환한다."""
    _require_product(product_id, db)

    ranked = (
        select(
            PriceObservation.listing_id.label("listing_id"),
            PriceObservation.price.label("price"),
            PriceObservation.observed_at.label("observed_at"),
            func.row_number()
            .over(
                partition_by=PriceObservation.listing_id,
                order_by=PriceObservation.observed_at.desc(),
            )
            .label("position"),
        )
        .subquery()
    )

    statement = (
        select(
            Listing.id,
            Listing.retailer,
            Listing.currency,
            ranked.c.price,
            ranked.c.observed_at,
        )
        .join(ranked, ranked.c.listing_id == Listing.id)
        .where(
            Listing.product_id == product_id,
            ranked.c.position == 1,
        )
        .order_by(Listing.id)
    )

    prices = [
        CurrentPrice(
            listing_id=row.id,
            retailer=row.retailer,
            price=row.price,
            currency=row.currency,
            observed_at=row.observed_at,
        )
        for row in db.execute(statement)
    ]
    return ProductCurrentPrices(product_id=product_id, prices=prices)


@router.get(
    "/{product_id}/prices/history",
    response_model=ProductPriceHistory,
)
def get_price_history(
    product_id: int,
    db: DbSession,
    days: PeriodDays = 30,
) -> ProductPriceHistory:
    """요청 기간 안의 모든 판매처 가격 기록을 시간 역순으로 반환한다."""
    _require_product(product_id, db)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    statement = (
        select(
            PriceObservation.id.label("observation_id"),
            Listing.id.label("listing_id"),
            Listing.retailer,
            PriceObservation.price,
            Listing.currency,
            PriceObservation.observed_at,
        )
        .join(Listing, Listing.id == PriceObservation.listing_id)
        .where(
            Listing.product_id == product_id,
            PriceObservation.observed_at >= since,
        )
        .order_by(PriceObservation.observed_at.desc())
    )

    observations = [
        PriceHistoryItem(**row._mapping)
        for row in db.execute(statement)
    ]
    return ProductPriceHistory(
        product_id=product_id,
        period_days=days,
        observations=observations,
    )


@router.get(
    "/{product_id}/statistics",
    response_model=ProductStatistics,
)
def get_price_statistics(
    product_id: int,
    db: DbSession,
    days: PeriodDays = 30,
) -> ProductStatistics:
    """판매처별 최저·최고·평균과 최근 가격 변화를 계산한다."""
    _require_product(product_id, db)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    aggregate_statement = (
        select(
            Listing.id.label("listing_id"),
            Listing.retailer,
            Listing.currency,
            func.count(PriceObservation.id).label("observation_count"),
            func.min(PriceObservation.price).label("minimum_price"),
            func.max(PriceObservation.price).label("maximum_price"),
            func.avg(PriceObservation.price).label("average_price"),
        )
        .join(PriceObservation, PriceObservation.listing_id == Listing.id)
        .where(
            Listing.product_id == product_id,
            PriceObservation.observed_at >= since,
        )
        .group_by(Listing.id, Listing.retailer, Listing.currency)
        .order_by(Listing.id)
    )

    ranked = (
        select(
            PriceObservation.listing_id.label("listing_id"),
            PriceObservation.price.label("price"),
            func.row_number()
            .over(
                partition_by=PriceObservation.listing_id,
                order_by=PriceObservation.observed_at.desc(),
            )
            .label("position"),
        )
        .join(Listing, Listing.id == PriceObservation.listing_id)
        .where(
            Listing.product_id == product_id,
            PriceObservation.observed_at >= since,
        )
        .subquery()
    )
    recent_statement = (
        select(ranked.c.listing_id, ranked.c.price, ranked.c.position)
        .where(ranked.c.position <= 2)
        .order_by(ranked.c.listing_id, ranked.c.position)
    )

    recent_prices: dict[int, list[Decimal]] = {}
    for row in db.execute(recent_statement):
        recent_prices.setdefault(row.listing_id, []).append(row.price)

    listing_statistics: list[ListingStatistics] = []
    for row in db.execute(aggregate_statement):
        prices = recent_prices[row.listing_id]
        latest = prices[0]
        previous = prices[1] if len(prices) > 1 else None
        absolute_change = latest - previous if previous is not None else None
        percentage_change = (
            (absolute_change / previous * Decimal("100")).quantize(
                Decimal("0.01")
            )
            if previous is not None
            else None
        )

        listing_statistics.append(
            ListingStatistics(
                listing_id=row.listing_id,
                retailer=row.retailer,
                currency=row.currency,
                observation_count=row.observation_count,
                minimum_price=row.minimum_price,
                maximum_price=row.maximum_price,
                average_price=Decimal(str(row.average_price)).quantize(
                    Decimal("0.01")
                ),
                latest_price=latest,
                previous_price=previous,
                absolute_change=absolute_change,
                percentage_change=percentage_change,
            )
        )

    return ProductStatistics(
        product_id=product_id,
        period_days=days,
        listings=listing_statistics,
    )
