# Data model

## Relationship

```text
products 1 --- N listings 1 --- N price_observations
                     |
collection_runs 1 --- N collection_attempts
products 1 --- N price_alert_rules 1 --- N price_alert_events
```

- A product represents the item being compared.
- A listing represents that product on one retailer page.
- A price observation records the price seen on that page at a specific time.
- A collection run records one execution across one or more listings.
- A collection attempt records each retailer result and request duration.
- An alert rule stores a product target price.
- An alert event records one observation that met a rule.

## `products`

| Column | Type | Rules | Purpose |
|---|---|---|---|
| `id` | integer | primary key | Internal product identifier |
| `name` | varchar(255) | required | Canonical product name |
| `brand` | varchar(100) | optional | Product brand |
| `model_number` | varchar(100) | optional | Manufacturer model number |
| `created_at` | timestamptz | required | Creation time |

The MVP does not assume that a product has a model number. If one is provided,
it can later be used for validation or product matching.

## `listings`

| Column | Type | Rules | Purpose |
|---|---|---|---|
| `id` | integer | primary key | Internal listing identifier |
| `product_id` | integer | foreign key, required | Related product |
| `retailer` | varchar(100) | required | Retailer name |
| `url` | text | unique, required | Product page to collect |
| `currency` | char(3) | required | ISO currency code such as `GBP` |
| `is_active` | boolean | required, default `true` | Whether collection is enabled |
| `created_at` | timestamptz | required | Creation time |

The listing is separated from the product because one product can appear on
multiple retailer pages.

## `price_observations`

| Column | Type | Rules | Purpose |
|---|---|---|---|
| `id` | integer | primary key | Internal observation identifier |
| `listing_id` | integer | foreign key, required | Listing that was observed |
| `price` | numeric(12,2) | required, greater than zero | Collected price |
| `observed_at` | timestamptz | required | Time the price was observed |
| `created_at` | timestamptz | required | Time the row was stored |

`price` uses a decimal database type rather than a floating-point type so that
currency calculations remain exact.

### Duplicate rule

The initial rule is:

```text
Do not insert a new row when the latest observation for the listing has the
same price.
```

This records price changes rather than filling the database with an identical
price on every scheduled run. A later version could record every observation
if collection-frequency auditing becomes important.

## `collection_runs`

| Column | Type | Rules | Purpose |
|---|---|---|---|
| `id` | integer | primary key | Collection execution identifier |
| `status` | varchar(20) | required | Running, completed, partial, or failed |
| `requested_count` | integer | non-negative | Number of listings requested |
| `created_count` | integer | non-negative | New price observations |
| `unchanged_count` | integer | non-negative | Successful unchanged prices |
| `failed_count` | integer | non-negative | Failed retailer attempts |
| `started_at` | timestamptz | required | Execution start time |
| `finished_at` | timestamptz | optional | Execution completion time |

## `collection_attempts`

| Column | Type | Rules | Purpose |
|---|---|---|---|
| `id` | integer | primary key | Individual attempt identifier |
| `run_id` | integer | foreign key, required | Parent collection run |
| `listing_id` | integer | foreign key, optional | Retailer listing |
| `retailer` | varchar(100) | required | Snapshot of retailer name |
| `status` | varchar(20) | required | Created, unchanged, or failed |
| `price` | numeric(12,2) | optional | Price returned by the scraper |
| `currency` | char(3) | optional | Price currency |
| `observation_id` | integer | foreign key, optional | Related stored observation |
| `message` | text | required | Human-readable result or error |
| `duration_ms` | integer | required | Retailer request duration |

Attempt rows preserve operational evidence even when an unchanged price does
not create a new `price_observations` row.

## `price_alert_rules`

| Column | Type | Rules | Purpose |
|---|---|---|---|
| `id` | integer | primary key | Target-price rule identifier |
| `product_id` | integer | foreign key, required | Product being monitored |
| `target_price` | numeric(12,2) | required, greater than zero | Trigger threshold |
| `currency` | char(3) | required | Rule currency |
| `is_active` | boolean | required | Whether the rule is evaluated |
| `created_at` | timestamptz | required | Rule creation time |

## `price_alert_events`

| Column | Type | Rules | Purpose |
|---|---|---|---|
| `id` | integer | primary key | Triggered-event identifier |
| `rule_id` | integer | foreign key, required | Rule that matched |
| `listing_id` | integer | foreign key, optional | Retailer listing |
| `observation_id` | integer | foreign key, optional | Matching observation |
| `retailer` | varchar(100) | required | Retailer snapshot |
| `observed_price` | numeric(12,2) | required | Price that matched |
| `target_price` | numeric(12,2) | required | Target snapshot |
| `currency` | char(3) | required | Event currency |
| `triggered_at` | timestamptz | required | Match time |
| `acknowledged_at` | timestamptz | optional | User confirmation time |

The `(rule_id, observation_id)` unique constraint prevents repeated scheduler
runs from generating duplicate events for the same stored price observation.

## Statistics

Statistics are calculated per product, listing, and requested period:

- Latest price
- Minimum price
- Maximum price
- Average price
- Difference from the previous recorded price
- Percentage change from the previous recorded price
