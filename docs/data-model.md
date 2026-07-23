# Data model

## Relationship

```text
products 1 --- N listings 1 --- N price_observations
```

- A product represents the item being compared.
- A listing represents that product on one retailer page.
- A price observation records the price seen on that page at a specific time.

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

## Statistics

Statistics are calculated per product, listing, and requested period:

- Latest price
- Minimum price
- Maximum price
- Average price
- Difference from the previous recorded price
- Percentage change from the previous recorded price
