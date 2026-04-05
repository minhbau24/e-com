"""Import product data from the source CSV into search_products."""

from __future__ import annotations

import argparse
import csv
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import execute_values


DEFAULT_SOURCE_CSV = Path(__file__).resolve().parents[2] / "e-com-service" / "data" / "product.csv"
DEFAULT_SEARCH_TABLE = "search_products"
BATCH_SIZE = 500


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    without_punctuation = re.sub(r"[^\w\s]", " ", without_accents.lower())
    return " ".join(without_punctuation.split())


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.replace("\r", " ").replace("\n", " ").split())


def extract_label_values(text: str | None, patterns: dict[str, list[str]]) -> dict[str, str]:
    if not text:
        return {}

    label_lookup: dict[str, str] = {}
    label_parts: list[str] = []
    for field_name, aliases in patterns.items():
        for alias in aliases:
            label_lookup[alias.casefold()] = field_name
            label_parts.append(re.escape(alias))

    if not label_parts:
        return {}

    regex = re.compile(rf"(?P<label>{'|'.join(label_parts)})\s*:\s*", re.IGNORECASE)
    matches = list(regex.finditer(text))
    if not matches:
        return {}

    extracted: dict[str, str] = {}
    for index, match in enumerate(matches):
        field_name = label_lookup.get(match.group("label").casefold())
        if not field_name or field_name in extracted:
            continue

        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        value = clean_text(text[start:end]).strip("-–—. ")
        value = re.split(r"\s*-{5,}\s*", value, maxsplit=1)[0].strip()
        if value:
            extracted[field_name] = value

    return extracted


def extract_year(text: str | None) -> int | None:
    if not text:
        return None
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    if year_match:
        return int(year_match.group(1))
    publication_match = re.search(r"Publication date:\s*([^\n|]+)", text, re.IGNORECASE)
    if publication_match:
        publication_text = publication_match.group(1)
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", publication_text)
        if year_match:
            return int(year_match.group(1))
    return None


def normalize_cover_type(value: str | None) -> str | None:
    if not value:
        return None
    lowered = value.lower()
    if "hard" in lowered or "bìa cứng" in lowered:
        return "Bìa cứng"
    if "paper" in lowered or "bìa mềm" in lowered or "paperback" in lowered:
        return "Bìa mềm"
    if "board" in lowered:
        return "Bìa cứng"
    return clean_text(value)


@dataclass
class ParsedProduct:
    product_id: str
    name: str
    normalized_name: str
    price: int | None
    rating: float | None
    review_count: int | None
    stock: int | None
    category: str | None
    content: str | None
    author: str | None
    publisher: str | None
    publication_year: int | None
    language: str | None
    cover_type: str | None
    page_count: int | None
    created_at: datetime


def infer_language(text: str | None) -> str | None:
    if not text:
        return None
    if re.search(r"Ngôn ngữ:\s*Tiếng\s*Anh", text, re.IGNORECASE):
        return "Tiếng Anh"
    if re.search(r"Language:\s*English", text, re.IGNORECASE):
        return "Tiếng Anh"
    if re.search(r"Ngôn ngữ:\s*Tiếng\s*Việt", text, re.IGNORECASE):
        return "Tiếng Việt"
    return None


def extract_page_count(text: str | None) -> int | None:
    if not text:
        return None
    page_match = re.search(r"Số trang:\s*(\d+)", text, re.IGNORECASE)
    if page_match:
        return int(page_match.group(1))
    page_match = re.search(r"(\d+)\s*pages?", text, re.IGNORECASE)
    if page_match:
        return int(page_match.group(1))
    return None


def parse_product_row(row: dict[str, str]) -> ParsedProduct:
    short_description = clean_text(row.get("short_description"))
    description = clean_text(row.get("description"))
    combined_content = " ".join(part for part in [short_description, description] if part)

    metadata = extract_label_values(
        combined_content,
        {
            "author": ["Tác giả", "Author"],
            "publisher": ["Nhà xuất bản", "Publisher", "Công ty phát hành"],
            "cover_type": ["Loại bìa", "Format"],
        },
    )
    author = metadata.get("author")
    publisher = metadata.get("publisher")
    cover_type = normalize_cover_type(metadata.get("cover_type"))
    language = infer_language(combined_content)
    publication_year = extract_year(combined_content)
    page_count = extract_page_count(combined_content)

    price = row.get("price")
    rating = row.get("rating_average")
    review_count = row.get("review_count")
    stock = row.get("stock")
    category = "Books"

    return ParsedProduct(
        product_id=row["id"],
        name=clean_text(row.get("name")),
        normalized_name=normalize_text(row.get("name")),
        price=int(price) if price else None,
        rating=float(rating) if rating not in {None, ""} else None,
        review_count=int(review_count) if review_count else None,
        stock=int(stock) if stock else None,
        category=category,
        content=combined_content or None,
        author=author,
        publisher=publisher,
        publication_year=publication_year,
        language=language,
        cover_type=cover_type,
        page_count=page_count,
        created_at=datetime.now(timezone.utc),
    )


def load_rows(source_csv: Path, limit: int | None = None) -> list[ParsedProduct]:
    with source_csv.open("r", encoding="utf-8-sig", newline="") as file_handle:
        reader = csv.DictReader(file_handle)
        rows: list[ParsedProduct] = []
        for index, row in enumerate(reader):
            if limit is not None and limit > 0 and index >= limit:
                break
            rows.append(parse_product_row(row))
        return rows


def upsert_rows(database_url: str, table_name: str, rows: list[ParsedProduct]) -> int:
    if not rows:
        return 0

    insert_sql = f"""
        INSERT INTO {table_name} (
            product_id,
            name,
            normalized_name,
            price,
            rating,
            review_count,
            stock,
            category,
            content,
            author,
            publisher,
            publication_year,
            language,
            cover_type,
            page_count,
            created_at
        ) VALUES %s
        ON CONFLICT (product_id) DO UPDATE SET
            name = EXCLUDED.name,
            normalized_name = EXCLUDED.normalized_name,
            price = EXCLUDED.price,
            rating = EXCLUDED.rating,
            review_count = EXCLUDED.review_count,
            stock = EXCLUDED.stock,
            category = EXCLUDED.category,
            content = EXCLUDED.content,
            author = EXCLUDED.author,
            publisher = EXCLUDED.publisher,
            publication_year = EXCLUDED.publication_year,
            language = EXCLUDED.language,
            cover_type = EXCLUDED.cover_type,
            page_count = EXCLUDED.page_count,
            created_at = EXCLUDED.created_at
    """

    payload = [
        (
            row.product_id,
            row.name,
            row.normalized_name,
            row.price,
            row.rating,
            row.review_count,
            row.stock,
            row.category,
            row.content,
            row.author,
            row.publisher,
            row.publication_year,
            row.language,
            row.cover_type,
            row.page_count,
            row.created_at,
        )
        for row in rows
    ]

    with psycopg2.connect(database_url) as connection:
        with connection.cursor() as cursor:
            execute_values(cursor, insert_sql, payload, page_size=BATCH_SIZE)
        connection.commit()

    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import source CSV into search_products.")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE_CSV), help="Source product CSV path")
    parser.add_argument("--limit", type=int, default=0, help="Optional max rows to import (0 means all)")
    parser.add_argument(
        "--database-url",
        default=os.getenv("POSTGRES_URL", ""),
        help="PostgreSQL connection string",
    )
    parser.add_argument(
        "--table",
        default=os.getenv("SEARCH_PRODUCTS_TABLE", DEFAULT_SEARCH_TABLE),
        help="Target table name",
    )
    args = parser.parse_args()

    source_csv = Path(args.source)
    if not source_csv.exists():
        raise SystemExit(f"Source CSV not found: {source_csv}")
    if not args.database_url:
        raise SystemExit("POSTGRES_URL is required")

    import_limit = args.limit if args.limit and args.limit > 0 else None
    rows = load_rows(source_csv, limit=import_limit)
    inserted = upsert_rows(args.database_url, args.table, rows)
    print(f"Imported {inserted} products into {args.table}")


if __name__ == "__main__":
    main()
