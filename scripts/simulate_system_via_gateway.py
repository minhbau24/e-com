import argparse
import csv
import random
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


@dataclass
class Config:
    gateway_url: str
    csv_path: Path
    users: int
    products: int
    min_items: int
    max_items: int
    orders_per_user: int
    max_retries: int
    retry_delay: float
    timeout: int
    seed: int


class ApiClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.session = requests.Session()

    def log(self, level: str, message: str, data: Optional[Dict[str, Any]] = None):
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        suffix = f" | {data}" if data else ""
        print(f"[{ts}] [{level}] {message}{suffix}")

    def request(self, method: str, path: str, json_body: Optional[Dict[str, Any]] = None) -> Optional[requests.Response]:
        url = f"{self.cfg.gateway_url.rstrip('/')}/{path.lstrip('/')}"
        for attempt in range(1, self.cfg.max_retries + 1):
            try:
                resp = self.session.request(method=method.upper(), url=url, json=json_body, timeout=self.cfg.timeout)
                if resp.status_code >= 500 and attempt < self.cfg.max_retries:
                    self.log("WARN", "Server error, retrying", {"path": path, "status": resp.status_code, "attempt": attempt})
                    time.sleep(self.cfg.retry_delay * attempt)
                    continue
                return resp
            except requests.RequestException as exc:
                if attempt < self.cfg.max_retries:
                    self.log("WARN", "Network error, retrying", {"path": path, "attempt": attempt, "error": str(exc)})
                    time.sleep(self.cfg.retry_delay * attempt)
                    continue
                self.log("ERROR", "Request failed after retries", {"path": path, "error": str(exc)})
                return None
        return None

    @staticmethod
    def to_json(resp: Optional[requests.Response]) -> Dict[str, Any]:
        if resp is None:
            return {}
        try:
            return resp.json()
        except ValueError:
            return {"raw": resp.text}


def parse_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or str(value).strip() == "":
            return default
        return int(float(str(value).strip()))
    except Exception:
        return default


def pick_first_url(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text.split(",")[0].strip()


def infer_category(name: str, idx: int) -> str:
    # Force a mixed catalog simulation: ~25% clothes.
    if idx % 4 == 0:
        return "clothes"
    lowered = name.lower()
    if "book" in lowered or "sách" in lowered:
        return "books"
    return "books"


def resolve_default_csv(root_dir: Path) -> Path:
    candidates = [
        root_dir / "product.csv",
        root_dir / "e-com-service" / "data" / "product.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_products_from_csv(csv_path: Path, limit: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if limit > 0 and i >= limit:
                break
            ext_id = parse_int(row.get("id"), i + 1)
            title = str(row.get("name") or f"Product {i+1}").strip()[:200]
            category = infer_category(title, i)
            payload = {
                "external_id": ext_id,
                "title": title,
                "author": "Unknown",
                "isbn": f"CSV-{ext_id}"[:40],
                "price": str(parse_int(row.get("price"), 0)),
                "stock": parse_int(row.get("stock"), 1000),
                "short_description": str(row.get("short_description") or "").strip(),
                "description": str(row.get("description") or "").strip(),
                "rating_average": str(row.get("rating_average") or "0"),
                "review_count": parse_int(row.get("review_count"), 0),
                "quantity_sold": parse_int(row.get("quantity_sold"), 0),
                "image_base_url": pick_first_url(row.get("image_base_url")),
                "image_large_url": pick_first_url(row.get("image_large_url")),
                "image_medium_url": pick_first_url(row.get("image_medium_url")),
                "image_small_url": pick_first_url(row.get("image_small_url")),
                "image_thumbnail_url": pick_first_url(row.get("image_thumbnail_url")),
                "source_category": category,
                "source_brand": "unknown",
            }
            rows.append(payload)
    return rows


def create_products(client: ApiClient, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    created: List[Dict[str, Any]] = []
    for p in products:
        resp = client.request("POST", "/books/", json_body=p)
        data = client.to_json(resp)
        if resp is not None and resp.status_code < 400:
            created.append(data)
            client.log("INFO", "Product created", {"id": data.get("id"), "title": data.get("title"), "category": data.get("source_category")})
        else:
            client.log("ERROR", "Product creation failed", {"status": getattr(resp, "status_code", None), "payload_title": p.get("title")})
    return created


def create_customers(client: ApiClient, users: int) -> List[Dict[str, Any]]:
    customers: List[Dict[str, Any]] = []
    for i in range(users):
        body = {
            "name": f"SimUser {i+1}",
            "email": f"sim_user_{int(time.time())}_{i+1}@example.com",
            "address": f"Street {i+1}, HCM City",
        }
        resp = client.request("POST", "/customers/", json_body=body)
        data = client.to_json(resp)
        if resp is not None and resp.status_code < 400:
            # customer-service may return wrapped payload when cart warning occurs.
            customer = data.get("customer", data)
            customers.append(customer)
            client.log("INFO", "Customer created", {"customer_id": customer.get("id"), "email": customer.get("email")})
        else:
            client.log("ERROR", "Customer creation failed", {"status": getattr(resp, "status_code", None), "body": data})
    return customers


def fetch_cart_map(client: ApiClient) -> Dict[int, int]:
    cart_map: Dict[int, int] = {}
    resp = client.request("GET", "/api/cart/carts/")
    data = client.to_json(resp)
    if resp is None or resp.status_code >= 400 or not isinstance(data, list):
        client.log("ERROR", "Cannot fetch carts", {"status": getattr(resp, "status_code", None), "body": data})
        return cart_map

    for row in data:
        cid = row.get("customer_id")
        cart_id = row.get("id")
        if isinstance(cid, int) and isinstance(cart_id, int):
            cart_map[cid] = cart_id
    client.log("INFO", "Cart map ready", {"count": len(cart_map)})
    return cart_map


def add_items_to_cart(client: ApiClient, cart_id: int, product_ids: List[int], min_items: int, max_items: int):
    item_count = random.randint(min_items, max_items)
    chosen = random.sample(product_ids, k=min(item_count, len(product_ids)))
    for pid in chosen:
        qty = random.randint(1, 3)
        body = {"cart": cart_id, "book_id": pid, "quantity": qty}
        resp = client.request("POST", "/api/cart/cart-items/", json_body=body)
        data = client.to_json(resp)
        if resp is not None and resp.status_code < 400:
            client.log("INFO", "Cart item added", {"cart_id": cart_id, "book_id": pid, "qty": qty})
        else:
            client.log("WARN", "Cart item failed", {"cart_id": cart_id, "book_id": pid, "status": getattr(resp, "status_code", None), "body": data})


def create_order(client: ApiClient, customer_id: int, cart_id: int, address: str) -> Optional[Dict[str, Any]]:
    body = {
        "customer_id": customer_id,
        "cart_id": cart_id,
        "address": address,
    }
    resp = client.request("POST", "/orders/", json_body=body)
    data = client.to_json(resp)
    if resp is not None and resp.status_code < 400:
        client.log(
            "INFO",
            "Order created",
            {
                "order_id": data.get("id"),
                "payment_status": data.get("payment_status"),
                "shipment_status": data.get("shipment_status"),
                "status": data.get("status"),
            },
        )
        return data
    client.log("ERROR", "Order creation failed", {"status": getattr(resp, "status_code", None), "body": data})
    return None


def add_ratings(client: ApiClient, customer_id: int, product_ids: List[int]):
    for pid in random.sample(product_ids, k=min(2, len(product_ids))):
        body = {
            "customer_id": customer_id,
            "book_id": pid,
            "rating": random.randint(3, 5),
            "comment": random.choice([
                "Good product",
                "Value for money",
                "Fast shipping",
                "Recommended",
            ]),
        }
        resp = client.request("POST", "/api/comment-rate/reviews/", json_body=body)
        if resp is not None and resp.status_code < 400:
            client.log("INFO", "Rating added", {"customer_id": customer_id, "book_id": pid})
        else:
            client.log("WARN", "Rating failed", {"status": getattr(resp, "status_code", None), "customer_id": customer_id, "book_id": pid})


def run_simulation(cfg: Config):
    random.seed(cfg.seed)
    client = ApiClient(cfg)

    client.log("INFO", "Loading CSV", {"csv": str(cfg.csv_path)})
    products_to_create = load_products_from_csv(cfg.csv_path, cfg.products)
    created_products = create_products(client, products_to_create)
    product_ids = [p.get("id") for p in created_products if isinstance(p.get("id"), int)]

    if not product_ids:
        client.log("ERROR", "No products created. Abort simulation.")
        return

    customers = create_customers(client, cfg.users)
    if not customers:
        client.log("ERROR", "No customers created. Abort simulation.")
        return

    cart_map = fetch_cart_map(client)

    orders_created = 0
    for customer in customers:
        customer_id = customer.get("id")
        address = customer.get("address", "Unknown")
        if not isinstance(customer_id, int):
            continue

        cart_id = cart_map.get(customer_id)
        if not cart_id:
            client.log("WARN", "Cart not found for customer, skipping", {"customer_id": customer_id})
            continue

        for _ in range(cfg.orders_per_user):
            add_items_to_cart(client, cart_id, product_ids, cfg.min_items, cfg.max_items)
            order = create_order(client, customer_id, cart_id, address)
            if order:
                orders_created += 1

        add_ratings(client, customer_id, product_ids)

    client.log("INFO", "Simulation finished", {"customers": len(customers), "products": len(product_ids), "orders": orders_created})


def build_parser() -> argparse.ArgumentParser:
    root_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Gateway-only BookStore microservices simulator")
    parser.add_argument("--gateway", default="http://localhost:8000", help="API Gateway URL")
    parser.add_argument("--csv", "--source", default=str(resolve_default_csv(root_dir)), help="CSV product file")
    parser.add_argument("--users", type=int, default=5, help="Number of users to create")
    parser.add_argument("--products", type=int, default=20, help="Number of products to load from CSV")
    parser.add_argument("--min-items", type=int, default=1, help="Min cart items per order")
    parser.add_argument("--max-items", type=int, default=4, help="Max cart items per order")
    parser.add_argument("--orders-per-user", type=int, default=2, help="Orders per user")
    parser.add_argument("--max-retries", type=int, default=3, help="HTTP retries")
    parser.add_argument("--retry-delay", type=float, default=1.0, help="Base retry delay (seconds)")
    parser.add_argument("--timeout", type=int, default=8, help="HTTP timeout seconds")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    cfg = Config(
        gateway_url=args.gateway,
        csv_path=Path(args.csv),
        users=args.users,
        products=args.products,
        min_items=args.min_items,
        max_items=args.max_items,
        orders_per_user=args.orders_per_user,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
        timeout=args.timeout,
        seed=args.seed,
    )

    if not cfg.csv_path.exists():
        print(f"CSV not found: {cfg.csv_path}")
        raise SystemExit(1)

    run_simulation(cfg)
