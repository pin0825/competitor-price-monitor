from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AlertRuleCreate(BaseModel):
    """상품 목표가 알림 생성 요청이다."""

    target_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="GBP", min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()


class AlertRuleUpdate(BaseModel):
    """목표가 또는 활성 상태의 부분 수정 요청이다."""

    target_price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_change(self) -> "AlertRuleUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class AlertRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    target_price: Decimal
    currency: str
    is_active: bool
    created_at: datetime


class AlertEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rule_id: int
    listing_id: int | None
    observation_id: int | None
    retailer: str
    observed_price: Decimal
    target_price: Decimal
    currency: str
    triggered_at: datetime
    acknowledged_at: datetime | None
