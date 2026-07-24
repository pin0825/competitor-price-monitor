from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class CurrentPrice(BaseModel):
    listing_id: int
    retailer: str
    price: Decimal
    currency: str
    observed_at: datetime


class ProductCurrentPrices(BaseModel):
    product_id: int
    prices: list[CurrentPrice]


class PriceHistoryItem(BaseModel):
    observation_id: int
    listing_id: int
    retailer: str
    price: Decimal
    currency: str
    observed_at: datetime


class ProductPriceHistory(BaseModel):
    product_id: int
    period_days: int
    observations: list[PriceHistoryItem]


class ListingStatistics(BaseModel):
    listing_id: int
    retailer: str
    currency: str
    observation_count: int
    minimum_price: Decimal
    maximum_price: Decimal
    average_price: Decimal
    latest_price: Decimal
    previous_price: Decimal | None
    absolute_change: Decimal | None
    percentage_change: Decimal | None


class ProductStatistics(BaseModel):
    product_id: int
    period_days: int
    listings: list[ListingStatistics]
