from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.listing import Listing
from app.schemas.collection import CollectionRunResult
from app.services.collection import collect_listings

router = APIRouter(tags=["collection"])
DbSession = Annotated[Session, Depends(get_db)]


def _summarise(results: list) -> CollectionRunResult:
    """개별 결과를 Swagger에서 보기 쉬운 개수 요약과 함께 반환한다."""
    return CollectionRunResult(
        requested=len(results),
        created=sum(result.status == "created" for result in results),
        unchanged=sum(result.status == "unchanged" for result in results),
        failed=sum(result.status == "failed" for result in results),
        results=results,
    )


@router.post("/collection-runs", response_model=CollectionRunResult)
async def collect_all_active_listings(db: DbSession) -> CollectionRunResult:
    """모든 활성 listing을 비동기로 수집한다."""
    statement = (
        select(Listing)
        .where(Listing.is_active.is_(True))
        .order_by(Listing.id)
    )
    listings = list(db.scalars(statement).all())
    results = await collect_listings(listings, db)
    return _summarise(results)


@router.post(
    "/listings/{listing_id}/collection-runs",
    response_model=CollectionRunResult,
)
async def collect_one_listing(
    listing_id: int,
    db: DbSession,
) -> CollectionRunResult:
    """지정한 listing 하나만 즉시 수집한다."""
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found",
        )

    results = await collect_listings([listing], db)
    return _summarise(results)
