"""SQL builders for product search."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from typing import Any

try:
    from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    HumanMessage = None
    SystemMessage = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    ChatGoogleGenerativeAI = None

from utils.config import settings
from models.search import SearchRequest


logger = logging.getLogger(__name__)


SORTABLE_FIELDS = {
    "relevance": "relevance",
    "price": "price",
    "rating": "rating",
    "review_count": "review_count",
    "stock": "stock",
    "created_at": "created_at",
    "publication_year": "publication_year",
    "page_count": "page_count",
    "name": "name",
}

ALLOWED_SQL_COLUMNS = {
    "product_id",
    "name",
    "normalized_name",
    "price",
    "rating",
    "review_count",
    "stock",
    "category",
    "content",
    "author",
    "publisher",
    "publication_year",
    "language",
    "cover_type",
    "page_count",
    "created_at",
    "relevance_score",
}

FORBIDDEN_SQL_PATTERNS = (
    ";",
    "INSERT ",
    "UPDATE ",
    "DELETE ",
    "DROP ",
    "ALTER ",
    "TRUNCATE ",
    "CREATE ",
    "GRANT ",
    "REVOKE ",
    "MERGE ",
)


def normalize_text(value: str) -> str:
    """Fold accents and lowercase for better keyword matching."""
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    without_punctuation = re.sub(r"[^\w\s]", " ", without_accents.lower())
    return " ".join(without_punctuation.split())


def _add_condition(conditions: list[str], params: dict[str, Any], clause: str, **values: Any) -> None:
    conditions.append(clause)
    params.update(values)


def _default_query_params(request: SearchRequest) -> dict[str, Any]:
    params: dict[str, Any] = {}
    query = request.query.strip()
    params["has_query"] = bool(query)
    params["query_like"] = f"%{query}%" if query else "%%"
    params["normalized_query_like"] = f"%{normalize_text(query)}%" if query else "%%"
    params["limit"] = request.pagination.size
    params["offset"] = (request.pagination.page - 1) * request.pagination.size

    filters = request.filters
    if filters.price_min is not None:
        params["price_min"] = filters.price_min
    if filters.price_max is not None:
        params["price_max"] = filters.price_max
    if filters.author:
        params["author"] = f"%{filters.author}%"
    if filters.publisher:
        params["publisher"] = f"%{filters.publisher}%"
    if filters.publication_year_min is not None:
        params["publication_year_min"] = filters.publication_year_min
    if filters.publication_year_max is not None:
        params["publication_year_max"] = filters.publication_year_max
    if filters.language:
        params["language"] = f"%{filters.language}%"
    if filters.cover_type:
        params["cover_type"] = f"%{filters.cover_type}%"
    if filters.page_count_min is not None:
        params["page_count_min"] = filters.page_count_min
    if filters.page_count_max is not None:
        params["page_count_max"] = filters.page_count_max
    if filters.in_stock is True:
        params["in_stock"] = True
    elif filters.in_stock is False:
        params["in_stock"] = False

    logger.info(
        "[search_sql] base_params | query=%s | normalized_query=%s | has_query=%s | filters=%s | page=%s | size=%s",
        query,
        normalize_text(query) if query else "",
        params["has_query"],
        request.filters.model_dump(),
        request.pagination.page,
        request.pagination.size,
    )

    return params


def _extract_json_block(text: str) -> dict[str, Any] | None:
    text = text.strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _is_safe_sql(sql: str) -> bool:
    normalized = " ".join(sql.strip().split())
    upper = normalized.upper()
    if not upper.startswith("SELECT"):
        return False
    if "FROM SEARCH_PRODUCTS" not in upper:
        return False
    if any(pattern in upper for pattern in FORBIDDEN_SQL_PATTERNS):
        return False
    return True


def _collect_placeholders(sql: str) -> set[str]:
    return set(re.findall(r"%\(([^)]+)\)s", sql))


def _sanitize_sql_payload(payload: dict[str, Any], base_params: dict[str, Any]) -> tuple[str, str, dict[str, Any]] | None:
    select_sql = str(payload.get("select_sql", "")).strip()
    count_sql = str(payload.get("count_sql", "")).strip()
    raw_params = payload.get("params", {}) if isinstance(payload.get("params", {}), dict) else {}

    if not select_sql or not count_sql:
        return None
    if not _is_safe_sql(select_sql) or not _is_safe_sql(count_sql):
        return None

    placeholders = _collect_placeholders(select_sql) | _collect_placeholders(count_sql)
    params = dict(base_params)

    for key, value in raw_params.items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(key)):
            return None
        if isinstance(value, (str, int, float, bool)) or value is None:
            params[str(key)] = value
        else:
            return None

    missing = placeholders - set(params.keys())
    if missing:
        return None

    return select_sql, count_sql, params


def _build_llm_sql_request(request: SearchRequest, base_params: dict[str, Any]) -> tuple[str, str, dict[str, Any]] | None:
    if not settings.SEARCH_SQL_GENERATION_ENABLED:
        logger.info("[search_sql] generation_disabled | fallback=deterministic")
        return None
    if ChatGoogleGenerativeAI is None or HumanMessage is None or SystemMessage is None:
        logger.info("[search_sql] llm_dependencies_missing | fallback=deterministic")
        return None
    if not settings.GOOGLE_API_KEY:
        logger.info("[search_sql] google_api_key_missing | fallback=deterministic")
        return None

    schema_description = """
Table: search_products
Columns: product_id, name, normalized_name, price, rating, review_count, stock, category,
content, author, publisher, publication_year, language, cover_type, page_count, created_at.

Rules:
- Return JSON only with keys: select_sql, count_sql, params.
- Generate READ-ONLY PostgreSQL SQL only.
- Use only SELECT queries against search_products.
- Use named placeholders with psycopg2 style, for example %(query_like)s.
- You may use extra semantic search terms in params such as term_1, term_2, term_3 if helpful.
- Keep queries safe: no joins, no subqueries unless essential, no semicolon, no DDL/DML.
- The select query must include an ORDER BY and LIMIT/OFFSET.
- The count query must count the same WHERE clause and must not include LIMIT/OFFSET.
- The count query MUST be exactly in form `SELECT COUNT(*) AS total FROM ...` (alias bắt buộc là total).
- The select query MUST include these columns for API contract compatibility:
    product_id, name, normalized_name, price, rating, review_count, stock, category,
    content, author, publisher, publication_year, language, cover_type, page_count,
    created_at.
- The select query SHOULD include a numeric expression aliased as relevance_score.
- Prefer broad matching for product discovery queries; for example, a query like "sách kiến trúc" can search terms such as "kiến trúc" and "architecture".
- Do NOT overfit to the full original sentence (for example "%Cho tôi sách ...%"), use discriminative terms and filters instead.
- If a strong structured filter exists (e.g. author/publisher/language/cover_type), prioritize that filter and avoid generic full-text conditions.
- If sort field is relevance, include stable secondary sort: rating DESC, review_count DESC, created_at DESC.
""".strip()

    system_prompt = (
        "Bạn là bộ sinh SQL cho PostgreSQL. "
        "Mục tiêu: tạo truy vấn tìm kiếm sản phẩm an toàn, chính xác, và có tính ngữ nghĩa tốt. "
        "Chỉ trả về JSON hợp lệ, không markdown, không giải thích."
    )
    user_prompt = json.dumps(
        {
            "request": request.model_dump(),
            "available_params": base_params,
            "schema": schema_description,
            "examples": {
                "author_query_good": {
                    "input": "Cho toi sach cua tac gia Claudia Martinez Alonso",
                    "select_sql": "SELECT product_id, name, normalized_name, price, rating, review_count, stock, category, content, author, publisher, publication_year, language, cover_type, page_count, created_at, (COALESCE(rating, 0) * 2 + LN(COALESCE(review_count, 0) + 1)) AS relevance_score FROM search_products WHERE author ILIKE %(author)s ORDER BY relevance_score DESC, rating DESC, review_count DESC, created_at DESC LIMIT %(limit)s OFFSET %(offset)s",
                    "count_sql": "SELECT COUNT(*) AS total FROM search_products WHERE author ILIKE %(author)s",
                    "params": {"author": "%Claudia Martinez Alonso%"},
                },
                "author_query_bad": {
                    "reason": "Sai vi count khong alias total va/hoac select thieu cot API contract",
                    "select_sql": "SELECT product_id, name, price, rating, author FROM search_products WHERE author ILIKE %(author)s ORDER BY rating DESC LIMIT %(limit)s OFFSET %(offset)s",
                    "count_sql": "SELECT COUNT(*) FROM search_products WHERE author ILIKE %(author)s",
                },
            },
        },
        ensure_ascii=False,
    )

    try:
        logger.info("[search_sql] llm_generation_start | model=%s | query=%s", settings.SEARCH_SQL_MODEL, request.query)
        llm = ChatGoogleGenerativeAI(
            model=settings.SEARCH_SQL_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0,
        )
        response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
        content = response.content if hasattr(response, "content") else str(response)
        parsed = _extract_json_block(content)
        if isinstance(parsed, dict):
            sanitized = _sanitize_sql_payload(parsed, base_params)
            if sanitized is not None:
                logger.info(
                    "[search_sql] llm_generation_success | select_len=%d | count_len=%d | params=%s",
                    len(sanitized[0]),
                    len(sanitized[1]),
                    sorted(sanitized[2].keys()),
                )
                logger.info(
                    "[search_sql] llm_generated_sql | select_sql=%s | count_sql=%s | params=%s",
                    sanitized[0],
                    sanitized[1],
                    sanitized[2],
                )
                return sanitized
        logger.warning("[search_sql] llm_generation_invalid | fallback=deterministic")
    except Exception:
        logger.exception("[search_sql] llm_generation_error | fallback=deterministic")
        return None

    return None


def build_where_clause(request: SearchRequest) -> tuple[str, dict[str, Any]]:
    conditions: list[str] = []
    params: dict[str, Any] = {}

    query = request.query.strip()
    if query:
        query_like = f"%{query}%"
        normalized_query = normalize_text(query)
        normalized_query_like = f"%{normalized_query}%"
        conditions.append(
            "("
            + " OR ".join(
                [
                    "name ILIKE %(query_like)s",
                    "normalized_name ILIKE %(normalized_query_like)s",
                    "category ILIKE %(query_like)s",
                    "content ILIKE %(query_like)s",
                    "author ILIKE %(query_like)s",
                    "publisher ILIKE %(query_like)s",
                    "language ILIKE %(query_like)s",
                    "cover_type ILIKE %(query_like)s",
                ]
            )
            + ")"
        )
        params["query_like"] = query_like
        params["normalized_query_like"] = normalized_query_like

    filters = request.filters
    if filters.price_min is not None:
        _add_condition(conditions, params, "price >= %(price_min)s", price_min=filters.price_min)
    if filters.price_max is not None:
        _add_condition(conditions, params, "price <= %(price_max)s", price_max=filters.price_max)
    if filters.author:
        _add_condition(conditions, params, "author ILIKE %(author)s", author=f"%{filters.author}%")
    if filters.publisher:
        _add_condition(conditions, params, "publisher ILIKE %(publisher)s", publisher=f"%{filters.publisher}%")
    if filters.publication_year_min is not None:
        _add_condition(
            conditions,
            params,
            "publication_year >= %(publication_year_min)s",
            publication_year_min=filters.publication_year_min,
        )
    if filters.publication_year_max is not None:
        _add_condition(
            conditions,
            params,
            "publication_year <= %(publication_year_max)s",
            publication_year_max=filters.publication_year_max,
        )
    if filters.language:
        _add_condition(conditions, params, "language ILIKE %(language)s", language=f"%{filters.language}%")
    if filters.cover_type:
        _add_condition(conditions, params, "cover_type ILIKE %(cover_type)s", cover_type=f"%{filters.cover_type}%")
    if filters.page_count_min is not None:
        _add_condition(conditions, params, "page_count >= %(page_count_min)s", page_count_min=filters.page_count_min)
    if filters.page_count_max is not None:
        _add_condition(conditions, params, "page_count <= %(page_count_max)s", page_count_max=filters.page_count_max)
    if filters.in_stock is True:
        conditions.append("stock > 0")
    elif filters.in_stock is False:
        conditions.append("COALESCE(stock, 0) <= 0")

    if not conditions:
        return "", params

    return "WHERE " + " AND ".join(conditions), params


def build_order_by_clause(request: SearchRequest) -> str:
    field = request.sort.field if request.sort.field in SORTABLE_FIELDS else "relevance"
    order = request.sort.order.upper() if request.sort.order.upper() in {"ASC", "DESC"} else "DESC"

    if field == "relevance":
        return (
            "ORDER BY "
            "(" 
            "CASE WHEN %(has_query)s THEN "
            "(CASE WHEN normalized_name ILIKE %(normalized_query_like)s THEN 100 ELSE 0 END + "
            "CASE WHEN name ILIKE %(query_like)s THEN 50 ELSE 0 END + "
            "CASE WHEN category ILIKE %(query_like)s THEN 20 ELSE 0 END + "
            "CASE WHEN content ILIKE %(query_like)s THEN 10 ELSE 0 END) "
            "ELSE 0 END + "
            "COALESCE(rating, 0) * 2 + LN(COALESCE(review_count, 0) + 1)"
            ") DESC, rating DESC, review_count DESC, created_at DESC"
        )

    return f"ORDER BY {SORTABLE_FIELDS[field]} {order}, created_at DESC"


def build_score_expression() -> str:
    return (
        "(" 
        "CASE WHEN %(has_query)s THEN "
        "(CASE WHEN normalized_name ILIKE %(normalized_query_like)s THEN 100 ELSE 0 END + "
        "CASE WHEN name ILIKE %(query_like)s THEN 50 ELSE 0 END + "
        "CASE WHEN category ILIKE %(query_like)s THEN 20 ELSE 0 END + "
        "CASE WHEN content ILIKE %(query_like)s THEN 10 ELSE 0 END) "
        "ELSE 0 END + "
        "COALESCE(rating, 0) * 2 + LN(COALESCE(review_count, 0) + 1)"
        ")"
    )


def build_search_sql(request: SearchRequest) -> tuple[str, str, dict[str, Any]]:
    where_clause, params = build_where_clause(request)
    params["has_query"] = bool(request.query.strip())
    params.setdefault("query_like", "%%")
    params.setdefault("normalized_query_like", "%%")
    params["limit"] = request.pagination.size
    params["offset"] = (request.pagination.page - 1) * request.pagination.size

    logger.info(
        "[search_sql] deterministic_params | query_like=%s | normalized_query_like=%s | has_query=%s | limit=%s | offset=%s",
        params.get("query_like"),
        params.get("normalized_query_like"),
        params.get("has_query"),
        params.get("limit"),
        params.get("offset"),
    )

    score_expression = build_score_expression()
    order_by_clause = build_order_by_clause(request)

    select_sql = f"""
        SELECT
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
            created_at,
            {score_expression} AS relevance_score
        FROM {settings.SEARCH_PRODUCTS_TABLE}
        {where_clause}
        {order_by_clause}
        LIMIT %(limit)s OFFSET %(offset)s
    """

    count_sql = f"SELECT COUNT(*) AS total FROM {settings.SEARCH_PRODUCTS_TABLE} {where_clause}"

    logger.info(
        "[search_sql] deterministic_sql_ready | select_len=%d | count_len=%d | where_present=%s",
        len(select_sql),
        len(count_sql),
        bool(where_clause),
    )
    return select_sql, count_sql, params


def build_generated_search_sql(request: SearchRequest) -> tuple[str, str, dict[str, Any]]:
    base_params = _default_query_params(request)
    generated = _build_llm_sql_request(request, base_params)
    if generated is not None:
        logger.info("[search_sql] path=llm")
        return generated

    logger.info("[search_sql] path=fallback_deterministic")
    return build_search_sql(request)


def build_llm_context(items: list[dict[str, Any]], total: int, request: SearchRequest) -> str:
    lines = [
        f"Query: {request.query or '(empty)'}",
        f"Total matches: {total}",
        f"Returned: {len(items)}",
    ]
    for index, item in enumerate(items, start=1):
        parts = [
            f"{index}. {item.get('name')}",
            f"price={item.get('price')}",
            f"rating={item.get('rating')}",
            f"reviews={item.get('review_count')}",
            f"stock={item.get('stock')}",
            f"category={item.get('category')}",
        ]
        if item.get("author"):
            parts.append(f"author={item.get('author')}")
        if item.get("publisher"):
            parts.append(f"publisher={item.get('publisher')}")
        if item.get("publication_year") is not None:
            parts.append(f"year={item.get('publication_year')}")
        if item.get("language"):
            parts.append(f"language={item.get('language')}")
        if item.get("cover_type"):
            parts.append(f"cover={item.get('cover_type')}")
        if item.get("page_count") is not None:
            parts.append(f"pages={item.get('page_count')}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)
