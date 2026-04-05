"""Recommend view — Django REST Framework.

Replaces api/recommend.py (FastAPI router).
Returns product recommendations from search-service or CSV fallback.
"""

from __future__ import annotations

import logging

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from services.db_service import search_products


logger = logging.getLogger(__name__)

_DEFAULT_QUERY = "sách kiến trúc"


class RecommendView(APIView):
    """Recommendation endpoint — GET /recommend/<user_id>."""

    def get(self, request: Request, user_id: str) -> Response:
        query: str = request.query_params.get("query") or _DEFAULT_QUERY
        if not query.strip():
            query = _DEFAULT_QUERY

        logger.info(
            "[api.recommend] request | user_id=%s | query=%s", user_id, query
        )

        items = search_products(query=query, limit=10)
        return Response({"user_id": user_id, "query": query, "items": items})
