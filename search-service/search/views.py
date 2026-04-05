"""Search API views — Django REST Framework.

Replaces the FastAPI router in api/search.py.
Business logic is unchanged: delegates to SearchService which uses
raw psycopg2 + optional LLM SQL generation.
"""

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from models.search import SearchFilters, SearchPagination, SearchRequest, SearchSort
from services.search_service import SearchService, SearchServiceError


logger = logging.getLogger(__name__)
_service = SearchService()


class HealthView(APIView):
    """Health-check endpoint — GET /health."""

    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})


class SearchView(APIView):
    """Product search endpoint — POST /search."""

    def post(self, request: Request) -> Response:
        data = request.data

        try:
            filters_data = data.get("filters") or {}
            sort_data = data.get("sort") or {}
            pagination_data = data.get("pagination") or {}

            search_request = SearchRequest(
                query=data.get("query") or "",
                filters=SearchFilters(**filters_data),
                sort=SearchSort(**sort_data),
                pagination=SearchPagination(**pagination_data),
            )
        except Exception as exc:
            return Response(
                {"detail": f"Invalid request payload: {exc}"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        logger.info(
            "[api.search] received | query=%s | filters=%s | sort=%s | page=%s | size=%s",
            search_request.query,
            search_request.filters.model_dump(),
            search_request.sort.model_dump(),
            search_request.pagination.page,
            search_request.pagination.size,
        )

        try:
            result = _service.search(search_request)
            return Response(result.model_dump())
        except SearchServiceError as exc:
            logger.exception("[api.search] search failed | error=%s", exc)
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("[api.search] unexpected error | error=%s", exc)
            return Response(
                {"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
