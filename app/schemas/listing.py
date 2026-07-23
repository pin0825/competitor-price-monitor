from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class ListingCreate(BaseModel):
    """listing 생성 요청으로 받을 JSON 구조와 검증 규칙이다."""

    retailer: str = Field(min_length=1, max_length=100)
    # HttpUrl을 사용하면 잘못된 형태의 URL을 API 진입 단계에서 거부한다.
    url: HttpUrl
    currency: str = Field(default="GBP", min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        """gbp처럼 입력해도 DB에는 GBP로 통일해 저장한다."""
        return value.upper()


class ListingRead(BaseModel):
    """DB의 listing을 API 응답 JSON으로 변환할 때 사용하는 구조다."""

    # SQLAlchemy 객체의 속성을 읽어 Pydantic 응답으로 변환할 수 있게 한다.
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    retailer: str
    url: str
    currency: str
    is_active: bool
    created_at: datetime
