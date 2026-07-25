from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.collection_attempt import CollectionAttempt
from app.models.collection_run import CollectionRun
from app.models.listing import Listing
from app.schemas.collection import CollectionRunRead, CollectionRunResult
from app.services.collection import collect_listings

router = APIRouter(tags=["collection"])
DbSession = Annotated[Session, Depends(get_db)]


async def _execute_collection(
    listings: list[Listing],
    db: Session,
) -> CollectionRunResult:
    """실행 레코드를 만든 뒤 수집 결과와 판매처별 시도를 영구 저장한다."""
    started_at = datetime.now(timezone.utc)
    run = CollectionRun(
        status="running",
        requested_count=len(listings),
        started_at=started_at,
    )
    db.add(run)
    # 수집 중에도 실행 중 상태를 조회할 수 있도록 먼저 확정한다.
    db.commit()
    db.refresh(run)

    try:
        results = await collect_listings(listings, db)
        created = sum(result.status == "created" for result in results)
        unchanged = sum(result.status == "unchanged" for result in results)
        failed = sum(result.status == "failed" for result in results)
        successful = created + unchanged
        run_status = (
            "completed"
            if failed == 0
            else "partial"
            if successful > 0
            else "failed"
        )
        finished_at = datetime.now(timezone.utc)

        run.status = run_status
        run.created_count = created
        run.unchanged_count = unchanged
        run.failed_count = failed
        run.finished_at = finished_at

        for result in results:
            db.add(
                CollectionAttempt(
                    run_id=run.id,
                    listing_id=result.listing_id,
                    retailer=result.retailer,
                    status=result.status,
                    price=result.price,
                    currency=result.currency,
                    observation_id=result.observation_id,
                    message=result.message,
                    duration_ms=result.duration_ms,
                )
            )
        db.commit()

        return CollectionRunResult(
            run_id=run.id,
            requested=len(results),
            created=created,
            unchanged=unchanged,
            failed=failed,
            status=run_status,
            started_at=started_at,
            finished_at=finished_at,
            results=results,
        )
    except BaseException:
        db.rollback()
        run = db.get(CollectionRun, run.id)
        if run is not None:
            run.status = "failed"
            run.failed_count = run.requested_count
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
        raise


def _run_statement():
    """attempt를 함께 읽는 실행 조회문을 한곳에서 구성한다."""
    return select(CollectionRun).options(
        selectinload(CollectionRun.attempts)
    )


@router.get(
    "/collection-runs",
    response_model=list[CollectionRunRead],
)
def list_collection_runs(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[CollectionRun]:
    """최근 수집 실행을 최신순으로 반환한다."""
    statement = (
        _run_statement()
        .order_by(CollectionRun.started_at.desc(), CollectionRun.id.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).all())


@router.get(
    "/collection-runs/latest",
    response_model=CollectionRunRead | None,
)
def get_latest_collection_run(db: DbSession) -> CollectionRun | None:
    """대시보드가 새로고침 후 복원할 가장 최근 실행을 반환한다."""
    statement = (
        _run_statement()
        .order_by(CollectionRun.started_at.desc(), CollectionRun.id.desc())
        .limit(1)
    )
    return db.scalar(statement)


@router.post("/collection-runs", response_model=CollectionRunResult)
async def collect_all_active_listings(db: DbSession) -> CollectionRunResult:
    """모든 활성 listing을 비동기로 수집한다."""
    statement = (
        select(Listing)
        .where(Listing.is_active.is_(True))
        .order_by(Listing.id)
    )
    listings = list(db.scalars(statement).all())
    return await _execute_collection(listings, db)


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

    return await _execute_collection([listing], db)
