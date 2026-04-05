"""Track view — Django REST Framework.

Replaces api/track.py (FastAPI router).
Behavior tracking is intentionally disabled in this build variant.
"""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class TrackView(APIView):
    """Tracking endpoint — POST /track (disabled)."""

    def post(self, request: Request) -> Response:
        return Response(
            {
                "status": "disabled",
                "message": "Behavior tracking is excluded in this build.",
            }
        )
