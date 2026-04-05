# API Simulation Flow (Gateway-Only)

## 1) Flow Diagram (Text)

```text
CSV products + synthetic users
        |
        v
[API Gateway :8000]
  |-- POST /books/ ------------------------------> [book-service]
  |                                                 (create product: books + clothes category)
  |
  |-- POST /customers/ --------------------------> [customer-service]
  |                                                 |-- POST /carts/ --> [cart-service]
  |                                                 (auto cart creation)
  |
  |-- GET /api/cart/carts/ ----------------------> [cart-service]
  |
  |-- POST /api/cart/cart-items/ ----------------> [cart-service]
  |                                                 |-- GET /books/{id}/validate/ -> [book-service]
  |
  |-- POST /orders/ -----------------------------> [order-service]
  |                                                 |-- GET /carts/{id}/ + /cart-items/ -> [cart-service]
  |                                                 |-- POST /payments/ -> [pay-service]
  |                                                 |-- POST /shipments/ -> [ship-service]
  |
  |-- POST /api/comment-rate/reviews/ -----------> [comment-rate-service]
  |
  |-- GET /api/recommender-ai/recommendations/{customer_id}/ -> [recommender-ai-service]
```

## 2) API Call Sequence

All calls go through API Gateway base URL:
- `http://localhost:8000`

### Step A: Create products (book + clothes)
1. `POST /books/`
2. Request body example:

```json
{
  "external_id": 278805060,
  "title": "Bathrooms: Architecture Today",
  "author": "Unknown",
  "isbn": "CSV-278805060",
  "price": "780000",
  "stock": 1000,
  "short_description": "...",
  "description": "...",
  "rating_average": "0",
  "review_count": 0,
  "quantity_sold": 0,
  "image_base_url": "https://...",
  "image_large_url": "https://...",
  "image_medium_url": "https://...",
  "image_small_url": "https://...",
  "image_thumbnail_url": "https://...",
  "source_category": "books",
  "source_brand": "unknown"
}
```

For clothes simulation, keep same endpoint and set:
- `source_category: "clothes"`

### Step B: Register customer (cart auto-created)
1. `POST /customers/`
2. Body example:

```json
{
  "name": "Alice Nguyen",
  "email": "alice_1@example.com",
  "address": "District 1, HCM City"
}
```

### Step C: Get customer cart id
1. `GET /api/cart/carts/`
2. Find row where `customer_id == created_customer_id`

### Step D: Add items to cart
1. `POST /api/cart/cart-items/`
2. Body example:

```json
{
  "cart": 1,
  "book_id": 5,
  "quantity": 2
}
```

### Step E: Create order (payment + shipment trigger)
1. `POST /orders/`
2. Body example:

```json
{
  "customer_id": 1,
  "cart_id": 1,
  "address": "District 1, HCM City"
}
```

Expected behavior:
- order-service calls pay-service and ship-service internally
- order response includes `payment_status` and `shipment_status`

### Step F: Add ratings
1. `POST /api/comment-rate/reviews/`
2. Body example:

```json
{
  "customer_id": 1,
  "book_id": 5,
  "rating": 4,
  "comment": "Good quality and fast shipping"
}
```

### Step G: Get recommendations (optional validation)
1. `GET /api/recommender-ai/recommendations/1/`

## 3) Notes

- No direct DB access.
- Strict business flow is preserved: customer -> cart -> order -> payment/shipment.
- API retries and structured logs are implemented in the simulation script.
