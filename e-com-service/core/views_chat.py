"""Chat view — Django REST Framework.

Replaces api/chat.py (FastAPI router).
Delegates to services.rag_service.run_chat (LangGraph pipeline).
"""

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from services.rag_service import run_chat


logger = logging.getLogger(__name__)


class ChatView(APIView):
    """Chatbot endpoint — POST /chat."""

    def post(self, request: Request) -> Response:
        data = request.data
        user_id: str = data.get("user_id") or "anonymous"
        query: str = data.get("query") or ""
        debug: bool = bool(data.get("debug", False))

        if not user_id:
            return Response(
                {"detail": "user_id must not be empty"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if not query:
            return Response(
                {"detail": "query must not be empty"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        logger.info(
            "[api.chat] request | user_id=%s | debug=%s | query=%s",
            user_id,
            debug,
            query[:160],
        )

        try:
            result = run_chat(query=query, user_id=user_id, debug=debug)
            if result.get("error"):
                logger.error(
                    "[api.chat] graph error | user_id=%s | error=%s",
                    user_id,
                    result.get("error"),
                )
                return Response(
                    {"detail": str(result["error"])},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            logger.info(
                "[api.chat] response | user_id=%s | intent=%s",
                user_id,
                result.get("intent"),
            )
            return Response(result)
        except Exception as exc:
            logger.exception(
                "[api.chat] unexpected error | user_id=%s | error=%s", user_id, exc
            )
            return Response(
                {"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
