import asyncio
from decimal import Decimal
from types import SimpleNamespace

import httpx
from fastapi.testclient import TestClient

from app.api.routes import collection as collection_routes
from app.models.listing import Listing
from app.scheduler import trigger_collection
from app.scrapers.base import ScrapedProduct
from app.services import collection as collection_service


def _create_product_and_listing(client: TestClient) -> tuple[int, int]:
    product = client.post(
        "/api/v1/products",
        json={
            "name": "Apple iPhone 17 256GB Black",
            "brand": "Apple",
            "model_number": "MG6J4QN/A",
        },
    ).json()
    listing = client.post(
        f"/api/v1/products/{product['id']}/listings",
        json={
            "retailer": "Laptops Direct",
            "url": (
                "https://www.laptopsdirect.co.uk/apple-iphone-17-black-"
                "6.3-256gb-5g-unlocked-sim-free-smartphone-mg6j4qn-a/"
                "version.asp"
            ),
            "currency": "GBP",
        },
    ).json()
    return product["id"], listing["id"]


def test_target_price_creates_one_acknowledgeable_event(
    client: TestClient,
    monkeypatch,
) -> None:
    product_id, _ = _create_product_and_listing(client)
    rule = client.post(
        f"/api/v1/products/{product_id}/alert-rules",
        json={"target_price": "760.00", "currency": "gbp"},
    )
    assert rule.status_code == 201
    assert rule.json()["currency"] == "GBP"

    async def fake_scrape(listing: Listing, _) -> ScrapedProduct:
        return ScrapedProduct(
            retailer=listing.retailer,
            title="Apple iPhone 17 256GB Black",
            price=Decimal("749.00"),
            currency="GBP",
            url=listing.url,
        )

    monkeypatch.setattr(collection_service, "_scrape_listing", fake_scrape)

    first_run = client.post("/api/v1/collection-runs")
    assert first_run.status_code == 200
    assert first_run.json()["created"] == 1

    second_run = client.post("/api/v1/collection-runs")
    assert second_run.status_code == 200
    assert second_run.json()["unchanged"] == 1

    events = client.get(
        "/api/v1/alert-events",
        params={"product_id": product_id, "acknowledged": False},
    )
    assert events.status_code == 200
    assert len(events.json()) == 1
    assert events.json()[0]["observed_price"] == "749.00"
    assert events.json()[0]["target_price"] == "760.00"

    acknowledged = client.patch(
        f"/api/v1/alert-events/{events.json()[0]['id']}/acknowledge"
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["acknowledged_at"] is not None


def test_new_rule_is_evaluated_against_existing_latest_price(
    client: TestClient,
    db,
) -> None:
    product_id, listing_id = _create_product_and_listing(client)
    from datetime import datetime, timezone

    from app.models.price_observation import PriceObservation

    db.add(
        PriceObservation(
            listing_id=listing_id,
            price=Decimal("749.00"),
            observed_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    rule = client.post(
        f"/api/v1/products/{product_id}/alert-rules",
        json={"target_price": "750.00"},
    )
    assert rule.status_code == 201

    events = client.get(
        "/api/v1/alert-events",
        params={"product_id": product_id},
    )
    assert len(events.json()) == 1
    assert events.json()[0]["retailer"] == "Laptops Direct"


def test_scheduled_endpoint_requires_configured_key(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        collection_routes,
        "get_settings",
        lambda: SimpleNamespace(collection_api_key="scheduler-secret"),
    )

    assert client.post(
        "/api/v1/internal/scheduled-collection-runs"
    ).status_code == 401
    assert client.post(
        "/api/v1/internal/scheduled-collection-runs",
        headers={"X-Collection-Key": "wrong"},
    ).status_code == 401

    authorised = client.post(
        "/api/v1/internal/scheduled-collection-runs",
        headers={"X-Collection-Key": "scheduler-secret"},
    )
    assert authorised.status_code == 200
    assert authorised.json()["requested"] == 0


def test_scheduler_sends_internal_key(monkeypatch) -> None:
    seen_request = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_request
        seen_request = request
        return httpx.Response(
            200,
            json={
                "run_id": 7,
                "requested": 3,
                "created": 0,
                "unchanged": 3,
                "failed": 0,
            },
        )

    monkeypatch.setattr(
        "app.scheduler.get_settings",
        lambda: SimpleNamespace(
            scheduler_api_url="http://api:8000",
            collection_api_key="scheduler-secret",
        ),
    )

    async def execute() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            await trigger_collection(client)

    asyncio.run(execute())
    assert seen_request is not None
    assert seen_request.url.path.endswith("/scheduled-collection-runs")
    assert seen_request.headers["X-Collection-Key"] == "scheduler-secret"
