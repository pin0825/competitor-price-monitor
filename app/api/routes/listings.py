from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.listing import Listing
from app.schemas.listing import ListingRead, ListingUpdate

router = APIRouter(prefix="/listings", tags=["listings"])
DbSession = Annotated[Session, Depends(get_db)]


@router.patch("/{listing_id}", response_model=ListingRead)
def update_listing(
    listing_id: int,
    payload: ListingUpdate,
    db: DbSession,
) -> Listing:
    """주소가 바뀐 판매처 listing의 필요한 필드만 수정한다."""
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found",
        )

    changes = payload.model_dump(exclude_unset=True)
    if changes.get("url") is not None:
        # HttpUrl 객체는 SQLAlchemy 문자열 컬럼에 맞춰 변환한다.
        changes["url"] = str(changes["url"])

    for field, value in changes.items():
        setattr(listing, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Listing URL already exists",
        ) from exc

    db.refresh(listing)
    return listing
