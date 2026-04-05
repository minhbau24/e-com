"""Search service orchestration."""

from __future__ import annotations

import logging
from math import ceil
from typing import Any

from db.connection import DatabaseError, get_connection
from db.queries import build_generated_search_sql, build_llm_context
from models.search import SearchPagination, SearchProduct, SearchRequest, SearchResponse


class SearchServiceError(RuntimeError):
    """Raised when the search request cannot be processed."""


logger = logging.getLogger(__name__)


def _extract_total_from_count_row(count_row: Any) -> int:
    """Extract the row count from different COUNT(*) result shapes."""
    if count_row is None:
        return 0

    if isinstance(count_row, dict):
        if "total" in count_row:
            return int(count_row["total"])

        keys = list(count_row.keys())
        if keys:
            first_key = keys[0]
            logger.warning(
                "[search_service] count alias missing total | keys=%s | using=%s",
                keys,
                first_key,
            )
            return int(count_row[first_key])
        return 0

    if hasattr(count_row, "keys"):
        keys = list(count_row.keys())
        if "total" in keys:
            return int(count_row["total"])
        if keys:
            first_key = keys[0]
            logger.warning(
                "[search_service] count alias missing total | keys=%s | using=%s",
                keys,
                first_key,
            )
            return int(count_row[first_key])

    if isinstance(count_row, (list, tuple)) and count_row:
        return int(count_row[0])

    return int(count_row)


class SearchService:
    """Search product catalog data for downstream LLM use."""

    def search(self, request: SearchRequest) -> SearchResponse:
        logger.info(
            "[search_service] start | query=%s | filters=%s | sort=%s | page=%s | size=%s",
            request.query,
            request.filters.model_dump(),
            request.sort.model_dump(),
            request.pagination.page,
            request.pagination.size,
        )

        select_sql, count_sql, params = build_generated_search_sql(request)
        logger.info(
            "[search_service] sql_ready | select_len=%d | count_len=%d | params=%s",
            len(select_sql),
            len(count_sql),
            sorted(params.keys()),
        )
        try:
            with get_connection() as connection:
                with connection.cursor() as cursor:
                    logger.info("[search_service] executing count query")
                    cursor.execute(count_sql, params)
                    count_row = cursor.fetchone() or {"total": 0}
                    logger.info(
                        "[search_service] count_row | keys=%s | row=%s",
                        list(count_row.keys()) if hasattr(count_row, "keys") else type(count_row).__name__,
                        count_row,
                    )
                    total = _extract_total_from_count_row(count_row)
                    logger.info("[search_service] count_total | total=%d", total)

                    logger.info("[search_service] executing select query")
                    cursor.execute(select_sql, params)
                    rows = cursor.fetchall() or []
        except DatabaseError as exc:
            logger.exception("[search_service] database error | error=%s", exc)
            raise SearchServiceError(str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive wrapper
            logger.exception("[search_service] unexpected error | error=%s", exc)
            raise SearchServiceError(f"Search execution failed: {exc}") from exc

        items = [self._row_to_product(row) for row in rows]
        total_pages = ceil(total / request.pagination.size) if total else 0
        pagination = SearchPagination(
            page=request.pagination.page,
            size=request.pagination.size,
            total=total,
            total_pages=total_pages,
        )

        llm_context = build_llm_context([item.model_dump() for item in items], total, request)
        logger.info(
            "[search_service] done | total=%d | returned=%d | total_pages=%d | context_len=%d",
            total,
            len(items),
            total_pages,
            len(llm_context),
        )
        return SearchResponse(
            query=request.query,
            filters=request.filters,
            sort=request.sort,
            pagination=pagination,
            total=total,
            items=items,
            llm_context=llm_context,
        )

    @staticmethod
    def _row_to_product(row: dict[str, Any]) -> SearchProduct:
        return SearchProduct(**row)
