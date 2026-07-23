from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class CollectionItemResult(BaseModel):
    """listing 하나의 수집·저장 결과다."""

    listing_id: int
    retailer: str
    status: Literal["created", "unchanged", "failed"]
    price: Decimal | None = None
    currency: str | None = None
    observation_id: int | None = None
    message: str


class CollectionRunResult(BaseModel):
    """한 번의 수집 요청에서 처리된 모든 listing 결과를 묶는다."""

    requested: int
    created: int
    unchanged: int
    failed: int
    results: list[CollectionItemResult]
