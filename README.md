# Competitor Price Monitor

[![CI](https://github.com/pin0825/competitor-price-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/pin0825/competitor-price-monitor/actions/workflows/ci.yml)

A FastAPI service that collects configured retailer prices, stores historical
observations in PostgreSQL, and exposes current prices, history, and statistics.

The included demonstration tracks the same UK product variant across three
retailers:

```text
Apple iPhone 17 / 256GB / Black / SIM-free / GBP
```

## Features

- Extensible site-specific scraper adapters
- Concurrent collection with `HTTPX` and `asyncio`
- Structured product extraction from JSON-LD
- Per-listing failure isolation
- Currency and positive-price validation
- Duplicate prevention when the latest price is unchanged
- Current price, history, and retailer-level statistics endpoints
- Responsive price intelligence dashboard with live collection controls
- PostgreSQL schema migrations with Alembic
- Docker Compose development environment
- Deterministic parser and API integration tests
- Interactive OpenAPI documentation at `/docs`

## Architecture

```text
Manual API request                  Future AWS EventBridge schedule
        |                                      |
        +------------------+-------------------+
                           |
                           v
                  CollectionService
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
          Apple UK     John Lewis   Laptops Direct
             |             |             |
             +------ concurrent HTTP -----+
                           |
                           v
              validation + duplicate check
                           |
                           v
                  PostgreSQL history
                           |
                           v
           FastAPI current/history/statistics
```

Network requests run concurrently, but synchronous SQLAlchemy writes are
performed sequentially because a `Session` is not shared across concurrent
tasks.

## Supported retailers

| Retailer | Extraction method |
|---|---|
| Apple UK | Product JSON-LD |
| John Lewis | Exact URL variant from ProductGroup JSON-LD |
| Laptops Direct | Product node inside JSON-LD `@graph` |

Sites that return access-denied responses are not bypassed. Collection should
remain low-frequency and comply with each site's terms and access policies.

## Quick start with Docker

Prerequisite: Docker Desktop or Docker Engine with Compose.

```bash
docker compose up --build
```

This starts:

- Dashboard on `http://localhost:8000`
- FastAPI on `http://localhost:8000`
- Swagger UI on `http://localhost:8000/docs`
- PostgreSQL on `localhost:5432`
- Alembic migrations before the API server starts

Stop the services with:

```bash
docker compose down
```

The PostgreSQL volume is preserved. Use `docker compose down --volumes` only
when you intentionally want to delete the local database.

## Local development without Docker

Python 3.10 or later is required.

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

$env:DATABASE_URL="sqlite+pysqlite:///./local.db"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

SQLite is provided only as a convenient local and test fallback. PostgreSQL is
the intended application database.

## Example API flow

Create a product:

```http
POST /api/v1/products
```

```json
{
  "name": "Apple iPhone 17 256GB Black",
  "brand": "Apple",
  "model_number": "MG6J4QN/A"
}
```

Attach a retailer page:

```http
POST /api/v1/products/1/listings
```

```json
{
  "retailer": "Apple UK",
  "url": "https://www.apple.com/uk/shop/buy-iphone/iphone-17/6.3-inch-display-256gb-black",
  "currency": "GBP"
}
```

Run collection and query results:

```http
POST /api/v1/collection-runs
GET  /api/v1/products/1/prices/current
GET  /api/v1/products/1/prices/history?days=30
GET  /api/v1/products/1/statistics?days=30
```

The full request and response contract is documented in
[`docs/api.md`](docs/api.md).

## Database model

```text
products 1 --- N listings 1 --- N price_observations
```

- `products`: the canonical item being compared
- `listings`: one retailer page for that product
- `price_observations`: a price seen at a specific time

Prices use `NUMERIC(12, 2)` rather than floating-point values. The database also
enforces a positive-price check constraint. See
[`docs/data-model.md`](docs/data-model.md).

## Tests and code quality

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

The suite covers:

- JSON-LD parsing for all supported retailers
- Correct John Lewis colour-variant selection
- Invalid price and unsupported-domain handling
- Product and listing API validation
- Concurrent collection result storage
- Consecutive duplicate-price prevention
- Price change and percentage calculations
- Per-listing failure isolation

To run a live three-retailer collection without the API:

```powershell
.\.venv\Scripts\python.exe -m scripts.scrape_demo
```

## Scheduling and AWS deployment

The collection logic is separated from its trigger. The API currently exposes a
manual collection endpoint, while a production AWS deployment can invoke the
same operation from EventBridge Scheduler.

```text
EventBridge Scheduler
        |
        v
ECS task or authenticated collection endpoint
        |
        v
Amazon RDS for PostgreSQL
```

This avoids embedding a scheduler in every API replica and accidentally running
the same collection multiple times when the service scales horizontally.

## Project structure

```text
app/
├── api/routes/       FastAPI endpoints
├── core/             environment configuration
├── db/               SQLAlchemy engine and sessions
├── models/           database tables
├── schemas/          request and response models
├── scrapers/         retailer adapters and JSON-LD parsing
└── services/         collection and persistence workflow

alembic/               database migrations
docs/                  API and data-model documentation
scripts/               live scraper demonstration
tests/                 parser and API integration tests
```

## Deliberate scope

This project does not attempt CAPTCHA bypassing, proxy rotation, user
authentication, automatic web-wide product discovery, or AI-based product
matching. Listings are configured explicitly so that price comparisons remain
deterministic and explainable.
