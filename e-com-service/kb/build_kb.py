"""Build a product knowledge base from CSV files.

This script reads product CSV data, normalizes the product text,
extracts useful structured attributes, chunks the text for retrieval,
creates embeddings, and exports both document and embedding artifacts.
"""

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import pandas as pd

try:
    import psycopg2  # type: ignore[import-not-found]
    from psycopg2.extras import execute_values  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency in editor environment
    psycopg2 = None
    execute_values = None

try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency in editor environment
    GoogleGenerativeAIEmbeddings = None

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency in editor environment
    RecursiveCharacterTextSplitter = None

from utils.config import settings
from utils.logging import setup_logging


REQUIRED_COLUMNS = [
    "id",
    "name",
    "price",
    "short_description",
    "description",
    "rating_average",
    "review_count",
    "stock",
    "quantity_sold",
]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
KB_DIR = PROJECT_ROOT / "kb"
DOCUMENTS_PATH = KB_DIR / "documents.json"
EMBEDDINGS_PATH = KB_DIR / "embeddings" / "embeddings.json"

EMBEDDING_MODEL_NAME = "models/gemini-embedding-001"
KB_EMBEDDING_BATCH_SIZE = settings.KB_EMBEDDING_BATCH_SIZE
KB_EMBEDDING_REQUEST_DELAY_SECONDS = settings.KB_EMBEDDING_REQUEST_DELAY_SECONDS
KB_EMBEDDING_MAX_RETRIES = settings.KB_EMBEDDING_MAX_RETRIES
POSTGRES_URL = settings.POSTGRES_URL
KB_VECTOR_TABLE = settings.KB_VECTOR_TABLE
KB_EMBEDDING_DIMENSION = settings.KB_EMBEDDING_DIMENSION
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

ATTRIBUTE_PATTERNS = [
    ("author", ["Tác giả", "Author"]),
    ("publisher", ["Nhà xuất bản", "Publisher"]),
    ("publication_year", ["Năm xuất bản"]),
    ("distributor", ["Công ty phát hành", "Distributor"]),
    ("cover_type", ["Loại bìa", "Cover"]),
    ("page_count", ["Số trang", "Pages"]),
    ("language", ["Ngôn ngữ", "Language"]),
    ("isbn", ["ISBN"]),
    ("dimensions", ["Kích thước", "Dimensions"]),
]

ATTRIBUTE_STOP_PATTERN = re.compile(r"\s*-{5,}\s*")


def concatenate_dataframes() -> pd.DataFrame:
    """Concatenate all CSV files in the configured data folder."""
    folder_data_build_kb = Path(settings.FOLDER_DATA_BUILD_KB)
    if not folder_data_build_kb.is_absolute():
        folder_data_build_kb = PROJECT_ROOT / folder_data_build_kb

    dataframes: List[pd.DataFrame] = []
    logging.info("Starting to concatenate CSV files from %s", folder_data_build_kb)

    for root, _, files in os.walk(folder_data_build_kb):
        for file in files:
            if not file.lower().endswith(".csv"):
                continue

            file_path = Path(root) / file
            dataframe = pd.read_csv(file_path)
            dataframes.append(dataframe)
            logging.info("Loaded CSV: %s (%d rows)", file_path, len(dataframe))

    if not dataframes:
        logging.warning("No CSV file found in %s", folder_data_build_kb)
        return pd.DataFrame()

    combined_df = pd.concat(dataframes, ignore_index=True)
    logging.info("Finished concatenating CSV files. Result has %d rows.", combined_df.shape[0])
    return combined_df


def _clean_text(value: Any) -> str:
    """Normalize text to reduce embedding noise."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""

    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return default
        return int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return default
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def _first_image_url(row: pd.Series) -> str:
    image_raw = row.get("image_base_url", "")
    image_text = _clean_text(image_raw)
    if not image_text:
        return ""

    return image_text.split(",")[0].strip()


def _extract_labeled_value(text: str, label_names: Sequence[str]) -> str:
    if not text:
        return ""

    label_pattern = "|".join(re.escape(label) for label in label_names)
    if not label_pattern:
        return ""

    pattern = re.compile(
        rf"(?:{label_pattern})\s*:\s*(.*?)(?=(?:\s*(?:Tác giả|Author|Nhà xuất bản|Publisher|Năm xuất bản|Công ty phát hành|Distributor|Loại bìa|Cover|Số trang|Pages|Ngôn ngữ|Language|ISBN|Kích thước|Dimensions)\s*:\s*)|$)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return ""

    value = match.group(1)
    value = ATTRIBUTE_STOP_PATTERN.split(value, maxsplit=1)[0]
    return _clean_text(value).strip("-–— .")


def _extract_product_attributes(row: pd.Series) -> Dict[str, Any]:
    raw_text = " ".join(
        [
            _clean_text(row.get("short_description", "")),
            _clean_text(row.get("description", "")),
        ]
    )

    source_text = ATTRIBUTE_STOP_PATTERN.split(raw_text, maxsplit=1)[0]

    attributes: Dict[str, Any] = {}
    for key, labels in ATTRIBUTE_PATTERNS:
        value = _extract_labeled_value(source_text, labels)
        if value:
            attributes[key] = value

    return attributes


def _normalize_name(name: str) -> str:
    normalized = name.lower()
    normalized = re.sub(r"[^a-z0-9\s\u00C0-\u1EF9]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _build_document_text(row: pd.Series, attributes: Dict[str, Any]) -> str:
    name = _clean_text(row.get("name", ""))
    short_description = _clean_text(row.get("short_description", ""))
    description = _clean_text(row.get("description", ""))

    structured_sections: List[str] = [
        f"Product name: {name}" if name else "",
        f"Short description: {short_description}" if short_description else "",
        f"Detailed description: {description}" if description else "",
    ]

    if attributes:
        attributes_text = " | ".join(f"{key}: {value}" for key, value in attributes.items())
        structured_sections.append(f"Extracted attributes: {attributes_text}")

    return "\n".join(section for section in structured_sections if section)


def _row_to_product_document(row: pd.Series) -> Dict[str, Any]:
    product_id = _clean_text(row.get("id", ""))
    attributes = _extract_product_attributes(row)
    name = _clean_text(row.get("name", ""))
    text = _build_document_text(row, attributes)

    metadata = {
        "id": product_id,
        "name": name,
        "normalized_name": _normalize_name(name) if name else "",
        "price": _to_int(row.get("price", 0)),
        "rating_average": _to_float(row.get("rating_average", 0.0)),
        "review_count": _to_int(row.get("review_count", 0)),
        "quantity_sold": _to_int(row.get("quantity_sold", 0)),
        "stock": _to_int(row.get("stock", 0)),
        "image_url": _first_image_url(row),
        "content_type": "book" if attributes else "product",
        **attributes,
    }

    return {
        "doc_id": f"product_{product_id}" if product_id else "",
        "source": "product.csv",
        "text": text,
        "metadata": metadata,
    }


def _validate_required_columns(df: pd.DataFrame) -> None:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _build_splitter() -> Any:
    if RecursiveCharacterTextSplitter is None:
        raise ImportError(
            "langchain_text_splitters is required to build KB chunks. Install the package before running build_kb.py."
        )

    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )


def _build_embeddings_model() -> Any:
    if GoogleGenerativeAIEmbeddings is None:
        raise ImportError(
            "langchain_google_genai is required to generate embeddings. Install the package before running build_kb.py."
        )

    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL_NAME,
        google_api_key=settings.GOOGLE_API_KEY or None,
    )


def _batch_items(items: Sequence[Any], batch_size: int) -> Iterable[Sequence[Any]]:
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


def _embed_documents_with_retry(embedding_model: Any, batch: Sequence[str]) -> List[List[float]]:
    last_error: Exception | None = None
    for attempt in range(KB_EMBEDDING_MAX_RETRIES):
        try:
            return embedding_model.embed_documents(list(batch))
        except Exception as error:  # noqa: BLE001
            last_error = error
            retry_match = re.search(r"Please retry in ([0-9]+(?:\.[0-9]+)?)s", str(error))
            if retry_match:
                wait_seconds = float(retry_match.group(1)) + 1.0
            else:
                wait_seconds = KB_EMBEDDING_REQUEST_DELAY_SECONDS * (2 ** attempt)
            logging.warning(
                "Embedding batch failed on attempt %d/%d. Waiting %.2fs before retrying. Error: %s",
                attempt + 1,
                KB_EMBEDDING_MAX_RETRIES,
                wait_seconds,
                error,
            )
            time.sleep(wait_seconds)

    if last_error is not None:
        raise last_error
    raise RuntimeError("Embedding failed without an explicit error.")


def _documents_path() -> Path:
    configured = os.getenv("KB_DOCUMENTS_OUTPUT", "")
    if configured:
        return Path(configured)
    return DOCUMENTS_PATH


def _embeddings_path() -> Path:
    configured = os.getenv("KB_EMBEDDINGS_OUTPUT", "")
    if configured:
        return Path(configured)
    return EMBEDDINGS_PATH


def _vector_to_pg_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(f"{float(value):.10f}" for value in vector) + "]"


def _persist_embeddings_to_postgres(embedding_records: List[Dict[str, Any]]) -> int:
    if not embedding_records:
        return 0

    if not POSTGRES_URL:
        logging.warning("POSTGRES_URL is empty. Skipping PostgreSQL persistence.")
        return 0

    if psycopg2 is None or execute_values is None:
        raise ImportError("psycopg2-binary is required to store embeddings in PostgreSQL.")

    table_name = KB_VECTOR_TABLE
    rows = []
    for record in embedding_records:
        vector = record.get("embedding", [])
        if not isinstance(vector, list) or not vector:
            continue

        metadata = record.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        rows.append(
            (
                str(record.get("chunk_id", "")),
                str(record.get("doc_id", "")),
                int(record.get("chunk_index", 0)),
                str(record.get("text", "")),
                json.dumps(metadata, ensure_ascii=False),
                _vector_to_pg_literal(vector),
                str(record.get("source", "product.csv")),
            )
        )

    if not rows:
        return 0

    create_sql = f"""
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE TABLE IF NOT EXISTS {table_name} (
        chunk_id TEXT PRIMARY KEY,
        doc_id TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        metadata JSONB NOT NULL,
        embedding VECTOR({KB_EMBEDDING_DIMENSION}) NOT NULL,
        source TEXT NOT NULL DEFAULT 'product.csv',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """

    upsert_sql = f"""
    INSERT INTO {table_name}
        (chunk_id, doc_id, chunk_index, content, metadata, embedding, source)
    VALUES %s
    ON CONFLICT (chunk_id) DO UPDATE SET
        doc_id = EXCLUDED.doc_id,
        chunk_index = EXCLUDED.chunk_index,
        content = EXCLUDED.content,
        metadata = EXCLUDED.metadata,
        embedding = EXCLUDED.embedding,
        source = EXCLUDED.source,
        updated_at = NOW();
    """

    with psycopg2.connect(POSTGRES_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(create_sql)
            execute_values(
                cursor,
                upsert_sql,
                rows,
                template="(%s,%s,%s,%s,%s::jsonb,%s::vector,%s)",
                page_size=500,
            )
        connection.commit()

    logging.info("Stored %d embedding rows into PostgreSQL table %s", len(rows), table_name)
    return len(rows)


def build_kb() -> Dict[str, Any]:
    """Build KB artifacts from CSV files and save documents plus embeddings."""
    setup_logging()

    combined_df = concatenate_dataframes()
    if combined_df.empty:
        logging.warning("No data available to build KB.")
        return {"documents": 0, "chunks": 0, "output_path": None}

    _validate_required_columns(combined_df)

    splitter = _build_splitter()
    embedding_model = _build_embeddings_model()

    documents: List[Dict[str, Any]] = []
    embedding_records: List[Dict[str, Any]] = []
    all_chunk_texts: List[str] = []
    chunk_index_records: List[Dict[str, Any]] = []

    for _, row in combined_df.iterrows():
        document = _row_to_product_document(row)
        if not document["doc_id"] or not document["text"]:
            continue

        chunks = splitter.split_text(document["text"])
        chunk_items: List[Dict[str, Any]] = []

        for chunk_index, chunk_text in enumerate(chunks):
            chunk_id = f"{document['doc_id']}_chunk_{chunk_index}"
            chunk_item = {
                "chunk_id": chunk_id,
                "chunk_index": chunk_index,
                "text": chunk_text,
                "token_hint": len(chunk_text.split()),
            }
            chunk_items.append(chunk_item)
            all_chunk_texts.append(chunk_text)
            chunk_index_records.append(
                {
                    "doc_id": document["doc_id"],
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index,
                    "metadata": document["metadata"],
                }
            )

        document["chunks"] = chunk_items
        document["chunk_count"] = len(chunk_items)
        documents.append(document)

    if all_chunk_texts:
        logging.info("Creating embeddings for %d chunks.", len(all_chunk_texts))
        batch_size = max(1, KB_EMBEDDING_BATCH_SIZE)
        chunk_vectors: List[List[float]] = []
        for batch_index, batch in enumerate(_batch_items(all_chunk_texts, batch_size), start=1):
            vectors = _embed_documents_with_retry(embedding_model, batch)
            chunk_vectors.extend(vectors)
            logging.info(
                "Embedded batch %d, size %d, total vectors %d",
                batch_index,
                len(batch),
                len(chunk_vectors),
            )
            if KB_EMBEDDING_REQUEST_DELAY_SECONDS > 0:
                time.sleep(KB_EMBEDDING_REQUEST_DELAY_SECONDS)

        for record, vector, text in zip(chunk_index_records, chunk_vectors, all_chunk_texts):
            embedding_records.append(
                {
                    **record,
                    "text": text,
                    "embedding": vector,
                }
            )

    documents_path = _documents_path()
    embeddings_path = _embeddings_path()

    documents_path.parent.mkdir(parents=True, exist_ok=True)
    embeddings_path.parent.mkdir(parents=True, exist_ok=True)

    with documents_path.open("w", encoding="utf-8") as file:
        json.dump(documents, file, ensure_ascii=False, indent=2)

    with embeddings_path.open("w", encoding="utf-8") as file:
        json.dump(embedding_records, file, ensure_ascii=False, indent=2)

    postgres_rows = _persist_embeddings_to_postgres(embedding_records)

    logging.info("Built KB with %d documents and %d chunks.", len(documents), len(embedding_records))
    logging.info("Documents output: %s", documents_path)
    logging.info("Embeddings output: %s", embeddings_path)
    if postgres_rows:
        logging.info("PostgreSQL rows written: %d", postgres_rows)

    return {
        "documents": len(documents),
        "chunks": len(embedding_records),
        "documents_path": str(documents_path),
        "embeddings_path": str(embeddings_path),
        "postgres_rows": postgres_rows,
    }


if __name__ == "__main__":
    result = build_kb()
    logging.info("Build KB result: %s", result)
