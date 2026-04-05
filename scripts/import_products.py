import argparse
import csv
import os
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

import requests


def clean_text(value: str) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_int(value, default=0):
    text = clean_text(value)
    if not text:
        return default
    try:
        return int(float(text))
    except ValueError:
        return default


def parse_decimal(value, default="0"):
    text = clean_text(value).replace(",", "")
    if not text:
        return Decimal(default)
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return Decimal(default)


def pick_first_url(value: str) -> str:
    text = clean_text(value)
    if not text:
        return ""
    return text.split(",")[0].strip()


def infer_author(short_description: str, description: str) -> str:
    source = f"{clean_text(short_description)} {clean_text(description)}"
    # Matches both "Tac gia" and Vietnamese variants with diacritics.
    match = re.search(r"(?:Tac gia|T\u00e1c gi\u1ea3)\s*:\s*([^\n\r|]+)", source, re.IGNORECASE)
    if match:
        return match.group(1).strip()[:120]
    return "Unknown"


def infer_category(name: str, description: str) -> str:
    text = f"{clean_text(name)} {clean_text(description)}".lower()
    if "architecture" in text or "kien truc" in text or "ki\u1ebfn tr\u00fac" in text:
        return "architecture"
    if "interior" in text:
        return "interior-design"
    if "artbook" in text or "design" in text:
        return "design"
    if "book" in text or "s\u00e1ch" in text:
        return "books"
    return "general"


def infer_brand(description: str) -> str:
    text = clean_text(description)
    match = re.search(r"(?:Nha xuat ban|Nh\u00e0 xu\u1ea5t b\u1ea3n|Publisher)\s*:\s*([^\n\r|]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()[:80]
    return "unknown"


def build_payload(row: dict) -> dict:
    name = clean_text(row.get("name"))
    short_description = clean_text(row.get("short_description"))
    description = clean_text(row.get("description"))

    external_id = parse_int(row.get("id"), default=None)
    isbn_fallback = f"CSV-{external_id}" if external_id is not None else f"CSV-{name[:20]}"

    payload = {
        "external_id": external_id,
        "title": name[:200],
        "author": infer_author(short_description, description),
        "isbn": isbn_fallback[:40],
        "price": str(parse_decimal(row.get("price"), default="0")),
        "stock": parse_int(row.get("stock"), default=0),
        "short_description": short_description,
        "description": description,
        "rating_average": str(parse_decimal(row.get("rating_average"), default="0")),
        "review_count": parse_int(row.get("review_count"), default=0),
        "quantity_sold": parse_int(row.get("quantity_sold"), default=0),
        "image_base_url": pick_first_url(row.get("image_base_url")),
        "image_large_url": pick_first_url(row.get("image_large_url")),
        "image_medium_url": pick_first_url(row.get("image_medium_url")),
        "image_small_url": pick_first_url(row.get("image_small_url")),
        "image_thumbnail_url": pick_first_url(row.get("image_thumbnail_url")),
        "source_category": infer_category(name, description),
        "source_brand": infer_brand(description),
    }
    return payload


def import_books(csv_path: Path, book_service_url: str, catalog_service_url: str = ""):
    created = 0
    updated = 0
    errors = 0

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            payload = build_payload(row)
            ext_id = payload.get("external_id")

            try:
                list_resp = requests.get(f"{book_service_url}/books/", timeout=8)
                list_resp.raise_for_status()
                books = list_resp.json()
                existing = next((b for b in books if b.get("external_id") == ext_id), None)

                if existing:
                    resp = requests.put(
                        f"{book_service_url}/books/{existing['id']}/",
                        json=payload,
                        timeout=8,
                    )
                    if resp.status_code < 400:
                        updated += 1
                    else:
                        errors += 1
                        print(f"[ERROR] update failed external_id={ext_id}: {resp.text}")
                        continue
                    book_id = existing["id"]
                else:
                    resp = requests.post(f"{book_service_url}/books/", json=payload, timeout=8)
                    if resp.status_code < 400:
                        created += 1
                        book_id = resp.json().get("id")
                    else:
                        errors += 1
                        print(f"[ERROR] create failed external_id={ext_id}: {resp.text}")
                        continue

                if catalog_service_url and book_id:
                    catalog_payload = {
                        "book_id": book_id,
                        "category": payload["source_category"],
                        "tags": payload["source_brand"],
                        "is_active": True,
                    }
                    catalog_resp = requests.post(
                        f"{catalog_service_url}/catalog/",
                        json=catalog_payload,
                        timeout=8,
                    )
                    if catalog_resp.status_code >= 400:
                        print(f"[WARN] catalog insert failed book_id={book_id}: {catalog_resp.text}")

            except requests.RequestException as exc:
                errors += 1
                print(f"[ERROR] request failed external_id={ext_id}: {exc}")

    print("--- Import Summary ---")
    print(f"created={created}")
    print(f"updated={updated}")
    print(f"errors={errors}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import product.csv into book-service and optional catalog-service")
    parser.add_argument("--csv", default="product.csv", help="Path to CSV file")
    parser.add_argument("--book-url", default=os.getenv("BOOK_SERVICE_URL", "http://localhost:8002"))
    parser.add_argument("--catalog-url", default=os.getenv("CATALOG_SERVICE_URL", "http://localhost:8008"))
    parser.add_argument("--no-catalog", action="store_true", help="Skip writing to catalog-service")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        sys.exit(1)

    import_books(
        csv_path=csv_path,
        book_service_url=args.book_url.rstrip("/"),
        catalog_service_url="" if args.no_catalog else args.catalog_url.rstrip("/"),
    )
