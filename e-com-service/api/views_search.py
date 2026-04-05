"""Search proxy view — Django REST Framework.

Replaces api/search.py (FastAPI router).
Forwards rich search payloads to search-service via HTTP.
"""

from __future__ import annotations

import json
import logging
from urllib import error, request as urlrequest

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.config import settings


logger = logging.getLogger(__name__)


class SearchProxyView(APIView):
    """Search proxy endpoint — POST /search."""

    def post(self, request: Request) -> Response:
        if not settings.SEARCH_SERVICE_URL:
            return Response(
                {"detail": "SEARCH_SERVICE_URL is not configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        payload = {
            "query": request.data.get("query") or "",
            "filters": request.data.get("filters") or {},
            "sort": request.data.get("sort") or {"field": "relevance", "order": "desc"},
            "pagination": request.data.get("pagination") or {"page": 1, "size": 10},
        }

        body = json.dumps(payload).encode("utf-8")
        req_obj = urlrequest.Request(
            settings.SEARCH_SERVICE_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlrequest.urlopen(
                req_obj, timeout=settings.SEARCH_SERVICE_TIMEOUT_SECONDS
            ) as resp:
                response_text = resp.read().decode("utf-8")
                if not response_text.strip():
                    return Response({})
                return Response(json.loads(response_text))
        except error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="ignore")
            return Response(
                {"detail": error_body or "search-service HTTP error"},
                status=exc.code,
            )
        except error.URLError as exc:
            return Response(
                {"detail": f"search-service unavailable: {exc.reason}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except TimeoutError:
            return Response(
                {"detail": "search-service timeout"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except json.JSONDecodeError:
            return Response(
                {"detail": "search-service returned invalid JSON"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
