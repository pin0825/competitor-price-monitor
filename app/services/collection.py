import asyncio
from datetime import datetime, timezone
from time import perf_counter

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.listing import Listing
from app.models.price_observation import PriceObservation
from app.schemas.collection import CollectionItemResult
from app.scrapers.base import ScrapedProduct
from app.scrapers.registry import get_scraper_for_url
from app.services.alerts import evaluate_price_alerts

REQUEST_HEADERS = {
    "User-Agent": (
        "CompetitorPriceMonitor/0.1 "
        "(portfolio project; low-frequency requests)"
    )
}


async def _scrape_listing(
    listing: Listing,
    client: httpx.AsyncClient,
) -> ScrapedProduct:
    """scraper 선택까지 개별 작업 안에서 실행해 listing별 실패로 격리한다."""
    scraper = get_scraper_for_url(listing.url)
    return await scraper.scrape(listing.url, client)


async def _timed_scrape_listing(
    listing: Listing,
    client: httpx.AsyncClient,
) -> tuple[ScrapedProduct | None, BaseException | None, int]:
    """성공과 실패 모두에 네트워크 처리 시간을 붙여 반환한다."""
    started = perf_counter()
    try:
        scraped = await _scrape_listing(listing, client)
        return scraped, None, round((perf_counter() - started) * 1000)
    except BaseException as exc:
        return None, exc, round((perf_counter() - started) * 1000)


async def collect_listings(
    listings: list[Listing],
    db: Session,
) -> list[CollectionItemResult]:
    """여러 listing을 동시에 수집한 뒤 결과를 순서대로 DB에 저장한다."""
    if not listings:
        return []

    async with httpx.AsyncClient(
        headers=REQUEST_HEADERS,
        timeout=20,
        follow_redirects=True,
    ) as client:
        # 네트워크 요청은 시간이 오래 걸리므로 세 사이트를 동시에 처리한다.
        tasks = [
            _timed_scrape_listing(listing, client)
            for listing in listings
        ]
        scrape_results = await asyncio.gather(*tasks)

    observed_at = datetime.now(timezone.utc)
    collection_results: list[CollectionItemResult] = []

    # SQLAlchemy의 sync Session은 동시 작업에 안전하지 않으므로
    # 네트워크 수집이 끝난 뒤 DB 쓰기는 하나씩 처리한다.
    for listing, scrape_outcome in zip(listings, scrape_results):
        scraped, error, duration_ms = scrape_outcome
        if error is not None:
            collection_results.append(
                CollectionItemResult(
                    listing_id=listing.id,
                    retailer=listing.retailer,
                    status="failed",
                    message=f"{type(error).__name__}: {error}",
                    duration_ms=duration_ms,
                )
            )
            continue

        assert scraped is not None
        collection_results.append(
            _store_scraped_product(
                db=db,
                listing=listing,
                scraped=scraped,
                observed_at=observed_at,
                duration_ms=duration_ms,
            )
        )

    # 성공한 observation들을 한 transaction으로 확정한다.
    db.commit()
    return collection_results


def _store_scraped_product(
    db: Session,
    listing: Listing,
    scraped: ScrapedProduct,
    observed_at: datetime,
    duration_ms: int,
) -> CollectionItemResult:
    """통화와 중복 가격을 검증하고 필요한 경우 observation을 생성한다."""
    if scraped.currency != listing.currency:
        return CollectionItemResult(
            listing_id=listing.id,
            retailer=listing.retailer,
            status="failed",
            message=(
                f"Currency mismatch: listing={listing.currency}, "
                f"scraped={scraped.currency}"
            ),
            duration_ms=duration_ms,
        )

    latest_statement = (
        select(PriceObservation)
        .where(PriceObservation.listing_id == listing.id)
        .order_by(PriceObservation.observed_at.desc())
        .limit(1)
    )
    latest = db.scalar(latest_statement)

    if latest is not None and latest.price == scraped.price:
        return CollectionItemResult(
            listing_id=listing.id,
            retailer=listing.retailer,
            status="unchanged",
            price=scraped.price,
            currency=scraped.currency,
            observation_id=latest.id,
            message="Latest stored price is unchanged",
            duration_ms=duration_ms,
        )

    observation = PriceObservation(
        listing_id=listing.id,
        price=scraped.price,
        observed_at=observed_at,
    )
    db.add(observation)
    # commit 전에 id를 받아 응답에 넣기 위해 INSERT를 DB로 보낸다.
    db.flush()
    # 새 가격이 목표가를 충족하면 같은 transaction 안에서 알림을 만든다.
    evaluate_price_alerts(db, listing, observation)

    return CollectionItemResult(
        listing_id=listing.id,
        retailer=listing.retailer,
        status="created",
        price=scraped.price,
        currency=scraped.currency,
        observation_id=observation.id,
        message="New price observation stored",
        duration_ms=duration_ms,
    )
