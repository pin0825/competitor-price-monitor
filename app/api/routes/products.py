from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.listing import Listing
from app.models.product import Product
from app.schemas.listing import ListingCreate, ListingRead
from app.schemas.product import ProductCreate, ProductRead

router = APIRouter(prefix="/products", tags=["products"])

# Depends(get_db)를 매 endpoint마다 길게 반복하지 않기 위한 타입 별칭이다.
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: DbSession) -> Product:
    """검증된 요청 JSON으로 상품을 생성하고 DB에 저장한다."""
    # model_dump()는 Pydantic 객체를 Product가 받을 수 있는 dict로 바꾼다.
    product = Product(**payload.model_dump())
    db.add(product)
    # commit 전까지 변경은 현재 세션에만 존재하고, commit 후 DB에 확정된다.
    db.commit()
    # DB가 생성한 id와 created_at을 product 객체에 다시 불러온다.
    db.refresh(product)
    return product


@router.get("", response_model=list[ProductRead])
def list_products(db: DbSession) -> list[Product]:
    """모든 상품과 각 상품에 연결된 listing을 조회한다."""
    # selectinload는 상품 조회 후 listing을 묶어서 추가 조회해 N+1 문제를 줄인다.
    statement = select(Product).options(selectinload(Product.listings))
    return list(db.scalars(statement).all())


@router.post(
    "/{product_id}/listings",
    response_model=ListingRead,
    status_code=status.HTTP_201_CREATED,
)
def create_listing(
    product_id: int,
    payload: ListingCreate,
    db: DbSession,
) -> Listing:
    """경로의 product_id에 쇼핑몰 listing 하나를 연결한다."""
    # 먼저 부모 상품이 실제로 존재하는지 확인한다.
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # URL은 HttpUrl 타입이므로 DB에 넣기 전에 일반 문자열로 변환한다.
    listing = Listing(
        product_id=product_id,
        retailer=payload.retailer,
        url=str(payload.url),
        currency=payload.currency,
    )
    db.add(listing)

    try:
        db.commit()
    except IntegrityError as exc:
        # URL unique 제약조건 등을 위반하면 실패한 transaction을 되돌린다.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Listing URL already exists",
        ) from exc

    db.refresh(listing)
    return listing
