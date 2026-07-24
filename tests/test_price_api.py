from decimal import Decimal

from fastapi.testclient import TestClient

from app.models.listing import Listing
from app.scrapers.base import ScrapedProduct
from app.services import collection as collection_service

PRODUCT = {
    "name": "Apple iPhone 17 256GB Black",
    "brand": "Apple",
    "model_number": "MG6J4QN/A",
}

LISTINGS = (
    {
        "retailer": "Apple UK",
        "url": (
            "https://www.apple.com/uk/shop/buy-iphone/iphone-17/"
            "6.3-inch-display-256gb-black"
        ),
        "currency": "GBP",
    },
    {
        "retailer": "John Lewis",
        "url": (
            "https://www.johnlewis.com/apple-iphone-17-ios-6-3-inch-5g-"
            "sim-free-256gb/black/p114322975"
        ),
        "currency": "GBP",
    },
    {
        "retailer": "Laptops Direct",
        "url": (
            "https://www.laptopsdirect.co.uk/apple-iphone-17-black-6.3-"
            "256gb-5g-unlocked-sim-free-smartphone-mg6j4qn-a/version.asp"
        ),
        "currency": "GBP",
    },
)


def _create_product_and_listings(client: TestClient) -> tuple[int, list[int]]:
    product_response = client.post("/api/v1/products", json=PRODUCT)
    assert product_response.status_code == 201
    product_id = product_response.json()["id"]

    listing_ids = []
    for listing in LISTINGS:
        response = client.post(
            f"/api/v1/products/{product_id}/listings",
            json=listing,
        )
        assert response.status_code == 201
        listing_ids.append(response.json()["id"])

    return product_id, listing_ids


def test_collection_stores_prices_and_prevents_duplicates(
    client: TestClient,
    monkeypatch,
) -> None:
    product_id, listing_ids = _create_product_and_listings(client)
    prices = {
        "Apple UK": Decimal("799.00"),
        "John Lewis": Decimal("799.00"),
        "Laptops Direct": Decimal("749.00"),
    }

    async def fake_scrape_listing(listing: Listing, _) -> ScrapedProduct:
        return ScrapedProduct(
            retailer=listing.retailer,
            title=PRODUCT["name"],
            price=prices[listing.retailer],
            currency=listing.currency,
            url=listing.url,
        )

    monkeypatch.setattr(
        collection_service,
        "_scrape_listing",
        fake_scrape_listing,
    )

    first_run = client.post("/api/v1/collection-runs")
    assert first_run.status_code == 200
    assert first_run.json()["created"] == 3
    assert first_run.json()["failed"] == 0

    second_run = client.post("/api/v1/collection-runs")
    assert second_run.status_code == 200
    assert second_run.json()["unchanged"] == 3

    history = client.get(
        f"/api/v1/products/{product_id}/prices/history",
        params={"days": 30},
    )
    assert history.status_code == 200
    assert len(history.json()["observations"]) == 3

    current = client.get(f"/api/v1/products/{product_id}/prices/current")
    assert current.status_code == 200
    current_prices = {
        item["retailer"]: item["price"]
        for item in current.json()["prices"]
    }
    assert current_prices == {
        "Apple UK": "799.00",
        "John Lewis": "799.00",
        "Laptops Direct": "749.00",
    }

    # Laptops Direct 가격만 변경한 뒤 해당 listing 하나를 다시 수집한다.
    prices["Laptops Direct"] = Decimal("729.00")
    changed_run = client.post(
        f"/api/v1/listings/{listing_ids[2]}/collection-runs"
    )
    assert changed_run.status_code == 200
    assert changed_run.json()["created"] == 1

    statistics = client.get(
        f"/api/v1/products/{product_id}/statistics",
        params={"days": 30},
    )
    assert statistics.status_code == 200
    laptops_stats = next(
        item
        for item in statistics.json()["listings"]
        if item["retailer"] == "Laptops Direct"
    )
    assert laptops_stats["observation_count"] == 2
    assert laptops_stats["latest_price"] == "729.00"
    assert laptops_stats["previous_price"] == "749.00"
    assert laptops_stats["absolute_change"] == "-20.00"
    assert laptops_stats["percentage_change"] == "-2.67"


def test_listing_validation_and_conflicts(client: TestClient) -> None:
    product_id, _ = _create_product_and_listings(client)

    duplicate = client.post(
        f"/api/v1/products/{product_id}/listings",
        json=LISTINGS[0],
    )
    assert duplicate.status_code == 409

    missing_product = client.post(
        "/api/v1/products/9999/listings",
        json={
            "retailer": "Example",
            "url": "https://example.com/product/1",
            "currency": "GBP",
        },
    )
    assert missing_product.status_code == 404


def test_unsupported_listing_is_reported_without_crashing(
    client: TestClient,
) -> None:
    product = client.post("/api/v1/products", json=PRODUCT).json()
    listing = client.post(
        f"/api/v1/products/{product['id']}/listings",
        json={
            "retailer": "Unsupported Store",
            "url": "https://example.com/product/iphone-17",
            "currency": "GBP",
        },
    )
    assert listing.status_code == 201

    collection = client.post("/api/v1/collection-runs")

    assert collection.status_code == 200
    assert collection.json()["failed"] == 1
    assert collection.json()["results"][0]["status"] == "failed"
