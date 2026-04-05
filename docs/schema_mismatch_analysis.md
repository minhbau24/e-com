# Schema Mismatch Analysis (product.csv vs current microservices)

## 1) Dataset Profile

Source: product.csv

- Rows: 65
- Columns: 14
- Column list:
  - id
  - name
  - price
  - short_description
  - description
  - rating_average
  - review_count
  - image_base_url
  - image_large_url
  - image_medium_url
  - image_small_url
  - image_thumbnail_url
  - stock
  - quantity_sold

Type inference from CSV:
- id: integer (int64)
- name: string
- price: integer (currency-like)
- short_description: string
- description: string
- rating_average: decimal/float
- review_count: integer
- image_*_url: string (often comma-separated list in one cell)
- stock: integer-like, with 1 missing value
- quantity_sold: integer

Missing values:
- stock: 1 / 65 (1.54%)
- all other fields: 0

## 2) Service Ownership Detection

Dataset is product-centric and belongs primarily to:
- book-service: core product attributes
- catalog-service: derived category/tag projection

Not directly belonging to:
- cart-service, order-service, pay-service, ship-service, customer-service
  - these consume product ids via APIs, not product master data

Note on clothes-service:
- Current workspace does not contain clothes-service.
- If mixed product domains are expected, add product_type/category routing in ingestion and send non-book rows to clothes-service API when that service exists.

## 3) Mismatch With Existing DB Schema

Current book-service Book model before fix:
- title, author, isbn, price, stock, description

CSV fields missing in DB schema:
- external product id (id)
- short_description
- rating_average
- review_count
- quantity_sold
- all image URL fields

Type mismatches / constraint mismatches:
- CSV id is large integer; DB had only auto id and no external_id
- CSV price is int-like; DB price Decimal is compatible via cast
- CSV stock has null; DB stock default int is compatible if null handling is added
- CSV has no isbn; DB required isbn unique (causes insert failure without transformation)
- CSV has no author; DB required author (causes insert failure without transformation)

Redundant/normalization opportunities:
- 5 separate image URL columns can be normalized into a ProductImage table (future, optional)
- category/brand do not exist explicitly in CSV columns; can be inferred from text and normalized in catalog-service

## 4) Proposed Non-Breaking Fixes

Implemented in book-service model (additive + relaxed fields):
- Add external_id (unique, nullable)
- Keep existing fields, relax author/isbn to optional defaults
- Add short_description, rating_average, review_count, quantity_sold
- Add image_base_url/image_large_url/image_medium_url/image_small_url/image_thumbnail_url
- Add source_category/source_brand (for simple normalization feed)
- Add indexes on title and source_category

Compatibility rationale:
- Existing API paths remain unchanged
- Existing fields are still present
- New fields are additive and optional for old clients

## 5) CSV -> Service Data Mapping

| CSV Column | Target Service | Target Table/Field | Rule |
|---|---|---|---|
| id | book-service | Book.external_id | int parse |
| name | book-service | Book.title | trim, max 200 |
| price | book-service | Book.price | int/str -> Decimal |
| short_description | book-service | Book.short_description | trim |
| description | book-service | Book.description | trim |
| rating_average | book-service | Book.rating_average | float -> Decimal(3,1) |
| review_count | book-service | Book.review_count | int parse |
| image_base_url | book-service | Book.image_base_url | split by comma, keep first URL |
| image_large_url | book-service | Book.image_large_url | split by comma, keep first URL |
| image_medium_url | book-service | Book.image_medium_url | split by comma, keep first URL |
| image_small_url | book-service | Book.image_small_url | split by comma, keep first URL |
| image_thumbnail_url | book-service | Book.image_thumbnail_url | split by comma, keep first URL |
| stock | book-service | Book.stock | null -> 0 |
| quantity_sold | book-service | Book.quantity_sold | int parse |
| derived from name+description | catalog-service | CatalogEntry.category | keyword-based category inference |
| derived from description | catalog-service | CatalogEntry.tags | publisher/brand extraction |

Additional fallback transformations:
- author: infer from description patterns; fallback "Unknown"
- isbn: generated stable fallback "CSV-{external_id}" when absent

## 6) Import Strategy

Implemented importer: scripts/import_products.py

Behavior:
- Reads CSV
- Applies transformation rules
- Upserts records into book-service via REST:
  - GET /books/
  - POST /books/
  - PUT /books/{id}/
- Optionally writes catalog projection to catalog-service via POST /catalog/

Run example:

```bash
python scripts/import_products.py --csv product.csv --book-url http://localhost:8002 --catalog-url http://localhost:8008
```

Skip catalog write:

```bash
python scripts/import_products.py --csv product.csv --book-url http://localhost:8002 --no-catalog
```

## 7) Optional SQL Alternative (if not using Django migrations)

Use Django migrations for SQLite safety. If needed, equivalent SQL should be generated from migration tooling per environment.
