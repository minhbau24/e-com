"""Health view — Django REST Framework."""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Health-check endpoint — GET /health."""

    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})
