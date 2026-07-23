from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.listing import ListingRead


class ProductCreate(BaseModel):
    """상품 생성 요청으로 받을 JSON 구조와 검증 규칙이다."""

    name: str = Field(min_length=1, max_length=255)
    brand: str | None = Field(default=None, max_length=100)
    model_number: str | None = Field(default=None, max_length=100)


class ProductRead(BaseModel):
    """상품과 연결된 listing을 함께 반환하는 응답 구조다."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    brand: str | None
    model_number: str | None
    created_at: datetime
    # default_factory를 사용해 응답 객체마다 별도의 빈 리스트를 만든다.
    listings: list[ListingRead] = Field(default_factory=list)
