from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CollectionItemResult(BaseModel):
    """listing 하나의 수집·저장 결과다."""

    listing_id: int
    retailer: str
    status: Literal["created", "unchanged", "failed"]
    price: Decimal | None = None
    currency: str | None = None
    observation_id: int | None = None
    message: str
    duration_ms: int


class CollectionRunResult(BaseModel):
    """한 번의 수집 요청에서 처리된 모든 listing 결과를 묶는다."""

    run_id: int
    requested: int
    created: int
    unchanged: int
    failed: int
    status: Literal["completed", "partial", "failed"]
    started_at: datetime
    finished_at: datetime
    results: list[CollectionItemResult]


class CollectionAttemptRead(BaseModel):
    """DB에 보존된 판매처별 수집 시도 응답이다."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_id: int | None
    retailer: str
    status: Literal["created", "unchanged", "failed"]
    price: Decimal | None
    currency: str | None
    observation_id: int | None
    message: str
    duration_ms: int
    created_at: datetime


class CollectionRunRead(BaseModel):
    """새로고침 후에도 조회 가능한 수집 실행 기록이다."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: Literal["running", "completed", "partial", "failed"]
    requested_count: int
    created_count: int
    unchanged_count: int
    failed_count: int
    started_at: datetime
    finished_at: datetime | None
    attempts: list[CollectionAttemptRead]
