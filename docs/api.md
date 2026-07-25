# API contract

Base path:

```text
/api/v1
```

## Create a product

```http
POST /api/v1/products
Content-Type: application/json
```

```json
{
  "name": "Apple AirPods Pro 2",
  "brand": "Apple",
  "model_number": "MTJV3"
}
```

Successful response:

```text
201 Created
```

## List products

```http
GET /api/v1/products
```

Returns products with their registered retailer listings.

## Add a retailer listing

```http
POST /api/v1/products/{product_id}/listings
Content-Type: application/json
```

```json
{
  "retailer": "Example Store",
  "url": "https://example.com/products/airpods-pro-2",
  "currency": "GBP"
}
```

Successful response:

```text
201 Created
```

The API rejects duplicate listing URLs.

## Update a retailer listing

Retailer product pages can move, so an existing listing can be updated without
losing its historical price observations:

```http
PATCH /api/v1/listings/{listing_id}
Content-Type: application/json
```

```json
{
  "url": "https://example.com/products/new-product-page"
}
```

`retailer`, `url`, `currency`, and `is_active` are optional, but the request
must include at least one of them.

## Run collection

Collect every active listing:

```http
POST /api/v1/collection-runs
```

Collect one listing:

```http
POST /api/v1/listings/{listing_id}/collection-runs
```

The server records the observation time. Clients do not provide
`observed_at` during normal scraper collection.

Example response:

```json
{
  "run_id": 42,
  "requested": 3,
  "created": 3,
  "unchanged": 0,
  "failed": 0,
  "status": "completed",
  "started_at": "2026-07-25T20:30:20Z",
  "finished_at": "2026-07-25T20:30:21Z",
  "results": [
    {
      "listing_id": 1,
      "retailer": "Apple UK",
      "status": "created",
      "price": "799.00",
      "currency": "GBP",
      "observation_id": 1,
      "message": "New price observation stored",
      "duration_ms": 469
    }
  ]
}
```

Running collection again without a price change returns `unchanged` and does
not create a duplicate observation.

Collection runs and per-retailer attempts are stored independently of price
changes. This provides an audit trail even when every price is unchanged.

Recent runs:

```http
GET /api/v1/collection-runs?limit=20
```

Latest run, used by the dashboard after a page refresh:

```http
GET /api/v1/collection-runs/latest
```

## Get current prices

```http
GET /api/v1/products/{product_id}/prices/current
```

Example response:

```json
{
  "product_id": 1,
  "prices": [
    {
      "listing_id": 10,
      "retailer": "Example Store",
      "price": "199.99",
      "currency": "GBP",
      "observed_at": "2026-07-23T10:00:00Z"
    }
  ]
}
```

## Get price history

```http
GET /api/v1/products/{product_id}/prices/history?days=30
```

`days` defaults to `30` and must be a positive integer.

## Get price statistics

```http
GET /api/v1/products/{product_id}/statistics?days=30
```

Example response:

```json
{
  "product_id": 1,
  "period_days": 30,
  "listings": [
    {
      "listing_id": 1,
      "retailer": "Apple UK",
      "currency": "GBP",
      "observation_count": 2,
      "minimum_price": "789.00",
      "maximum_price": "799.00",
      "average_price": "794.00",
      "latest_price": "789.00",
      "previous_price": "799.00",
      "absolute_change": "-10.00",
      "percentage_change": "-1.25"
    }
  ]
}
```

## Error responses

The API uses consistent error bodies:

```json
{
  "detail": "Product not found"
}
```

Expected status codes include:

- `400 Bad Request` for invalid input
- `404 Not Found` for unknown resources
- `409 Conflict` for duplicate listing URLs
- `422 Unprocessable Entity` for schema validation failures
